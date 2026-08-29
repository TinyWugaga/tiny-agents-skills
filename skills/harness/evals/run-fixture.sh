#!/bin/sh
# run-fixture.sh <fixture-id> <prompt> <plugin-dir>
#
# 起一個真實的 fresh Claude Code session，測 implicit invocation。
#
# **不使用 CLAUDE_CONFIG_DIR。** 換 config dir 會同時切掉 host 的登入狀態，
# 而本 harness 不搬運任何憑證（不讀取、不複製、不匯出、不輸出、不連結、不留存）。
# 改以下列組合達成隔離，登入狀態沿用 host 預設路徑：
#   --setting-sources project,local  排除 user 層設定與 user 層 skills
#   --plugin-dir <變體>              只餵入本次要測的 skill 集合（plugin skill 仍是 model-invoked）
#   CLAUDE_CODE_DISABLE_CLAUDE_MDS=1 不自動載入任何 CLAUDE.md
#   --append-system-prompt-file      改以明確複製的規則檔注入專案規則
# session 的 cwd 是拋棄式 seed 副本，裡面沒有 CLAUDE.md 也沒有 .claude/。
#
# 環境變數：
#   HARNESS_OUT            raw trace 落點（預設 $BASE/out）
#   HARNESS_WORK           session cwd（預設 $BASE/work）
#   HARNESS_RULES_FILE     必填，--append-system-prompt-file 的來源
#   HARNESS_SETTINGS_FILE  選填，只含單一 env 鍵的消毒後 settings
#   HARNESS_SUBJECT_MODEL  受測 model（預設 sonnet）——不 pin 則結果不可重現
#   HARNESS_DENY_EXTRA     在預設 deny list 之外「額外」停用的工具（fixture 的 env.deny_extra）
#   HARNESS_TIMEOUT        單筆上限秒數（預設 300）；逾時以 rc 124 記錄，不得記 PASS
#
# **Fail-closed**：CLI 失敗不吞。退出碼、stderr、實際 prompt、plugin dir、model 與 deny list
# 都落成旁證檔，讓 scorer 能把「跑失敗」跟「跑完但沒觸發」分開。
set -eu

[ $# -eq 3 ] || { echo "usage: $0 <fixture-id> <prompt> <plugin-dir>" >&2; exit 2; }
ID="$1"; PROMPT="$2"; PLUGIN="$3"
BASE="$(cd "$(dirname "$0")" && pwd)"
OUT="${HARNESS_OUT:-$BASE/out}"
WORK="${HARNESS_WORK:-$BASE/work}"
MODEL="${HARNESS_SUBJECT_MODEL:-sonnet}"
TMO="${HARNESS_TIMEOUT:-300}"
RULES="${HARNESS_RULES_FILE:-}"
SETTINGS="${HARNESS_SETTINGS_FILE:-}"
mkdir -p "$OUT" "$WORK"

[ -d "$PLUGIN" ] || { echo "plugin dir 不存在: $PLUGIN" >&2; exit 2; }
[ -n "$RULES" ] && [ -f "$RULES" ] || { echo "HARNESS_RULES_FILE 未設或不存在: $RULES" >&2; exit 2; }

# 預設允許 Agent 與 Bash：
#   - 擋掉 Agent，派工類 fixture 的 response contract 永遠測不過。
#   - 擋掉 Bash，「驗收條件要求機械計數佐證」這類條件也測不出來。
# 檔案寫入類工具一律擋，並額外封鎖破壞性 Bash 指令。
DENY="Edit Write NotebookEdit WebFetch WebSearch"
DENY="$DENY Bash(rm:*) Bash(rmdir:*) Bash(mv:*) Bash(dd:*) Bash(chmod:*) Bash(chown:*)"
DENY="$DENY Bash(git push:*) Bash(git reset:*) Bash(git checkout:*) Bash(curl:*) Bash(npm:*)"
DENY="$DENY ${HARNESS_DENY_EXTRA:-}"

# POSIX watchdog：macOS 沒有 GNU timeout，不能假設它存在。
# 主 shell 直接輪詢，不另開背景 job——多一個背景 job 會在被 kill 時讓 shell 把
# `Terminated: 15` 印到 stderr，正常結束與逾時清理都會冒出來。
run_with_timeout() {
  _t=$1; shift
  "$@" &
  _c=$!
  _i=0
  while [ "$_i" -lt "$_t" ]; do
    kill -0 "$_c" 2>/dev/null || break
    sleep 1
    _i=$((_i + 1))
  done
  _killed=0
  if kill -0 "$_c" 2>/dev/null; then
    kill -TERM "$_c" 2>/dev/null || true
    sleep 2
    kill -KILL "$_c" 2>/dev/null || true
    _killed=1
  fi
  # 用 `|| _rc=$?` 而非 set +e/set -e：函式內切換 errexit 會覆蓋呼叫端的設定,
  # 逾時回非 0 時整支腳本會當場中止,meta 檔就寫不出來（實測踩過）。
  _rc=0
  wait "$_c" 2>/dev/null || _rc=$?
  # 逾時以「我們主動殺了它」這個事實判定,不靠 143/137 反推。
  if [ "$_killed" -eq 1 ]; then return 124; fi
  return "$_rc"
}

export CLAUDE_CODE_DISABLE_CLAUDE_MDS=1

set -- claude -p "$PROMPT" \
  --output-format stream-json --verbose \
  --model "$MODEL" \
  --setting-sources project,local \
  --plugin-dir "$PLUGIN" \
  --add-dir "$PLUGIN" \
  --append-system-prompt-file "$RULES" \
  --disallowedTools "$DENY" \
  --no-session-persistence
if [ -n "$SETTINGS" ]; then set -- "$@" --settings "$SETTINGS"; fi

cd "$WORK"
set +e
run_with_timeout "$TMO" "$@" \
  > "$OUT/$ID.jsonl" 2>"$OUT/$ID.err" < /dev/null
RC=$?
set -e

# scorer 以此判定該筆是否真的跑完；缺這個檔一律視為 ERROR，不得記 PASS
python3 - "$OUT/$ID.meta.json" "$ID" "$RC" "$PLUGIN" "$WORK" "$PROMPT" "$DENY" "$MODEL" "$TMO" \
         "$RULES" "$SETTINGS" <<'META'
import json, sys, datetime
p, fid, rc, plugin, work, prompt, deny, model, tmo, rules, settings = sys.argv[1:12]
rc = int(rc)
json.dump({"id": fid, "exit_code": rc, "timed_out": rc == 124,
           "plugin_dir": plugin, "setting_sources": "project,local",
           "rules_file": rules, "settings_file": settings or None,
           "disable_claude_mds": True,
           "cwd": work, "disallowed_tools": deny,
           "subject_model": model, "timeout_s": int(tmo), "prompt": prompt,
           "ran_at": datetime.datetime.now(datetime.timezone.utc).isoformat()},
          open(p, "w"), ensure_ascii=False, indent=2)
META

echo "$ID exit=$RC events=$(wc -l < "$OUT/$ID.jsonl" | tr -d ' ')"
if [ "$RC" -eq 124 ]; then
  echo "  !! 逾時 ${TMO}s，已終止" >&2
elif [ "$RC" -ne 0 ]; then
  echo "  !! CLI 失敗: $(head -c 200 "$OUT/$ID.err")" >&2
fi
exit "$RC"
