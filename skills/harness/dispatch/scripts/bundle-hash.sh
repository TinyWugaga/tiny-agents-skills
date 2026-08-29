#!/bin/sh
# bundle-hash.sh — 計算 bundle 的 deterministic 內容 hash
#
# 用法: bundle-hash.sh <目錄> [skill|suite]     (mode 預設 skill)
#
#   skill 傳 **skill 目錄**            例: skills/harness/dispatch
#   suite 傳 **collection 目錄**       例: skills/harness
#
# 傳錯目錄會使 allowlist 一筆都不match,此時本腳本以 exit 3 中止,
# 不會回傳「空輸入的 hash」——那種值看起來完全正常,是版本綁定最危險的失敗模式。
#
# 設計要求:
#   1. **路徑無關**:同一份內容,不論經 symlink 或實體路徑存取,結果必須相同。
#      (直接對 `shasum` 輸出再摘要會失敗——它的輸出含絕對路徑。)
#   2. **檔名敏感**:改檔名要改變 hash,所以摘要對象是「相對路徑 + 內容 hash」的組合。
#   3. **allowlist**:只有下列明列路徑進入摘要。未列出的一律不影響 hash——
#      包含 `evals/runs/`(結果檔不得反過來改變被測版本)與任何暫存或編輯器產物。
#
# allowlist:
#   skill = SKILL.md + references/** + scripts/** + evals/fixtures.json
#   suite = evals/*.py + evals/*.sh + evals/routing-fixtures.json + evals/seed/**
#
# 兩種 mode 都排除 .DS_Store:Finder 隨機產生,不屬於任何契約。
#
# 輸出: 單行 SHA-256

set -eu

[ $# -ge 1 ] && [ $# -le 2 ] || { echo "usage: $0 <dir> [skill|suite]" >&2; exit 2; }
DIR=$(cd -P "$1" && pwd)   # -P 解析 symlink,確保兩種存取路徑收斂到同一實體目錄
MODE="${2:-skill}"

case "$MODE" in
  skill|suite) ;;
  *) echo "unknown mode: $MODE (skill|suite)" >&2; exit 2 ;;
esac

cd "$DIR"

emit_file() { [ -f "$1" ] && echo "$1" || true; }
emit_tree() { [ -d "$1" ] && find -L "$1" -type f || true; }

emit_allowlist() {
  if [ "$MODE" = skill ]; then
    emit_file SKILL.md
    emit_tree references
    emit_tree scripts
    emit_file evals/fixtures.json
  else
    for f in evals/*.py evals/*.sh; do emit_file "$f"; done
    emit_file evals/routing-fixtures.json
    emit_tree evals/seed
  fi
}

LIST=$(emit_allowlist | grep -v -e '^\.DS_Store$' -e '/\.DS_Store$' | LC_ALL=C sort)
[ -n "$LIST" ] || {
  echo "no files matched the $MODE allowlist under $DIR — 目錄或 mode 傳錯?" >&2
  exit 3
}

printf '%s\n' "$LIST" \
  | while IFS= read -r f; do
      printf '%s  %s\n' "$f" "$(shasum -a 256 "$f" | cut -d' ' -f1)"
    done \
  | shasum -a 256 | cut -d' ' -f1
