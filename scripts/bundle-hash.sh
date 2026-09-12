#!/bin/sh
# bundle-hash.sh — 各 identity domain 的 deterministic 內容 hash（hash schema v6）
#
# 用法:
#   bundle-hash.sh schema-version
#   bundle-hash.sh skill      <skill 目錄>          例: skills/harness/dispatch
#   bundle-hash.sh evaluator  <collection 目錄>     例: skills/harness
#   bundle-hash.sh runner     <collection 目錄>     例: skills/harness
#   bundle-hash.sh fixtures   <檔案或目錄> [...]    例: .../dispatch/evals/fixtures.json .../evals/seed
#   bundle-hash.sh execution-context <rules 檔> <settings 檔|-> <descriptor 檔|->
#   bundle-hash.sh evaluation-context <judge descriptor 檔>
#   bundle-hash.sh rescore-runner
#
# ## 為什麼是 v6
#
# v5 把 `run-rescore.sh` 排除在所有 identity domain 之外，理由是「它只負責依正確順序呼叫，
# 每項保證都由 judge.py／record.py 自己執行」。那個理由被兩件事推翻：它決定了 judge 的
# **輸出寫到哪裡**（寫回來源目錄會蓋掉原始逐筆判定證據，而 trace manifest 不涵蓋
# `.judge.json`，偵測不到），也決定了**驗證的先後順序**（把付費 judge 排在 provenance
# 驗證之前，等於保留了「判不了仍先花錢」的路徑）。
#
# 能決定證據寫到哪裡、以什麼順序驗證的東西，就是 identity 的一部分。
# v6 因此新增 `rescore-runner`，並納入 contract manifest——它只影響 derived record，
# 不影響原生 run 的 subject 證據。
#
# ## 為什麼是 v5
#
# v4 的重新評分路徑把 `fixtures` 整個歸給 subject 那半，從來源 run 的紀錄沿用。但
# **judge 是用「現在」的 fixtures 判定的**——`required_elements`／`forbidden_elements`
# 就寫在那份檔案裡。改掉 assertion 再重評舊 trace，derived record 仍會宣稱使用來源
# fixtures，紀錄與實際判定依據不符。
#
# v5 拆出 `contract_fixtures`：judge 判定當下實際載入的 fixture 檔。它與 `fixtures`
# 用同一個 mode 與同一套演算法（allowlist 未變），差別只在**量的時機與歸屬**——
# `fixtures` 屬 subject（決定 prompt，作廢 observation），
# `contract_fixtures` 屬 contract（決定 assertion，只作廢判定）。
# 新增 domain 依既有規則提版；v4 的值不得與 v5 直接比較。
#
# ## 為什麼是 v4
#
# v3 把「受測 session 的執行環境」記進了 `execution-context`，卻完全沒記
# **判定端的環境**。judge 是另一個 model 的另一個 session：換 `HARNESS_JUDGE_MODEL`、
# 換 judge 的 CLI flags、或 host 的 `claude` 版本一升，contract 判定就可能翻轉，
# 而 v3 的 run record 對此一個字都沒有。兩輪 hash 完全相同卻得到相反的 contract 結論，
# 讀紀錄的人找不到任何解釋。
#
# v4 新增 `evaluation-context`，且**刻意與 `execution-context` 分開**：
# 受測環境變更作廢的是 subject 行為證據（要重跑付費 session）；判定環境變更作廢的只有
# 判定本身（保留的 raw trace 可重新評分）。混在同一個 domain 會讓「換 judge model」
# 看起來像「受測環境變了」，把便宜的重評誤判成昂貴的重跑。
#
# ## 為什麼是 v3
#
# v2 有三個缺口：
#
#   1. `skill` allowlist 漏掉 `agents/**`。`agents/openai.yaml` 的 `default_prompt` 是
#      runtime 行為契約的一部分（在 OpenAI 平台上直接決定 agent 開場行為），改它卻不動
#      skill hash，等於宣稱「行為證據仍有效」而實際上受測物已變。納入後 allowlist 改變，
#      依本檔自己的規則必須提版。
#   2. 沒有 `execution-context` domain。同一份 skill／fixture／runner／evaluator，在不同的
#      注入規則檔（`~/.claude/CLAUDE.md`）、不同 model、不同 deny list 之下會得到不同行為，
#      但 v2 的 run record 對此完全沉默。這是「同 hash 卻不同結果」最大的未記錄來源。
#   3. `runner` allowlist 未含 `evals/manifest.py`（v3 新增的 run-start／run-end 快照工具）。
#      它決定「量測了哪些 domain」，屬 runner 契約。
#
# ## 為什麼是 v2
#
# v1 只有 `skill` 與 `suite` 兩個 mode，且把 evaluator 程式、runner 腳本與 fixture 全部
# 塞進同一個 `suite` hash，`skill` mode 又納入 `evals/fixtures.json`。結果是 evaluator
# 工具被錯誤納入 runtime skill 的 identity domain，形成版本污染：改 judge.py 的解析
# 邏輯會作廢所有 skill observation，即使那個改動不可能影響那些判定。
#
# v2 把識別拆成四個互斥 domain，各自只在自己的內容變動時改變：
#
#   skill      SKILL.md + references/** + scripts/** + assets/**
#              變更作廢：subject 的 skill 行為證據
#   fixtures   本次實際載入的 fixture 檔與 seed（**不掃全 repo**）
#              變更作廢：對應案例的 observation
#   runner     session 隔離、plugin 組裝、transport、工具權限
#              變更作廢：subject trace
#   evaluator  score／judge／record 與判定 prompt
#              變更作廢：routing／contract 判定；**保留的 raw trace 可重新評分，
#              不必重跑付費 subject session**
#
# v3 再加第五個 domain：
#
#   execution-context  注入的規則檔內容、消毒後 settings 內容、model／CLI flags／deny list
#                      變更作廢：subject 行為證據（同一份 skill 在不同執行環境下行為不同）
#
# v4 再加第六個：
#
#   evaluation-context judge model、實際 claude --version、judge CLI flags、structured output 設定
#                      變更作廢：contract 判定；**保留的 raw trace 可重新評分**
#
# v5 再加第七個（沿用 `fixtures` mode 計算，只是歸屬不同）：
#
#   contract_fixtures  judge 判定當下實際載入的 fixture 檔（assertion 的來源）
#                      變更作廢：contract 判定
#
# v6 再加第八個：
#
#   rescore-runner     scripts/run-rescore.sh——決定 derived 判定寫到哪裡、以什麼順序驗證
#                      變更作廢：derived record（不影響原生 run）
#
# 排除項與理由：
#   - skill 排除 `evals/**`。fixture 變更不得改動 skill identity。
#   - evaluator 排除 `*_selftest.py`。改測試本身不得作廢 observation。
#   - fixtures 只收呼叫端明列的路徑。掃全 repo 會讓無關案例互相污染。
#   - 前四個 domain 都排除 `evals/runs/`：結果檔不得反過來改變被測版本。
#   - execution-context 只取內容 hash，不取路徑：rules／settings 是每輪 mktemp 的副本。
#   - 都排除 .DS_Store：Finder 隨機產生，不屬於任何契約。
#
# ## hash_schema_version
#
# 本腳本輸出的所有值綁定 `HASH_SCHEMA_VERSION`。演算法或任一 domain 的 allowlist 變動時
# 必須提版；**不同 schema version 的 hash 不得直接比較**，也不得宣稱「值不同 = 內容變了」。
# v1 紀錄一律標 `hash_schema: v1` 保留，不覆寫、不宣告失效。
#
# ## 設計要求（沿用 v1，未變）
#
#   1. **路徑無關**：同一份內容，不論經 symlink 或實體路徑存取，結果必須相同。
#      （直接對 `shasum` 輸出再摘要會失敗——它的輸出含絕對路徑。）
#   2. **檔名敏感**：改檔名要改變 hash，摘要對象是「相對路徑 + 內容 hash」的組合。
#   3. **allowlist 明列**：不用副檔名比對。未列出的一律不影響 hash。
#   4. **不回傳空輸入的 hash**：allowlist 一筆都沒 match 時 exit 3。空輸入的 SHA-256
#      看起來完全正常，是版本綁定最危險的失敗模式。
#
# 輸出: 單行 SHA-256（schema-version mode 輸出版本字串）

