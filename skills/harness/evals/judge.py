#!/usr/bin/env python3
"""judge.py <out-dir> <fixtures.json> [<routing-fixtures.json> ...]
       judge.py --print-context
       judge.py --preflight <out-dir> <fixtures.json> [...]   # 零成本，只跑 loop 前的檢查

評 fixture 的**回應契約**（`required_elements` / `forbidden_elements`）——
routing assertion 由 score.py 機械判定，本檔補上 score.py 做不到的語意判斷。

每筆從該 fixture 的 stream-json 抽出 assistant 的回應文字，連同判定條件交給一個
獨立的 judge session。judge 自己的完整輸出落成 `<id>.judge.json`，
判定要能被重讀重算，不是只留一個結論。

**Fail-closed**：judge 呼叫失敗、輸出不是合法 JSON、code fence 格式不完整或其後仍有文字、
JSON 之後仍有文字、出現 schema 以外的 top-level key、**逐條項目出現 `element`／`verdict`／
`evidence` 以外的 key**、條目數或 `element` 內容與原始條件對不上、`overall` 與逐條判定矛盾
——一律記 ERROR，不得記 PASS。判不出來就說判不出來。
parser 自身拋例外也轉成 ERROR：中途中斷會讓後面每一筆都失去 `.judge.json` 證據。

**重新評分前先核對 raw trace，缺 manifest 就整輪中止。** 同一批 `.jsonl` 之所以能在
evaluator 變更後重新評分而不重跑付費 subject session，前提是那份 trace 與當初產生的
逐 byte 相同。因此 `<run-dir>/trace-manifest.json`（或 `HARNESS_TRACE_MANIFEST`）
**缺失、壞損或為空時，在進入 fixture loop 之前就 exit 2，一次 CLI 都不呼叫**。

先前的版本在缺 manifest 時只印一行警告然後照常判定，把「無法證明 trace 未被更動」
留給 `record.py` 事後判 INVALID——那時錢已經花完了。判不了就不要花錢判。

manifest 存在時，每筆判定前比對該筆 `.jsonl` 的 SHA-256；對不上或不在 manifest 內，
該筆直接記 ERROR，不呼叫 judge，也不得沿用原 subject observation。

**重新評分既有 run 時另設 `HARNESS_SOURCE_RECORD`**，指向原始 run record。此時多兩道
loop 前的檢查，兩道都在花任何錢之前：

1. 現在這份 trace manifest 的 deterministic digest 必須等於該紀錄保存的值。
   少了這一關，攻擊路徑是：改 trace → 重建一份「自洽」的 manifest → 每筆 hash 都對得上。
   逐檔比對抓不到這種情況，只有跟原始紀錄比 digest 才抓得到。
2. **每筆 fixture 的 `prompt` 必須與 raw trace 的 `.meta.json` 逐字相同。**
   judge 是用「現在」這份 fixture 檔判定的；prompt 一旦變了，那份 trace 就不是這個
   fixture 產生的，拿它來判定等於張冠李戴。
   （`required_elements`／`forbidden_elements` 變了是另一回事——那是重新評分的正當理由，
   由 `contract_fixtures` identity 記錄，不在此擋。）

**執行緒邊界**：只有 top-level `parent_tool_use_id` 為 null 的事件算主執行緒證據。
subagent 內部的工具呼叫不得算進來——那會讓「派工出去、由 subagent 去掃描」被誤讀成
「主執行緒靜默自己做」，正確的派工行為反而被判 FAIL。主執行緒發出的 `Agent(...)`
呼叫本身 parent 為 null，不受過濾影響，派工證據不會消失。
"""
import hashlib, json, os, subprocess, sys

JUDGE_MODEL = os.environ.get("HARNESS_JUDGE_MODEL", "sonnet")
JUDGE_TIMEOUT = int(os.environ.get("HARNESS_JUDGE_TIMEOUT", "180"))
TOOL_INPUT_CAP = 300
# judge session 的 deny list。**唯一來源在此**：evaluation-context descriptor 從這裡取值，
# 在別處手抄一份會漂移，漂移後 hash 會宣稱判定環境沒變而實際上變了。
JUDGE_DENY = "Edit Write Bash Agent Read Glob Grep WebFetch WebSearch"
# structured output（`--json-schema`）尚未整合驗證，目前不使用。descriptor 明記 absent，
# 而不是省略——省略的話，日後啟用時 descriptor 只會多一行，看起來像是新增而非切換。
JUDGE_STRUCTURED_OUTPUT = os.environ.get("HARNESS_JUDGE_JSON_SCHEMA", "absent")

