#!/usr/bin/env python3
"""manifest.py — identity 快照、raw trace 與 post-judge 產物的 hash manifest。

## 為什麼需要它

v2 的 `record.py` 是在**整輪跑完之後**才現算各 domain hash。那個值回答的是
「錄這份紀錄的當下，repo 長什麼樣」，不是「這輪 subject session 實際跑在什麼版本上」。
兩者在 run 期間有任何一次編輯就會分歧，而分歧完全不可見：run record 會安靜地把
**跑完之後**的 hash 綁到**跑之前**產生的 observation 上。

v3 改成：run 開始前先量一次（start），跑完再量一次（end），兩份都留在 manifest 裡，
由 `record.py` 比對。任一 domain 在兩次量測間變動，整輪判 `INVALID`——
fail-closed，因為此時已經無法斷定 observation 對應哪一個版本。

`record.py` **只讀 manifest，不自己現算**：若它現算，就等於再次引入「錄製當下」的值。

## 為什麼 trace manifest 是獨立的一份，而且不可覆寫

subject session 是付費產物，evaluator 變更後允許「重新評分既有 trace」而不重跑。
這個省錢路徑成立的前提是：被重新評分的 trace 與當初產生的那一份逐 byte 相同。
因此 subject 迴圈一結束就立刻對每一筆 `.jsonl`／`.meta.json` 取 SHA-256，
之後任何重新評分都必須先核對；對不上就不得沿用原 subject observation。

**`trace` 預設不覆寫既有檔案，目標存在即 exit 3。** 允許覆寫的話，逐檔比對就形同虛設：
改 trace、重跑一次 `trace`，新 manifest 裡每一筆 hash 都會對得上。要重建就必須先明確
刪掉舊的，而那個動作會讓 digest 與原始 run record 保存的值對不上——那才是真正的關卡。

manifest 內同時寫入 `digest`（files 對照表的 canonical JSON 之 SHA-256）。
`record.py` 不信任這個欄位，一律自己重算；寫進去是為了讓人不必自己算就能比對。

## run nonce：證明 trace manifest 真的是當下產生的

先前用一個環境變數（`HARNESS_TRACE_MANIFEST_ORIGIN`）宣告「這份 trace manifest 是當下
產生的」，而 `record.py` 直接採信。那不是證明，是自述：對任何事後湊出來的目錄設一次
環境變數，就能得到 `evidence_class: contract_evidence`。

v6 改成一條**必須四方一致**的鏈：

  1. `snapshot start` 產生一次性的 `run_nonce`（128-bit 隨機），寫進 manifest。
  2. runner 把同一個 nonce 傳給每一個 subject session，`run-fixture.sh` 寫進 `.meta.json`。
  3. `trace` 收到 nonce 時逐檔核對每份 `.meta.json`，並把 nonce 寫進 trace manifest。
  4. `record.py` 要求三者一致，才判 `contemporaneous`；任一環缺失或不符即
     `legacy_diagnostic`。

這擋不住一個能同時改寫全部四樣東西的人——沒有外部錨定（commit、可信封存）的方案都擋不住。
它擋掉的是「補一份 manifest 或設一個環境變數就升格」，門檻從一個字串變成一整條鏈。

## 為什麼同名 phase 不可覆寫

`doc[phase] = snap` 無條件寫入的話，start 可以被第二次 start 蓋掉。實測依序寫入
start=A、start=B、end=B，三次都回傳 0，而 `record.check_manifest()` 得到**零問題**——
原始 start 已經不存在，drift 因此被完全隱藏。這比沒有比對更糟：紀錄看起來通過了比對。
因此同名 phase 已存在即 exit 3；要重量就得換一份 manifest 檔。

## 兩種 manifest

`snapshot` 產生 **full** manifest（八個 domain），給原生 run 用。
`contract-snapshot` 產生 **contract** manifest（`evaluator`、`evaluation_context`、
`contract_fixtures`、`rescore_runner`），給「重新評分既有 trace」用：那條路徑的 subject identity 來自
**來源 run 的紀錄**，不是現在的 repo 狀態，此刻重量 skill／runner 只會量到與該 trace
無關的東西。

`contract_fixtures` 是 v5 新增的：judge 是用**現在**這份 fixture 檔判定的，
`required_elements`／`forbidden_elements` 就寫在裡面。少了它，改掉 assertion 再重評舊
trace，紀錄仍會宣稱使用來源 fixtures。它與 subject 的 `fixtures` 用同一套演算法，
差別在量的時機與歸屬。

CLI:
  manifest.py snapshot          <out.json> <start|end> <rules|-> <settings|-> \
                                <exec-descriptor|-> <judge-descriptor> <fixture 路徑…>
  manifest.py contract-snapshot <out.json> <start|end> <judge-descriptor> <fixture 路徑…>
  manifest.py trace             <out.json> <raw 目錄> [<run-nonce>]
  manifest.py post-judge        <out.json> <raw 目錄> <trace-manifest.json> <fixture 路徑…>
"""
import binascii, datetime, hashlib, json, os, subprocess, sys

