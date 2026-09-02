# 獨立驗收 r2：tiny-agents-skills harness provenance（hash schema v6）

你是這份產出物的獨立驗收者。**只做驗收，不做修復。**
本文不提供修改歷史與實作者論證；你要驗的是「現在的程式碼是否滿足下列條件」。

repo 內沒有 `AGENTS.md`。開始前先讀
`skills/discipline/judgment/references/verifier.md`；本文件與該檔是本次驗收的適用指示。
本文件把 A～I 定義為九個驗收條件，編號子項是各條件的必要檢查。

版本標記：

- acceptance revision：`r2`
- repository baseline commit：`b96f41049a3a736dab320ccc5e848ac872377c50`
- 前版 `ACCEPTANCE.md` SHA-256：`4db7c8cc7ac733280d19a9a51ec896e5b7d1d25e172802f8ec6c6f12cc351033`
- 受驗 `record.py` SHA-256：`f59becd79d780873e021a3059464b3f3734f66355948c3b7bef1f4dc99dfe593`


## 0. 執行規則（違反即整份驗收作廢）

- **禁止付費 session。** 不得執行 `claude -p`、不得跑 `run-suite.sh`（不帶 `--dry-run`）、
  不得跑 `run-rescore.sh` 對真實 `claude` 執行。
  例外：`claude --version` 可以（純版本查詢，不起 session）。下列測試腳本內部會呼叫它。
- **不得修改 repo。** 不 commit、不 push、不發布、不 `npx skills`、不動任何檔案。
- **會寫檔的測試只能在 mktemp 副本執行**（下方 SETUP 已備妥）。
  唯讀檢查（`cat`／`grep`／`sed -n`／`bundle-hash.sh`）可直接對原始 repo 執行。
- 固定完成 A～I 九組檢查；出現 FAIL 也繼續完成其餘既定檢查，但不要擴張範圍、修復或重跑修正後版本。
- 每個子項的指令、exit code 與實際輸出寫入暫存 evidence log；最終回覆只對 A～I 九組輸出
  `PASS` / `FAIL` / `UNVERIFIABLE` 與證據摘要，不超過 40 行。
- `UNVERIFIABLE` 用於「在本次限制下無法判定」，要寫清楚缺什麼。

## 1. 產出物

repo：`/Users/tinywu/Desktop/Apps/tiny-agents-skills`

受驗檔案：

```
scripts/bundle-hash.sh
scripts/run-rescore.sh
scripts/hash-domain-selftest.sh
scripts/run-provenance-selftest.sh
skills/harness/evals/manifest.py
skills/harness/evals/judge.py
skills/harness/evals/record.py
skills/harness/evals/run-suite.sh
skills/harness/evals/run-fixture.sh
skills/harness/evals/{judge,record,score,transport}_selftest.py
```

文件（**最後一步才看，不得作為實作證據**）：
`skills/harness/README.md`、`skills/harness/evals/STATUS.md`、
`skills/harness/evals/KNOWN-ISSUES.md`

宣稱的 identity（`hash_schema v6`、`manifest_version 2`）：

| domain | 量測指令 | 宣稱值 |
|---|---|---|
| `hash_schema` | `sh scripts/bundle-hash.sh schema-version` | `v6` |
| `dispatch_skill` | `sh scripts/bundle-hash.sh skill skills/harness/dispatch` | `2d6c0d99b1c4ca927e2c06c82e065c389fa6a6b8ddbc325b0e9bde9bc071c4fc` |
| `judgment_skill` | `sh scripts/bundle-hash.sh skill skills/discipline/judgment` | `0c5a3deaec63cb3c39c1aea4b0b6417784a734d33b3b1ad3edf84334738de7ac` |
| `token_preflight_skill` | `sh scripts/bundle-hash.sh skill skills/discipline/token-preflight` | `be72017e9fc7952e9a403cf90e951669496b08f4339938bc73a2829d44ef592a` |
| `evaluator` | `sh scripts/bundle-hash.sh evaluator skills/harness` | `feddd58c1acd2e2b952384e799afdd6e87cb39e60d3bf38c1bd99e6e859d7133` |
| `runner` | `sh scripts/bundle-hash.sh runner skills/harness` | `005ed2f71ac49a8b6747dd1c43f42c8ee67315a9fb3ec8ce395f921ccf6cee3c` |
| `fixtures`（judgment） | `sh scripts/bundle-hash.sh fixtures skills/discipline/judgment/evals/fixtures.json skills/harness/evals/routing-fixtures.json skills/harness/evals/seed` | `c7559b7168d92ceba6304cefa78a234185b07e640eb51a179d87dd4d759de52c` |
| `fixtures`（default） | `sh scripts/bundle-hash.sh fixtures skills/harness/dispatch/evals/fixtures.json skills/harness/evals/routing-fixtures.json skills/harness/evals/seed` | `a5413158ee621cebfcb595ef4562acc4fcc3d8ec1dd7f33763551122d1afe1c5` |
| `rescore_runner` | `sh scripts/bundle-hash.sh rescore-runner` | `2301a9daa8d90536e31b64f571767307e27a541fc369920bd882960354660b28` |

