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
RULES_SOURCE="$BASE/context/rules.md"
# hash schema v6：腳本在 repo root，identity 拆成 skill／evaluator／runner／fixtures／
# execution-context／evaluation-context（＋重評用的 contract-fixtures／rescore-runner）。
# evaluator 或 runner 變更不再作廢 skill observation；judge 端環境自成一個 domain。
HASH_SH="$BASE/../../../scripts/bundle-hash.sh"
MANIFEST_PY="$BASE/manifest.py"

# 受測 skill 的唯一來源是本 repo。record.py 也從同一批 repo 路徑算 hash；若 runner
# 改讀已安裝副本，副本一旦落後就會出現「實際測 A、紀錄卻綁 B」的假版本綁定。
DISPATCH_SRC="$BASE/../dispatch"
JUDGMENT_SRC="$BASE/../../discipline/judgment"
TOKEN_PREFLIGHT_SRC="$BASE/../../discipline/token-preflight"

skill_src() {
  case "$1" in
    dispatch) echo "$DISPATCH_SRC" ;;
    judgment) echo "$JUDGMENT_SRC" ;;
    token-preflight) echo "$TOKEN_PREFLIGHT_SRC" ;;
    *) echo "未知 skill source: $1" >&2; return 2 ;;
  esac
}

valid_hash() {
  [ "${#1}" -eq 64 ] || return 1
  case "$1" in *[!0-9a-f]*) return 1 ;; esac
}

DRY=0
if [ "${1:-}" = "--dry-run" ]; then DRY=1; shift; fi

# --- 前置檢查：缺什麼就明講，不要跑到一半才炸 ---
need_cmd() { command -v "$1" >/dev/null 2>&1 || { echo "缺少指令: $1" >&2; exit 2; }; }
need_file() { [ -f "$1" ] || { echo "缺少檔案: $1" >&2; exit 2; }; }

need_cmd python3
need_file "$FX"
need_file "$RT"
if [ "$DRY" -eq 0 ]; then
  need_cmd git; need_cmd openssl; need_cmd claude; need_cmd diff; need_cmd shasum
  need_file "$BASE/manifest.py"
  # 規則檔固定在 repo 內；host 的 ~/.claude/CLAUDE.md 變動不得靜默改變受測環境。
  need_file "$RULES_SOURCE"
  need_file "$HASH_SH"
  # skills 直接取自 repo source of truth；不讀 ~/.claude/skills 或 ~/.agents/skills。
  for s in dispatch judgment token-preflight; do
    SRC=$(skill_src "$s")
    [ -d "$SRC" ] || { echo "缺少 repo skill source: $SRC" >&2; exit 2; }
  done
  # settings.json 只在需要保留單一 env 鍵時讀取，且只取那一個鍵；不存在也能跑。
fi

MODEL="${HARNESS_SUBJECT_MODEL:-sonnet}"

# --- 從 JSON 載入 fixture 清單（US 分隔：suite / id / config / deny_extra / prompt）---
# 清單落在 mktemp 而非 repo 內：dry-run 因此不在 repo 產生任何檔案。
TSV="$(mktemp)"
trap 'rm -f "$TSV"' EXIT INT TERM
python3 - "$BASE" "$FX" "$RT" > "$TSV" <<'LOADER'
import json, os, sys
sys.path.insert(0, sys.argv[1])
from transport import encode
for p in sys.argv[2:]:
    d = json.load(open(p))
    suite = d.get("skill_name") or d.get("suite_name")
    for f in d["fixtures"]:
        env = f.get("env") or {}
        # US(0x1F) 而非 tab：tab 是 IFS whitespace，連續 tab 會被 read 併成一個，
        # deny_extra 為空的列會讓 prompt 位移一格。
        print("\x1f".join([suite, f["id"], env.get("config", "default"),
                           " ".join(env.get("deny_extra", [])), encode(f["prompt"])]))
LOADER
TOTAL=$(wc -l < "$TSV" | tr -d ' ')

# fail-closed:transport 記錄數必須等於 JSON fixture 數。多行 prompt 若沒被編碼成單行,
# read 會把續行當成新記錄,續行第一欄還會成為 SUITE 並拼進輸出檔名。寧可中止也不要跑。
EXPECTED=$(python3 - "$FX" "$RT" <<'COUNT'
import json, sys
print(sum(len(json.load(open(p))["fixtures"]) for p in sys.argv[1:]))
COUNT
)
if [ "$TOTAL" -ne "$EXPECTED" ]; then
  echo "transport 記錄數 $TOTAL != JSON fixture 數 $EXPECTED:prompt 序列化有誤,中止" >&2
  exit 2
fi