# manifest 文件的 schema 版本。v3 加入 context_components，讓合併值 drift 時可歸因。
MANIFEST_VERSION = 3
POST_JUDGE_MANIFEST_VERSION = 1

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE, "..", "..", ".."))
HASH_SH = os.path.join(ROOT, "scripts", "bundle-hash.sh")

# domain -> (mode, 路徑…)。fixtures 與 execution_context 的引數由呼叫端提供。
STATIC_DOMAINS = (
    ("dispatch_skill", "skill", ["skills/harness/dispatch"]),
    ("judgment_skill", "skill", ["skills/discipline/judgment"]),
    ("token_preflight_skill", "skill", ["skills/discipline/token-preflight"]),
    ("evaluator", "evaluator", ["skills/harness"]),
    ("runner", "runner", ["skills/harness"]),
)

TRACE_SUFFIXES = (".jsonl", ".meta.json")
JUDGE_SUFFIX = ".judge.json"


def _run_hash(mode, *paths):
    """呼叫 bundle-hash.sh。失敗一律回 None——空值或格式不合法都不得當成有效 hash。"""
    try:
        r = subprocess.run(["sh", HASH_SH, mode, *paths],
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    v = r.stdout.strip()
    if r.returncode != 0 or len(v) != 64 or any(c not in "0123456789abcdef" for c in v):
        return None
    return v


def schema_version():
    try:
        r = subprocess.run(["sh", HASH_SH, "schema-version"],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return (r.stdout.strip() or None) if r.returncode == 0 else None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _component_hash(path, allow_absent=False):
    if path == "-" and allow_absent:
        return "absent"
    if path == "-" or not os.path.isfile(path):
        return None
    return sha256_file(path)


def context_components(rules=None, settings=None, descriptor=None, judge_descriptor=None):
    """回傳 context domain 的分項內容 hash；路徑不屬 identity。"""
    out = {}
    if rules is not None or settings is not None or descriptor is not None:
        out["execution_context"] = {
            "rules": _component_hash(rules),
            "settings": _component_hash(settings, allow_absent=True),
            "descriptor": _component_hash(descriptor),
        }
    if judge_descriptor is not None:
        out["evaluation_context"] = {
            "descriptor": _component_hash(judge_descriptor),
        }
    return out


def expand_fixture_files(paths):
    """展開 fixture 引數成**實際檔案清單**（repo 相對路徑，排序、去重）。

    只記 `fixtures.json` 這種引數名不夠：`seed` 是目錄，裡面增刪一個檔案會改變
    fixture hash，但引數清單看起來完全一樣。要讓第三方能重算，得知道當時實際載入了哪些檔。
    """
    out = set()
    for p in paths:
        ap = os.path.abspath(p)
        if os.path.isdir(ap):
            for dirpath, _dirnames, filenames in os.walk(ap):
                for fn in filenames:
                    if fn == ".DS_Store":
                        continue
                    out.add(os.path.join(dirpath, fn))
        elif os.path.isfile(ap):
            out.add(ap)
        else:
            raise SystemExit(f"manifest: fixture 路徑不存在: {p}")
    return sorted(os.path.relpath(f, ROOT) for f in out)


def snapshot(rules, settings, descriptor, judge_descriptor, fixture_paths):
    hashes = {}
    for name, mode, rel in STATIC_DOMAINS:
        hashes[name] = _run_hash(mode, *[os.path.join(ROOT, r) for r in rel])
    hashes["fixtures"] = _run_hash("fixtures", *fixture_paths)
    hashes["execution_context"] = _run_hash("execution-context", rules, settings, descriptor)
    # 判定端的環境是獨立 domain：它變更只作廢 contract 判定，保留的 raw trace 仍可重評；
    # 混進 execution_context 會讓「換 judge model」看起來像「受測環境變了」。
    hashes["evaluation_context"] = _run_hash("evaluation-context", judge_descriptor)
    return {
        "recorded_at": datetime.datetime.now().astimezone().isoformat(),
        "hash_schema": schema_version(),
        "hashes": hashes,
        "context_components": context_components(
            rules, settings, descriptor, judge_descriptor),
        "fixture_args": [os.path.relpath(os.path.abspath(p), ROOT) for p in fixture_paths],
        "fixture_files": expand_fixture_files(fixture_paths),
    }


def cmd_snapshot(out, phase, rules, settings, descriptor, judge_descriptor,
                 fixture_paths):
    if phase not in ("start", "end"):
        raise SystemExit("manifest: phase 只能是 start 或 end")
    if judge_descriptor == "-" or not os.path.isfile(judge_descriptor):
        print(f"manifest: 缺 judge descriptor（evaluation-context 為必要 domain）: "
              f"{judge_descriptor}", file=sys.stderr)
        return 3
    snap = snapshot(rules, settings, descriptor, judge_descriptor, fixture_paths)
    missing = [k for k, v in snap["hashes"].items() if v is None]
    missing_components = [
        f"{domain}.{name}"
        for domain, components in snap["context_components"].items()
        for name, value in components.items() if value is None
    ]
    if missing or missing_components or not snap["hash_schema"]:
        print(f"manifest: 無法量測 {'hash_schema ' if not snap['hash_schema'] else ''}"
              f"{', '.join(missing + missing_components)}", file=sys.stderr)
        return 3
    doc = {}
    if os.path.exists(out):
        try:
            doc = json.load(open(out))
        except (OSError, ValueError):
            print(f"manifest: 既有 manifest 壞損，拒絕覆寫: {out}", file=sys.stderr)
            return 3
    if phase == "end" and "start" not in doc:
        print("manifest: 沒有 start 快照就不能寫 end", file=sys.stderr)
        return 3
    if phase in doc:
        # 覆寫同名 phase = 讓 drift 被隱藏（見檔頭）。要重量就換一份 manifest 檔。
        print(f"manifest: {phase} 快照已存在，拒絕覆寫: {out}", file=sys.stderr)
        return 3
    doc["manifest_version"] = MANIFEST_VERSION
    doc["kind"] = "full"
    if phase == "start":
        # 一次性 nonce：subject meta 與 trace manifest 都要帶上同一個值，
        # record.py 才會認這輪的 trace manifest 是當下產生的。
        doc["run_nonce"] = binascii.hexlify(os.urandom(16)).decode()
    elif not doc.get("run_nonce"):
        print("manifest: start 快照沒有 run_nonce，無法寫 end", file=sys.stderr)
        return 3
    doc[phase] = snap
    json.dump(doc, open(out, "w"), ensure_ascii=False, indent=2)
    print(f"  manifest[{phase}]: hash_schema {snap['hash_schema']}，"
          f"{len(snap['hashes'])} domain，{len(snap['fixture_files'])} 個 fixture 檔")
    return 0


def trace_digest(files):
    """files 對照表的 deterministic digest；judge.py／record.py 各自持有同規則的一份。"""
    return hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False).encode("utf-8")).hexdigest()