`execution_context` 與 `evaluation_context` 綁定 run 當下的規則檔／settings／descriptor，
不是 repo 內容，**不在本次驗收範圍**。

## SETUP（每次會寫檔的測試都在這裡跑）

```bash
SRC=/Users/tinywu/Desktop/Apps/tiny-agents-skills
WORK=$(mktemp -d)
EVIDENCE=$(mktemp -d)
( cd "$SRC" && find . -path ./.git -prune -o -type f -print \
  | while IFS= read -r f; do mkdir -p "$WORK/$(dirname "$f")"; cp -p "$SRC/$f" "$WORK/$f"; done )
echo "WORK=$WORK"
echo "EVIDENCE=$EVIDENCE"
```

之後所有「跑測試」都在 `$WORK` 內執行；「量 hash／讀原始碼」對 `$SRC` 執行。
（`bundle-hash.sh` 宣稱路徑無關；A-1 會驗這件事。）

每次 shell tool call 都可能是新 process，不得假設 `SRC`／`WORK`／`EVIDENCE` 會自動保留；
記下上方印出的絕對路徑，之後每個 tool call 都明確重設三個變數或直接使用絕對路徑。

在執行任何檢查前，於 `$EVIDENCE` 建立唯讀 tree-fingerprint helper：使用
`os.walk(..., followlinks=False)` 對 `$SRC/.git` 以外的每個 entry 記錄相對路徑、型態、mode；
一般檔案另記 SHA-256，symlink 另記 target。將排序後結果的 SHA-256 寫入
`$EVIDENCE/src-before.sha256`。H-8 以同一 helper 重新量測，不得只依賴 `git status`。

---

## A. identity 與 hash

**A-1** 對 `$SRC` 執行上表九個量測指令，逐一比對宣稱值。全部相符才 PASS。

**A-2** 對 `$WORK` 執行同樣九個指令（`cd "$WORK"`），結果必須與 `$SRC` **完全相同**。
不同即 FAIL（路徑無關性不成立，所有 hash 宣稱失去意義）。

**A-3** `grep -n 'MANIFEST_VERSION' "$SRC/skills/harness/evals/manifest.py"` 應為 `2`；
`grep -n 'SUPPORTED_MANIFEST_VERSIONS' "$SRC/skills/harness/evals/record.py"` 應為 `(2,)`。
兩者必須一致。

**A-4** `record.py` 的 domain 常數必須恰好是：

```
REQUIRED_DOMAINS   dispatch_skill judgment_skill token_preflight_skill
                   evaluator runner fixtures execution_context evaluation_context   （8）
CONTRACT_DOMAINS   evaluator evaluation_context contract_fixtures rescore_runner     （4）
SUBJECT_DOMAINS    REQUIRED_DOMAINS 扣掉 evaluator 與 evaluation_context             （6）
```

用 `python3 -c` 直接 import 讀常數驗證，不要只看原始碼字面。

---

## B. run-rescore 的 run id 字元與 containment

以下每一項都必須 **exit code 2**，且**不得在 `derived/` 之外建立或刪除任何東西**。
被拒的 run id 也不得留下 `derived/<id>` 目錄。

在 `$WORK` 內自行造一個最小來源 run 目錄後測試（或直接用不存在的來源目錄——
字元檢查在任何其他檢查之前，仍應回 2）。

**B-1** `../../victim`
**B-2** `a/b`
**B-3** `.hidden`（以 `.` 開頭）
**B-4** 空字串
**B-5** `x;rm`
**B-6** `with space`
**B-7** 含 `LF`：`$(printf 'safe\nline')`
**B-8** 純 `LF`
**B-9** 含 `CR`
**B-10** 含 `TAB`
**B-11** 含 ANSI escape（`$(printf '\033')[31mred`）

