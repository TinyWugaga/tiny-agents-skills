#!/bin/sh
# bundle-hash.sh — 計算 skill bundle 的 deterministic 內容 hash
#
# 用法: bundle-hash.sh <skill 目錄>
#
# 設計要求:
#   1. **路徑無關**:同一份內容,不論經 symlink 或實體路徑存取,結果必須相同。
#      (直接對 `shasum` 輸出再摘要會失敗——它的輸出含絕對路徑。)
#   2. **檔名敏感**:改檔名要改變 hash,所以摘要對象是「相對路徑 + 內容 hash」的組合。
#   3. **涵蓋範圍**:SKILL.md + references/** + evals/fixtures.json
#      **排除 evals/runs/**——結果檔不得反過來改變被測版本。
#
# 輸出: 單行 SHA-256

set -eu

[ $# -eq 1 ] || { echo "usage: $0 <skill-dir>" >&2; exit 2; }
DIR=$(cd -P "$1" && pwd)   # -P 解析 symlink,確保兩種存取路徑收斂到同一實體目錄

cd "$DIR"
find -L . -type f \( -name '*.md' -o -name 'fixtures.json' \) \
     -not -path './evals/runs/*' \
  | LC_ALL=C sort \
  | while IFS= read -r f; do
      printf '%s  %s\n' "${f#./}" "$(shasum -a 256 "$f" | cut -d' ' -f1)"
    done \
  | shasum -a 256 | cut -d' ' -f1