def cmd_contract_snapshot(out, phase, judge_descriptor, fixture_paths):
    """只量 contract 端的三個 domain，給重新評分用。

    重評的 subject identity 必須取自**來源 run 的紀錄**——那份 trace 是在那個版本下產生的，
    現在的 repo 可能早已不同。此刻重量 skill／runner 得到的是與該 trace 無關的值，
    寫進 derived record 只會製造一個看起來很完整、實際上對不上任何東西的版本綁定。

    但 `contract_fixtures` 必須是**現量**：judge 是用現在這份 fixture 檔的
    `required_elements`／`forbidden_elements` 判定的。沿用來源的 fixtures hash 會讓紀錄
    宣稱一份不是判定依據的檔案。
    """
    if phase not in ("start", "end"):
        raise SystemExit("manifest: phase 只能是 start 或 end")
    if not os.path.isfile(judge_descriptor):
        print(f"manifest: 缺 judge descriptor: {judge_descriptor}", file=sys.stderr)
        return 3
    if not fixture_paths:
        print("manifest: contract-snapshot 需要 judge 實際載入的 fixture 路徑",
              file=sys.stderr)
        return 3
    hashes = {
        "evaluator": _run_hash("evaluator", os.path.join(ROOT, "skills/harness")),
        "evaluation_context": _run_hash("evaluation-context", judge_descriptor),
        "contract_fixtures": _run_hash("fixtures", *fixture_paths),
        # 編排腳本決定 judge 的輸出位置與驗證順序，兩者都直接影響 derived record 的
        # 可信度，因此屬於 contract identity。
        "rescore_runner": _run_hash("rescore-runner"),
    }
    schema = schema_version()
    missing = [k for k, v in hashes.items() if v is None]
    if missing or not schema:
        print(f"manifest: 無法量測 {', '.join(missing) or 'hash_schema'}", file=sys.stderr)
        return 3
    doc = {}
    if os.path.exists(out):
        try:
            doc = json.load(open(out))
        except (OSError, ValueError):
            print(f"manifest: 既有 manifest 壞損，拒絕覆寫: {out}", file=sys.stderr)
            return 3
    if phase == "end" and "start" not in doc:
        print("manifest: 沒有 start 快照就不能寫 end", file=sys.stderr)
        return 3
    if phase in doc:
        print(f"manifest: {phase} 快照已存在，拒絕覆寫: {out}", file=sys.stderr)
        return 3
    doc["manifest_version"] = MANIFEST_VERSION
    doc["kind"] = "contract"
    components = context_components(judge_descriptor=judge_descriptor)
    if any(value is None for values in components.values() for value in values.values()):
        print("manifest: 無法量測 evaluation_context.descriptor", file=sys.stderr)
        return 3
    doc[phase] = {"recorded_at": datetime.datetime.now().astimezone().isoformat(),
                  "hash_schema": schema, "hashes": hashes,
                  "context_components": components,
                  "fixture_args": [os.path.relpath(os.path.abspath(p), ROOT)
                                   for p in fixture_paths],
                  "fixture_files": expand_fixture_files(fixture_paths)}
    json.dump(doc, open(out, "w"), ensure_ascii=False, indent=2)
    print(f"  contract manifest[{phase}]: hash_schema {schema}，"
          f"evaluator {hashes['evaluator'][:12]}、"
          f"evaluation_context {hashes['evaluation_context'][:12]}、"
          f"contract_fixtures {hashes['contract_fixtures'][:12]}、"
          f"rescore_runner {hashes['rescore_runner'][:12]}")
    return 0