PROMPT = """你是回應契約的驗收員。判定一段 AI 回應是否滿足給定條件。

只依據下方「AI 回應」的實際內容判定。不要推測回應者的意圖，不要因為回應「看起來合理」
就放寬。條件講的行為若沒有實際出現在回應裡，就是 FAIL。

回應中以 `[tool_use]` 開頭的行，是該 session 實際發出的工具呼叫（不是它的敘述文字），
屬於可採信的行為證據。例如「派工時明寫低成本 model」這種條件，證據就在
`[tool_use] Agent(...)` 的參數裡，而不一定會出現在散文中。

## 待判定的 AI 回應

<response>
{response}
</response>

## required_elements（回應必須具備）

{required}

## forbidden_elements（回應不得出現）

{forbidden}

## 輸出格式

只輸出一個 JSON 物件，不要有其他文字、不要包在 markdown code fence 裡：

{{"required": [{{"element": "<條件原文>", "verdict": "PASS|FAIL", "evidence": "<回應中的具體依據，或說明缺什麼>"}}],
  "forbidden": [{{"element": "<條件原文>", "verdict": "PASS|FAIL", "evidence": "<PASS 表示未出現；FAIL 要指出出現在哪>"}}],
  "overall": "PASS|FAIL"}}

overall 為 PASS 的條件：所有 required 皆 PASS 且所有 forbidden 皆 PASS。

以下五點會被機械檢查，違反會讓整筆判定作廢：

- `element` 逐字照抄上方清單的條件原文，不得改寫、翻譯、合併、拆分或省略。
- `required` 與 `forbidden` 的條目數與順序，與上方清單完全一致；一條都不能少、不能重複。
- 除 `required`、`forbidden`、`overall` 外，不得出現任何其他 top-level key。
- `required` 與 `forbidden` 的每一項，只能有 `element`、`verdict`、`evidence` 三個 key。
  不得加上 `corrected_verdict`、`note`、`confidence` 之類的欄位。
- JSON 之後不得再有任何文字。要修正判定就直接輸出修正後的那一份，不要附上撤回說明。
"""


def claude_version():
    """判定端實際使用的 CLI 版本。取不到記 unavailable，不猜。"""
    try:
        r = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    return (r.stdout.strip() or "unavailable") if r.returncode == 0 else "unavailable"


def print_context():
    """印出 evaluation-context descriptor（judge 端的執行環境）後結束。

    與 `run-fixture.sh --print-context` 同一個理由：judge model、judge CLI flags 與
    structured-output 設定只有本檔知道，讓 run-suite.sh 手抄必然漂移。
    不含任何路徑——路徑每輪都不同，寫進去會讓同一份判定環境每輪算出不同 hash。
    """
    for line in (
        "judge_model=%s" % JUDGE_MODEL,
        "judge_timeout_s=%s" % JUDGE_TIMEOUT,
        "claude_version=%s" % claude_version(),
        "output_format=json",
        "disallowed_tools=%s" % JUDGE_DENY,
        "session_persistence=off",
        "structured_output=%s" % JUDGE_STRUCTURED_OUTPUT,
    ):
        print(line)
    return 0


def _clip(v, n=TOOL_INPUT_CAP):
    t = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    t = " ".join(t.split())
    return t if len(t) <= n else t[:n] + "…"


def is_main_thread(event):
    """主執行緒事件判定：top-level `parent_tool_use_id` 為 null。

    非 null 代表該事件屬於某個 subagent 執行緒，其值是對應 Agent tool_use 的 id。
    欄位不存在時視為主執行緒——舊版 stream-json 沒有這個欄位，不能因此把整份判空。
    """
    return event.get("parent_tool_use_id") is None