# TSV 內的 prompt 是單行編碼形式;送進受測 session 前解碼。尾端 X 是 sentinel,
# 用來擋掉命令替換吃掉結尾換行。
decode_prompt() { printf '%s' "$1" | python3 "$BASE/transport.py"; printf 'X'; }

if [ "$DRY" -eq 1 ]; then
  echo "== dry-run: $TOTAL 筆 =="
  while IFS="$(printf '\037')" read -r SUITE ID CFGNAME DENYX PROMPT; do
    PROMPT=$(decode_prompt "$PROMPT"); PROMPT=${PROMPT%X}
    printf '%s__%s\n  config=%s  model=%s  deny_extra=[%s]\n  prompt=%s\n' \
      "$SUITE" "$ID" "$CFGNAME" "$MODEL" "$DENYX" "$PROMPT"
  done < "$TSV"
  exit 0
fi

RUN_ID="${1:-$(date +%Y%m%d-%H%M%S)-$(openssl rand -hex 3)}"
RUN="$RUNS_DIR/$RUN_ID"
OUT="$RUN/raw"
# work dir 與 config 副本一律建在 repo 之外：憑證連結與 session cwd 都不該落在版控目錄裡。
WORK="$(mktemp -d)"; PLUGD="$(mktemp -d)"
chmod 700 "$WORK" "$PLUGD"

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
if ! DISPATCH_HASH=$(sh "$HASH_SH" skill "$DISPATCH_SRC"); then
  echo "無法計算 repo bundle hash: dispatch" >&2
  rm -rf "$WORK" "$PLUGD"
  exit 2
fi
if ! JUDGMENT_HASH=$(sh "$HASH_SH" skill "$JUDGMENT_SRC"); then
  echo "無法計算 repo bundle hash: judgment" >&2
  rm -rf "$WORK" "$PLUGD"
  exit 2
fi
if ! TOKEN_PREFLIGHT_HASH=$(sh "$HASH_SH" skill "$TOKEN_PREFLIGHT_SRC"); then
  echo "無法計算 repo bundle hash: token-preflight" >&2
  rm -rf "$WORK" "$PLUGD"
  exit 2
fi
for HASH_PAIR in \
  "dispatch:$DISPATCH_HASH" \
  "judgment:$JUDGMENT_HASH" \
  "token-preflight:$TOKEN_PREFLIGHT_HASH"; do
  HASH_NAME=${HASH_PAIR%%:*}
  HASH_VALUE=${HASH_PAIR#*:}
  if ! valid_hash "$HASH_VALUE"; then
    echo "repo bundle hash 格式無效: $HASH_NAME (${HASH_VALUE:-空值})" >&2
    rm -rf "$WORK" "$PLUGD"
    exit 2
  fi
done

skill_expected_hash() {
  case "$1" in
    dispatch) echo "$DISPATCH_HASH" ;;
    judgment) echo "$JUDGMENT_HASH" ;;
    token-preflight) echo "$TOKEN_PREFLIGHT_HASH" ;;
    *) echo "未知 skill hash: $1" >&2; return 2 ;;
  esac
}

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
    if [ "$variant" = "no-$s" ]; then continue; fi
    SRC=$(skill_src "$s")
    cp -RL "$SRC" "$D/skills/$s"
    if ! diff -r "$SRC" "$D/skills/$s" >/dev/null; then
      echo "plugin 複製後與 repo source 不一致: $variant/$s" >&2
      rm -rf "$WORK" "$PLUGD"
      exit 2
    fi
    EXPECTED_HASH=$(skill_expected_hash "$s")
    if ! COPIED_HASH=$(sh "$HASH_SH" skill "$D/skills/$s"); then
      echo "無法計算 plugin bundle hash: $variant/$s" >&2
      rm -rf "$WORK" "$PLUGD"
      exit 2
    fi
    if ! valid_hash "$COPIED_HASH"; then
      echo "plugin bundle hash 格式無效: $variant/$s (${COPIED_HASH:-空值})" >&2
      rm -rf "$WORK" "$PLUGD"
      exit 2
    fi
    if [ "$COPIED_HASH" != "$EXPECTED_HASH" ]; then
      echo "plugin bundle hash 與 repo 不一致: $variant/$s" >&2
      echo "  repo=$EXPECTED_HASH plugin=$COPIED_HASH" >&2
      rm -rf "$WORK" "$PLUGD"
      exit 2
    fi
  done
  # 一般檔案設唯讀：session 改不動它,變體才是決定性的。不含 symlink（此處也沒有）。
  find "$D" -type f -exec chmod a-w {} +
done

