#!/usr/bin/env python3
"""record.py [--source <原始 run record.json>] [--migration-audit <audit.json>] \
          [--validate-only] \
          <run-dir> <run-id> <manifest.json> <fixtures.json> [<routing-fixtures.json> ...]

`--validate-only` 只跑 provenance 檢查後結束，不寫任何紀錄、不花任何錢。
重新評分前先跑它：所有會讓整輪變成 INVALID 的條件（來源紀錄、trace digest、
subject hash 格式、migration audit、contract manifest）都在這裡判得出來，
沒有理由等付費 judge 跑完才發現。

產生 run record：`<run-dir>/<run-id>.json` 與 `.md`。

**這份檔案的用途是讓第三方能重算、能比對。** 因此每個數字都必須可回溯：
逐筆判定取自 raw trace 與 `.judge.json`，成本取自 session 自己回報的 `total_cost_usd`。
沒有實測來源的欄位一律寫 null，不以推估補完。

## 版本綁定為什麼改由 manifest 提供

v2 是在這裡現算 hash。那個值回答的是「錄紀錄的當下 repo 長什麼樣」，而不是
「這輪 subject session 跑在什麼版本上」——run 期間任何一次編輯都會讓兩者分歧，
而且分歧完全不可見。v3 改成 `manifest.py` 在 run 開始前量一次、跑完再量一次，
本檔**只讀不算**，並比對兩次：

  - manifest 缺失、壞損、缺 start 或 end                → INVALID
  - `manifest_version` 缺失或不是支援的值               → INVALID
  - start／end 的 domain 集合不是**恰好** REQUIRED_DOMAINS → INVALID
  - `hash_schema` 缺失／空值／格式不合法／前後不一致    → INVALID
  - 任一 domain hash 缺失、格式不合法或前後不同（drift）→ INVALID
  - trace manifest 缺失，或 raw trace 與其對不上        → INVALID
  - post-judge manifest 缺失，或 `.judge.json` 與其對不上 → INVALID

全部 fail-closed：此時已無法斷定 observation 對應哪一個版本，
把它記成 PASS／FAIL 等於宣稱一件無法成立的事。

**為什麼要求「恰好」而不是「至少」。** 只檢查前後一致的話，一份只含 `fixtures` 一個
domain 的 manifest 會完美通過比對——start 等於 end，沒有 drift，於是整輪記成有效證據，
而 skill、runner、evaluator、兩個 context 全都沒有版本綁定。少量到看不出來的紀錄比
沒有紀錄更危險，因為它看起來像有。多出未知 domain 同樣擋掉：那代表產生 manifest 的
工具與本檔對「要量什麼」的認知已經不同，此時任何比對結論都不可信。

## 重新評分既有 run（`--source`）

evaluator 或 evaluation-context 變更後，保留的 raw trace 可以重新評分而不重跑付費
subject session。**derived record 的 identity 由兩半組成，各有各的來源：**

| 半邊 | domain | 取自 |
|---|---|---|
| subject identity | skill × 3、`runner`、`fixtures`、`execution_context` | **來源 run 的紀錄** |
| contract identity | `evaluator`、`evaluation_context` | **本次現量**（contract manifest） |

先前把整份 identity 都從傳入的 manifest 取，結果有兩個：v3 來源的 manifest 少一個
`evaluation_context`，必定被 `REQUIRED_DOMAINS` 擋掉；而 `rescored_with.evaluator`
拿到的是**來源 run 的** evaluator，不是「現在的」——正好與它宣稱的意思相反。

那份 trace 是在來源版本下產生的，此刻重量 skill／fixtures／runner 得到的是與該 trace
無關的值。因此重評要傳的是 `manifest.py contract-snapshot` 產生的 **contract manifest**
（只含兩個 contract domain），subject 那半由 `--source` 的紀錄提供。

四個硬性要求，全部在此實作：

  1. 現在這份 trace manifest 的 deterministic digest，必須等於**原始 run record** 保存的
     `provenance.trace_manifest_digest`。逐檔比對抓不到「改 trace 再重建一份自洽 manifest」，
     只有跟原始紀錄比 digest 才抓得到。
  2. **不得覆寫原始 run record。** 輸出路徑與來源相同時直接拒絕，不寫任何檔案。
  3. 來源紀錄必須提供全部六個 subject domain 的 hash；缺任何一個就沒有 subject 綁定。
  4. **跨 schema 不得直接比較 hash。** 來源與現行 `hash_schema` 不同時，必須另附
     `--migration-audit`：一份獨立的內容等價稽核，說明那些 subject domain 在兩個 schema
     下指的是不是同一份內容。沒有它就只能宣稱「值不同」，而值不同在跨 schema 下**必然**
     成立，什麼都證明不了。

環境變數（由 run-suite.sh 傳入，缺了就記 null）：
  HARNESS_RUN_STARTED / HARNESS_RUN_ENDED   epoch 秒
  HARNESS_SUBJECT_MODEL / HARNESS_JUDGE_MODEL
  HARNESS_CLI_FAILED                        CLI 失敗筆數
"""
import datetime, hashlib, json, os, re, subprocess, sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE, "..", "..", ".."))
HASH_REL = "scripts/bundle-hash.sh"

