#!/bin/sh
# run-rescore.sh <來源 run 目錄> <新 run id> <fixtures.json> [<fixtures.json> …]
#
# 用保留的 raw trace 重新評分，產生 derived record。**這是重新評分的唯一建議入口。**
#
# ## 三件這支腳本負責的事（都不是「純便利」）
#
#   1. **判定寫到哪裡。** judge 會把 `<fixture>.judge.json` 寫進它被指到的目錄。
#      直接把來源 `raw/` 交給它，會覆蓋掉來源 run 的逐筆判定證據——而 trace manifest
#      只涵蓋 `.jsonl`／`.meta.json`，這種破壞偵測不到。因此本檔把 `.jsonl`／`.meta.json`
#      複製到獨立的 derived 目錄，judge 只寫那裡；結束前再核對來源目錄逐 byte 未變。
#   2. **驗證的先後順序。** 所有會讓整輪變 INVALID 的條件（來源紀錄、trace digest、
#      prompt 對應、subject hash 格式、migration audit）都是零成本可判的，因此全部排在
#      付費 judge **之前**。先跑 judge 再驗，等於保留「判不了仍先花錢」的路徑。
#   3. **descriptor 每次重新產生。** judge 前後各量一次 contract identity，兩次都重新
#      執行 `judge.py --print-context`；沿用同一份會讓重評期間的 CLI 升版完全隱形。
#
# ## exit code
#
#   0  judge 全數通過且 derived record 正常寫出
#   1  judge 判出 contract FAIL／ERROR，或 record 寫出失敗（derived record 仍保留）
#   2  preflight 或 containment 檢查不通過（未進入付費 judge，或未產生可信輸出）
#
# 因為前兩件事直接決定 derived record 的可信度，本檔**屬於 identity**：
# `bundle-hash.sh rescore-runner`，並記在 contract manifest 的 `rescore_runner` domain。
#
# 環境變數：
#   HARNESS_SOURCE_RECORD    來源 run record（預設 <來源目錄>/<目錄名>.json）
#   HARNESS_MIGRATION_AUDIT  跨 hash_schema 時必填的內容等價稽核
#   HARNESS_JUDGE_MODEL      judge model（預設 sonnet）
set -eu

[ $# -ge 3 ] || {
  echo "usage: $0 <來源 run 目錄> <新 run id> <fixtures.json> [...]" >&2; exit 2; }

SRC_DIR=$(cd -P "$1" && pwd); shift
NEW_ID="$1"; shift
BASE="$(cd "$(dirname "$0")/../skills/harness/evals" && pwd)"
SRC_RAW="$SRC_DIR/raw"
SRC_RECORD="${HARNESS_SOURCE_RECORD:-$SRC_DIR/$(basename "$SRC_DIR").json}"