**B-12** 拒絕訊息**不得包含原始控制字元**（用 `grep -c $'\033'` 或 `od -c` 檢查輸出）。

**B-13** `derived/` 本身是指向 repo 外的 symlink 時，即使 run id 合法也必須 exit 2，
且該外部目錄**未被刪除**。

**B-14** 上述每一個被拒案例執行後，來源 run 目錄與其父目錄下不得出現新目錄。
用執行前後的 `find` 快照比對。

判定重點：驗證邏輯不得依賴命令替換的輸出是否為空——`$( )` 會剝掉尾端換行。
你可以自行構造測試確認 `safe<LF>line` 確實被拒。

---

## C. 重新評分不得寫入來源

**C-1** 造一個來源 run 目錄，其中 `raw/*.judge.json` 放一個可辨識的 marker 字串。
記下 `raw/` 的內容指紋（逐檔 sha256 的摘要）。

**C-2** 以 PATH 前置的假 `claude`（不呼叫真實 CLI）跑一次 `run-rescore.sh`。
執行後來源 `raw/` 的內容指紋必須**逐 byte 相同**，marker 必須還在。

**C-3** 新的 `.judge.json` 必須出現在 `derived/<id>/raw/`，且**不含**來源的 marker。

**C-4** derived record 必須寫在 `derived/<id>/` 內，不得覆寫來源 run record。

---

## D. preflight 必須排在付費 judge 之前

**D-1** 讓來源 run record 的某個 subject hash 變成 `null`（或非 64 位 hex），
跑 `run-rescore.sh`，用會累計呼叫次數的假 `claude` 統計。
要求：exit 非 0、**未產生 derived record**、且 judge 判定次數為 0
（只允許 `--print-context` 造成的 `--version` 查詢）。

**D-2** 缺 `--migration-audit` 而來源 `hash_schema` 與現行不同時，同樣必須在 judge 之前中止。

**D-3** `record.py --validate-only` 必須**不寫任何檔案**：合法輸入回 0、
壞損輸入回非 0，兩種情況下都不得產生 run record。

**D-4** `judge.py --preflight` 必須零成本：trace manifest 缺失／壞損／為空三種情況
各自 exit 2 且 CLI 呼叫次數 0。

---

## E. run nonce 鏈

`record.py` 判定 `evidence_class` 時**不得採信任何環境變數**。

**E-1** 用 `python3 -c` 直接呼叫 `record.check_nonce_chain`。以下四種情形的 origin
都必須是 `unknown`：manifest 無 `run_nonce`／trace manifest 的 nonce 不符／
某份 `.meta.json` 無 nonce／某份 `.meta.json` 的 nonce 不符。四方一致
（manifest、trace manifest、全部 `.meta.json`）時 origin 才能是 `contemporaneous`。

**E-2** 另走 `record.main()` 驗映射結果：E-1 的四種不完整情形都必須得到
`evidence_class=legacy_diagnostic` 且 `is_contract_evidence=false`；完整一致時才得到
`evidence_class=contract_evidence` 且 `is_contract_evidence=true`。

**E-3** **反例必驗（行為為主）**：設定 `HARNESS_TRACE_MANIFEST_ORIGIN=contemporaneous`
且 nonce 鏈不完整時，結果仍必須是 `legacy_diagnostic` 且 `is_contract_evidence=false`。

上述行為測試是主判準且必驗。以下 AST 檢查是**輔助**，不得取代行為測試；兩者任一不過即 FAIL。
輔助檢查只辨識常數名稱的 `os.environ.get(...)`、`os.getenv(...)`、`os.environ[...]`，
而且 receiver 必須是名為 `os` 的 `ast.Name`。註解與 docstring 不構成環境變數讀取，不得因字串命中判 FAIL。