SCHEMA_RE = re.compile(r"^v[1-9][0-9]*$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
TRACE_SUFFIXES = (".jsonl", ".meta.json")

# run manifest 文件本身的 schema 版本（與 hash_schema 是兩回事）。v3 要求 context 分項 hash。
SUPPORTED_MANIFEST_VERSIONS = (3,)
POST_JUDGE_MANIFEST_VERSION = 1

# **恰好**要有這些 domain，不多不少。缺一個代表那部分沒有版本綁定；多一個代表產生
# manifest 的工具與本檔對「要量什麼」的認知已經不同。兩種情況下比對結論都不可信。
REQUIRED_DOMAINS = frozenset((
    "dispatch_skill",
    "judgment_skill",
    "token_preflight_skill",
    "evaluator",
    "runner",
    "fixtures",
    "execution_context",
    "evaluation_context",
))

# 判定端的 domain。重新評分時只有這一半是「現在」量的，另一半來自來源 run 的紀錄。
# `contract_fixtures` 是 v5 新增：judge 用的是**現在**這份 fixture 檔的
# required_elements／forbidden_elements，沿用來源的 `fixtures` hash 會讓紀錄宣稱一份
# 不是判定依據的檔案。它不屬於 full manifest——原生 run 的 fixtures 本來就是同一份。
CONTRACT_DOMAINS = frozenset((
    "evaluator", "evaluation_context", "contract_fixtures",
    # 編排腳本決定 derived 判定寫到哪裡、以什麼順序驗證，兩者都直接影響可信度。
    "rescore_runner",
))
SUBJECT_DOMAINS = REQUIRED_DOMAINS - frozenset(("evaluator", "evaluation_context"))

# manifest 的兩種形態：原生 run 用 full，重新評分用 contract。
MANIFEST_KINDS = {"full": REQUIRED_DOMAINS, "contract": CONTRACT_DOMAINS}
CONTEXT_COMPONENTS = {
    "full": {
        "execution_context": frozenset(("rules", "settings", "descriptor")),
        "evaluation_context": frozenset(("descriptor",)),
    },
    "contract": {
        "evaluation_context": frozenset(("descriptor",)),
    },
}

# 原始 trace manifest 是不是在 subject 迴圈結束當下產生的。
# 「事後補一份」只能證明**目前檔案**的內容，不能證明它從產生到現在沒被改過——
# 那兩件事在證據強度上差很多，因此分開記，並決定這份紀錄能不能算契約證據。
TRACE_ORIGIN_CONTEMPORANEOUS = "contemporaneous"
NONCE_RE = re.compile(r"^[0-9a-f]{32}$")


def check_nonce_chain(manifest, trace_manifest, outdir):
    """核對 run nonce 的四方一致性，回傳 (origin, notes)。

    先前這件事是由一個環境變數宣告的（`HARNESS_TRACE_MANIFEST_ORIGIN`），而本檔直接
    採信。那不是證明，是自述：對任何事後湊出來的目錄設一次環境變數，就能得到
    `evidence_class: contract_evidence`——實測確實如此。

    現在要求 manifest 的 `run_nonce`、trace manifest 的 `run_nonce`、以及**每一份**
    `.meta.json` 的 `run_nonce` 三方相同。nonce 由 `snapshot start` 在跑任何 session
    之前產生，subject session 各自把它寫進自己的 meta。

    這擋不住一個能同時改寫全部四樣東西的人——沒有外部錨定（commit、可信封存）的方案
    都擋不住。它擋掉的是「補一份 manifest 或設一個環境變數就升格」。
    """
    notes = []
    nonce = (manifest or {}).get("run_nonce")
    if not (isinstance(nonce, str) and NONCE_RE.match(nonce or "")):
        return "unknown", ["run manifest 沒有合法的 run_nonce"]
    tnonce = (trace_manifest or {}).get("run_nonce")
    if tnonce != nonce:
        return "unknown", [f"trace manifest 的 run_nonce 與 run manifest 不符"
                           f"（{str(tnonce)[:12]!r} != {nonce[:12]!r}）"]
    bad = []
    try:
        names = sorted(os.listdir(outdir))
    except OSError as e:
        return "unknown", [f"無法列出 raw 目錄: {e}"]
    metas = [n for n in names if n.endswith(".meta.json")]
    if not metas:
        return "unknown", ["raw 目錄沒有任何 .meta.json，無法核對 run_nonce"]
    for fn in metas:
        try:
            got = json.load(open(os.path.join(outdir, fn))).get("run_nonce")
        except (OSError, ValueError) as e:
            bad.append(f"{fn}（無法讀取: {e}）")
            continue
        if got != nonce:
            bad.append(f"{fn}（run_nonce={str(got)[:12]!r}）")
    if bad:
        return "unknown", ["這些 subject meta 沒有帶上本輪的 run_nonce: "
                           + ", ".join(bad[:5])]
    return TRACE_ORIGIN_CONTEMPORANEOUS, notes

VOIDS = {
    "dispatch_skill": "該 skill 的行為證據",
    "judgment_skill": "該 skill 的行為證據",
    "token_preflight_skill": "該 skill 的行為證據",
    "evaluator": "routing／contract 判定；保留的 raw trace 可重新評分",
    "runner": "subject trace",
    "fixtures": "對應案例的 observation",
    "execution_context": "subject 行為證據（規則檔／settings／model／flags／deny list）",
    "evaluation_context": "contract 判定（judge model／CLI 版本／flags）；保留的 raw trace 可重新評分",
    "contract_fixtures": "contract 判定（judge 實際載入的 assertion 來源）",
}


def claude_version():
    try:
        r = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=60)
        return r.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def trace_digest(files):
    """trace manifest 的 deterministic digest。

    與 judge.py／manifest.py 的同名函式同規則，三邊各自持有一份——記錄器不該為了算一個
    digest 而相依於判定器。canonical JSON（排序、無空白）確保同一份 files 永遠同值。
    **不採信 manifest 內寫著的 `digest` 欄位**，一律自己重算：那個欄位是給人看的方便值，
    當成證據用就等於讓被驗的一方自己出具證明。
    """
    return hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False).encode("utf-8")).hexdigest()


# --- manifest：只讀、只比對，不現算 ------------------------------------------------

def check_schema(value):
    """`hash_schema` fail-closed。

    空值或格式不合法時，先前只是把 null 寫進紀錄然後照常記 PASS／FAIL——
    那等於宣稱「這輪的判定綁定在某個版本上」，而實際上沒有任何版本可綁。
    """
    if value is None or value == "":
        return "hash_schema 缺失或為空值"
    if not isinstance(value, str) or not SCHEMA_RE.match(value):
        return f"hash_schema 格式不合法: {value!r}（預期 v<正整數>）"
    return None


def load_manifest(path):
    """回傳 (doc | None, problems)。"""
    if not path:
        return None, ["未提供 run manifest 路徑"]
    if not os.path.exists(path):
        return None, [f"run manifest 不存在: {os.path.relpath(path, ROOT)}"]
    try:
        doc = json.load(open(path))
    except (OSError, ValueError) as e:
        return None, [f"run manifest 無法讀取或壞損: {e}"]
    if not isinstance(doc, dict):
        return None, ["run manifest 不是物件"]
    return doc, []


def _check_snapshot(label, snap, required):
    """單一快照自己就判得出來的事：hash 集合恰好、每個值是合法的 64 位 hex。

    抽成獨立函式的理由是 start 與 end 的可判時機不同：start 在 run 開始前就完整存在，
    end 要等整輪跑完才寫。把兩者綁在同一段程式裡，就會像 v6 初版那樣——end 還沒寫時
    整段直接早退，start 明明判得出來的問題全部跳過。
    """
    problems = []
    hashes = snap.get("hashes")
    if not isinstance(hashes, dict) or not hashes:
        problems.append(f"run manifest 的 {label} hashes 缺失或為空")
        return None, problems
    missing = sorted(required - set(hashes))
    unknown = sorted(set(hashes) - required)
    if missing:
        problems.append(f"{label} 缺少必要 domain: {missing}")
    if unknown:
        problems.append(f"{label} 出現未知 domain: {unknown}")
    for name, value in sorted(hashes.items()):
        if not isinstance(value, str) or not HEX64_RE.match(value or ""):
            problems.append(f"{label} hash 格式不合法: {name}={value!r}")
    return hashes, problems