def cmd_trace(out, rawdir, run_nonce=None):
    if os.path.exists(out):
        # 覆寫 = 讓「改 trace 再重建一份自洽 manifest」變成一行指令。要重建就先明確刪掉，
        # 而刪掉重建後的 digest 會與原始 run record 保存的值對不上——那才是真正的關卡。
        print(f"manifest: trace manifest 已存在，拒絕覆寫: {out}\n"
              f"  重建前請先確認你真的要放棄原始 trace 綁定，並明確刪除該檔。",
              file=sys.stderr)
        return 3
    if not os.path.isdir(rawdir):
        print(f"manifest: raw 目錄不存在: {rawdir}", file=sys.stderr)
        return 3
    files = {}
    for fn in sorted(os.listdir(rawdir)):
        if fn.endswith(TRACE_SUFFIXES):
            files[fn] = sha256_file(os.path.join(rawdir, fn))
    if run_nonce:
        # 逐檔核對 subject session 是不是真的帶著這一輪的 nonce 跑的。
        bad = []
        for fn in sorted(files):
            if not fn.endswith(".meta.json"):
                continue
            try:
                got = json.load(open(os.path.join(rawdir, fn))).get("run_nonce")
            except (OSError, ValueError) as e:
                bad.append(f"{fn}（無法讀取: {e}）")
                continue
            if got != run_nonce:
                bad.append(f"{fn}（run_nonce={got!r}）")
        if bad:
            print("manifest: 這些 .meta.json 沒有帶上本輪的 run_nonce，"
                  "拒絕產生 trace manifest:\n  " + "\n  ".join(bad), file=sys.stderr)
            return 3
    if not files:
        # 空 manifest 看起來與「全部核對通過」無法區分，是最危險的失敗模式。
        print("manifest: raw 目錄內沒有任何 .jsonl／.meta.json，拒絕產生空 trace manifest",
              file=sys.stderr)
        return 3
    digest = trace_digest(files)
    json.dump({"recorded_at": datetime.datetime.now().astimezone().isoformat(),
               "algorithm": "sha256", "digest": digest,
               "run_nonce": run_nonce, "files": files},
              open(out, "w"), ensure_ascii=False, indent=2)
    print(f"  trace manifest: {len(files)} 個檔案，digest {digest[:12]}")
    return 0


