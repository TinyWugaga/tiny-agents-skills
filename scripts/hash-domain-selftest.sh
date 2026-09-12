#!/bin/sh
# hash-domain-selftest.sh — 機械證明 hash schema v6 的 domain 互斥性（零成本，不起任何 session）
#
# 每個案例改動**一個**檔案，然後斷言**恰好一個** domain hash 變動。
# 這是 v2／v3 的核心主張——「evaluator 變更不作廢 skill observation」——唯一的機械證據；
# 沒有這支測試，domain 分離只是註解裡的宣稱。
#
# v3 新增涵蓋：
#   - `agents/**` 納入 skill domain（`default_prompt` 影響 runtime 行為）
#   - `token-preflight` 的 runtime 檔案只動它自己的 skill hash
#   - `execution-context` domain：規則檔／settings／descriptor 只動這一個
#   - raw trace 只動 trace manifest，不動任何輸入 domain
#
# v4 新增涵蓋：
#   - `evaluation-context` domain：judge model／judge CLI flags／structured-output 設定
#     只動這一個，**不動 `execution-context`**（受測環境與判定環境必須分開）
#
# v5 新增涵蓋：
#   - `contract_fixtures` domain：judge 判定當下實際載入的 fixture 檔。
#     它與 subject 的 `fixtures` 用同一套演算法，但**分別定址**——本檔讓兩者指向不同的
#     fixture 檔，證明改一邊不會動到另一邊。真實的重新評分正是這種情形：
#     subject 的 fixtures 來自來源 run，contract 的 fixtures 是現在這一份。
#
# v6 新增涵蓋：
#   - `rescore_runner` domain：`scripts/run-rescore.sh` 決定 derived 判定寫到哪裡、
#     以什麼順序驗證，因此屬於 identity 而不是純便利工具。
#
# 已知且刻意的耦合：descriptor 由 `run-fixture.sh --print-context` 產生，因此改動
# run-fixture.sh 的 deny list 會同時改變 runner 與 execution-context 兩個 hash。
# 那是正確的——deny list 既是 runner 的程式內容，也是實際執行環境的一部分。
# 本測試用固定的 descriptor 檔，量的是「descriptor 內容變了誰會動」，
# 不是「改 run-fixture.sh 誰會動」（後者由 runner 案例覆蓋）。
#
# 「run 中途修改輸入 → 整輪 INVALID」不在本檔：那是 record.py 的 manifest 比對行為，
# 由 scripts/run-provenance-selftest.sh 以真實 manifest 端到端驗證。
#
# 用法: sh scripts/hash-domain-selftest.sh      (exit 0 通過 / 1 失敗)

set -eu