def _check_context_components(label, snap, kind):
    """驗 context 分項集合與內容 hash；settings 可明確記為 absent。"""
    problems = []
    expected = CONTEXT_COMPONENTS.get(kind, CONTEXT_COMPONENTS["full"])
    groups = snap.get("context_components")
    if not isinstance(groups, dict):
        return None, [f"run manifest 的 {label} 缺 context_components"]
    missing_groups = sorted(set(expected) - set(groups))
    extra_groups = sorted(set(groups) - set(expected))
    if missing_groups:
        problems.append(f"{label} 缺少 context component group: {missing_groups}")
    if extra_groups:
        problems.append(f"{label} 出現未知 context component group: {extra_groups}")
    for domain in sorted(set(expected) & set(groups)):
        values = groups[domain]
        if not isinstance(values, dict):
            problems.append(f"{label} context component group 不是物件: {domain}")
            continue
        missing = sorted(expected[domain] - set(values))
        extra = sorted(set(values) - expected[domain])
        if missing:
            problems.append(f"{label} {domain} 缺 component: {missing}")
        if extra:
            problems.append(f"{label} {domain} 出現未知 component: {extra}")
        for name, value in sorted(values.items()):
            valid = (domain == "execution_context" and name == "settings"
                     and value == "absent")
            if not valid and not (isinstance(value, str) and HEX64_RE.match(value or "")):
                problems.append(f"{label} component hash 格式不合法: "
                                f"{domain}.{name}={value!r}")
        if not missing and not extra:
            labels = (("rules", "settings", "descriptor") if domain == "execution_context"
                      else ("descriptor",))
            if all(isinstance(values.get(name), str) for name in labels):
                canonical = "".join(
                    f"{'judge_descriptor' if domain == 'evaluation_context' else name}  "
                    f"{values[name]}\n" for name in labels)
                derived = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                combined = (snap.get("hashes") or {}).get(domain)
                if combined != derived:
                    problems.append(f"{label} {domain} 合併 hash 與分項重算不符: "
                                    f"{str(combined)[:12]} != {derived[:12]}")
    return groups, problems


def check_manifest(doc, require_end=True):
    """比對 run-start 與 run-end 快照。

    回傳 (hashes | None, hash_schema | None, fixture_files, problems)。
    hashes 取 start 的值——start 才是 subject session 實際跑的版本；
    end 只用來證明期間沒有變動。

    **`require_end=False` 給 `--validate-only` 用。** 零成本 preflight 跑在 judge 之前，
    那時 end 快照本來就還沒寫，那不是缺陷；但 start 那半是**現在就判得出來的**，
    必須完整驗完並回傳。先前這裡在 end 缺席時整段早退並回傳 `hash_schema=None`，
    後果不只是「少驗一項」：`main()` 的 `cross_schema` 以 `hash_schema` 為前提，
    值為 None 時恆為 False，於是**跨 schema 缺 `--migration-audit` 這道閘在 preflight
    期間完全不觸發**——而那正是決定要不要花 judge 的錢的那一關。
    連帶被跳過的還有 `manifest_version`、domain 集合、hash 格式、fixture 清單，
    亦即 preflight 期間 contract manifest 實質未受任何驗證。

    另一個被一併刪掉的脆弱處理是 `main()` 裡的
    `prov = [x for x in prov if "缺 end 快照" not in x]`：那是先製造錯誤再按訊息文字
    濾掉，訊息一改就失效。缺 end 是否為缺陷應該由呼叫端的模式決定，不是由字串比對決定。
    """
    problems = []
    kind = doc.get("kind", "full")
    if kind not in MANIFEST_KINDS:
        problems.append(f"未知的 manifest kind: {kind!r}（支援 {sorted(MANIFEST_KINDS)}）")
    required = MANIFEST_KINDS.get(kind, REQUIRED_DOMAINS)
    version = doc.get("manifest_version")
    if version is None:
        problems.append("run manifest 缺 manifest_version")
    elif version not in SUPPORTED_MANIFEST_VERSIONS:
        problems.append(f"不支援的 manifest_version: {version!r}"
                        f"（支援 {list(SUPPORTED_MANIFEST_VERSIONS)}）")
    start, end = doc.get("start"), doc.get("end")
    if not isinstance(start, dict):
        # start 缺席才是真的什麼都判不了：subject 跑在哪個版本上完全沒有紀錄。
        problems.append("run manifest 缺 start 快照")
        return None, None, [], problems
    has_end = isinstance(end, dict)
    if not has_end and require_end:
        problems.append("run manifest 缺 end 快照（run 結束後未重新量測）")

    # --- start 那半：不論 require_end，現在就完整驗完 ---
    schema_problem = check_schema(start.get("hash_schema"))
    if schema_problem:
        problems.append("start " + schema_problem)
    hs, sp = _check_snapshot("start", start, required)
    problems += sp
    cs, cp = _check_context_components("start", start, kind)
    problems += cp
    fs = start.get("fixture_files") or []
    if not fs:
        problems.append("run manifest 的 start 缺 fixture_files"
                        "（無法得知本輪實際載入了哪些 fixture 檔）")

    # --- end 那半：只有 end 真的存在時才判得動 ---
    he = ce = None
    if has_end:
        end_schema_problem = check_schema(end.get("hash_schema"))
        if end_schema_problem:
            problems.append("end " + end_schema_problem)
        if (not schema_problem and not end_schema_problem
                and start["hash_schema"] != end["hash_schema"]):
            problems.append(f"hash_schema 在 run 期間變動: "
                            f"{start['hash_schema']} → {end['hash_schema']}")
        he, ep = _check_snapshot("end", end, required)
        problems += ep
        ce, cep = _check_context_components("end", end, kind)
        problems += cep

    if hs is not None and he is not None:
        only_start = sorted(set(hs) - set(he))
        only_end = sorted(set(he) - set(hs))
        if only_start or only_end:
            problems.append(f"前後量測的 domain 集合不同：只在 start {only_start}、"
                            f"只在 end {only_end}")
        for name in sorted(set(hs) & set(he)):
            if hs[name] != he[name]:
                problems.append(f"domain drift（run 期間輸入被修改）: {name} "
                                f"{hs[name][:12]} → {he[name][:12]}")
    if cs is not None and ce is not None and cs != ce:
        problems.append("context component drift（run 期間 rules／settings／descriptor 被修改）")
    if has_end:
        fe = end.get("fixture_files") or []
        if fs != fe:
            problems.append(f"fixture 檔案清單在 run 期間變動："
                            f"start {len(fs)} 筆、end {len(fe)} 筆")
    return hs, start.get("hash_schema"), fs, problems