[ ! -e "$PLUGD/no-dispatch/skills/dispatch" ] || {
  echo "no-dispatch 變體意外含 dispatch" >&2; rm -rf "$WORK" "$PLUGD"; exit 2;
}
[ ! -e "$PLUGD/no-judgment/skills/judgment" ] || {
  echo "no-judgment 變體意外含 judgment" >&2; rm -rf "$WORK" "$PLUGD"; exit 2;
}
echo "repo skill hashes:"
echo "  dispatch       $DISPATCH_HASH"
echo "  judgment       $JUDGMENT_HASH"
echo "  token-preflight $TOKEN_PREFLIGHT_HASH"

# 規則檔：從 repo 內固定來源複製；CLAUDE.md 不再自動載入。
RULES="$PLUGD/rules.md"
cp "$RULES_SOURCE" "$RULES"
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

# --- run-start manifest（必須在任何 session 之前）---
# 量測的是「這一輪 subject 實際跑在什麼版本上」。跑完再量一次，兩份由 record.py 比對；
# 任一 domain 在兩次量測之間變動，整輪 INVALID。先前的作法是跑完才現算一次，
# 那個值回答的是「錄紀錄的當下 repo 長什麼樣」，run 期間的任何編輯都會安靜地綁錯版本。
MANIFEST="$RUN/manifest.json"
TRACE_MANIFEST="$RUN/trace-manifest.json"
POST_JUDGE_MANIFEST="$RUN/post-judge-manifest.json"
DESC="$PLUGD/execution-context.txt"
JDESC="$PLUGD/evaluation-context.txt"
# descriptor 的唯一來源是產生它的那支程式自己——deny list 與 CLI flags 只有它們知道，
# 在此手抄一份必然漂移。不設 HARNESS_DENY_EXTRA：那是 fixture 層級的值，屬 fixtures domain。
if ! sh "$R" --print-context > "$DESC"; then
  echo "無法取得 execution-context descriptor" >&2
  rm -rf "$WORK" "$PLUGD"; exit 2
fi
# judge 端環境（model、CLI 版本、flags、structured output）是獨立 domain：
# 它變更只作廢 contract 判定，保留的 raw trace 仍可重新評分，不必重跑付費 subject session。
if ! HARNESS_JUDGE_MODEL="${HARNESS_JUDGE_MODEL:-sonnet}" \
     python3 "$BASE/judge.py" --print-context > "$JDESC"; then
  echo "無法取得 evaluation-context descriptor" >&2
  rm -rf "$WORK" "$PLUGD"; exit 2
fi
if ! python3 "$MANIFEST_PY" snapshot "$MANIFEST" start \
       "$RULES" "${SETTINGS:--}" "$DESC" "$JDESC" "$FX" "$RT" "$BASE/seed"; then
  echo "run-start manifest 產生失敗，中止（不得在沒有版本綁定的情況下花錢跑 session）" >&2
  rm -rf "$WORK" "$PLUGD"; exit 2
fi
# 一次性 nonce：每個 subject session 都把它寫進自己的 .meta.json，trace manifest 再逐檔
# 核對。record.py 要求 manifest／trace manifest／每份 meta 三方帶同一個值，才認這輪的
# trace manifest 是當下產生的。少了這條鏈，「事後補一份 manifest」就能升格成契約證據。
RUN_NONCE=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["run_nonce"])' \
              "$MANIFEST")
case "$RUN_NONCE" in
  [0-9a-f][0-9a-f]*) ;;
  *) echo "run manifest 沒有可用的 run_nonce，中止" >&2; rm -rf "$WORK" "$PLUGD"; exit 2 ;;
esac
export HARNESS_RUN_NONCE="$RUN_NONCE"

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
  PROMPT=$(decode_prompt "$PROMPT"); PROMPT=${PROMPT%X}
  HARNESS_DENY_EXTRA="$DENYX" "$R" "${SUITE}__${ID}" "$PROMPT" "$PLUGD/$CFGNAME" \
    || FAILED=$((FAILED + 1))
done < "$TSV"

echo
echo "== CLI 失敗筆數: $FAILED / $TOTAL =="

# --- raw trace manifest（subject 迴圈一結束就立刻算）---
# 之後允許「evaluator 變更後重新評分既有 trace 而不重跑付費 session」，這條路徑成立的前提
# 就是被重評的 trace 與當初產生的那一份逐 byte 相同。judge.py 重評前會核對本檔。
echo "== raw trace manifest =="
set +e
python3 "$MANIFEST_PY" trace "$TRACE_MANIFEST" "$OUT" "$RUN_NONCE"
TRACE_RC=$?
set -e
[ "$TRACE_RC" -eq 0 ] || echo "  !! trace manifest 產生失敗（可能是同路徑已存在，拒絕覆寫）；本輪跳過 judge，record.py 判 INVALID" >&2

