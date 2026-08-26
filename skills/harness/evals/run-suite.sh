#!/bin/sh
# run-suite.sh [run-id]
#
# 跑完整 harness suite：自動建立 precondition（seed 產出物）與隔離 config，
# 依序跑完 17 筆，然後評 routing 與 response contract。
#
# 一切前置狀態都由本檔建立，不依賴人工步驟——上一輪的失敗有一半來自
# 「fixture 假設某些檔案存在，但沒人負責建立它們」。
set -eu

BASE="$(cd "$(dirname "$0")" && pwd)"
RUN_ID="${1:-$(date +%Y%m%d-%H%M%S)-$(openssl rand -hex 3)}"
RUN="$BASE/runs/$RUN_ID"
OUT="$RUN/raw"; WORK="$BASE/.work-$RUN_ID"; CFGD="$BASE/.cfg-$RUN_ID"
mkdir -p "$OUT" "$WORK" "$CFGD"

export HARNESS_OUT="$OUT" HARNESS_WORK="$WORK"
R="$BASE/run-fixture.sh"
FX="$BASE/../dispatch/evals/fixtures.json"
RT="$BASE/routing-fixtures.json"

echo "== run id: $RUN_ID =="

# --- precondition：seed 產出物進 work dir ---
cp -R "$BASE/seed/." "$WORK/"
# 初始化成 git repo：多個 fixture 的 prompt 是「掃整個 repo」，
# 沒有 git repo 時 session 會正確地回「這裡不是 repo」而寫不出派工單，
# response contract 於是永遠測不過——那是 harness 的錯，不是 skill 的錯。
( cd "$WORK" && git init -q && git add -A \
  && git -c user.email=harness@local -c user.name=harness commit -qm "seed" )
echo "seed 已就位（git repo）: $(cd "$WORK" && git ls-files | wc -l | tr -d ' ') 個檔"

# --- 隔離 config：各缺一個 skill，使用者的真實 ~/.claude 全程不動 ---
for miss in dispatch judgment; do
  D="$CFGD/no-$miss"; mkdir -p "$D/skills" "$D/harness"
  cp "$HOME/.claude/CLAUDE.md" "$D/CLAUDE.md"
  cp "$HOME/.claude/settings.json" "$D/settings.json"
  cp "$HOME/.claude/harness/maintenance.md" "$D/harness/maintenance.md"
  for s in dispatch judgment token-preflight; do
    [ "$s" = "$miss" ] && continue
    ln -sf "$(cd -P "$HOME/.claude/skills/$s" && pwd)" "$D/skills/$s"
  done
done
echo "隔離 config 已就位"

FAILED=0
run() { "$R" "$@" || FAILED=$((FAILED+1)); }

# --- dispatch suite ---
run dispatch__positive-1  "幫我派個 agent 掃一下整個 repo,找出所有還在用舊版 API 的地方"
run dispatch__positive-2  "這個子任務要用 sonnet 還是 opus?effort 開多少比較合適?"
run dispatch__positive-3  "幫我寫一份派工 prompt,要讓 subagent 去重構 useCart 這個 hook"
run dispatch__positive-4  "這件事我要不要開三個 agent 平行跑?"
run dispatch__negative-1  "幫我把這個 function 改成 async"
run dispatch__negative-2  "這個 bug 我連續兩輪都修不好,怎麼辦"
run dispatch__negative-3  "幫我驗收 docs/api.md 有沒有照 SPEC.md 寫"
run dispatch__ambiguous-1 "這個任務有點大,要不要拆出去跑?"
run dispatch__explicit-mention-1 "跑一下 dispatch"

# --- routing suite ---
run harness-routing__handoff-1  "judgment 已經判定這份規則檔需要 fresh-context 驗收了,幫我把驗收派出去"
run harness-routing__boundary-1 "我照 SPEC.md 把 formatDate 實作在 src/utils/date.ts 了,可以宣告完成了嗎?"
run harness-routing__boundary-2 "同樣的錯誤我改兩輪了還是失敗,是不是該換更強的模型"
run harness-routing__ambiguous-1 "src/utils/date.ts 這份產出品質夠了嗎?要不要找人再看一次?"
run harness-routing__dispatch-absent-1 "幫我派一個 subagent 去掃 src/ 底下所有的 TODO" "$CFGD/no-dispatch"
run harness-routing__dispatch-absent-2 "幫我看看這個 hook 為什麼會重複觸發" "$CFGD/no-dispatch"
run harness-routing__judgment-absent-1 "這個多步驟重構我做完了,可以宣告完成了嗎" "$CFGD/no-judgment"
# 只有這一筆額外停用 Agent——這正是它要測的條件本身。
# 其餘 fixture 一律允許 Agent，否則派工類的 response contract 測不出來。
HARNESS_DENY="Edit Write NotebookEdit WebFetch WebSearch Agent" \
  run harness-routing__agent-unavailable-1 "幫我派個 agent 去做全 repo 掃描"

echo
echo "== CLI 失敗筆數: $FAILED =="
echo "== routing assertions =="
python3 "$BASE/score.py" "$OUT" "$FX" "$RT" || true
echo
echo "== response contract (LLM judge) =="
python3 "$BASE/judge.py" "$OUT" "$FX" "$RT" || true
echo
echo "raw trace: $OUT"
rm -rf "$WORK" "$CFGD"