def load_source_record(path, current_digest):
    """重新評分時比對原始 run record 的 trace digest。回傳 (source | None, problems)。"""
    if not os.path.exists(path):
        return None, [f"--source 指向的原始 run record 不存在: {path}"]
    try:
        src = json.load(open(path))
    except (OSError, ValueError) as e:
        return None, [f"原始 run record 無法讀取或壞損: {e}"]
    expected = (src.get("provenance") or {}).get("trace_manifest_digest")
    if not expected:
        return src, ["原始 run record 沒有 trace_manifest_digest，無法證明 trace 未被更動"]
    if current_digest is None:
        return src, ["目前這一輪算不出 trace digest，無法與原始紀錄比對"]
    if expected != current_digest:
        return src, [f"trace manifest digest 與原始紀錄不符，禁止沿用原 subject observation: "
                     f"原始 {expected[:12]} != 現在 {current_digest[:12]}"]
    return src, []


AUDIT_ITEM_KEYS = {"equivalent", "evidence", "method"}


def load_migration_audit(path, source_schema, target_schema, subject_domains):
    """讀跨 schema 的內容等價稽核。回傳 (summary | None, problems)。

    跨 schema 時 hash 值**必然**不同（allowlist 與演算法都變了），所以「值不同」什麼都
    證明不了。要主張來源 run 的 subject 內容與現在等價，只能靠一份獨立的、逐 domain
    說明比對方法的稽核文件。

    **固定 schema，逐 domain 檢查。** 先前只驗 domain 名稱有沒有到齊，於是六個 domain
    全填 `null` 也能通過——那份「稽核」什麼都沒說，卻換到一個 `is_contract_evidence: true`
    的紀錄。現在每一項必須是 `{"equivalent": true, "evidence": <非空>, "method": <非空>}`：
    `false`、`null`、缺欄位、多欄位、未知 domain、缺 domain 一律擋下。

    本檔仍**不驗結論對不對**——那是人的責任。它驗的是「這份文件確實逐條做出了可歸責的
    主張」，而不是「主張為真」。兩者的差別就是這次修正的全部內容。
    """
    if not os.path.exists(path):
        return None, [f"--migration-audit 檔案不存在: {path}"]
    try:
        doc = json.load(open(path))
    except (OSError, ValueError) as e:
        return None, [f"migration audit 無法讀取或壞損: {e}"]
    problems = []
    if doc.get("source_hash_schema") != source_schema:
        problems.append(f"migration audit 的 source_hash_schema "
                        f"{doc.get('source_hash_schema')!r} != 來源紀錄的 {source_schema!r}")
    if doc.get("target_hash_schema") != target_schema:
        problems.append(f"migration audit 的 target_hash_schema "
                        f"{doc.get('target_hash_schema')!r} != 現行的 {target_schema!r}")
    domains = doc.get("domains")
    if not isinstance(domains, dict) or not domains:
        problems.append("migration audit 缺 domains（逐 domain 的等價說明）")
        domains = {}
    else:
        uncovered = sorted(set(subject_domains) - set(domains))
        if uncovered:
            problems.append(f"migration audit 未涵蓋的 subject domain: {uncovered}")
        unknown = sorted(set(domains) - set(subject_domains))
        if unknown:
            problems.append(f"migration audit 出現未知 domain: {unknown}")
        for name in sorted(set(domains) & set(subject_domains)):
            item = domains[name]
            if not isinstance(item, dict):
                problems.append(f"migration audit 的 {name} 不是物件"
                                f"（需 equivalent／evidence／method）")
                continue
            extra = sorted(set(item) - AUDIT_ITEM_KEYS)
            if extra:
                problems.append(f"migration audit 的 {name} 多出未知欄位: {extra}")
            if item.get("equivalent") is not True:
                problems.append(f"migration audit 的 {name} equivalent="
                                f"{item.get('equivalent')!r}，不是 true")
            if not (isinstance(item.get("evidence"), str) and item["evidence"].strip()):
                problems.append(f"migration audit 的 {name} 缺非空 evidence")
            if not (isinstance(item.get("method"), str) and item["method"].strip()):
                problems.append(f"migration audit 的 {name} 缺非空 method")
    if not (isinstance(doc.get("method"), str) and doc["method"].strip()):
        problems.append("migration audit 缺 method（沒說明整體是怎麼比對的）")
    summary = {"path": os.path.relpath(path, ROOT),
               "digest": sha256_file(path),
               "method": doc.get("method"),
               "reviewed_at": doc.get("reviewed_at"),
               "domains": sorted(domains) if isinstance(domains, dict) else None}
    return summary, problems


def verify_traces(outdir, path):
    """核對 raw trace 與 trace manifest。

    重新評分既有 trace 之所以可以省下付費 subject session，前提是那份 trace 與當初
    產生的逐 byte 相同。對不上就不得沿用原 subject observation——那已經是另一份輸入了。

    回傳 (trace_manifest | None, digest | None, problems)。
    """
    if not os.path.exists(path):
        return None, None, [f"trace manifest 不存在: {os.path.basename(path)}"
                            "（無法證明 raw trace 未被更動）"]
    try:
        tm = json.load(open(path))
        files = tm["files"]
        assert isinstance(files, dict) and files
    except (OSError, ValueError, KeyError, AssertionError) as e:
        return None, None, [f"trace manifest 壞損或為空: {e}"]

    problems = []
    digest = trace_digest(files)
    stated = tm.get("digest")
    if stated and stated != digest:
        problems.append(f"trace manifest 自述的 digest 與重算值不符: "
                        f"自述 {str(stated)[:12]} != 重算 {digest[:12]}")
    for name in sorted(files):
        p = os.path.join(outdir, name)
        if not os.path.exists(p):
            problems.append(f"trace 檔案遺失: {name}")
            continue
        actual = sha256_file(p)
        if actual != files[name]:
            problems.append(f"trace hash 不符（不得沿用原 subject observation）: {name} "
                            f"manifest {files[name][:12]} != 實際 {actual[:12]}")
    on_disk = {f for f in os.listdir(outdir) if f.endswith(TRACE_SUFFIXES)}
    extra = sorted(on_disk - set(files))
    if extra:
        problems.append(f"raw 目錄多出未列於 manifest 的 trace: {extra[:5]}")
    return tm, digest, problems


