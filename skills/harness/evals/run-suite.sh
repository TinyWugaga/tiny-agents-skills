#!/bin/sh
# run-suite.sh [--dry-run] [run-id]
#
# 跑完整 harness suite：自動建立 precondition（seed 產出物）與隔離 config，
# 依 fixtures JSON 依序跑完全部 fixture，然後評 routing 與 response contract。
#
# **prompt 的唯一來源是 fixtures JSON。** 本檔不得出現任何 prompt 字面——
# 手抄一份會 drift，上一版就是這樣讓 routing fixture 的環境前綴與實跑內容對不上。
# 本檔只負責建立前置狀態、解析 env 條件、依序執行、彙整 exit code。
#
# --dry-run：印出每筆將執行的 (id, config, model, deny_extra, prompt) 後結束，
#            不起任何 session、不建 config 副本。用來對照 JSON 是否零差異。
set -eu

BASE="$(cd "$(dirname "$0")" && pwd)"
# 三個路徑可覆寫：縮減版 smoke test 才能在不動 repo 內容的前提下跑。
FX="${HARNESS_FX:-$BASE/../dispatch/evals/fixtures.json}"
RT="${HARNESS_RT:-$BASE/routing-fixtures.json}"
RUNS_DIR="${HARNESS_RUNS_DIR:-$BASE/runs}"
R="$BASE/run-fixture.sh"

DRY=0
if [ "${1:-}" = "--dry-run" ]; then DRY=1; shift; fi

# --- 前置檢查：缺什麼就明講，不要跑到一半才炸 ---
need_cmd() { command -v "$1" >/dev/null 2>&1 || { echo "缺少指令: $1" >&2; exit 2; }; }
need_file() { [ -f "$1" ] || { echo "缺少檔案: $1" >&2; exit 2; }; }

need_cmd python3
need_file "$FX"
need_file "$RT"
if [ "$DRY" -eq 0 ]; then
  need_cmd git; need_cmd openssl; need_cmd claude
  # 規則檔：CLAUDE_CODE_DISABLE_CLAUDE_MDS=1 之後不再自動載入，改由此檔明確注入。
  need_file "$HOME/.claude/CLAUDE.md"
  # skills 來源：複製進 plugin 變體，不是 symlink、不是 config dir。
  for s in dispatch judgment token-preflight; do
    [ -d "$HOME/.claude/skills/$s" ] || { echo "缺少 skill: ~/.claude/skills/$s" >&2; exit 2; }
  done
  # settings.json 只在需要保留單一 env 鍵時讀取，且只取那一個鍵；不存在也能跑。
fi

if [ "$DRY" -eq 1 ]; then RUN_ID="dry-run"; else
  RUN_ID="${1:-$(date +%Y%m%d-%H%M%S)-$(openssl rand -hex 3)}"
fi
RUN="$RUNS_DIR/$RUN_ID"
OUT="$RUN/raw"
# work dir 與 config 副本一律建在 repo 之外：憑證連結與 session cwd 都不該落在版控目錄裡。
WORK="$(mktemp -d)"; PLUGD="$(mktemp -d)"
chmod 700 "$WORK" "$PLUGD"
MODEL="${HARNESS_SUBJECT_MODEL:-sonnet}"

# --- 從 JSON 載入 fixture 清單（US 分隔：suite / id / config / deny_extra / prompt）---
# 清單落在 mktemp 而非 repo 內：dry-run 因此不在 repo 產生任何檔案。
TSV="$(mktemp)"
trap 'rm -f "$TSV"' EXIT INT TERM
python3 - "$FX" "$RT" > "$TSV" <<'LOADER'
import json, sys
for p in sys.argv[1:]:
    d = json.load(open(p))
    suite = d.get("skill_name") or d.get("suite_name")
    for f in d["fixtures"]:
        env = f.get("env") or {}
        # US(0x1F) 而非 tab：tab 是 IFS whitespace，連續 tab 會被 read 併成一個，
        # deny_extra 為空的列會讓 prompt 位移一格。
        print("\x1f".join([suite, f["id"], env.get("config", "default"),
                           " ".join(env.get("deny_extra", [])), f["prompt"]]))
LOADER
TOTAL=$(wc -l < "$TSV" | tr -d ' ')

if [ "$DRY" -eq 1 ]; then
  echo "== dry-run: $TOTAL 筆 =="
  while IFS="$(printf '\037')" read -r SUITE ID CFGNAME DENYX PROMPT; do
    printf '%s__%s\n  config=%s  model=%s  deny_extra=[%s]\n  prompt=%s\n' \
      "$SUITE" "$ID" "$CFGNAME" "$MODEL" "$DENYX" "$PROMPT"
  done < "$TSV"
  exit 0
fi