def expected_judge_files(fixture_paths):
    expected = set()
    for path in fixture_paths:
        try:
            doc = json.load(open(path))
        except (OSError, ValueError) as e:
            raise ValueError(f"fixture 檔無法讀取: {path} ({e})")
        suite = doc.get("skill_name") or doc.get("suite_name")
        fixtures = doc.get("fixtures")
        if not isinstance(suite, str) or not suite or not isinstance(fixtures, list):
            raise ValueError(f"fixture 檔缺 suite 名稱或 fixtures: {path}")
        for fixture in fixtures:
            fixture_id = fixture.get("id") if isinstance(fixture, dict) else None
            if not isinstance(fixture_id, str) or not fixture_id:
                raise ValueError(f"fixture id 缺失或格式錯誤: {path}")
            name = f"{suite}__{fixture_id}{JUDGE_SUFFIX}"
            if name in expected:
                raise ValueError(f"fixture 產生重複 judge 檔名: {name}")
            expected.add(name)
    return expected


def cmd_post_judge(out, rawdir, trace_path, fixture_paths):
    """在 judge 完成後綁定每份 `.judge.json`；目標存在時拒絕覆寫。"""
    if os.path.exists(out):
        print(f"manifest: post-judge manifest 已存在，拒絕覆寫: {out}", file=sys.stderr)
        return 3
    if not os.path.isdir(rawdir):
        print(f"manifest: raw 目錄不存在: {rawdir}", file=sys.stderr)
        return 3
    try:
        trace = json.load(open(trace_path))
        trace_files = trace["files"]
        if not isinstance(trace_files, dict) or not trace_files:
            raise ValueError("files 缺失或為空")
        expected = expected_judge_files(fixture_paths)
    except (OSError, ValueError, KeyError) as e:
        print(f"manifest: 無法建立 post-judge 綁定: {e}", file=sys.stderr)
        return 3
    actual = {name for name in os.listdir(rawdir) if name.endswith(JUDGE_SUFFIX)}
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        print(f"manifest: post-judge 檔案集合不符；缺少 {missing[:5]}、多出 {extra[:5]}",
              file=sys.stderr)
        return 3
    if not expected:
        print("manifest: fixture 集合為空，拒絕產生空 post-judge manifest", file=sys.stderr)
        return 3
    files = {name: sha256_file(os.path.join(rawdir, name)) for name in sorted(expected)}
    digest = trace_digest(files)
    trace_manifest_digest = trace_digest(trace_files)
    doc = {
        "manifest_version": POST_JUDGE_MANIFEST_VERSION,
        "kind": "post_judge",
        "recorded_at": datetime.datetime.now().astimezone().isoformat(),
        "algorithm": "sha256",
        "run_nonce": trace.get("run_nonce"),
        "trace_manifest_digest": trace_manifest_digest,
        "digest": digest,
        "files": files,
    }
    json.dump(doc, open(out, "w"), ensure_ascii=False, indent=2)
    print(f"  post-judge manifest: {len(files)} 個檔案，digest {digest[:12]}，"
          f"trace {trace_manifest_digest[:12]}")
    return 0


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    cmd = argv[0]
    if cmd == "snapshot":
        if len(argv) < 8:
            raise SystemExit(__doc__)
        return cmd_snapshot(argv[1], argv[2], argv[3], argv[4], argv[5], argv[6],
                            list(argv[7:]))
    if cmd == "contract-snapshot":
        if len(argv) < 5:
            raise SystemExit(__doc__)
        return cmd_contract_snapshot(argv[1], argv[2], argv[3], list(argv[4:]))
    if cmd == "trace":
        if len(argv) not in (3, 4):
            raise SystemExit(__doc__)
        return cmd_trace(argv[1], argv[2], argv[3] if len(argv) == 4 else None)
    if cmd == "post-judge":
        if len(argv) < 5:
            raise SystemExit(__doc__)
        return cmd_post_judge(argv[1], argv[2], argv[3], list(argv[4:]))
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