def verify_post_judge(outdir, path, fixture_ids, trace_manifest, trace_manifest_digest):
    """核對 judge 之後產生的 contract artifacts 與其獨立 manifest。"""
    if not os.path.exists(path):
        return None, None, [f"post-judge manifest 不存在: {os.path.basename(path)}"]
    try:
        doc = json.load(open(path))
        files = doc["files"]
        if not isinstance(files, dict) or not files:
            raise ValueError("files 缺失或為空")
    except (OSError, ValueError, KeyError) as e:
        return None, None, [f"post-judge manifest 壞損或為空: {e}"]
    problems = []
    if doc.get("manifest_version") != POST_JUDGE_MANIFEST_VERSION:
        problems.append(f"post-judge manifest_version 不支援: "
                        f"{doc.get('manifest_version')!r}")
    if doc.get("kind") != "post_judge":
        problems.append(f"post-judge manifest kind 不合法: {doc.get('kind')!r}")
    if doc.get("algorithm") != "sha256":
        problems.append(f"post-judge manifest algorithm 不合法: {doc.get('algorithm')!r}")
    expected = {fixture_id + ".judge.json" for fixture_id in fixture_ids}
    missing = sorted(expected - set(files))
    extra = sorted(set(files) - expected)
    if missing:
        problems.append(f"post-judge manifest 缺 judge 產物: {missing[:5]}")
    if extra:
        problems.append(f"post-judge manifest 多出未知 judge 產物: {extra[:5]}")
    for name, value in sorted(files.items()):
        if not isinstance(value, str) or not HEX64_RE.match(value or ""):
            problems.append(f"post-judge hash 格式不合法: {name}={value!r}")
            continue
        disk_path = os.path.join(outdir, name)
        if not os.path.exists(disk_path):
            problems.append(f"judge 產物遺失: {name}")
        elif sha256_file(disk_path) != value:
            problems.append(f"judge 產物 hash 不符: {name}")
    on_disk = {name for name in os.listdir(outdir) if name.endswith(".judge.json")}
    disk_extra = sorted(on_disk - set(files))
    if disk_extra:
        problems.append(f"raw 目錄多出未列於 post-judge manifest 的產物: {disk_extra[:5]}")
    digest = trace_digest(files)
    if doc.get("digest") != digest:
        problems.append(f"post-judge manifest digest 與重算值不符: "
                        f"{str(doc.get('digest'))[:12]} != {digest[:12]}")
    if doc.get("trace_manifest_digest") != trace_manifest_digest:
        problems.append("post-judge manifest 綁定的 trace digest 與目前 trace manifest 不符")
    if doc.get("run_nonce") != (trace_manifest or {}).get("run_nonce"):
        problems.append("post-judge manifest 的 run_nonce 與 trace manifest 不符")
    return doc, digest, problems


# --- 逐筆判定與成本 ----------------------------------------------------------------

def subject_cost(jsonl):
    """從 result 事件取 session 自報成本；取不到回 None，不推估。"""
    try:
        for line in open(jsonl):
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if d.get("type") == "result" and d.get("total_cost_usd") is not None:
                return float(d["total_cost_usd"])
    except (OSError, ValueError):
        pass
    return None


def collect(outdir, fixture_files):
    sys.path.insert(0, BASE)
    import score as scorer
    rows = scorer.score(outdir, *fixture_files)
    subj_cost, judge_cost, n_subject, n_judge = 0.0, 0.0, 0, 0
    subj_missing = judge_missing = False
    for r in rows:
        jl = os.path.join(outdir, r["id"] + ".jsonl")
        if os.path.exists(jl):
            n_subject += 1
            c = subject_cost(jl)
            if c is None:
                subj_missing = True
            else:
                subj_cost += c
        jf = os.path.join(outdir, r["id"] + ".judge.json")
        if os.path.exists(jf):
            n_judge += 1
            try:
                jd = json.load(open(jf))
            except (OSError, ValueError):
                jd = {"error": "judge 檔壞損"}
            r["contract"] = jd.get("error") and "ERROR" or jd.get("overall", "ERROR")
            r["contract_detail"] = jd.get("error", "")
            # parser 異常必須進正式紀錄，否則只留在 raw/*.judge.json，
            # 第三方讀 run record 看不出這一輪的判定是怎麼壞的。
            r["contract_anomaly"] = jd.get("anomaly")
            c = jd.get("_cost_usd")
            if c is None:
                judge_missing = True
            else:
                judge_cost += float(c)
        else:
            r["contract"] = "NOT_RUN"
            r["contract_detail"] = "無 .judge.json"
            r["contract_anomaly"] = None
    # preflight 也是真實 session，成本要算進來，否則紀錄少報。
    pf = os.path.join(outdir, "_preflight.jsonl")
    pf_cost = subject_cost(pf) if os.path.exists(pf) else None
    cost = {
        "preflight_usd": pf_cost,
        "preflight_sessions": 1 if os.path.exists(pf) else 0,
        "subject_usd": None if subj_missing else round(subj_cost, 4),
        "judge_usd": None if judge_missing else round(judge_cost, 4),
        "subject_sessions": n_subject,
        "judge_sessions": n_judge,
    }
    parts = [cost["subject_usd"], cost["judge_usd"]]
    if cost["preflight_sessions"]:
        parts.append(cost["preflight_usd"])
    cost["total_usd"] = (None if any(x is None for x in parts) else round(sum(parts), 4))
    return rows, cost


def collect_warnings(rows):
    """把逐筆 parser 異常收成 run 層級的 warnings。

    異常不等於 INVALID——機制上允許「判定可用但有異常」，`usable` 欄就是記這件事；
    但 Batch 13f 收緊後目前每一種 anomaly kind 都不可用，此欄實際恆為否，保留給日後
    確定良性的異常。
    `extra_data` / `schema_violation` 這類已經讓該筆記成 ERROR，
    INVALID 判定由既有的 unusable 檢查負責，本函式只負責可追溯性。
    """
    out = []
    for r in rows:
        a = r.get("contract_anomaly")
        if a:
            out.append({"fixture_id": r["id"], "source": "judge_parser",
                        "kind": a.get("kind"), "usable": r["contract"] != "ERROR",
                        "detail": a})
    return out


def result_row(r):
    return {"id": r["id"], "category": r["category"], "routing": r["routing"],
            "routing_detail": r["detail"], "contract": r["contract"],
            "contract_detail": r["contract_detail"],
            "contract_anomaly": r.get("contract_anomaly"),
            "triggered": r["triggered"]}