mkdir -p "$OUT" "$WORK"
export HARNESS_OUT="$OUT" HARNESS_WORK="$WORK"
RUN_STARTED=$(date +%s)
echo "== run id: $RUN_ID =="

# --- precondition：seed 產出物進 work dir ---
cp -R "$BASE/seed/." "$WORK/"
# 初始化成 git repo：多個 fixture 的 prompt 是「掃整個 repo」，
# 沒有 git repo 時 session 會正確地回「這裡不是 repo」而寫不出派工單，
# response contract 於是永遠測不過——那是 harness 的錯，不是 skill 的錯。
( cd "$WORK" && git init -q && git add -A \
  && git -c user.email=harness@local -c user.name=harness commit -qm "seed" )
echo "seed 已就位（git repo）: $(cd "$WORK" && git ls-files | wc -l | tr -d ' ') 個檔"
# --setting-sources project,local 會讀 cwd 的專案層設定。seed 一旦夾帶 CLAUDE.md 或
# .claude/，隔離就破了而且不會有任何錯誤訊息，只會安靜地讓結果失去意義。
if find "$WORK" -maxdepth 2 \( -iname 'CLAUDE.md' -o -name '.claude' \) | grep -q .; then
  echo "seed 夾帶 CLAUDE.md 或 .claude/，隔離前提不成立，中止。" >&2
  rm -rf "$WORK" "$PLUGD"; exit 2
fi

# --- plugin 變體：每個變體是一個最小 plugin，只含該變體要載入的 skill ---
# 為什麼是 plugin 而不是 config dir：換 config dir 會連 host 登入狀態一起切掉，
# 而本 harness 不搬運任何憑證。plugin skill 一樣是 model-invoked，
# 只是名稱帶 namespace（score.py 已用 s.split(":")[-1] 正規化）。
for variant in default no-dispatch no-judgment; do
  D="$PLUGD/$variant"
  mkdir -p "$D/.claude-plugin" "$D/skills"
  cat > "$D/.claude-plugin/plugin.json" <<PLUGINJSON
{
  "name": "harness-eval",
  "version": "0.0.0",
  "description": "harness eval fixture 用的臨時 skill 集合（${variant}）"
}
PLUGINJSON
  for s in dispatch judgment token-preflight; do
    [ "$variant" = "no-$s" ] && continue
    cp -RL "$HOME/.claude/skills/$s" "$D/skills/$s"
  done
  # 一般檔案設唯讀：session 改不動它,變體才是決定性的。不含 symlink（此處也沒有）。
  find "$D" -type f -exec chmod a-w {} +
done

# 規則檔：CLAUDE.md 不再自動載入，改複製一份明確注入。
RULES="$PLUGD/rules.md"
cp "$HOME/.claude/CLAUDE.md" "$RULES"
chmod a-w "$RULES"

# 消毒過的 settings：**只**取 env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH 這一個鍵。
# 絕不整份帶入 user settings.json——那裡面有 enabledPlugins 與 marketplace 設定，
# 帶進來會把 host 的 plugin 生態一起拉進受測環境，隔離就沒有意義了。
SETTINGS=""
if [ "${HARNESS_NO_SETTINGS:-0}" = "1" ]; then
  echo "  HARNESS_NO_SETTINGS=1，不傳 --settings"
elif [ -f "$HOME/.claude/settings.json" ]; then
  SETTINGS="$PLUGD/settings.sanitized.json"
  if ! python3 - "$HOME/.claude/settings.json" "$SETTINGS" <<'SANITIZE'
import json, sys
KEY = "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"
try:
    src = json.load(open(sys.argv[1]))
except (OSError, ValueError):
    sys.exit(1)
val = (src.get("env") or {}).get(KEY)
if val is None:
    sys.exit(1)          # 沒有這個鍵就不要產生檔案，也不要傳 --settings
json.dump({"env": {KEY: val}}, open(sys.argv[2], "w"), indent=2)
print(f"  消毒後 settings 只含 env.{KEY}={val}")
SANITIZE
  then
    SETTINGS=""
    echo "  settings.json 無 CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH，不傳 --settings"
  fi
fi
export HARNESS_RULES_FILE="$RULES" HARNESS_SETTINGS_FILE="$SETTINGS"

echo "plugin 變體已就位: default / no-dispatch / no-judgment（skills 為複製副本，檔案唯讀）"
echo "隔離方式: --setting-sources project,local + --plugin-dir + CLAUDE_CODE_DISABLE_CLAUDE_MDS=1；未使用 CLAUDE_CONFIG_DIR，未搬運任何憑證"