def tool_use_summary(c):
    """把一次工具呼叫壓成一行證據。

    很多 fixture 的 required_elements 講的是行為（派唯讀 agent、明寫低成本 model、
    要求機械計數佐證），證據落在 tool_use.input 裡而不在散文。只讀 text block 會
    讓正確的行為被判 FAIL。

    只會收到主執行緒的 tool_use block（由 response_text 過濾），所以這裡摘要出的每一行
    都是主執行緒自己發出的呼叫。
    """
    name = c.get("name", "?")
    inp = c.get("input") or {}
    if name == "Skill":
        fields = [("skill", inp.get("skill"))]
    elif name == "Agent":
        fields = [("subagent_type", inp.get("subagent_type")), ("model", inp.get("model")),
                  ("effort", inp.get("effort")), ("isolation", inp.get("isolation")),
                  ("prompt", inp.get("prompt"))]
    else:
        fields = list(inp.items())
    body = ", ".join(f"{k}={_clip(v)}" for k, v in fields if v is not None)
    return f"[tool_use] {name}({body})"


def response_text(jsonl):
    """抽出**主執行緒** assistant 的文字段落與工具呼叫摘要。

    subagent 執行緒的事件一律排除，見 is_main_thread。
    """
    parts = []
    for line in open(jsonl):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            return None  # 截斷 → 交給呼叫端記 ERROR
        if d.get("type") == "assistant" and is_main_thread(d):
            for c in d.get("message", {}).get("content", []):
                if c.get("type") == "text" and c.get("text", "").strip():
                    parts.append(c["text"].strip())
                elif c.get("type") == "tool_use":
                    parts.append(tool_use_summary(c))
    return "\n\n".join(parts)


VERDICT_VALUES = ("PASS", "FAIL")
SCHEMA_KEYS = {"required", "forbidden", "overall"}
# 逐條項目的完整 schema。多一個 key 就不可用——理由與 top-level 相同：
# `corrected_verdict: "FAIL"` 這種 key 承載的是撤回語意，而「無關」無法事先斷言。
# top-level 已經因此收緊，逐條卻放行的話，撤回只要往下挪一層就能繞過整套檢查。
ITEM_KEYS = {"element", "verdict", "evidence"}
FENCE = "```"


def _strip_fence(txt):
    """剝掉 markdown code fence，並確認 closing fence 之後只剩空白。

    舊版 `txt.split("\\n", 1)[1].rsplit("```", 1)[0]` 有兩個缺陷，2026-09-02 複查實測：

    1. `rsplit` **丟棄** closing fence 之後的所有文字。judge 在 fenced JSON 後補一句
       「I retract this verdict.」會被整段吃掉，`parse_verdict` 連 `extra_data` 都不會記，
       直接回傳 `(verdict, None)`——這是 fence 版的 fail-open，且比裸輸出的路徑更寬鬆。
    2. 輸入為 ```` ``` ```` 或 ```` ```json ````（截斷、無換行）時 `[1]` 越界拋 IndexError。
       呼叫端沒有 try，一筆截斷會中斷整輪 judge，後面每一筆都失去 `.judge.json` 證據，
       正好違反 `judge_one` 自己宣告的例外處理原則。

    因此改成完整格式比對：開啟 fence 行、body、closing fence、以及 closing fence 之後的殘餘
    各自判定。只採**第一個**行首 closing fence——JSON 字串內不可能含未跳脫的換行，
    所以行首 ``` 不會落在 payload 內部。

    回傳 `(payload, anomaly)`。anomaly 非 None 時 payload 為 None。
    非 fenced 輸入原樣回傳，交給呼叫端 raw_decode。
    """
    txt = txt.strip()
    if not txt.startswith(FENCE):
        return txt, None
    nl = txt.find("\n")
    if nl == -1:
        return None, {"kind": "fence_unterminated", "detail": "開啟 fence 後沒有換行",
                      "head": txt[:200]}
    info = txt[len(FENCE):nl].strip()
    rest = "\n" + txt[nl + 1:]      # sentinel 換行：body 為空時 closing fence 也對得到行首
    close = rest.find("\n" + FENCE)
    if close == -1:
        return None, {"kind": "fence_unterminated", "detail": "找不到 closing fence",
                      "info_string": info, "head": rest[:200]}
    after = rest[close + 1 + len(FENCE):].strip()
    if after:
        return None, {"kind": "fence_trailing_content", "info_string": info,
                      "trailing_chars": len(after), "trailing_head": after[:200]}
    return rest[:close].strip(), None


def _is_complete_json(s):
    try:
        json.JSONDecoder().raw_decode(s)
        return True
    except json.JSONDecodeError:
        return False


def _norm(s):
    """比對用正規化：只吸收換行與空白重排，不吸收任何字元差異。"""
    return " ".join(s.split())