def main(outdir, run_id, manifest_path, *fixture_files, **kwargs):
    source_path = kwargs.pop("source_record", None)
    audit_path = kwargs.pop("migration_audit", None)
    validate_only = kwargs.pop("validate_only", False)
    assert not kwargs, kwargs
    rundir = os.path.dirname(os.path.abspath(outdir))
    jpath = os.path.join(rundir, run_id + ".json")
    # 覆寫原始紀錄等於銷毀重評的比對基準。在做任何事之前就擋掉，不寫半份檔案。
    if source_path and os.path.abspath(source_path) == os.path.abspath(jpath):
        print(f"  ✗ derived record 的輸出路徑與 --source 相同，拒絕覆寫原始 run record: "
              f"{jpath}")
        return 3
    rows, cost = collect(outdir, fixture_files)

    started = os.environ.get("HARNESS_RUN_STARTED")
    ended = os.environ.get("HARNESS_RUN_ENDED")
    dur = (int(ended) - int(started)) if (started and ended) else None
    cli_failed = os.environ.get("HARNESS_CLI_FAILED")
    cli_failed = int(cli_failed) if cli_failed is not None else None

    # --- provenance：manifest 與 trace manifest ---
    manifest, prov = load_manifest(manifest_path)
    hashes, hash_schema, fixture_file_list = None, None, []
    context_components = None
    if manifest is not None:
        # preflight（judge 之前）時 end 快照本來就還沒寫，那不是缺陷；
        # 但 start 那半必須在這裡就驗完——cross-schema 那道閘依賴 hash_schema。
        hashes, hash_schema, fixture_file_list, mp = check_manifest(
            manifest, require_end=not validate_only)
        prov += mp
        context_components = (manifest.get("start") or {}).get("context_components")
    trace_manifest, tm_digest, tp = verify_traces(
        outdir, os.path.join(rundir, "trace-manifest.json"))
    prov += tp
    # 這一輪的 trace manifest 是不是「當下」產生的——由 run nonce 鏈判定，不採信任何自述。
    trace_origin, nonce_notes = check_nonce_chain(manifest, trace_manifest, outdir)
    post_judge_manifest, post_judge_digest = None, None
    if not validate_only:
        post_judge_manifest, post_judge_digest, pp = verify_post_judge(
            outdir, os.path.join(rundir, "post-judge-manifest.json"),
            [row["id"] for row in rows], trace_manifest, tm_digest)
        prov += pp
    # manifest 形態必須與模式相符：原生 run 要 full，重新評分要 contract。
    manifest_kind = (manifest or {}).get("kind", "full")
    if source_path and manifest_kind != "contract":
        prov.append(f"重新評分必須傳入 contract manifest"
                    f"（manifest.py contract-snapshot），實得 kind={manifest_kind!r}")
    if not source_path and manifest_kind == "contract":
        prov.append("原生 run 不得使用 contract manifest：subject identity 會整個缺席")

    source, derived_from, hash_provenance = None, None, None
    if source_path:
        source, sp = load_source_record(source_path, tm_digest)
        prov += sp
        # --- derived identity 的兩半 ---
        # subject 那半取自來源紀錄：那份 trace 是在**那個**版本下產生的，
        # 此刻重量 skill／fixtures／runner 只會量到與該 trace 無關的東西。
        src_hashes = (source or {}).get("hashes") or {}
        subject = dict((k, v) for k, v in src_hashes.items() if k in SUBJECT_DOMAINS)
        missing_subject = sorted(SUBJECT_DOMAINS - set(subject))
        if missing_subject:
            prov.append(f"來源 run record 缺 subject domain，無法建立 subject 綁定: "
                        f"{missing_subject}")
        # 只檢查 key 在不在是不夠的：六個值全填 null 也會通過，而那份紀錄
        # 對 subject 什麼都沒綁定，卻換到一個 is_contract_evidence: true。
        bad_subject = sorted(k for k, v in subject.items()
                             if not (isinstance(v, str) and HEX64_RE.match(v or "")))
        if bad_subject:
            prov.append(f"來源 run record 的 subject hash 不是合法的 64 位 hex: "
                        f"{bad_subject}")
        # contract 那半是現量的，這才是「現在的 evaluator」。
        contract = dict((k, v) for k, v in (hashes or {}).items() if k in CONTRACT_DOMAINS)
        combined = dict(subject)
        combined.update(contract)
        hash_provenance = dict(
            [(k, "source_run") for k in subject] + [(k, "measured_now") for k in contract])
        source_schema = (source or {}).get("hash_schema")
        cross_schema = bool(source_schema and hash_schema and source_schema != hash_schema)
        audit = None
        if audit_path:
            audit, ap = load_migration_audit(audit_path, source_schema, hash_schema,
                                             SUBJECT_DOMAINS)
            prov += ap
        elif cross_schema:
            # 跨 schema 時 hash 值必然不同，「值不同」什麼都不能證明。
            prov.append(f"來源 hash_schema {source_schema} 與現行 {hash_schema} 不同，"
                        f"必須另附 --migration-audit 記錄內容等價；缺此不得沿用 subject 綁定")
        # 事後補的 trace manifest 只能證明「目前檔案」的內容，不能證明它從產生到現在
        # 沒被改過。這種來源最多是 legacy diagnostic，不得記為契約證據——
        # 否則「補一份 manifest」就等於把任何舊檔案升格成證據。
        src_origin = ((source or {}).get("provenance") or {}).get(
            "trace_manifest_origin") or "unknown"
        derived_from = {
            "source_run_id": (source or {}).get("run_id"),
            "source_trace_manifest_origin": src_origin,
            "source_record": os.path.relpath(source_path, ROOT),
            "source_trace_manifest_digest":
                ((source or {}).get("provenance") or {}).get("trace_manifest_digest"),
            "source_hash_schema": source_schema,
            "cross_schema": cross_schema,
            "migration_audit": audit,
            "subject_identity_from_source": subject,
            # 「用哪一版工具、對哪一份 trace、做出這份判定」——三者缺一，derived record
            # 就沒辦法回答第三方最想問的那個問題。
            "rescored_with": {
                "hash_schema": hash_schema,
                "evaluator": contract.get("evaluator"),
                "evaluation_context": contract.get("evaluation_context"),
                "contract_fixtures": contract.get("contract_fixtures"),
                "rescore_runner": contract.get("rescore_runner"),
            },
        }
        hashes = combined
        source_components = (source or {}).get("context_components") or {}
        measured_components = ((manifest or {}).get("start") or {}).get(
            "context_components") or {}
        context_components = {}
        if "execution_context" in source_components:
            context_components["execution_context"] = source_components["execution_context"]
        if "evaluation_context" in measured_components:
            context_components["evaluation_context"] = measured_components["evaluation_context"]

    if validate_only:
        # 缺 end 是否為缺陷，由 check_manifest(require_end=...) 從結構上決定；
        # 先製造一個錯誤再按訊息文字濾掉的作法已刪除——訊息一改就會失效。
        # 零成本 preflight：把所有 provenance 檢查跑完再決定要不要花 judge 的錢。
        # 先前這些檢查排在付費 judge **之後**，缺 audit 或 source hash 壞損時，
        # 整輪跑完才判 INVALID——正是「判不了仍先花錢」的老問題換個位置重現。
        if prov:
            print("  ✗ rescore preflight 不通過，未呼叫任何 judge session：")
            for item in prov:
                print(f"    - {item}")
            return 3
        src_origin = (((source or {}).get("provenance") or {}).get(
            "trace_manifest_origin") or "unknown") if source_path else trace_origin
        cls = ("contract_evidence" if src_origin == TRACE_ORIGIN_CONTEMPORANEOUS
               else "legacy_diagnostic")
        print(f"  ✓ rescore preflight 通過；本輪產出的證據等級將是 {cls}")
        return 0

    # 三值判定。**FAIL 與 INVALID 必須分開**：
    #   FAIL    = 每一筆都產生了可用觀測，而其中有觀測不符預期 → 這是關於 skill 的證據。
    #   INVALID = 有 fixture 根本沒產生可用觀測（CLI 失敗、逾時、未跑、judge 無法判定），
    #             或 provenance 無法成立（版本綁定斷了）
    #             → 這一輪對 skill 什麼都沒說,不得被當成契約證據。
    # 少了這個區分,一輪「登入過期、18 筆全部在推論前就失敗」的執行會被記成 FAIL,
    # 日後讀起來像是 skill 沒通過。
    USABLE = ("PASS", "FAIL")
    unusable = [r for r in rows
                if r["routing"] not in USABLE or r["contract"] not in USABLE]
    bad = [r for r in rows if r["routing"] == "FAIL" or r["contract"] == "FAIL"]
    if not rows:
        status, evidence = "INVALID", False
        reason = "沒有任何 fixture"
    elif unusable:
        status, evidence = "INVALID", False
        reason = (f"{len(unusable)}/{len(rows)} 筆未產生可用觀測"
                  f"（CLI 失敗 {cli_failed if cli_failed is not None else '?'}）"
                  f"；樣本：{unusable[0]['id']} — "
                  f"routing={unusable[0]['routing']} {unusable[0]['detail']} / "
                  f"contract={unusable[0]['contract']} {unusable[0]['contract_detail']}")
    elif bad:
        status, evidence, reason = "FAIL", True, ""
    else:
        status, evidence, reason = "PASS", True, ""

    # provenance 失敗一律壓過上面的判定：版本綁定斷掉時，PASS 與 FAIL 都沒有意義。
    if prov:
        status, evidence = "INVALID", False
        prov_reason = "provenance 不成立：" + "；".join(prov)
        reason = f"{reason}；{prov_reason}" if reason else prov_reason

    # 證據等級與 run_status 是兩個獨立的軸：
    #   run_status      這一輪的觀測可不可用（PASS／FAIL／INVALID）
    #   evidence_class  這些觀測能不能當契約證據
    # 一份 legacy diagnostic 可以是 PASS——它只是不能拿去過發布 gate。
    origin_for_class = trace_origin
    if source_path:
        # derived record 的證據等級由**來源** trace manifest 的來源決定：
        # 本輪重新產生的 manifest 再怎麼「當下」，也只是重算了同一批舊檔案。
        origin_for_class = ((source or {}).get("provenance") or {}).get(
            "trace_manifest_origin") or "unknown"
    if origin_for_class == TRACE_ORIGIN_CONTEMPORANEOUS:
        evidence_class = "contract_evidence"
    else:
        evidence_class = "legacy_diagnostic"
        if evidence:
            detail = ("；".join(nonce_notes) if (nonce_notes and not source_path)
                      else "")
            reason = (f"{reason}；" if reason else "") + (
                f"trace manifest 來源為 {origin_for_class}（非 contemporaneous），"
                f"只能作為 legacy diagnostic，不得計為契約證據"
                + (f"：{detail}" if detail else ""))
        evidence = False

    doc = {
        "run_id": run_id,
        "recorded_at": datetime.datetime.now().astimezone().isoformat(),
        "run_status": status,
        "evidence_class": evidence_class,
        "is_contract_evidence": evidence,
        "invalid_reason": reason or None,
        "claude_code_version": claude_version(),
        "subject_model": os.environ.get("HARNESS_SUBJECT_MODEL"),
        "judge_model": os.environ.get("HARNESS_JUDGE_MODEL"),
        "duration_s": dur,
        "cli_failed": cli_failed,
        "cost": cost,
        "hash_schema": hash_schema,
        "hashes": hashes,
        "context_components": context_components,
        "record_kind": "derived" if source_path else "source",
        "derived_from": derived_from,
        "hash_provenance": hash_provenance,
        "provenance": {
            "manifest_file": (os.path.relpath(manifest_path, ROOT)
                              if manifest_path else None),
            "problems": prov,
            "start_recorded_at": (manifest or {}).get("start", {}).get("recorded_at"),
            "end_recorded_at": (manifest or {}).get("end", {}).get("recorded_at"),
            "start_end_identical": bool(manifest) and not prov,
            "trace_manifest_digest": tm_digest,
            "trace_manifest_origin": trace_origin,
            "trace_manifest_origin_notes": nonce_notes,
            "run_nonce": (manifest or {}).get("run_nonce"),
            "trace_manifest": trace_manifest,
            "post_judge_manifest_digest": post_judge_digest,
            "post_judge_manifest": post_judge_manifest,
        },
        "hash_method": (f"{HASH_REL} — allowlist、路徑無關（相對路徑+內容 hash）、"
                        f"排除未列出路徑與 .DS_Store。六個互斥 domain："
                        f"skill／evaluator／runner／fixtures／execution-context／"
                        f"evaluation-context。"
                        + ("derived record：subject 那半取自來源 run 的紀錄，"
                           "contract 那半（evaluator／evaluation-context）為本次現量，"
                           "逐 domain 見 hash_provenance。"
                           if source_path else
                           "值取自 run-start 快照，並與 run-end 快照比對。")
                        + "**不同 hash_schema 的值不得直接比較**"),
        "fixture_files": fixture_file_list,
        "totals": {
            "fixtures": len(rows),
            "routing_pass": sum(1 for r in rows if r["routing"] == "PASS"),
            "contract_pass": sum(1 for r in rows if r["contract"] == "PASS"),
        },
        "warnings": collect_warnings(rows),
        "results": [result_row(r) for r in rows],
    }
    json.dump(doc, open(jpath, "w"), ensure_ascii=False, indent=2)

    def cell(v):
        return "—" if v is None else str(v)

    banner = ([f"> **本輪不構成契約證據（run_status: {status}，"
               f"evidence_class: {evidence_class}）。** {reason}", ""]
              if not evidence else [])
    md = [f"# harness run {run_id}", ""] + banner + [
          f"- 狀態：**{status}**　證據等級：**{evidence_class}**",
          f"- Claude Code 版本：{cell(doc['claude_code_version'])}",
          f"- 受測 model：{cell(doc['subject_model'])}　judge model：{cell(doc['judge_model'])}",
          f"- 耗時：{cell(dur)} 秒　CLI 失敗：{cell(doc['cli_failed'])} 筆",
          f"- session 數：preflight {cost['preflight_sessions']}／受測 {cost['subject_sessions']}"
          f"／judge {cost['judge_sessions']}",
          f"- 成本 USD：preflight {cell(cost['preflight_usd'])}／受測 {cell(cost['subject_usd'])}"
          f"／judge {cell(cost['judge_usd'])}／"
          f"合計 {cell(cost['total_usd'])}　（null 表示該來源未回報，未以推估補完）",
          "", f"## identity hashes（hash_schema {cell(hash_schema)}）", ""]
    if hashes:
        md += (["**derived record**：subject 那半取自來源 run 的紀錄，"
                "contract 那半為本次現量。"]
               if source_path else
               ["值取自 **run-start 快照**；run-end 已重新量測並比對，"
                "任一 domain 不同即整輪 INVALID。"])
        md += ["", "| domain | sha256 | 量測來源 | 變更後作廢 |", "|---|---|---|---|"]
        for k, v in sorted(hashes.items()):
            src = (hash_provenance or {}).get(k, "run-start 快照")
            md.append(f"| `{k}` | `{cell(v)}` | {src} | {VOIDS.get(k, '—')} |")
    else:
        md.append("（無可用的 run manifest，本輪沒有任何版本綁定）")
    md += ["", "本次 fixtures domain 實際涵蓋的檔案："
           + ("、".join(f"`{f}`" for f in fixture_file_list) or "（無）"),
           "", "### context component hashes", "",
           "| domain | component | sha256／狀態 |", "|---|---|---|"]
    for domain, components in sorted((context_components or {}).items()):
        for name, value in sorted(components.items()):
            md.append(f"| `{domain}` | `{name}` | `{cell(value)}` |")
    if not context_components:
        md.append("| — | — | （來源紀錄未保存分項 hash） |")
    md += [
           "", f"重算方式：`{HASH_REL} <mode> <路徑…>`（mode: skill｜evaluator｜runner｜"
           f"fixtures｜execution-context｜evaluation-context｜schema-version）。",
           "**不同 `hash_schema` 的值不得直接比較。**", "",
           "## provenance", "",
           f"- run-start 量測：{cell(doc['provenance']['start_recorded_at'])}",
           f"- run-end 量測：{cell(doc['provenance']['end_recorded_at'])}",
           f"- raw trace manifest："
           f"{len((trace_manifest or {}).get('files', {}))} 個檔案，digest "
           f"{cell(tm_digest and tm_digest[:12])}，"
           f"{'核對通過' if trace_manifest and not tp else '未通過或缺失'}", ""]
    md += [f"- post-judge manifest："
           f"{len((post_judge_manifest or {}).get('files', {}))} 個檔案，digest "
           f"{cell(post_judge_digest and post_judge_digest[:12])}，"
           f"{'核對通過' if post_judge_manifest else '未通過或缺失'}", ""]
    if derived_from:
        md += ["- **derived record**（重新評分，非原生 run）："
               f"來源 `{cell(derived_from['source_run_id'])}`"
               f"（`{derived_from['source_record']}`）；"
               f"來源 trace digest "
               f"`{cell(derived_from['source_trace_manifest_digest'] and derived_from['source_trace_manifest_digest'][:12])}`；"
               f"本次 evaluator "
               f"`{cell(derived_from['rescored_with']['evaluator'] and derived_from['rescored_with']['evaluator'][:12])}`、"
               f"evaluation_context "
               f"`{cell(derived_from['rescored_with']['evaluation_context'] and derived_from['rescored_with']['evaluation_context'][:12])}`", ""]
    if prov:
        md += ["違反項："] + [f"- {p}" for p in prov] + [""]
    if doc["warnings"]:
        md += ["## parser 警告", "",
               "| fixture | 來源 | 型態 | 判定仍可用 |", "|---|---|---|---|"]
        for w in doc["warnings"]:
            md.append(f"| `{w['fixture_id']}` | {w['source']} | {w['kind']} | "
                      f"{'是' if w['usable'] else '否'} |")
        md.append("")
    md += ["## 逐筆判定", "",
           "| fixture | 類別 | routing | contract | 觸發 | 說明 |", "|---|---|---|---|---|---|"]
    for r in doc["results"]:
        detail = (r["routing_detail"] or r["contract_detail"] or "").replace("|", "/")
        md.append(f"| `{r['id']}` | {r['category']} | {r['routing']} | {r['contract']} | "
                  f"{','.join(r['triggered']) or '（無）'} | {detail} |")
    open(os.path.join(rundir, run_id + ".md"), "w").write("\n".join(md) + "\n")
    print(f"  run record: {jpath}")
    if prov:
        print("  ✗ provenance 不成立 → INVALID")
        for p in prov:
            print(f"    - {p}")
    return 2 if prov else 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    src = audit = None
    validate = False
    while argv and argv[0] in ("--source", "--migration-audit", "--validate-only"):
        if argv[0] == "--validate-only":
            validate = True
            argv = argv[1:]
            continue
        if len(argv) < 2:
            sys.exit(__doc__)
        if argv[0] == "--source":
            src = argv[1]
        else:
            audit = argv[1]
        argv = argv[2:]
    if len(argv) < 4:
        sys.exit(__doc__)
    if audit and not src:
        sys.exit("--migration-audit 只在 --source 重新評分時有意義")
    sys.exit(main(argv[0], argv[1], argv[2], *argv[3:],
                  source_record=src, migration_audit=audit, validate_only=validate))