SRC=$(cd -P "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
WORK="$TMP/repo"

mkdir -p "$WORK"
# 不複製 runs/：內容龐大且依 allowlist 本就不影響任何輸入 domain（下有專門案例驗證這點）。
(cd "$SRC" && find . -path ./.git -prune -o -path './skills/harness/evals/runs' -prune -o \
   -type f -print | while IFS= read -r f; do
     mkdir -p "$WORK/$(dirname "$f")"; cp "$SRC/$f" "$WORK/$f"
   done)

H="$WORK/scripts/bundle-hash.sh"
MP="$WORK/skills/harness/evals/manifest.py"
FX="$WORK/skills/harness/dispatch/evals/fixtures.json"
JFX="$WORK/skills/discipline/judgment/evals/fixtures.json"
RT="$WORK/skills/harness/evals/routing-fixtures.json"
SEED="$WORK/skills/harness/evals/seed"

# --- execution-context 的三個組件 ---
# 放在 repo 內但不屬於任何 allowlist 的路徑，證明它們只影響 execution-context。
# 真實 run 裡這三個檔都在 mktemp 目錄下，識別的是內容不是路徑。
CTX="$WORK/.selftest-ctx"
mkdir -p "$CTX"
printf '# 假的注入規則檔\n直接、不客套。\n' > "$CTX/rules.md"
printf '{"env":{"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH":"2"}}\n' > "$CTX/settings.json"
sh "$WORK/skills/harness/evals/run-fixture.sh" --print-context > "$CTX/desc.txt"

# --- evaluation-context 的 descriptor（judge 端環境）---
# 與 execution-context 同樣的道理：descriptor 是 judge.py 的輸出，這裡把它固定成一個檔，
# 量的是「descriptor 內容變了誰會動」。改 judge.py 本身走的是 evaluator 案例。
HARNESS_JUDGE_MODEL=sonnet python3 "$WORK/skills/harness/evals/judge.py" \
  --print-context > "$CTX/judge-desc.txt"

# --- raw trace（trace manifest 的量測對象）---
TRACEDIR="$WORK/skills/harness/evals/runs/tracecase/raw"
mkdir -p "$TRACEDIR"
printf '{"type":"system","subtype":"init"}\n{"type":"result","subtype":"success"}\n' \
  > "$TRACEDIR/suite__case-1.jsonl"
printf '{"id":"suite__case-1","exit_code":0}\n' > "$TRACEDIR/suite__case-1.meta.json"

DOMAINS="dispatch_skill judgment_skill token_preflight_skill evaluator runner fixtures contract_fixtures execution_context evaluation_context rescore_runner trace_manifest"

hash_of() {
  case "$1" in
    dispatch_skill)        sh "$H" skill "$WORK/skills/harness/dispatch" ;;
    judgment_skill)        sh "$H" skill "$WORK/skills/discipline/judgment" ;;
    token_preflight_skill) sh "$H" skill "$WORK/skills/discipline/token-preflight" ;;
    evaluator)             sh "$H" evaluator "$WORK/skills/harness" ;;
    runner)                sh "$H" runner "$WORK/skills/harness" ;;
    fixtures)              sh "$H" fixtures "$FX" "$RT" "$SEED" ;;
    # contract 那半指向另一份 fixture 檔，證明兩個 domain 分別定址。
    contract_fixtures)     sh "$H" fixtures "$JFX" "$RT" "$SEED" ;;
    execution_context)     sh "$H" execution-context \
                              "$CTX/rules.md" "$CTX/settings.json" "$CTX/desc.txt" ;;
    evaluation_context)    sh "$H" evaluation-context "$CTX/judge-desc.txt" ;;
    rescore_runner)        (cd "$WORK" && sh "$H" rescore-runner) ;;
    # BR-F24 之後 `manifest.py trace` 不覆寫既有檔案，因此每次量測前先明確刪除。
    # 這正是它要求的姿態：重建 trace manifest 必須是一個刻意的動作。
    trace_manifest)        rm -f "$TMP/tm.json"
                           python3 "$MP" trace "$TMP/tm.json" "$TRACEDIR" >/dev/null \
                              && python3 -c 'import hashlib,json,sys;
d=json.load(open(sys.argv[1]))["files"];
print(hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest())' "$TMP/tm.json" ;;
  esac
}

snapshot() { for d in $DOMAINS; do printf '%s=%s\n' "$d" "$(hash_of "$d")"; done; }

BASE=$(snapshot)
fails=0
ncase=0

# case_run <說明> <要改的檔案（相對 repo root），"-NEW-" 表示新增檔案> <預期變動的 domain，"none" 表示都不變> [新檔路徑]
case_run() {
  label="$1"; target="$2"; expect="$3"
  ncase=$((ncase + 1))
  if [ "$target" = "-NEW-" ]; then
    newfile="$4"
    mkdir -p "$WORK/$(dirname "$newfile")"
    echo "x" > "$WORK/$newfile"
    after=$(snapshot)
    rm -f "$WORK/$newfile"
  else
    cp "$WORK/$target" "$TMP/orig"
    printf '\n# hash-domain-selftest mutation\n' >> "$WORK/$target"
    after=$(snapshot)
    cp "$TMP/orig" "$WORK/$target"
  fi

  changed=""
  for d in $DOMAINS; do
    b=$(printf '%s\n' "$BASE"  | grep "^$d=" | cut -d= -f2)
    a=$(printf '%s\n' "$after" | grep "^$d=" | cut -d= -f2)
    [ "$b" = "$a" ] || changed="$changed $d"
  done
  changed=$(echo $changed)
  [ -z "$changed" ] && changed="none"

  if [ "$changed" = "$expect" ]; then
    echo "  ok   $label → $changed"
  else
    echo "  FAIL $label → 預期 [$expect]，實得 [$changed]"
    fails=$((fails + 1))
  fi

  # 還原後必須回到 baseline，否則後續案例的比較基準已經漂移。
  now=$(snapshot)
  [ "$now" = "$BASE" ] || { echo "  FAIL $label 還原後未回到 baseline"; fails=$((fails + 1)); }
}