set -eu

HASH_SCHEMA_VERSION=v6

usage() {
  echo "usage: $0 schema-version" >&2
  echo "       $0 skill|evaluator|runner <dir>" >&2
  echo "       $0 fixtures <path> [path...]" >&2
  echo "       $0 execution-context <rules> <settings|-> <descriptor|->" >&2
  echo "       $0 evaluation-context <judge descriptor>" >&2
  echo "       $0 rescore-runner" >&2
  exit 2
}

[ $# -ge 1 ] || usage
MODE="$1"; shift

if [ "$MODE" = schema-version ]; then
  [ $# -eq 0 ] || usage
  echo "$HASH_SCHEMA_VERSION"
  exit 0
fi

emit_file() { [ -f "$1" ] && echo "$1" || true; }
emit_tree() { [ -d "$1" ] && find -L "$1" -type f || true; }

case "$MODE" in
  skill|evaluator|runner)
    [ $# -eq 1 ] || usage
    DIR=$(cd -P "$1" && pwd)   # -P 解析 symlink,兩種存取路徑收斂到同一實體目錄
    cd "$DIR"
    case "$MODE" in
      skill)
        # runtime 契約物件。evals/** 不在此列——fixture 不是 skill identity 的一部分。
        # agents/**（v3 新增）：`default_prompt` 等欄位直接決定 runtime 行為，屬契約物件。
        LIST=$( { emit_file SKILL.md
                  emit_tree references
                  emit_tree scripts
                  emit_tree assets
                  emit_tree agents
                } | grep -v -e '^evals/' -e '/evals/' )
        ;;
      evaluator)
        # 實際參與判定的程式與判定 prompt。selftest 不在此列。
        LIST=$( { emit_file evals/judge.py
                  emit_file evals/score.py
                  emit_file evals/record.py
                } )
        ;;
      runner)
        # session 隔離、plugin 組裝、prompt transport、工具權限、run 快照的量測範圍。
        LIST=$( { emit_file evals/run-suite.sh
                  emit_file evals/run-fixture.sh
                  emit_file evals/transport.py
                  emit_file evals/manifest.py
                } )
        ;;
    esac
    ;;
  fixtures)
    # 只收呼叫端明列的路徑：本次實際載入的 fixture 檔與 seed。
    # 相對路徑以 repo root（本腳本的上一層）為基準，確保與 cwd 無關且檔名敏感。
    [ $# -ge 1 ] || usage
    ROOT=$(cd -P "$(dirname "$0")/.." && pwd)
    LIST=""
    for p in "$@"; do
      [ -e "$p" ] || { echo "fixtures: 路徑不存在: $p" >&2; exit 3; }
      abs=$(cd -P "$(dirname "$p")" && pwd)/$(basename "$p")
      case "$abs" in
        "$ROOT"/*) ;;
        *) echo "fixtures: 路徑不在 repo root ($ROOT) 內: $p" >&2; exit 2 ;;
      esac
      rel=${abs#"$ROOT"/}
      if [ -d "$abs" ]; then
        found=$(cd "$ROOT" && emit_tree "$rel")
      else
        found=$(cd "$ROOT" && emit_file "$rel")
      fi
      LIST="$LIST
$found"
    done
    cd "$ROOT"
    ;;
  execution-context)
    # 實際注入受測 session 的執行環境：規則檔內容、消毒後 settings 內容、
    # 以及 model／CLI flags／deny list 的 descriptor。
    #
    # **識別對象是內容，不是路徑。** rules 與 settings 都是 mktemp 出來的副本，
    # 路徑每輪都不同；把路徑算進去會讓同一份環境每輪得到不同 hash，這個 domain 就永遠
    # 顯示為 drift 而失去偵測能力。因此只取每個組件的內容 hash，配上固定標籤。
    # descriptor 由 run-fixture.sh --print-context 產生（單一來源，避免 deny list 手抄漂移）。
    [ $# -eq 3 ] || usage
    for f in "$@"; do
      if [ "$f" != "-" ] && [ ! -f "$f" ]; then
        echo "execution-context: 檔案不存在: $f" >&2; exit 3
      fi
    done
    ctx_component() {
      if [ "$2" = "-" ]; then
        printf '%s  %s\n' "$1" "absent"
      else
        printf '%s  %s\n' "$1" "$(shasum -a 256 "$2" | cut -d' ' -f1)"
      fi
    }
    { ctx_component rules "$1"
      ctx_component settings "$2"
      ctx_component descriptor "$3"
    } | shasum -a 256 | cut -d' ' -f1
    exit 0
    ;;
  rescore-runner)
    # 重新評分的編排腳本。它決定 judge 的輸出位置與驗證順序，兩者都直接影響
    # derived record 的可信度，因此屬於 identity 而不是「純便利工具」。
    [ $# -eq 0 ] || usage
    ROOT=$(cd -P "$(dirname "$0")/.." && pwd)
    [ -f "$ROOT/scripts/run-rescore.sh" ] || {
      echo "rescore-runner: 找不到 scripts/run-rescore.sh" >&2; exit 3; }
    cd "$ROOT"
    printf '%s  %s\n' scripts/run-rescore.sh \
      "$(shasum -a 256 scripts/run-rescore.sh | cut -d' ' -f1)" \
      | shasum -a 256 | cut -d' ' -f1
    exit 0
    ;;
  evaluation-context)
    # 判定端的執行環境。descriptor 由 `judge.py --print-context` 產生——judge model、
    # judge CLI flags 與 structured-output 設定都只有 judge.py 知道，在別處手抄必然漂移。
    #
    # 與 execution-context 分開的理由見檔頭「為什麼是 v4」：兩者作廢的範圍不同，
    # 混在一起會把「換 judge model」誤讀成「受測環境變了」。
    [ $# -eq 1 ] || usage
    [ -f "$1" ] || { echo "evaluation-context: 檔案不存在: $1" >&2; exit 3; }
    printf 'judge_descriptor  %s\n' "$(shasum -a 256 "$1" | cut -d' ' -f1)" \
      | shasum -a 256 | cut -d' ' -f1
    exit 0
    ;;
  *)
    echo "unknown mode: $MODE (schema-version|skill|evaluator|runner|fixtures|execution-context|evaluation-context|rescore-runner)" >&2
    exit 2
    ;;
esac

LIST=$(printf '%s\n' "$LIST" \
       | grep -v -e '^$' -e '^\.DS_Store$' -e '/\.DS_Store$' -e '^evals/runs/' -e '/evals/runs/' \
       | LC_ALL=C sort -u)
[ -n "$LIST" ] || {
  echo "no files matched the $MODE allowlist — 目錄或 mode 傳錯?" >&2
  exit 3
}

printf '%s\n' "$LIST" \
  | while IFS= read -r f; do
      printf '%s  %s\n' "$f" "$(shasum -a 256 "$f" | cut -d' ' -f1)"
    done \
  | shasum -a 256 | cut -d' ' -f1