# --- run id 的路徑範圍 ---
# `NEW_ID` 會被拼進輸出路徑，而失敗路徑上有 `rm -rf "$DERIVED"`。未經檢查時
# `../../victim` 會解析到 `derived/` 之外——實測 `<run>/derived/../../victim` 落在
# `runs/victim`，而且 preflight 失敗時那個路徑就是 `rm -rf` 的目標。
# 因此先用字元 allowlist 擋掉分隔符與相對路徑，之後再用 canonical path 複驗一次：
# 前者擋掉字面上的逸出，後者擋掉 symlink 造成的逸出。
# 判定一律用 shell pattern，**不用 command substitution**。
# `x=$(printf %s "$id" | tr -d 'A-Za-z0-9._-')` 看起來等價，實際上有洞：
# 命令替換會剝掉尾端換行，所以 `safe<LF>line` 過完 tr 只剩一個 `\n`，被剝成空字串，
# 判定成「沒有非法字元」而放行。實測如此。控制字元因此能進到檔名與 log。
case "$NEW_ID" in
  ""|.*|*/*)
    echo "run id 不合法（不得為空、以 . 開頭或含 /）" >&2; exit 2 ;;
esac
case "$NEW_ID" in
  *[!A-Za-z0-9._-]*)
    # 不回顯原字串：它可能帶控制字元或 ANSI escape，那正是要擋的東西。
    # 只把非法位元組換成 ? 之後顯示，供人辨認是哪一段有問題。
    echo "run id 只允許 A-Z a-z 0-9 . _ -（收到: $(printf '%s' "$NEW_ID" \
         | tr -c 'A-Za-z0-9._-' '?')）" >&2
    exit 2 ;;
esac

DERIVED_ROOT="$SRC_DIR/derived"
DERIVED="$DERIVED_ROOT/$NEW_ID"
DRAW="$DERIVED/raw"
CMAN="$DERIVED/contract-manifest.json"
POST_JUDGE_MANIFEST="$DERIVED/post-judge-manifest.json"
JDESC="$(mktemp -t harness-judge-desc)"
trap 'rm -f "$JDESC"' EXIT INT TERM

# 在確認 containment 之前，abort 不得刪任何東西。
DERIVED_SAFE=0

need() { [ -e "$1" ] || { echo "缺少: $1" >&2; exit 2; }; }
need "$SRC_RAW"
need "$SRC_RECORD"
need "$SRC_DIR/trace-manifest.json"
for f in "$@"; do need "$f"; done
[ ! -e "$DERIVED" ] || { echo "derived 目錄已存在，換一個 run id: $DERIVED" >&2; exit 2; }

# 來源目錄的內容指紋：結束前再算一次，證明重評沒有動到它。
src_fingerprint() {
  find "$SRC_RAW" -type f | LC_ALL=C sort | while IFS= read -r f; do
    printf '%s  %s\n' "${f#"$SRC_RAW"/}" "$(shasum -a 256 "$f" | cut -d' ' -f1)"
  done | shasum -a 256 | cut -d' ' -f1
}
SRC_BEFORE=$(src_fingerprint)

echo "== 重新評分 =="
echo "  來源 run     : $SRC_DIR"
echo "  來源 record  : $SRC_RECORD"
echo "  derived 目錄 : $DERIVED"
echo "  judge model  : ${HARNESS_JUDGE_MODEL:-sonnet}"

# --- 0. containment 複驗，然後才建立目錄 ---
# 兩道檢查合起來才夠：字元 allowlist（上面）擋字面上的逸出，canonical path 擋 symlink。
# 順序很重要——**先驗再建**，否則逸出的路徑上已經留下檔案才被發現。
mkdir -p "$DERIVED_ROOT"
if [ -L "$DERIVED_ROOT" ]; then
  echo "derived/ 是 symlink，拒絕使用：$DERIVED_ROOT" >&2; exit 2
fi
DERIVED_ROOT_REAL=$(cd -P "$DERIVED_ROOT" && pwd)
if [ "$DERIVED_ROOT_REAL" != "$SRC_DIR/derived" ]; then
  echo "derived/ 解析後不在來源 run 目錄內：$DERIVED_ROOT_REAL" >&2; exit 2
fi

# --- 只複製 subject 產物到 derived 目錄；judge 的新判定只寫這裡 ---
mkdir -p "$DRAW"
DERIVED_REAL=$(cd -P "$DERIVED" && pwd)
if [ "$DERIVED_REAL" != "$DERIVED_ROOT_REAL/$NEW_ID" ]; then
  echo "derived 目標逸出 derived/：$DERIVED_REAL（預期 $DERIVED_ROOT_REAL/$NEW_ID）" >&2
  echo "已建立的目錄不會被自動刪除——未確認 containment 前不對任何路徑執行 rm -rf。" >&2
  exit 2
fi
DERIVED_SAFE=1
for f in "$SRC_RAW"/*.jsonl "$SRC_RAW"/*.meta.json; do
  [ -e "$f" ] || continue
  cp "$f" "$DRAW/"
done
SRC_NONCE=$(python3 - "$SRC_RECORD" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    print("")
else:
    print(((d.get("provenance") or {}).get("run_nonce")) or "")
PY
)
if [ -n "$SRC_NONCE" ]; then
  python3 "$BASE/manifest.py" trace "$DERIVED/trace-manifest.json" "$DRAW" "$SRC_NONCE"
else
  python3 "$BASE/manifest.py" trace "$DERIVED/trace-manifest.json" "$DRAW"
fi

# --- 1. contract identity（判定前）；descriptor 重新產生 ---
HARNESS_JUDGE_MODEL="${HARNESS_JUDGE_MODEL:-sonnet}" python3 "$BASE/judge.py" \
  --print-context > "$JDESC"
python3 "$BASE/manifest.py" contract-snapshot "$CMAN" start "$JDESC" "$@"

# 只在 containment 通過後才清理，且刪的是解析過的路徑。
abort() {
  echo "$1" >&2
  [ "$DERIVED_SAFE" -eq 1 ] && rm -rf "$DERIVED_REAL"
  exit 2
}

# --- 2. 零成本 preflight：所有可判的 provenance 條件都在花錢之前判完 ---
echo
echo "== preflight（零成本，未呼叫任何 judge session）=="
if [ -n "${HARNESS_MIGRATION_AUDIT:-}" ]; then
  python3 "$BASE/record.py" --source "$SRC_RECORD" \
    --migration-audit "$HARNESS_MIGRATION_AUDIT" --validate-only \
    "$DRAW" "$NEW_ID" "$CMAN" "$@" || abort "preflight 不通過，不進入付費 judge。"
else
  python3 "$BASE/record.py" --source "$SRC_RECORD" --validate-only \
    "$DRAW" "$NEW_ID" "$CMAN" "$@" || abort "preflight 不通過，不進入付費 judge。"
fi
HARNESS_SOURCE_RECORD="$SRC_RECORD" python3 "$BASE/judge.py" --preflight "$DRAW" "$@" \
  || abort "judge preflight 不通過，不進入付費 judge。"

# --- 3. 重新判定（唯一會花錢的一步）---
echo
echo "== judge =="
# judge rc: 0 全過 / 1 有 FAIL 或 ERROR（仍要記錄）/ 2 fail-closed 中止（不可繼續）。
set +e
HARNESS_SOURCE_RECORD="$SRC_RECORD" python3 "$BASE/judge.py" "$DRAW" "$@"
JUDGE_RC=$?
set -e
[ "$JUDGE_RC" -ne 2 ] || abort "judge fail-closed 中止（未呼叫任何 judge session）。"

# --- 4. post-judge 產物綁定 ---
# `.judge.json` 在 trace manifest 之後才產生，另建不可覆寫的 manifest，並綁定來源 trace digest。
set +e
python3 "$BASE/manifest.py" post-judge "$POST_JUDGE_MANIFEST" "$DRAW" \
  "$DERIVED/trace-manifest.json" "$@"
POST_JUDGE_RC=$?
set -e

# --- 5. contract identity（判定後）；**重新產生**，不是重用步驟 1 那一份 ---
HARNESS_JUDGE_MODEL="${HARNESS_JUDGE_MODEL:-sonnet}" python3 "$BASE/judge.py" \
  --print-context > "$JDESC"
python3 "$BASE/manifest.py" contract-snapshot "$CMAN" end "$JDESC" "$@"

# --- 6. derived record ---
echo
echo "== derived record =="
set +e
if [ -n "${HARNESS_MIGRATION_AUDIT:-}" ]; then
  python3 "$BASE/record.py" --source "$SRC_RECORD" \
    --migration-audit "$HARNESS_MIGRATION_AUDIT" "$DRAW" "$NEW_ID" "$CMAN" "$@"
else
  python3 "$BASE/record.py" --source "$SRC_RECORD" "$DRAW" "$NEW_ID" "$CMAN" "$@"
fi
RECORD_RC=$?
set -e

# --- 7. 證明來源目錄逐 byte 未變 ---
SRC_AFTER=$(src_fingerprint)
if [ "$SRC_BEFORE" != "$SRC_AFTER" ]; then
  echo "!! 來源 raw 目錄在重評期間被更動了（$SRC_BEFORE -> $SRC_AFTER）" >&2
  echo "   這是嚴重錯誤：重評不得寫入來源。derived record 不可採信。" >&2
  exit 2
fi

# --- 8. exit code 必須同時反映判定結果與紀錄結果 ---
# 先前只看 RECORD_RC：judge 判出 contract FAIL（rc 1）而 record 正常寫出時，
# 整支腳本回 0，CI 或發布流程會把 contract FAIL 讀成成功。
# derived record 仍然保留——FAIL 是結論不是故障，紀錄要留著；但 exit code 不得說成功。
RC=0
[ "$JUDGE_RC" -eq 0 ] || RC=1
[ "$POST_JUDGE_RC" -eq 0 ] || RC=1
[ "$RECORD_RC" -eq 0 ] || RC=1
echo
echo "== 判定: judge rc $JUDGE_RC / post-judge rc $POST_JUDGE_RC / record rc $RECORD_RC / 來源目錄未變 -> exit $RC =="
if [ "$JUDGE_RC" -ne 0 ]; then
  echo "   （judge rc 1 = 有 contract FAIL 或 ERROR；derived record 已保留）"
fi
exit "$RC"