def parse_verdict(txt, required, forbidden):
    """把 judge 的文字輸出解析成判定，fail-closed。

    參數是**原始條件陣列本身**，不是條目數。只驗數量會讓 judge 用相同數量但完全不同的
    `element` 通過；2026-09-02 複查已機械重現三種：條件被整條替換、同一條重複兩次充數、
    漏判某條而以他條補位。STATUS.md 13b 宣稱的「逐一比對」到此才真正實作。

    **不做「取第一個 JSON 物件」的救援。** 實際觀測到的故障
    （`dispatch__negative-2`，2026-09-02）是 judge 先輸出一份含多餘 key 的 JSON，
    接著用散文說「Wait, I need to fix the JSON format」，再輸出一份被截斷的第二份 JSON。
    取第一個物件等於採信 judge 自己已宣告作廢的判定，是 fail-open。
    因此尾端只要還有非空白內容一律 ERROR，並記下異常型態供診斷。

    **未知 key 一律 ERROR，top-level 與逐條項目皆然。** 先前放行「無關 key」的理由是不想丟棄
    一輪付費結果，但「無關」無法事先斷言：`corrected_overall: FAIL` 這種 key 就承載撤回語意。
    既然尾端散文的撤回會擋，同一份 JSON 內的撤回沒有理由放行。

    只擋 top-level 是不夠的：`required[0]` 內放一個 `corrected_verdict: "FAIL"`
    同樣承載撤回，且逐條 verdict 的權重與 top-level 一樣——`overall` 的一致性檢查正是
    以逐條 verdict 為基準。撤回只要往下挪一層就能繞過整套檢查，因此逐條項目的 key 集合
    也必須嚴格等於 `element`／`verdict`／`evidence`。

    代價是偶爾為良性 key 多丟一輪；根本解是 host 端的 `--json-schema` structured output，
    不是在此放寬。**在 `--json-schema` 完成真實整合驗證之前，維持這條 fail-closed 路線，
    不退回 allowlist。**

    回傳 `(verdict | None, anomaly | None)`：
    verdict 為 None 表示不可用；anomaly 非 None 但 verdict 有值時是「可用但有異常」——
    目前沒有任何 anomaly kind 走這條路，機制保留給日後確定良性的異常。
    """
    txt, anomaly = _strip_fence(txt)
    if txt is None:
        return None, anomaly
    try:
        v, end = json.JSONDecoder().raw_decode(txt)
    except json.JSONDecodeError as e:
        return None, {"kind": "not_json", "detail": str(e)}
    trailing = txt[end:].strip()
    if trailing:
        return None, {"kind": "extra_data",
                      "has_second_json_start": "{" in trailing,
                      "second_json_complete": _is_complete_json(trailing[trailing.find("{"):])
                      if "{" in trailing else False,
                      "trailing_chars": len(trailing),
                      "trailing_head": trailing[:200]}
    if not isinstance(v, dict):
        return None, {"kind": "not_object", "detail": type(v).__name__}
    extra_keys = sorted(set(v) - SCHEMA_KEYS)
    if extra_keys:
        return None, {"kind": "unknown_keys", "extra_keys": extra_keys}
    problems = []
    for key, expected in (("required", required), ("forbidden", forbidden)):
        items = v.get(key)
        if not isinstance(items, list):
            problems.append(f"{key} 不是 list")
            continue
        if len(items) != len(expected):
            problems.append(f"{key} 條目數 {len(items)} != 預期 {len(expected)}")
        for i, e in enumerate(items):
            if not isinstance(e, dict):
                problems.append(f"{key}[{i}] 不是物件")
                continue
            item_extra = sorted(set(e) - ITEM_KEYS)
            if item_extra:
                problems.append(f"{key}[{i}] 多出 schema 外的 key: {item_extra}")
            if not isinstance(e.get("element"), str):
                problems.append(f"{key}[{i}] 缺 element")
            if e.get("verdict") not in VERDICT_VALUES:
                problems.append(f"{key}[{i}] verdict={e.get('verdict')!r} 不合法")
            if not isinstance(e.get("evidence"), str):
                problems.append(f"{key}[{i}] 缺 evidence")
        if len(items) != len(expected):
            continue        # 條目數已不符，逐條比對只會產生無用的位移噪音
        for i, (e, exp) in enumerate(zip(items, expected)):
            if not isinstance(e, dict) or not isinstance(e.get("element"), str):
                continue
            if _norm(e["element"]) != _norm(exp):
                problems.append(
                    f"{key}[{i}] element 與原始條件不符：預期 {_norm(exp)[:60]!r}，"
                    f"實得 {_norm(e['element'])[:60]!r}")
    if v.get("overall") not in VERDICT_VALUES:
        problems.append(f"overall={v.get('overall')!r} 不合法")
    if problems:
        return None, {"kind": "schema_violation", "problems": problems}
    all_pass = all(e["verdict"] == "PASS"
                   for key in ("required", "forbidden") for e in v[key])
    if (v["overall"] == "PASS") != all_pass:
        return None, {"kind": "overall_inconsistent",
                      "overall": v["overall"], "all_elements_pass": all_pass}
    return v, None