echo "hash schema $(sh "$H" schema-version) — domain 互斥性"

# --- evaluator ---
case_run "改 judge.py（判定程式）"            skills/harness/evals/judge.py          evaluator
case_run "改 score.py（判定程式）"            skills/harness/evals/score.py          evaluator
case_run "改 record.py（紀錄程式）"           skills/harness/evals/record.py         evaluator

# --- runner ---
case_run "改 run-fixture.sh（session 隔離）"  skills/harness/evals/run-fixture.sh    runner
case_run "改 run-suite.sh（plugin 組裝）"     skills/harness/evals/run-suite.sh      runner
case_run "改 transport.py（prompt 傳輸）"     skills/harness/evals/transport.py      runner
case_run "改 manifest.py（run 快照範圍）"     skills/harness/evals/manifest.py       runner

# --- rescore-runner（v6）---
case_run "改 run-rescore.sh（重評編排）"      scripts/run-rescore.sh                 rescore_runner

# --- skill（含 v3 新增的 agents/**）---
case_run "改 dispatch/SKILL.md"               skills/harness/dispatch/SKILL.md       dispatch_skill
case_run "改 dispatch/references/templates.md" skills/harness/dispatch/references/templates.md dispatch_skill
case_run "改 judgment/SKILL.md"               skills/discipline/judgment/SKILL.md    judgment_skill
case_run "改 judgment/references/verifier.md" skills/discipline/judgment/references/verifier.md judgment_skill
case_run "改 token-preflight/SKILL.md（runtime 檔）" skills/discipline/token-preflight/SKILL.md token_preflight_skill
case_run "新增 dispatch/agents/openai.yaml（v3 納入）" -NEW- dispatch_skill skills/harness/dispatch/agents/openai.yaml
case_run "新增 judgment/agents/openai.yaml（v3 納入）" -NEW- judgment_skill skills/discipline/judgment/agents/openai.yaml
case_run "新增 token-preflight/agents/openai.yaml（v3 納入）" -NEW- token_preflight_skill skills/discipline/token-preflight/agents/openai.yaml

# --- fixtures ---
case_run "改 dispatch fixtures.json（subject 側）" skills/harness/dispatch/evals/fixtures.json fixtures
# routing-fixtures 與 seed 是兩側共用的輸入，因此兩個 domain 都會動——這是正確的，
# 不是耦合缺陷：subject 與 contract 確實都載入了這兩份。
case_run "改 routing-fixtures.json（兩側共用）" skills/harness/evals/routing-fixtures.json "fixtures contract_fixtures"
case_run "改 seed/SPEC.md（兩側共用）"          skills/harness/evals/seed/SPEC.md      "fixtures contract_fixtures"

# --- execution-context ---
case_run "改注入的規則檔（CLAUDE.md 副本）"   .selftest-ctx/rules.md                 execution_context
case_run "改消毒後 settings"                  .selftest-ctx/settings.json            execution_context
case_run "改 descriptor（model／flags／deny）" .selftest-ctx/desc.txt                execution_context

# --- evaluation-context（v4）---
case_run "改 judge descriptor"                .selftest-ctx/judge-desc.txt           evaluation_context

