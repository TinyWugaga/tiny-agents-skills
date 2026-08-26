#!/bin/sh
# run-fixture.sh <fixture-id> <prompt> [config-dir]
#
# 起一個真實的 fresh Claude Code session，測 implicit invocation。
# 擋掉所有會改變狀態的工具：session 載入 skill 後無事可做就會收尾。
#
# **Fail-closed**：CLI 失敗不吞。退出碼、stderr、實際 prompt 與 config 都落成
# 旁證檔，讓 scorer 能把「跑失敗」跟「跑完但沒觸發」分開——
# 兩者混為一談會讓負向 fixture 拿到假綠燈。
set -eu

[ $# -ge 2 ] || { echo "usage: $0 <fixture-id> <prompt> [config-dir]" >&2; exit 2; }
ID="$1"; PROMPT="$2"; CFG="${3:-}"
BASE="$(cd "$(dirname "$0")" && pwd)"
OUT="${HARNESS_OUT:-$BASE/out}"
WORK="${HARNESS_WORK:-$BASE/work}"
mkdir -p "$OUT" "$WORK"

# 預設允許 Agent 與 Bash：
#   - 擋掉 Agent，派工類 fixture 的 response contract 永遠測不過。
#   - 擋掉 Bash，「驗收條件要求機械計數佐證」這類條件也測不出來。
# 但檔案寫入類工具一律擋，並額外封鎖破壞性 Bash 指令。
# session 的 cwd 是拋棄式 temp 副本；--add-dir 只為讓它讀得到 skill 的 references。
DENY="${HARNESS_DENY:-Edit Write NotebookEdit WebFetch WebSearch}"
DENY="$DENY Bash(rm:*) Bash(rmdir:*) Bash(mv:*) Bash(dd:*) Bash(chmod:*) Bash(chown:*)"
DENY="$DENY Bash(git push:*) Bash(git reset:*) Bash(git checkout:*) Bash(curl:*) Bash(npm:*)"

cd "$WORK"
set +e
if [ -n "$CFG" ]; then
  CLAUDE_CONFIG_DIR="$CFG" claude -p "$PROMPT" \
    --output-format stream-json --verbose \
    --add-dir "$HOME/.claude/skills" \
    --disallowedTools "$DENY" \
    --no-session-persistence \
    > "$OUT/$ID.jsonl" 2>"$OUT/$ID.err" < /dev/null
else
  claude -p "$PROMPT" \
    --output-format stream-json --verbose \
    --add-dir "$HOME/.claude/skills" \
    --disallowedTools "$DENY" \
    --no-session-persistence \
    > "$OUT/$ID.jsonl" 2>"$OUT/$ID.err" < /dev/null
fi
RC=$?
set -e

# scorer 以此判定該筆是否真的跑完；缺這個檔一律視為 ERROR，不得記 PASS
python3 - "$OUT/$ID.meta.json" "$ID" "$RC" "${CFG:-default}" "$WORK" "$PROMPT" "$DENY" <<'PY'
import json, sys, datetime
p, fid, rc, cfg, work, prompt, deny = sys.argv[1:8]
json.dump({"id": fid, "exit_code": int(rc), "config_dir": cfg, "cwd": work, "disallowed_tools": deny,
           "prompt": prompt,
           "ran_at": datetime.datetime.now(datetime.timezone.utc).isoformat()},
          open(p, "w"), ensure_ascii=False, indent=2)
PY

echo "$ID exit=$RC events=$(wc -l < "$OUT/$ID.jsonl" | tr -d ' ')"
[ "$RC" -eq 0 ] || { echo "  !! CLI 失敗: $(head -c 200 "$OUT/$ID.err")" >&2; }
exit "$RC"