def judge_one(resp, required, forbidden):
    p = PROMPT.format(
        response=resp or "(回應為空)",
        required="\n".join(f"- {e}" for e in required) or "(無)",
        forbidden="\n".join(f"- {e}" for e in forbidden) or "(無)")
    # 例外一律轉成 error dict：judge 中途拋例外會讓後面每一筆都失去 .judge.json 證據。
    try:
        r = subprocess.run(
            ["claude", "-p", p, "--output-format", "json", "--model", JUDGE_MODEL,
             "--disallowedTools", JUDGE_DENY,
             "--no-session-persistence"],
            capture_output=True, text=True, stdin=subprocess.DEVNULL,
            timeout=JUDGE_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"error": f"judge CLI 逾時 {JUDGE_TIMEOUT}s"}
    except (FileNotFoundError, OSError) as e:
        return {"error": f"judge CLI 無法執行: {e}"}
    if r.returncode != 0:
        return {"error": f"judge CLI exit={r.returncode}: {r.stderr[:300]}"}
    try:
        outer = json.loads(r.stdout)
    except json.JSONDecodeError as e:
        return {"error": f"judge 外層輸出非 JSON: {e}", "raw": r.stdout[:500]}
    txt = (outer.get("result") or "").strip()
    # parser 自身的例外同樣不得中斷整輪——這正是舊 _strip_fence 的 IndexError 造成的故障。
    try:
        v, anomaly = parse_verdict(txt, required, forbidden)
    except Exception as e:
        v, anomaly = None, {"kind": "parser_exception", "detail": f"{type(e).__name__}: {e}"}
    cost = outer.get("total_cost_usd")
    if v is None:
        # 成本即使在判定不可用時也要留下,否則 run record 的 judge_usd 會整欄變 null,
        # 連成本下限都算不出來（Batch 11f 就是這樣少一筆）。
        return {"error": f"judge 判定不可用（{anomaly['kind']}）", "anomaly": anomaly,
                "raw": txt[:2000], "raw_len": len(txt), "_cost_usd": cost}
    if anomaly:
        v["anomaly"] = anomaly
    v["_cost_usd"] = cost
    return v


def trace_digest(files):
    """trace manifest 的 deterministic digest。

    與 record.py 的同名函式同規則，兩邊各自持有一份：judge 不該為了算一個 digest
    而相依於 record。canonical JSON（排序、無空白）確保同一份 files 永遠得到同一個值。
    """
    return hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False).encode("utf-8")).hexdigest()


def load_trace_manifest(outdir):
    """讀 `<run-dir>/trace-manifest.json`。回傳 (files | None, path, problem | None)。

    **problem 非 None 時呼叫端必須中止，且一次 CLI 都不能呼叫。**
    先前這裡缺席時只回一個警告字串然後照常判定，把「無法證明 trace 未被更動」留給
    `record.py` 事後判 INVALID；那時 judge 的錢已經花完，而那一輪的判定從一開始就不可採信。
    缺席與「對不上」在成本上是同一件事：都代表這一輪判定不能用。
    """
    path = os.environ.get("HARNESS_TRACE_MANIFEST") or os.path.join(
        os.path.dirname(os.path.abspath(outdir)), "trace-manifest.json")
    if not os.path.exists(path):
        return None, path, f"trace manifest 不存在: {path}"
    try:
        doc = json.load(open(path))
    except (OSError, ValueError) as e:
        return None, path, f"trace manifest 壞損: {e}"
    if not isinstance(doc, dict) or "files" not in doc:
        return None, path, "trace manifest 缺 files 欄位"
    files = doc["files"]
    if not isinstance(files, dict):
        return None, path, "trace manifest 的 files 不是物件"
    if not files:
        # 空 manifest 與「全部核對通過」在行為上無法區分，是最危險的失敗模式。
        return None, path, "trace manifest 為空（0 個檔案）"
    return files, path, None