# judge model 與 judge CLI flags 是 evaluation-context 的實質內容，不是附加註解。
# 這兩個案例重新產生 descriptor 而不是附加一行，證明「換 judge model／換 flags」
# 真的只動 evaluation_context——尤其是**不動 execution_context**，那是受測端的環境。
case_regen() {
  label="$1"; expect="$2"; shift 2
  ncase=$((ncase + 1))
  cp "$CTX/judge-desc.txt" "$TMP/orig-judge"
  env "$@" python3 "$WORK/skills/harness/evals/judge.py" --print-context \
    > "$CTX/judge-desc.txt"
  if cmp -s "$TMP/orig-judge" "$CTX/judge-desc.txt"; then
    echo "  FAIL $label → descriptor 內容沒有改變，這個案例沒有測到東西"
    fails=$((fails + 1))
    cp "$TMP/orig-judge" "$CTX/judge-desc.txt"
    return
  fi
  after=$(snapshot)
  cp "$TMP/orig-judge" "$CTX/judge-desc.txt"
  changed=""
  for d in $DOMAINS; do
    b=$(printf '%s\n' "$BASE"  | grep "^$d=" | cut -d= -f2)
    a=$(printf '%s\n' "$after" | grep "^$d=" | cut -d= -f2)
    [ "$b" = "$a" ] || changed="$changed $d"
  done
  changed=$(echo $changed)
  [ -z "$changed" ] && changed="none"
  if [ "$changed" = "$expect" ]; then
    echo "  ok   $label → $changed"
  else
    echo "  FAIL $label → 預期 [$expect]，實得 [$changed]"
    fails=$((fails + 1))
  fi
  now=$(snapshot)
  [ "$now" = "$BASE" ] || { echo "  FAIL $label 還原後未回到 baseline"; fails=$((fails + 1)); }
}

case_regen "換 judge model（sonnet → opus）" evaluation_context HARNESS_JUDGE_MODEL=opus
case_regen "換 judge CLI flag（structured output）" evaluation_context \
  HARNESS_JUDGE_MODEL=sonnet HARNESS_JUDGE_JSON_SCHEMA=schemas/verdict.json
case_regen "換 judge timeout" evaluation_context \
  HARNESS_JUDGE_MODEL=sonnet HARNESS_JUDGE_TIMEOUT=600

# --- raw trace 只動 trace manifest ---
case_run "改 raw trace（.jsonl）"             skills/harness/evals/runs/tracecase/raw/suite__case-1.jsonl  trace_manifest
case_run "改 raw trace 旁證（.meta.json）"    skills/harness/evals/runs/tracecase/raw/suite__case-1.meta.json trace_manifest

# --- 都不該動任何 domain ---
case_run "改 judge_selftest.py（測試本身）"   skills/harness/evals/judge_selftest.py none
case_run "改 record_selftest.py（測試本身）"  skills/harness/evals/record_selftest.py none
case_run "改 STATUS.md（紀錄文件）"           skills/harness/evals/STATUS.md         none
case_run "改 KNOWN-ISSUES.md（紀錄文件）"     skills/harness/evals/KNOWN-ISSUES.md   none
case_run "新增其他 run 的結果檔"              -NEW-  none  skills/harness/evals/runs/x/raw/a.jsonl
case_run "新增 .DS_Store"                     -NEW-  none  skills/harness/dispatch/references/.DS_Store

# contract 側的 fixture 只動 contract_fixtures：改 assertion 重評舊 trace 時，
# subject 的 fixtures 綁定不該跟著變。
case_run "改 judgment fixtures.json（contract 側）" skills/discipline/judgment/evals/fixtures.json contract_fixtures

# 未在本次 fixtures 引數中列出的 fixture 不得污染 fixture hash——這是「只 hash 本次實際載入」的要點。
case_run "改 token-preflight fixtures.json（本次未載入）" skills/discipline/token-preflight/evals/fixtures.json none

echo
if [ "$fails" -eq 0 ]; then
  echo "hash-domain-selftest: $ncase 案例全部通過"
  exit 0
fi
echo "hash-domain-selftest: $fails/$ncase 失敗"
exit 1