echo "== routing assertions =="
set +e
python3 "$BASE/score.py" "$OUT" "$FX" "$RT"
SCORE_RC=$?
set -e
echo
echo "== response contract (LLM judge) =="
# 兩個跳過條件，任一成立就不呼叫 judge：
#   1. score.py 回 2 = 有 fixture 沒產生可用觀測。對空的或失敗的 trace 判定只會燒錢，
#      還會產生假的 contract FAIL（上一輪就白花了 $0.144）。
#   2. trace manifest 沒產生成功。此時無法證明 raw trace 未被更動，這一輪的 contract
#      判定從一開始就不可採信——先前只在 record 階段判 INVALID，錢卻已經花完了。
if [ "$TRACE_RC" -ne 0 ]; then
  echo "  跳過：trace manifest 未產生，無法證明 raw trace 未被更動，judge 不執行。"
  JUDGE_RC=2
elif [ "$SCORE_RC" -eq 2 ]; then
  echo "  跳過：routing 有未產生可用觀測的 fixture，本輪不構成契約證據，judge 不執行。"
  JUDGE_RC=0
else
  set +e
  python3 "$BASE/judge.py" "$OUT" "$FX" "$RT"
  JUDGE_RC=$?
  set -e
fi

# judge 產物在 subject trace manifest 之後才出現，必須另建 contemporaneous manifest。
# 只要 judge loop 曾執行，不論判定為 PASS 或 FAIL，都應完整產生每筆 `.judge.json`。
POST_JUDGE_RC=1
if [ "$TRACE_RC" -eq 0 ] && [ "$SCORE_RC" -ne 2 ]; then
  set +e
  python3 "$MANIFEST_PY" post-judge "$POST_JUDGE_MANIFEST" "$OUT" \
    "$TRACE_MANIFEST" "$FX" "$RT"
  POST_JUDGE_RC=$?
  set -e
  [ "$POST_JUDGE_RC" -eq 0 ] || echo "  !! post-judge manifest 產生失敗；record.py 會判 INVALID" >&2
else
  echo "  跳過 post-judge manifest：judge 未執行。"
fi
echo
echo "== run-end manifest（重新量測，與 run-start 比對）=="
# **descriptor 必須重新產生，不能重用 start 那兩份。** 重用等於事先宣告
# execution／evaluation context 不可能 drift：judge CLI 在 run 期間升版、
# HARNESS_JUDGE_MODEL 被改掉，兩種情況下 end 都會算出與 start 一模一樣的 hash，
# 「重新量測」變成一句空話。實測：CLI 版本改變後重用 descriptor 得到同一個
# evaluation_context hash，重新產生才會不同。
DESC_END="$PLUGD/execution-context.end.txt"
JDESC_END="$PLUGD/evaluation-context.end.txt"
set +e
sh "$R" --print-context > "$DESC_END" \
  && HARNESS_JUDGE_MODEL="${HARNESS_JUDGE_MODEL:-sonnet}" \
     python3 "$BASE/judge.py" --print-context > "$JDESC_END"
DESC_END_RC=$?
set -e
if [ "$DESC_END_RC" -ne 0 ]; then
  echo "  !! 無法重新產生 end descriptor；不寫 end 快照，record.py 會判 INVALID" >&2
  MANIFEST_END_RC=1
else
  set +e
  python3 "$MANIFEST_PY" snapshot "$MANIFEST" end \
    "$RULES" "${SETTINGS:--}" "$DESC_END" "$JDESC_END" "$FX" "$RT" "$BASE/seed"
  MANIFEST_END_RC=$?
  set -e
fi
[ "$MANIFEST_END_RC" -eq 0 ] || echo "  !! run-end manifest 產生失敗；record.py 會據此判 INVALID" >&2

echo
echo "== run record =="
RUN_ENDED=$(date +%s)
set +e
# 「這份 trace manifest 是當下產生的」不再由環境變數宣告——那只是自述。
# record.py 自己核對 manifest／trace manifest／每份 meta 的 run_nonce 是否三方一致。
HARNESS_RUN_STARTED="$RUN_STARTED" HARNESS_RUN_ENDED="$RUN_ENDED" \
HARNESS_CLI_FAILED="$FAILED" HARNESS_SUBJECT_MODEL="$MODEL" \
HARNESS_JUDGE_MODEL="${HARNESS_JUDGE_MODEL:-sonnet}" \
python3 "$BASE/record.py" "$OUT" "$RUN_ID" "$MANIFEST" "$FX" "$RT"
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
[ "$POST_JUDGE_RC" -eq 0 ] || SUITE_RC=1
[ "$RECORD_RC" -eq 0 ] || SUITE_RC=1
echo
echo "== suite 判定: CLI 失敗 $FAILED / routing rc $SCORE_RC / contract rc $JUDGE_RC / post-judge rc $POST_JUDGE_RC / record rc $RECORD_RC -> exit $SUITE_RC =="
exit "$SUITE_RC"