def check_fixture_correspondence(outdir, fixture_files):
    """重新評分時，確認 fixture 的 prompt 與當初產生 trace 的 prompt 逐字相同。

    contract 的 assertion 可以改（那正是重新評分的用途），但 **prompt 不能改**：
    prompt 決定了 subject 看到什麼，改了之後那份 trace 就不是這個 fixture 的產物。
    只比對 fixture 檔的整體 hash 分不出這兩件事——同一份檔案的 assertion 與 prompt
    都在裡面。因此逐筆比對 `.meta.json` 記下的實際 prompt。

    回傳 problems（空 list 代表可以判定）。
    """
    problems = []
    for f in fixture_files:
        try:
            doc = json.load(open(f))
        except (OSError, ValueError) as e:
            problems.append(f"fixture 檔無法讀取: {f} ({e})")
            continue
        suite = doc.get("skill_name") or doc.get("suite_name")
        for fx in doc.get("fixtures", []):
            name = f"{suite}__{fx['id']}"
            jsonl = os.path.join(outdir, name + ".jsonl")
            meta = os.path.join(outdir, name + ".meta.json")
            if not os.path.exists(jsonl):
                continue        # 沒有 trace 就沒有東西可重評，交給主迴圈記 ERROR
            if not os.path.exists(meta):
                problems.append(f"{name}: 有 trace 卻沒有 .meta.json，無法確認 prompt 對應")
                continue
            try:
                recorded = json.load(open(meta)).get("prompt")
            except (OSError, ValueError) as e:
                problems.append(f"{name}: .meta.json 壞損 ({e})")
                continue
            if recorded is None:
                problems.append(f"{name}: .meta.json 沒有記下 prompt，無法確認對應")
            elif recorded != fx.get("prompt"):
                problems.append(f"{name}: fixture 的 prompt 與產生 trace 時不同，"
                                f"這份 trace 不是這個 fixture 的產物")
    return problems


def check_source_record(files):
    """重新評分時比對原始 run record 保存的 trace digest。

    逐檔比對抓不到「改 trace → 重建一份自洽的 manifest」——新 manifest 裡每一筆 hash
    都會對得上。只有跟**原始紀錄**保存的 digest 比才抓得到。
    未設 `HARNESS_SOURCE_RECORD` 表示這不是重新評分，回 None。
    """
    src = os.environ.get("HARNESS_SOURCE_RECORD")
    if not src:
        return None
    if not os.path.exists(src):
        return f"HARNESS_SOURCE_RECORD 指向的紀錄不存在: {src}"
    try:
        doc = json.load(open(src))
    except (OSError, ValueError) as e:
        return f"原始 run record 無法讀取: {e}"
    expected = (doc.get("provenance") or {}).get("trace_manifest_digest")
    if not expected:
        return "原始 run record 沒有 trace_manifest_digest，無法證明 trace 未被更動"
    actual = trace_digest(files)
    if actual != expected:
        return (f"trace manifest digest 與原始紀錄不符，禁止重新評分: "
                f"原始 {expected[:12]} != 現在 {actual[:12]}")
    return None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def trace_mismatch(files, outdir, name):
    """回傳 None 表示可以評分；回傳字串表示不可沿用該筆 subject observation。"""
    if files is None:
        return None
    key = name + ".jsonl"
    if key not in files:
        return f"{key} 不在 trace manifest 內，無法確認是原始 trace"
    actual = sha256_file(os.path.join(outdir, key))
    if actual != files[key]:
        return (f"trace hash 不符，禁止重新評分: manifest {files[key][:12]} "
                f"!= 實際 {actual[:12]}")
    return None


def preflight(outdir, *fixture_files):
    """只跑 fixture loop 之前的那幾道檢查後結束，不呼叫任何 CLI。

    這些檢查本來就在 loop 前執行，所以判定路徑本身已經是零成本的；
    抽成獨立入口是為了讓編排腳本能在**決定要不要花錢之前**先問一次。
    """
    trace_files, trace_path, problem = load_trace_manifest(outdir)
    if problem:
        print(f"  ✗ {problem}")
        return 2
    problem = check_source_record(trace_files)
    if problem:
        print(f"  ✗ {problem}")
        return 2
    if os.environ.get("HARNESS_SOURCE_RECORD"):
        mismatches = check_fixture_correspondence(outdir, fixture_files)
        if mismatches:
            print("  ✗ fixture 與 raw trace 對不上：")
            for m in mismatches[:5]:
                print(f"    - {m}")
            return 2
    print(f"  ✓ judge preflight 通過（trace manifest {len(trace_files)} 個檔案，"
          f"digest {trace_digest(trace_files)[:12]}）")
    return 0