# --- preflight：走與 fixture 完全相同的隔離執行路徑，先確認真的能推論 ---
# 這一關存在的理由：前置檢查只驗得到「claude 這支指令在」，驗不到 session 能不能推論。
# 少了它，一次登入或憑證問題會讓 18 筆全部跑完才發現，並且白花 judge 的錢。
echo
echo "== preflight（1 筆真實 session，走 default 隔離 config）=="
set +e
"$R" "_preflight" "回覆 OK 兩個字，不要做其他事。" "$PLUGD/default"
PF_RC=$?
set -e
set +e
python3 - "$OUT/_preflight.jsonl" "$PF_RC" <<'PREFLIGHT'
import json, sys
path, rc = sys.argv[1], int(sys.argv[2])
result = None
try:
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        if d.get("type") == "result":
            result = d
except (OSError, ValueError) as e:
    print(f"  preflight trace 無法解析: {e}")
if rc != 0 or result is None or result.get("subtype") != "success" or result.get("is_error"):
    detail = ""
    if result is not None:
        detail = (f"subtype={result.get('subtype')} is_error={result.get('is_error')} "
                  f"cost={result.get('total_cost_usd')} "
                  f"{str(result.get('result') or result.get('error') or '')[:200]}")
    print("  ✗ preflight 失敗，中止；未執行任何 fixture、未呼叫 judge。")
    print(f"    exit={rc} {detail}")
    print("    隔離執行路徑下的 session 無法推論。逐項檢查：")
    print("    - host 是否已登入（本 harness 不搬運憑證，沿用 host 預設路徑）")
    print("    - --setting-sources / --plugin-dir / --append-system-prompt-file 是否為此 CLI 版本所支援")
    print("    - --settings 消毒檔是否與 --setting-sources 相容（可用 HARNESS_NO_SETTINGS=1 排除）")
    sys.exit(1)
print(f"  ✓ preflight 通過（cost={result.get('total_cost_usd')}）")
PREFLIGHT
PF_CHECK=$?
set -e
if [ "$PF_CHECK" -ne 0 ]; then
  rm -rf "$WORK" "$PLUGD"
  echo "== suite 中止於 preflight -> exit 2 =="
  exit 2
fi

FAILED=0
while IFS="$(printf '\037')" read -r SUITE ID CFGNAME DENYX PROMPT; do
  HARNESS_DENY_EXTRA="$DENYX" "$R" "${SUITE}__${ID}" "$PROMPT" "$PLUGD/$CFGNAME" \
    || FAILED=$((FAILED + 1))
done < "$TSV"

echo
echo "== CLI 失敗筆數: $FAILED / $TOTAL =="
echo "== routing assertions =="
set +e
python3 "$BASE/score.py" "$OUT" "$FX" "$RT"
SCORE_RC=$?
set -e
echo
echo "== response contract (LLM judge) =="
# score.py 回 2 = 有 fixture 沒產生可用觀測。那種情況下 judge 幫不上任何忙：
# 對空的或失敗的 trace 判定只會燒錢，還會產生假的 contract FAIL（上一輪就白花了 $0.144）。
if [ "$SCORE_RC" -eq 2 ]; then
  echo "  跳過：routing 有未產生可用觀測的 fixture，本輪不構成契約證據，judge 不執行。"
  JUDGE_RC=0
else
  set +e
  python3 "$BASE/judge.py" "$OUT" "$FX" "$RT"
  JUDGE_RC=$?
  set -e
fi
echo
echo "== run record =="
RUN_ENDED=$(date +%s)
set +e
HARNESS_RUN_STARTED="$RUN_STARTED" HARNESS_RUN_ENDED="$RUN_ENDED" \
HARNESS_CLI_FAILED="$FAILED" HARNESS_SUBJECT_MODEL="$MODEL" \
HARNESS_JUDGE_MODEL="${HARNESS_JUDGE_MODEL:-sonnet}" \
python3 "$BASE/record.py" "$OUT" "$RUN_ID" "$FX" "$RT"
RECORD_RC=$?
set -e
echo
echo "raw trace: $OUT"
rm -rf "$WORK" "$PLUGD"

# --- exit code：CLI / routing / contract 任一失敗即非 0 ---
# 清理必須排在 exit 之前，否則失敗時會殘留 .work-/.cfg- 目錄。
# 三個來源分開印出，讓失敗原因在 exit code 之外仍可辨識。
# run record 寫失敗也算 suite 失敗：沒有可重算的紀錄，這一輪就不構成憑據。
SUITE_RC=0
[ "$FAILED" -eq 0 ]    || SUITE_RC=1
[ "$SCORE_RC" -eq 0 ]  || SUITE_RC=1
[ "$JUDGE_RC" -eq 0 ]  || SUITE_RC=1
[ "$RECORD_RC" -eq 0 ] || SUITE_RC=1
echo
echo "== suite 判定: CLI 失敗 $FAILED / routing rc $SCORE_RC / contract rc $JUDGE_RC / record rc $RECORD_RC -> exit $SUITE_RC =="
exit "$SUITE_RC"