literal helper 分別處理三條路徑：`ast.Constant(str)` 是主要路徑；`ast.Str` 支援 Python 3.8–3.13，
已於 Python 3.14 移除；`ast.Index` 支援 Python 3.7–3.8 的 subscript 包裝，官方自 3.9 標為 deprecated，
尚未公告移除版本。後兩者以 `getattr` 守衛，不得用通用的 `hasattr(slice, "value")` 解包。
版本資訊來源：[Python 3.15 `ast` 官方文件](https://docs.python.org/3.15/library/ast.html)（查閱 2026-09-03）。

將下列完整 code block 存成 checker 後，以受驗 `record.py` 的絕對路徑作唯一參數執行：

<!-- E3_CHECKER_START -->
```python
#!/usr/bin/env python3
import ast
import json
import os
import platform
import sys
from collections import OrderedDict

TARGET_NAME = "HARNESS_TRACE_MANIFEST_ORIGIN"
_STR = getattr(ast, "Str", ())
_IDX = getattr(ast, "Index", ())


def literal_string(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, _STR):
        return node.s
    if isinstance(node, _IDX):
        return literal_string(node.value)
    return None


def is_os_name(node):
    return isinstance(node, ast.Name) and node.id == "os"


def is_os_environ(node):
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "environ"
        and is_os_name(node.value)
    )


def inspect_target(target):
    with open(target, encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), filename=target)
    reads = []
    for node in ast.walk(tree):
        literal = None
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.args
        ):
            if node.func.attr == "get" and is_os_environ(node.func.value):
                literal = literal_string(node.args[0])
            elif node.func.attr == "getenv" and is_os_name(node.func.value):
                literal = literal_string(node.args[0])
        elif isinstance(node, ast.Subscript) and is_os_environ(node.value):
            literal = literal_string(node.slice)
        if literal is not None:
            reads.append(literal)
    return sorted(set(reads))


def emit(status, target, reads):
    forbidden = sorted(name for name in reads if name == TARGET_NAME)
    payload = OrderedDict((
        ("status", status),
        ("target", target),
        ("python", platform.python_version()),
        ("all_env_reads", reads),
        ("forbidden_reads", forbidden),
    ))
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def main():
    target = os.path.abspath(
        sys.argv[1] if len(sys.argv) > 1 else "skills/harness/evals/record.py"
    )
    reads = []
    try:
        if len(sys.argv) != 2:
            raise ValueError("expected exactly one target path")
        reads = inspect_target(target)
        status = "forbidden" if TARGET_NAME in reads else "clean"
    except Exception as exc:
        status = "error"
        sys.stderr.write("E-3 checker error: %s\\n" % exc)
    emit(status, target, reads)
    return {"clean": 0, "forbidden": 1, "error": 2}[status]


if __name__ == "__main__":
    sys.exit(main())
```
<!-- E3_CHECKER_END -->

stdout 必須恰好有一個 JSON object，欄位固定為：

```json
{"status":"clean|forbidden|error","target":"<絕對路徑>","python":"<version>","all_env_reads":[],"forbidden_reads":[]}
```

`all_env_reads` 與 `forbidden_reads` 必須排序去重；目標名稱以
`== "HARNESS_TRACE_MANIFEST_ORIGIN"` 比對，不得使用 substring。
exit code 三態不得合併：`0` = clean；`1` = 找到 forbidden read，屬受測物問題；
`2` = checker 自身異常，屬量尺問題。exit 2 判 **UNVERIFIABLE**，不得判 FAIL；stdout
空白或不是單一合法 JSON object 一律不得視為 clean，同樣判 UNVERIFIABLE。

**E-4** derived record 的證據等級取自**來源紀錄**的宣告：來源標記非 `contemporaneous` 時，
derived record 必須是 `legacy_diagnostic`。

---

## F. derived record 的 identity 兩半

**F-1** derived record 的 `hashes` 必須恰好 10 個 domain（6 subject + 4 contract）。

**F-2** `hash_provenance` 必須逐 domain 標明來源：6 個 subject domain 為 `source_run`，
4 個 contract domain 為 `measured_now`。

**F-3** `derived_from.rescored_with` 的 `evaluator` 必須等於**本次量測值**，
不等於來源紀錄裡的值。

**F-4** 重評時傳入 full manifest（kind=full）必須被拒；
原生 run 傳入 contract manifest 必須被拒。

**F-5** 跨 `hash_schema` 時，`--migration-audit` 缺失、逐 domain `equivalent` 非 `true`、
`evidence` 或 `method` 為空、缺 domain、多出未知 domain，任一情形都必須 `INVALID`。

---

## G. exit code

用假 `claude` 指定 judge 的回應內容，驗證 `run-rescore.sh` 的三種結果：

**G-1** judge 全數 PASS → exit **0**，derived record 存在。
**G-2** judge 判出 contract FAIL → exit **非 0**，且 derived record **仍保留**、
`run_status` 為 `FAIL`。
**G-3** judge 判定不可用（ERROR）→ exit **非 0**，derived record 的 `run_status` 為 `INVALID`。
**G-4** preflight 或 containment 不通過 → exit **2**。

---

## H. 零成本測試與 dry-run

全部在 `$WORK` 執行。

**H-1** 以下四支必須**分別執行**，全部 exit 0，逐支記下 `ok` 項數；不得把四個路徑
一起傳給一次 `python3`（那只會執行第一支，其餘會變成 `sys.argv`）：

```bash
selftest_rc=0
for name in judge record score transport; do
  python3 "skills/harness/evals/${name}_selftest.py" || selftest_rc=1
done
[ "$selftest_rc" -eq 0 ]
```

**H-2** `python3 -m py_compile skills/harness/evals/*.py` 通過。
另確認直譯器版本：本專案要求 **Python 3.7 相容**。只有實際用 Python 3.7 執行
`py_compile` 與四支 selftest 才能把相容性判 PASS；環境不是 3.7 時，其他結果照常記錄，
但「Python 3.7 相容」這一子項記 UNVERIFIABLE，不得以較新版本代理。
**H-3** `sh -n` 對六支 shell（`bundle-hash`、`hash-domain-selftest`、
`run-provenance-selftest`、`run-rescore`、`run-suite`、`run-fixture`）逐支執行並全部通過；
不得把多個檔名一起交給一次 `sh -n`。
**H-4** `sh scripts/hash-domain-selftest.sh` → 全部通過，記下案例數。
**H-5** `sh scripts/run-provenance-selftest.sh` → 全部通過，記下 `ok` 項數。
（此腳本內部會呼叫 `claude --version`；那不是 session。若你的環境沒有 `claude`，
記為 UNVERIFIABLE 並說明。）
**H-6** `sh skills/harness/evals/run-suite.sh --dry-run` → **18** 筆。
**H-7** `HARNESS_FX=skills/discipline/judgment/evals/fixtures.json
sh skills/harness/evals/run-suite.sh --dry-run` → **28** 筆。
**H-8** 上述任何一支測試都不得寫入 `$SRC`。執行完後用 SETUP 所述的同一 helper
重新量測 `$SRC`，結果必須與 `$EVIDENCE/src-before.sha256` 完全相同；此 fingerprint
必須涵蓋 tracked、untracked、ignored files 與 symlink。另比對 `git status --short`
作輔助證據，但不得單獨用它判 PASS（例如 `.gitignore` 會隱藏 `__pycache__/`）。

---

## I. 文件一致性（**最後一步**）

在 A～H 全部完成後才讀 `README.md`、`STATUS.md`、`KNOWN-ISSUES.md`。
**這三份不得作為任何實作條件的證據**；只驗它們與你實測到的行為是否一致。

**I-1** 文件所述的 domain 清單、`hash_schema`、`manifest_version`、
`run-rescore.sh` 的 exit code 語意，與你實測結果一致。
**I-2** 文件宣稱「已修正」的項目，與你在 A～H 的實測結果不矛盾。
**I-3** 文件標為 `NOT_RUN`／`UNVERIFIABLE` 的項目（完整 `run-suite.sh` 控制流、
nonce 鏈的 runner 端、`--json-schema`、絕對路徑 `Read` 隔離）確實仍未驗證——
文件不得宣稱它們已通過。

---

## 輸出格式

完整的 50 個子項證據寫入 `$EVIDENCE/acceptance-evidence.md`，每項包含指令、exit code、
輸出摘要與判定。最終回覆遵守 `verifier.md` 的 40 行上限，只輸出九組：

```
判定: PASS / FAIL / UNVERIFIABLE（版本: hash_schema v6 + 八個 domain hash）
A. identity 與 hash — PASS／FAIL／UNVERIFIABLE（A-1～A-4 摘要）
B. run id 與 containment — PASS／FAIL／UNVERIFIABLE（B-1～B-14 摘要）
...
I. 文件一致性 — PASS／FAIL／UNVERIFIABLE（I-1～I-3 摘要）
Evidence log: <絕對路徑>
未驗證項目: <項目與原因；沒有則寫「無」>
可否進入 v6 native smoke: 是／否
```

組內任一子項 FAIL，該組即 FAIL；無 FAIL 但有 UNVERIFIABLE，該組即 UNVERIFIABLE；
全部子項 PASS，該組才 PASS。整體優先序 `FAIL > UNVERIFIABLE > PASS`。