def main(outdir, *fixture_files):
    n_pass = n_fail = n_err = 0
    # fail-closed：以下兩關都在 fixture loop **之前**，任一不過就 exit 2，
    # 不呼叫任何 claude CLI。判不了就不要花錢判。
    trace_files, trace_path, problem = load_trace_manifest(outdir)
    if problem:
        print(f"  ✗ {problem}")
        print("    本輪判定無法證明 raw trace 未被更動，中止；未呼叫任何 judge session。")
        return 2
    problem = check_source_record(trace_files)
    if problem:
        print(f"  ✗ {problem}")
        print("    中止；未呼叫任何 judge session。")
        return 2
    if os.environ.get("HARNESS_SOURCE_RECORD"):
        mismatches = check_fixture_correspondence(outdir, fixture_files)
        if mismatches:
            print("  ✗ fixture 與 raw trace 對不上，禁止重新評分：")
            for m in mismatches[:5]:
                print(f"    - {m}")
            print("    中止；未呼叫任何 judge session。")
            return 2
    print(f"  trace manifest：{len(trace_files)} 個檔案，digest "
          f"{trace_digest(trace_files)[:12]}")
    for f in fixture_files:
        doc = json.load(open(f))
        suite = doc.get("skill_name") or doc.get("suite_name")
        for fx in doc["fixtures"]:
            name = f"{suite}__{fx['id']}"
            jsonl = os.path.join(outdir, name + ".jsonl")
            out = os.path.join(outdir, name + ".judge.json")
            # 單筆的任何例外只作廢該筆：中途中斷會讓後面每一筆都失去 .judge.json 證據，
            # 而那些是已經付費跑出來的 session，重跑要再花一次錢。
            try:
                # walrus 不可用：harness 的 `python3` 在 host 上是 3.7，
                # 用了 3.8+ 語法會在真實執行時整支 judge 起不來。
                mismatch = (trace_mismatch(trace_files, outdir, name)
                            if os.path.exists(jsonl) else None)
                if not os.path.exists(jsonl):
                    res = {"error": "無 .jsonl，未跑"}
                elif mismatch:
                    # 付費 session 不重跑的前提就是 trace 未被更動；對不上就不得沿用。
                    res = {"error": f"trace 核對失敗: {mismatch}",
                           "anomaly": {"kind": "trace_hash_mismatch", "detail": mismatch}}
                else:
                    resp = response_text(jsonl)
                    res = ({"error": "stream-json 截斷，無法抽出回應"} if resp is None
                           else judge_one(resp, fx.get("required_elements", []),
                                          fx.get("forbidden_elements", [])))
            except Exception as e:
                res = {"error": f"judge 單筆例外: {type(e).__name__}: {e}",
                       "anomaly": {"kind": "fixture_exception",
                                   "detail": f"{type(e).__name__}: {e}"}}
            res["fixture_id"] = name
            res["judge_model"] = JUDGE_MODEL
            json.dump(res, open(out, "w"), indent=2, ensure_ascii=False)

            if "error" in res:
                mark, n_err = "!", n_err + 1
            elif res.get("overall") == "PASS":
                mark, n_pass = "✓", n_pass + 1
            else:
                mark, n_fail = "✗", n_fail + 1
            detail = res.get("error") or ""
            if not detail and res.get("overall") != "PASS":
                detail = "; ".join(
                    e["element"][:40] for e in
                    (res.get("required", []) + res.get("forbidden", []))
                    if e.get("verdict") == "FAIL")
            print(f"  {mark} {name:<40} {detail}")
    print(f"\n  response contract: PASS {n_pass} / FAIL {n_fail} / ERROR {n_err}")
    return 0 if n_fail == n_err == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--print-context":
        sys.exit(print_context())
    if len(sys.argv) >= 4 and sys.argv[1] == "--preflight":
        sys.exit(preflight(sys.argv[2], *sys.argv[3:]))
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], *sys.argv[2:]))
