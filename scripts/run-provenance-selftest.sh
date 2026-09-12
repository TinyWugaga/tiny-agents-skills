#!/bin/sh
# run-provenance-selftest.sh — 以**模擬 run** 端到端驗證版本綁定（零成本，不起任何 session）
#
# hash-domain-selftest.sh 證明的是「改一個檔案，恰好一個 domain 變動」。本檔證明的是
# 下一層問題：**那些 hash 真的被用來擋住不該成立的結論嗎，而且擋在花錢之前嗎。**
#
# 模擬 run 用合成的 stream-json 與 `.judge.json`，因此完全不呼叫真實 claude CLI、不花錢，
# 但走的是與真實 run 完全相同的 `manifest.py` → `record.py` → `judge.py` 路徑。
# 需要證明「CLI 沒被呼叫」或「CLI 版本變了會被抓到」的地方，PATH 前置一支可控的 stub。
#
# 驗證項：
#   1. 開始／結束 hash 相同 → 產生證據
#   2. run 中途修改任一輸入 → 一律 INVALID；manifest 不完整或缺 version → INVALID
#   3. trace manifest 缺失／壞損／為空 → judge 在進 loop 前中止，**CLI 呼叫次數 0**
#   4. trace manifest 不可覆寫；digest 不符禁止重評；derived record 不覆寫 source
#   5. judge 輸出在逐條項目內夾帶 corrected_verdict → 被拒
#   6. （BR-F26）end 必須**重新產生** descriptor：重用會讓 CLI 升版看起來像無 drift
#   7. （BR-F27）同名 phase 不可覆寫：否則 start 被蓋掉、drift 完全隱形
#   8. （BR-F28）v3 來源 trace 可以產生有效的 v4 derived record
#
# 用法: sh scripts/run-provenance-selftest.sh      (exit 0 通過 / 1 失敗)

set -eu

SRC=$(cd -P "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
WORK="$TMP/repo"

mkdir -p "$WORK"
(cd "$SRC" && find . -path ./.git -prune -o -path './skills/harness/evals/runs' -prune -o \
   -type f -print | while IFS= read -r f; do
     mkdir -p "$WORK/$(dirname "$f")"; cp "$SRC/$f" "$WORK/$f"
   done)

E="$WORK/skills/harness/evals"
H="$WORK/scripts/bundle-hash.sh"
RUN="$E/runs/sim"
RAW="$RUN/raw"
MAN="$RUN/manifest.json"
CMAN="$RUN/contract-manifest.json"
TM="$RUN/trace-manifest.json"
PJ="$RUN/post-judge-manifest.json"
FXJ="$E/sim-fixtures.json"
SEED="$E/seed"
CTX="$TMP/ctx"
mkdir -p "$RAW" "$CTX"

printf '# 模擬注入規則檔\n直接、不客套。\n' > "$CTX/rules.md"
printf '{"env":{"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH":"2"}}\n' > "$CTX/settings.json"
sh "$E/run-fixture.sh" --print-context > "$CTX/desc.txt"
HARNESS_JUDGE_MODEL=sonnet python3 "$E/judge.py" --print-context > "$CTX/judge-desc.txt"

cat > "$TMP/stamp.py" <<'STAMPPY'
import json, os, sys
man, raw = sys.argv[1], sys.argv[2]
nonce = json.load(open(man)).get("run_nonce") or None
for fn in sorted(os.listdir(raw)):
    if fn.endswith(".meta.json"):
        p = os.path.join(raw, fn)
        d = json.load(open(p))
        d["run_nonce"] = nonce
        json.dump(d, open(p, "w"), ensure_ascii=False)
print(nonce or "")
STAMPPY

fails=0
check() {
  if [ "$2" = "1" ]; then echo "  ok   $1"; else echo "  FAIL $1${3:+ — $3}"; fails=$((fails + 1)); fi
}

# --- 合成 fixture 與 trace ---
# score.py 要判 PASS 需要：meta exit_code 0、system/init、result success、
# 主執行緒的 Skill 呼叫對得到 tool_result 且 is_error 為 false。
cat > "$FXJ" <<'JSON'
{
  "skill_name": "dispatch",
  "fixtures": [
    {"id": "case-1", "category": "positive", "expected_trigger": true,
     "prompt": "模擬 prompt",
     "required_elements": ["寫出派工單"], "forbidden_elements": []}
  ]
}
JSON

cat > "$RAW/dispatch__case-1.jsonl" <<'JSONL'
{"type":"system","subtype":"init","skills":["dispatch"]}
{"type":"assistant","parent_tool_use_id":null,"message":{"content":[{"type":"tool_use","name":"Skill","id":"t1","input":{"skill":"dispatch"}}]}}
{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"t1","is_error":false}]}}
{"type":"assistant","parent_tool_use_id":null,"message":{"content":[{"type":"text","text":"派工單如下：目標、驗收條件、版本標記。"}]}}
{"type":"result","subtype":"success","total_cost_usd":0.05}
JSONL
# meta 必須記下實際送出的 prompt：重新評分前 judge 會拿它跟 fixture 的 prompt 逐字比對，
# 確認這份 trace 真的是這個 fixture 產生的（BR-F30）。
cat > "$RAW/dispatch__case-1.meta.json" <<'JSON'
{"id": "dispatch__case-1", "exit_code": 0, "timed_out": false, "prompt": "模擬 prompt"}
JSON
GOOD_JUDGE='{"required": [{"element": "寫出派工單", "verdict": "PASS", "evidence": "回應含派工單"}],
 "forbidden": [], "overall": "PASS", "_cost_usd": 0.02}'
printf '%s\n' "$GOOD_JUDGE" > "$RAW/dispatch__case-1.judge.json"

# BR-F27 之後同名 phase 不可覆寫，因此每次重量都換一份乾淨的 manifest 檔。
snap() { python3 "$E/manifest.py" snapshot "$MAN" "$1" \
           "$CTX/rules.md" "$CTX/settings.json" "$CTX/desc.txt" "${2:-$CTX/judge-desc.txt}" \
           "$FXJ" "$SEED" >/dev/null; }
fresh_manifest() { rm -f "$MAN"; }
# BR-F35：subject meta 必須帶上本輪 manifest 產生的 run_nonce，trace manifest 再逐檔核對。
# 真實流程是 snapshot start → subject sessions 寫 meta → trace；這裡照同一個順序模擬。
stamp_nonce() {
  python3 "$TMP/stamp.py" "$MAN" "$RAW"
}
# BR-F24 之後 trace manifest 不可覆寫，因此重建一律先明確刪除。
mktrace() {
  N=$(stamp_nonce)
  rm -f "$TM"
  python3 "$E/manifest.py" trace "$TM" "$RAW" "$N" >/dev/null
}
mkpost() {
  rm -f "$PJ"
  python3 "$E/manifest.py" post-judge "$PJ" "$RAW" "$TM" "$FXJ" >/dev/null 2>&1
}
record() {
  rm -f "$RUN/sim.json"
  mkpost || true
  python3 "$E/record.py" "$RAW" sim "$MAN" "$FXJ" >/dev/null 2>&1 || true
  [ -f "$RUN/sim.json" ] || echo '{"run_status":"RECORD_FAILED","invalid_reason":"record.py 未產生紀錄","is_contract_evidence":false}' > "$RUN/sim.json"
}
status() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["run_status"])' "$RUN/sim.json"; }
reason() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["invalid_reason"] or "")' "$RUN/sim.json"; }
evidence() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["is_contract_evidence"])' "$RUN/sim.json"; }

# --- 可控的 claude stub：計數，且 --version 輸出可變 ---
STUB="$TMP/bin"
mkdir -p "$STUB"
cat > "$STUB/claude" <<'STUBSH'
#!/bin/sh
echo call >> "$CLAUDE_CALL_LOG"
if [ "$1" = "--version" ]; then
  # CLAUDE_VERSION_INCREMENT=1 時每次 --version 都回不同版本，
  # 用來證明 descriptor 是重新產生的而不是重用。
  if [ -n "${CLAUDE_VERSION_INCREMENT:-}" ]; then
    n=$(cat "$CLAUDE_VERSION_FILE.n" 2>/dev/null || echo 0)
    n=$((n + 1)); echo "$n" > "$CLAUDE_VERSION_FILE.n"
    echo "9.9.$n (Claude Code)"
  else
    cat "$CLAUDE_VERSION_FILE"
  fi
  exit 0
fi
# CLAUDE_RESULT_JSON 讓測試指定 judge 要回什麼判定（PASS／FAIL）；未設時回不合 schema
# 的輸出，走 parser fail-closed 的 ERROR 路徑。
if [ -n "${CLAUDE_RESULT_JSON:-}" ]; then
  RESULT_JSON="$CLAUDE_RESULT_JSON" python3 -c 'import json,os,sys; sys.stdout.write(json.dumps({"result": os.environ["RESULT_JSON"], "total_cost_usd": 0.01}))'
  echo
else
  echo '{"result":"{}","total_cost_usd":0.01}'
fi
STUBSH
chmod +x "$STUB/claude"
CALL_LOG="$TMP/claude-calls"
VER="$TMP/claude-version"
: > "$CALL_LOG"
echo "2.1.247 (Claude Code)" > "$VER"
calls() { wc -l < "$CALL_LOG" | tr -d ' '; }
run_judge() {
  : > "$CALL_LOG"
  set +e
  CLAUDE_CALL_LOG="$CALL_LOG" CLAUDE_VERSION_FILE="$VER" PATH="$STUB:$PATH" \
    python3 "$E/judge.py" "$RAW" "$FXJ" > "$TMP/judge.out" 2>&1
  JRC=$?
  set -e
}

echo "== 1. 開始／結束 hash 相同 → 產生證據 =="
fresh_manifest; snap start; mktrace; snap end; record
S=$(status); EV=$(evidence)
check "run_status = PASS" "$([ "$S" = PASS ] && echo 1 || echo 0)" "實得 $S"
check "is_contract_evidence = True" "$([ "$EV" = True ] && echo 1 || echo 0)" "實得 $EV"
check "run record 記下 hash_schema 與八個 domain（含 evaluation_context）" \
  "$(python3 -c 'import json,sys
d=json.load(open(sys.argv[1]))
print(1 if d["hash_schema"]=="v6" and len(d["hashes"])==8
      and "evaluation_context" in d["hashes"] else 0)' "$RUN/sim.json")"
check "evaluation_context 與 execution_context 是不同的值" \
  "$(python3 -c 'import json,sys
h=json.load(open(sys.argv[1]))["hashes"]
print(1 if h["evaluation_context"]!=h["execution_context"] else 0)' "$RUN/sim.json")"
check "run record 保存 trace manifest digest" \
  "$(python3 -c 'import json,sys
d=json.load(open(sys.argv[1]))["provenance"]
print(1 if d["trace_manifest_digest"] and d["trace_manifest"]["files"] else 0)' "$RUN/sim.json")"
check "原始 run record 標為 source" \
  "$(python3 -c 'import json,sys
print(1 if json.load(open(sys.argv[1]))["record_kind"]=="source" else 0)' "$RUN/sim.json")"
check "hash_method 寫六個 domain 且重算 mode 含 evaluation-context" \
  "$(python3 -c 'import json,sys,io
d=json.load(open(sys.argv[1]))
md=io.open(sys.argv[2],encoding="utf-8").read()
print(1 if "六個互斥 domain" in d["hash_method"]
      and "evaluation-context" in d["hash_method"]
      and "evaluation-context" in md else 0)' "$RUN/sim.json" "$RUN/sim.md")"
check "fixture 檔案清單是實際檔案而非引數名" \
  "$(python3 -c 'import json,sys
fs=json.load(open(sys.argv[1]))["fixture_files"]
print(1 if any(f.endswith("sim-fixtures.json") for f in fs) and len(fs)>1 else 0)' "$RUN/sim.json")"

echo
echo "== 2. run 中途修改輸入 → INVALID =="
mutate() {
  case "$1" in
    *.json) python3 -c 'import json,sys
p=sys.argv[1]; d=json.load(open(p))
if isinstance(d, dict) and d.get("fixtures"):
    d["fixtures"][0]["prompt"] += "（drift）"
else:
    d["_drift"] = True
json.dump(d, open(p,"w"), ensure_ascii=False, indent=2)' "$1" ;;
    *) printf '\n<!-- provenance selftest mutation -->\n' >> "$1" ;;
  esac
}

drift_case() {
  label="$1"; target="$2"; expect_key="$3"
  cp "$target" "$TMP/orig"
  fresh_manifest; snap start; mktrace
  mutate "$target"
  snap end
  record
  S=$(status); R=$(reason)
  cp "$TMP/orig" "$target"
  ok=0
  [ "$S" = INVALID ] && case "$R" in *"$expect_key"*) ok=1 ;; esac
  check "$label → INVALID 且指出 $expect_key" "$ok" "status=$S reason=$R"
}
drift_case "run 中途改 fixture"    "$FXJ"                                   "fixtures"
drift_case "run 中途改 skill"      "$WORK/skills/harness/dispatch/SKILL.md" "dispatch_skill"
drift_case "run 中途改 rules"      "$CTX/rules.md"                          "execution_context"
drift_case "run 中途改 judge 環境" "$CTX/judge-desc.txt"                    "evaluation_context"
drift_case "run 中途改 evaluator"  "$E/judge.py"                            "evaluator"
drift_case "run 中途改 runner"     "$E/run-suite.sh"                        "runner"

fresh_manifest; snap start; mktrace
echo "x" > "$SEED/provenance-selftest-extra.md"
snap end
record
S=$(status); R=$(reason)
rm -f "$SEED/provenance-selftest-extra.md"
ok=0
[ "$S" = INVALID ] && case "$R" in *fixtures*) ok=1 ;; esac
check "run 中途在 seed 新增檔案 → INVALID" "$ok" "status=$S reason=$R"

# 不完整的 manifest：start 等於 end、沒有任何 drift，卻幾乎沒有版本綁定。
fresh_manifest; snap start; mktrace; snap end
python3 -c 'import json,sys
p=sys.argv[1]; d=json.load(open(p))
for ph in ("start","end"):
    d[ph]["hashes"] = {"fixtures": d[ph]["hashes"]["fixtures"]}
json.dump(d, open(p,"w"))' "$MAN"
record
S=$(status); R=$(reason)
ok=0
[ "$S" = INVALID ] && case "$R" in *"缺少必要 domain"*) ok=1 ;; esac
check "manifest 只含 fixtures 一個 domain → INVALID" "$ok" "status=$S reason=$R"

fresh_manifest; snap start; mktrace; snap end
python3 -c 'import json,sys
p=sys.argv[1]; d=json.load(open(p)); del d["manifest_version"]
json.dump(d, open(p,"w"))' "$MAN"
record
S=$(status); R=$(reason)
ok=0
[ "$S" = INVALID ] && case "$R" in *manifest_version*) ok=1 ;; esac
check "manifest 缺 manifest_version → INVALID" "$ok" "status=$S reason=$R"

echo
echo "== 3. trace manifest 缺失／壞損／為空 → judge 中止且 CLI 呼叫次數 0 =="
fresh_manifest; snap start; mktrace; snap end

mv "$TM" "$TMP/tm.bak"
run_judge
check "缺 trace manifest：judge 中止（exit 2）" "$([ "$JRC" = 2 ] && echo 1 || echo 0)" "rc=$JRC"
check "缺 trace manifest：CLI 呼叫次數 = 0" "$([ "$(calls)" = 0 ] && echo 1 || echo 0)" "calls=$(calls)"

printf 'this is not json {{{\n' > "$TM"
run_judge
check "trace manifest 壞損：judge 中止（exit 2）" "$([ "$JRC" = 2 ] && echo 1 || echo 0)" "rc=$JRC"
check "trace manifest 壞損：CLI 呼叫次數 = 0" "$([ "$(calls)" = 0 ] && echo 1 || echo 0)" "calls=$(calls)"

printf '{"recorded_at":"x","algorithm":"sha256","files":{}}\n' > "$TM"
run_judge
check "trace manifest 為空：judge 中止（exit 2）" "$([ "$JRC" = 2 ] && echo 1 || echo 0)" "rc=$JRC"
check "trace manifest 為空：CLI 呼叫次數 = 0" "$([ "$(calls)" = 0 ] && echo 1 || echo 0)" "calls=$(calls)"

cp "$TMP/tm.bak" "$TM"

printf '{"type":"assistant","message":{"content":[]}}\n' >> "$RAW/dispatch__case-1.jsonl"
run_judge
check "trace hash 不符：CLI 呼叫次數 = 0" "$([ "$(calls)" = 0 ] && echo 1 || echo 0)" "calls=$(calls)"
check "該筆記為 trace_hash_mismatch" \
  "$(python3 -c 'import json,sys
d=json.load(open(sys.argv[1]))
print(1 if d.get("anomaly",{}).get("kind")=="trace_hash_mismatch" else 0)' \
     "$RAW/dispatch__case-1.judge.json")"
record
S=$(status); R=$(reason)
ok=0
[ "$S" = INVALID ] && case "$R" in *"trace hash 不符"*) ok=1 ;; esac
check "record 對被改過的 trace 判 INVALID" "$ok" "status=$S reason=$R"

trim_last_line() { python3 -c 'import sys
p=sys.argv[1]
lines=open(p).read().splitlines(True)
open(p,"w").write("".join(lines[:-1]))' "$1"; }
trim_last_line "$RAW/dispatch__case-1.jsonl"
printf '%s\n' "$GOOD_JUDGE" > "$RAW/dispatch__case-1.judge.json"

echo
echo "== 4. trace manifest 不可覆寫；digest 不符禁止重評；derived 不覆寫 source =="
fresh_manifest; snap start; mktrace; snap end; record
cp "$RUN/sim.json" "$RUN/source.json"
SRC_BEFORE=$(shasum -a 256 "$RUN/source.json" | cut -d' ' -f1)
# 重評用的是 contract manifest：subject 那半由來源紀錄提供，不在此刻重量。
mkcontract() {
  rm -f "$CMAN"
  python3 "$E/manifest.py" contract-snapshot "$CMAN" start "$CTX/judge-desc.txt" "$FXJ" >/dev/null
  python3 "$E/manifest.py" contract-snapshot "$CMAN" end "$CTX/judge-desc.txt" "$FXJ" >/dev/null
}
mkcontract

TM_BEFORE=$(shasum -a 256 "$TM" | cut -d' ' -f1)
printf '{"type":"assistant","message":{"content":[]}}\n' >> "$RAW/dispatch__case-1.jsonl"
set +e
python3 "$E/manifest.py" trace "$TM" "$RAW" > "$TMP/mk.out" 2>&1
MKRC=$?
set -e
TM_AFTER=$(shasum -a 256 "$TM" | cut -d' ' -f1)
check "改 trace 後重建同一路徑 manifest → 被拒絕（exit 非 0）" \
  "$([ "$MKRC" -ne 0 ] && echo 1 || echo 0)" "rc=$MKRC"
check "被拒絕時原 trace manifest 未被改動" \
  "$([ "$TM_BEFORE" = "$TM_AFTER" ] && echo 1 || echo 0)"

mktrace
run_judge_src() {
  : > "$CALL_LOG"
  set +e
  CLAUDE_CALL_LOG="$CALL_LOG" CLAUDE_VERSION_FILE="$VER" PATH="$STUB:$PATH" \
    HARNESS_SOURCE_RECORD="$RUN/source.json" \
    python3 "$E/judge.py" "$RAW" "$FXJ" > "$TMP/judge.out" 2>&1
  JRC=$?
  set -e
}
run_judge_src
check "digest 不符：judge 中止（exit 2）" "$([ "$JRC" = 2 ] && echo 1 || echo 0)" "rc=$JRC"
check "digest 不符：CLI 呼叫次數 = 0" "$([ "$(calls)" = 0 ] && echo 1 || echo 0)" "calls=$(calls)"
set +e
python3 "$E/record.py" --source "$RUN/source.json" "$RAW" rescore-bad "$CMAN" "$FXJ" \
  > /dev/null 2>&1
set -e
check "digest 不符：record 判 INVALID 且指出 digest" \
  "$(python3 -c 'import json,sys
d=json.load(open(sys.argv[1]))
print(1 if d["run_status"]=="INVALID"
      and "digest 與原始紀錄不符" in (d["invalid_reason"] or "") else 0)' \
     "$RUN/rescore-bad.json")"

trim_last_line "$RAW/dispatch__case-1.jsonl"
printf '%s\n' "$GOOD_JUDGE" > "$RAW/dispatch__case-1.judge.json"
mktrace
set +e
python3 "$E/record.py" --source "$RUN/source.json" "$RAW" rescore-ok "$CMAN" "$FXJ" \
  > /dev/null 2>&1
RRC=$?
set -e
check "合法原始 trace → 可以重評（exit 0）" "$([ "$RRC" = 0 ] && echo 1 || echo 0)" "rc=$RRC"
check "derived record 記下來源 run ID、原始 digest 與本次 evaluator／evaluation_context" \
  "$(python3 -c 'import json,sys
d=json.load(open(sys.argv[1]))
df=d["derived_from"]
print(1 if d["record_kind"]=="derived" and df["source_run_id"]=="sim"
      and df["source_trace_manifest_digest"]
      and df["rescored_with"]["evaluator"]
      and df["rescored_with"]["evaluation_context"] else 0)' "$RUN/rescore-ok.json")"
check "derived record 的 subject 那半標為 source_run、contract 那半標為 measured_now" \
  "$(python3 -c 'import json,sys
hp=json.load(open(sys.argv[1]))["hash_provenance"]
subj={k for k,v in hp.items() if v=="source_run"}
cont={k for k,v in hp.items() if v=="measured_now"}
print(1 if cont=={"evaluator","evaluation_context","contract_fixtures","rescore_runner"}
      and len(subj)==6 else 0)' "$RUN/rescore-ok.json")"
check "derived record 含 contract_fixtures（judge 實際載入的 assertion 來源）" \
  "$(python3 -c 'import json,sys
d=json.load(open(sys.argv[1]))
print(1 if d["hashes"].get("contract_fixtures") and len(d["hashes"])==10 else 0)' \
     "$RUN/rescore-ok.json")"
check "傳 full manifest 進重評 → 被拒" \
  "$(sh -c 'python3 "$1" --source "$2" "$3" rescore-full "$4" "$5" >/dev/null 2>&1
python3 -c "import json,sys
d=json.load(open(sys.argv[1]))
print(1 if d[\"run_status\"]==\"INVALID\" and \"contract manifest\" in (d[\"invalid_reason\"] or \"\") else 0)" "$6"' \
   _ "$E/record.py" "$RUN/source.json" "$RAW" "$MAN" "$FXJ" "$RUN/rescore-full.json")"

SRC_AFTER=$(shasum -a 256 "$RUN/source.json" | cut -d' ' -f1)
check "derived record 不覆寫 source record" \
  "$([ "$SRC_BEFORE" = "$SRC_AFTER" ] && echo 1 || echo 0)"
set +e
python3 "$E/record.py" --source "$RUN/source.json" "$RAW" source "$CMAN" "$FXJ" \
  > /dev/null 2>&1
SAMERC=$?
set -e
SRC_AFTER2=$(shasum -a 256 "$RUN/source.json" | cut -d' ' -f1)
check "輸出路徑等於 source → 拒絕（exit 非 0）且原檔未變" \
  "$([ "$SAMERC" -ne 0 ] && [ "$SRC_BEFORE" = "$SRC_AFTER2" ] && echo 1 || echo 0)" \
  "rc=$SAMERC"

echo
echo "== 5. 逐條項目內的 corrected_verdict 被拒 =="
cat > "$TMP/nested.py" <<'PYEOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("judge", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

CASES = [
    ("required 項目內 corrected_verdict",
     '{"required": [{"element": "a", "verdict": "PASS", "evidence": "e",'
     ' "corrected_verdict": "FAIL"}], "forbidden": [], "overall": "PASS"}',
     ["a"], []),
    ("forbidden 項目內 note",
     '{"required": [], "forbidden": [{"element": "b", "verdict": "PASS",'
     ' "evidence": "e", "note": "不確定"}], "overall": "PASS"}',
     [], ["b"]),
]
bad = []
for label, txt, req, frb in CASES:
    v, an = m.parse_verdict(txt, req, frb)
    if not (v is None and an and an.get("kind") == "schema_violation"):
        bad.append((label, v, an))
v, an = m.parse_verdict(
    '{"required": [{"element": "a", "verdict": "PASS", "evidence": "e"}],'
    ' "forbidden": [], "overall": "PASS"}', ["a"], [])
if v is None or an is not None:
    bad.append(("合法輸出被誤擋", v, an))
print(0 if bad else 1)
if bad:
    print(bad, file=sys.stderr)
PYEOF
check "nested corrected_verdict／note 被拒，合法輸出不受影響" \
  "$(python3 "$TMP/nested.py" "$E/judge.py")"

echo
echo "== 6. BR-F26：end 必須重新產生 descriptor =="
# judge CLI 在 run 期間升版。重用 start 的 descriptor 會算出同一個 hash（漏檢）；
# 重新產生才會不同。兩邊都測，證明這個案例真的有鑑別力。
echo "2.1.247 (Claude Code)" > "$VER"
CLAUDE_CALL_LOG="$CALL_LOG" CLAUDE_VERSION_FILE="$VER" PATH="$STUB:$PATH" \
  python3 "$E/judge.py" --print-context > "$CTX/jd.start"
echo "9.9.9 (Claude Code)" > "$VER"
CLAUDE_CALL_LOG="$CALL_LOG" CLAUDE_VERSION_FILE="$VER" PATH="$STUB:$PATH" \
  python3 "$E/judge.py" --print-context > "$CTX/jd.end"
H_START=$(sh "$H" evaluation-context "$CTX/jd.start")
H_REUSE=$(sh "$H" evaluation-context "$CTX/jd.start")
H_REGEN=$(sh "$H" evaluation-context "$CTX/jd.end")
check "重用 descriptor 會看不到 CLI 升版（負向對照）" \
  "$([ "$H_START" = "$H_REUSE" ] && echo 1 || echo 0)"
check "重新產生 descriptor 才會反映 CLI 升版" \
  "$([ "$H_START" != "$H_REGEN" ] && echo 1 || echo 0)"
fresh_manifest
snap start "$CTX/jd.start"
snap end "$CTX/jd.end"
record
S=$(status); R=$(reason)
ok=0
[ "$S" = INVALID ] && case "$R" in *evaluation_context*) ok=1 ;; esac
check "start／end 用各自重新產生的 descriptor → 抓到 evaluation_context drift" "$ok" \
  "status=$S reason=$R"
# 結構檢查：run-suite.sh 必須在 end 快照前重新產生兩份 descriptor，且 end 用的是新檔。
check "run-suite.sh 產生 execution descriptor 兩次" \
  "$([ "$(grep -c -- '--print-context > "\$DESC' "$E/run-suite.sh")" -ge 2 ] && echo 1 || echo 0)"
check "run-suite.sh 產生 judge descriptor 兩次" \
  "$([ "$(grep -c -- 'judge.py\" --print-context' "$E/run-suite.sh")" -ge 2 ] && echo 1 || echo 0)"
check "run-suite.sh 的 end 快照用 DESC_END／JDESC_END" \
  "$(grep -A3 'snapshot "\$MANIFEST" end' "$E/run-suite.sh" \
     | grep -q 'DESC_END" "\$JDESC_END"' && echo 1 || echo 0)"

echo
echo "== 7. BR-F27：同名 phase 不可覆寫 =="
fresh_manifest
snap start "$CTX/jd.start"
S1=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["start"]["hashes"]["evaluation_context"])' "$MAN")
set +e
python3 "$E/manifest.py" snapshot "$MAN" start \
  "$CTX/rules.md" "$CTX/settings.json" "$CTX/desc.txt" "$CTX/jd.end" \
  "$FXJ" "$SEED" > "$TMP/dup.out" 2>&1
DUPRC=$?
set -e
S2=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["start"]["hashes"]["evaluation_context"])' "$MAN")
check "第二次寫 start → 被拒絕（exit 非 0）" "$([ "$DUPRC" -ne 0 ] && echo 1 || echo 0)" "rc=$DUPRC"
check "原始 start 快照未被改寫" "$([ "$S1" = "$S2" ] && echo 1 || echo 0)"
snap end "$CTX/jd.end"
set +e
python3 "$E/manifest.py" snapshot "$MAN" end \
  "$CTX/rules.md" "$CTX/settings.json" "$CTX/desc.txt" "$CTX/jd.start" \
  "$FXJ" "$SEED" > /dev/null 2>&1
DUPEND=$?
set -e
check "第二次寫 end → 被拒絕（exit 非 0）" "$([ "$DUPEND" -ne 0 ] && echo 1 || echo 0)" "rc=$DUPEND"
record
S=$(status)
ok=0
[ "$S" = INVALID ] && ok=1
check "覆寫被擋下後，原本的 drift 仍然看得到（判 INVALID）" "$ok" "status=$S"

echo
echo "== 8. BR-F28：v3 來源 trace → 有效的 v4 derived record =="
V3RUN="$E/runs/v3src"
mkdir -p "$V3RUN/raw"
cp "$RAW/dispatch__case-1.jsonl" "$V3RUN/raw/"
cp "$RAW/dispatch__case-1.meta.json" "$V3RUN/raw/"
printf '%s\n' "$GOOD_JUDGE" > "$V3RUN/raw/dispatch__case-1.judge.json"
python3 "$E/manifest.py" trace "$V3RUN/trace-manifest.json" "$V3RUN/raw" >/dev/null
python3 "$E/manifest.py" post-judge "$V3RUN/post-judge-manifest.json" "$V3RUN/raw" \
  "$V3RUN/trace-manifest.json" "$FXJ" >/dev/null
python3 - "$V3RUN/v3src.json" "$V3RUN/trace-manifest.json" <<'PY'
import hashlib, json, sys
files = json.load(open(sys.argv[2]))["files"]
dg = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False).encode()).hexdigest()
subject = ("dispatch_skill", "judgment_skill", "token_preflight_skill",
           "runner", "fixtures", "execution_context")
json.dump({"run_id": "v3src", "hash_schema": "v3", "record_kind": "source",
           "hashes": dict((k, "a" * 64) for k in subject),
           "provenance": {"trace_manifest_digest": dg,
                          "trace_manifest_origin": "contemporaneous"}},
          open(sys.argv[1], "w"), ensure_ascii=False, indent=2)
PY
V3CMAN="$V3RUN/contract-manifest.json"
python3 "$E/manifest.py" contract-snapshot "$V3CMAN" start "$CTX/judge-desc.txt" "$FXJ" >/dev/null
python3 "$E/manifest.py" contract-snapshot "$V3CMAN" end "$CTX/judge-desc.txt" "$FXJ" >/dev/null

# 8a：沒有 migration audit → 跨 schema 不得沿用 subject 綁定
set +e
python3 "$E/record.py" --source "$V3RUN/v3src.json" "$V3RUN/raw" no-audit "$V3CMAN" "$FXJ" \
  >/dev/null 2>&1
set -e
check "v3 來源、無 migration audit → INVALID 且指出要附 audit" \
  "$(python3 -c 'import json,sys
d=json.load(open(sys.argv[1]))
print(1 if d["run_status"]=="INVALID"
      and "migration-audit" in (d["invalid_reason"] or "") else 0)' "$V3RUN/no-audit.json")"

# 8b：audit 涵蓋不全 → 仍然擋下
cat > "$TMP/audit-bad.json" <<'JSON'
{"source_hash_schema":"v3","target_hash_schema":"v6",
 "method":"逐 domain 比對 allowlist 差異與檔案內容",
 "reviewed_at":"2026-09-02",
 "domains":{"dispatch_skill":{"equivalent":true,"evidence":"diff 為空","method":"逐檔 diff"}}}
JSON
set +e
python3 "$E/record.py" --source "$V3RUN/v3src.json" --migration-audit "$TMP/audit-bad.json" \
  "$V3RUN/raw" audit-bad "$V3CMAN" "$FXJ" >/dev/null 2>&1
set -e
check "audit 未涵蓋全部 subject domain → INVALID" \
  "$(python3 -c 'import json,sys
d=json.load(open(sys.argv[1]))
print(1 if d["run_status"]=="INVALID"
      and "未涵蓋" in (d["invalid_reason"] or "") else 0)' "$V3RUN/audit-bad.json")"

# 8c：完整 audit → 產生有效的 derived record
python3 - "$TMP/audit.json" <<'PY'
import json, sys
subject = ("dispatch_skill", "judgment_skill", "token_preflight_skill",
           "runner", "fixtures", "execution_context")
item = {"equivalent": True,
        "evidence": "v3 與 v5 的 allowlist 差異未 match 到本 run 的任何檔案，逐檔 diff 為空",
        "method": "逐檔 diff + allowlist 差集比對"}
json.dump({"source_hash_schema": "v3", "target_hash_schema": "v6",
           "method": "逐 domain 比對 v3/v6 allowlist 差異與實際檔案內容",
           "reviewed_at": "2026-09-02",
           "domains": dict((k, dict(item)) for k in subject)},
          open(sys.argv[1], "w"), ensure_ascii=False, indent=2)
PY
set +e
python3 "$E/record.py" --source "$V3RUN/v3src.json" --migration-audit "$TMP/audit.json" \
  "$V3RUN/raw" v4-derived "$V3CMAN" "$FXJ" >/dev/null 2>&1
DRC=$?
set -e
check "v3 來源 + 完整 audit → 產生有效 derived record（exit 0）" \
  "$([ "$DRC" = 0 ] && echo 1 || echo 0)" "rc=$DRC"
check "derived record 為 PASS 且構成契約證據" \
  "$(python3 -c 'import json,sys
d=json.load(open(sys.argv[1]))
print(1 if d["run_status"]=="PASS" and d["is_contract_evidence"] is True else 0)' \
     "$V3RUN/v4-derived.json")"
check "subject identity 取自 v3 來源、contract identity 為現量" \
  "$(python3 -c 'import json,sys
d=json.load(open(sys.argv[1]))
h=d["hashes"]; hp=d["hash_provenance"]
print(1 if h["dispatch_skill"]=="a"*64 and hp["dispatch_skill"]=="source_run"
      and hp["evaluator"]=="measured_now" and h["evaluator"]!="a"*64 else 0)' \
     "$V3RUN/v4-derived.json")"
check "derived record 標記 cross_schema 並保存 audit digest" \
  "$(python3 -c 'import json,sys
df=json.load(open(sys.argv[1]))["derived_from"]
print(1 if df["cross_schema"] is True and df["migration_audit"]["digest"]
      and df["source_hash_schema"]=="v3" else 0)' "$V3RUN/v4-derived.json")"

echo
echo "== 9. BR-F29：migration audit 與來源 hash 不得產生假 PASS =="
V3BAD="$E/runs/v3bad"
mkdir -p "$V3BAD/raw"
cp "$V3RUN/raw/dispatch__case-1.jsonl" "$V3BAD/raw/"
cp "$V3RUN/raw/dispatch__case-1.meta.json" "$V3BAD/raw/"
printf '%s\n' "$GOOD_JUDGE" > "$V3BAD/raw/dispatch__case-1.judge.json"
python3 "$E/manifest.py" trace "$V3BAD/trace-manifest.json" "$V3BAD/raw" >/dev/null
python3 "$E/manifest.py" post-judge "$V3BAD/post-judge-manifest.json" "$V3BAD/raw" \
  "$V3BAD/trace-manifest.json" "$FXJ" >/dev/null
python3 - "$V3BAD/src.json" "$V3BAD/trace-manifest.json" <<'PY'
import hashlib, json, sys
files = json.load(open(sys.argv[2]))["files"]
dg = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False).encode()).hexdigest()
subject = ("dispatch_skill", "judgment_skill", "token_preflight_skill",
           "runner", "fixtures", "execution_context")
# 六個 subject hash 全為 null——先前這樣仍會得到 PASS / is_contract_evidence=true
json.dump({"run_id": "v3bad", "hash_schema": "v3", "record_kind": "source",
           "hashes": dict((k, None) for k in subject),
           "provenance": {"trace_manifest_digest": dg,
                          "trace_manifest_origin": "contemporaneous"}},
          open(sys.argv[1], "w"), ensure_ascii=False, indent=2)
PY
BADCMAN="$V3BAD/contract.json"
python3 "$E/manifest.py" contract-snapshot "$BADCMAN" start "$CTX/judge-desc.txt" "$FXJ" >/dev/null
python3 "$E/manifest.py" contract-snapshot "$BADCMAN" end "$CTX/judge-desc.txt" "$FXJ" >/dev/null
cat > "$TMP/audit-null.json" <<'JSON'
{"source_hash_schema":"v3","target_hash_schema":"v6","method":"x","reviewed_at":"y",
 "domains":{"dispatch_skill":null,"judgment_skill":null,"token_preflight_skill":null,
            "runner":null,"fixtures":null,"execution_context":null}}
JSON
set +e
HARNESS_TRACE_MANIFEST_ORIGIN=contemporaneous python3 "$E/record.py" \
  --source "$V3BAD/src.json" --migration-audit "$TMP/audit-null.json" \
  "$V3BAD/raw" nullish "$BADCMAN" "$FXJ" >/dev/null 2>&1
set -e
check "六個 subject hash + 六個 audit 結論全為 null → INVALID（先前為 PASS）" \
  "$(python3 -c 'import json,sys
d=json.load(open(sys.argv[1]))
r=d["invalid_reason"] or ""
print(1 if d["run_status"]=="INVALID" and d["is_contract_evidence"] is False
      and "64 位 hex" in r else 0)' "$V3BAD/nullish.json")"

cat > "$TMP/audit-false.json" <<'JSON'
{"source_hash_schema":"v3","target_hash_schema":"v6","method":"逐檔 diff","reviewed_at":"y",
 "domains":{"dispatch_skill":{"equivalent":false,"evidence":"內容確實變了","method":"diff"},
            "judgment_skill":{"equivalent":true,"evidence":"diff 為空","method":"diff"},
            "token_preflight_skill":{"equivalent":true,"evidence":"diff 為空","method":"diff"},
            "runner":{"equivalent":true,"evidence":"diff 為空","method":"diff"},
            "fixtures":{"equivalent":true,"evidence":"diff 為空","method":"diff"},
            "execution_context":{"equivalent":true,"evidence":"diff 為空","method":"diff"}}}
JSON
set +e
HARNESS_TRACE_MANIFEST_ORIGIN=contemporaneous python3 "$E/record.py" \
  --source "$V3RUN/v3src.json" --migration-audit "$TMP/audit-false.json" \
  "$V3RUN/raw" audit-false "$V3CMAN" "$FXJ" >/dev/null 2>&1
set -e
check "audit 有一項 equivalent=false → INVALID" \
  "$(python3 -c 'import json,sys
d=json.load(open(sys.argv[1]))
print(1 if d["run_status"]=="INVALID"
      and "equivalent=False" in (d["invalid_reason"] or "") else 0)' \
     "$V3RUN/audit-false.json")"

echo
echo "== 10. BR-F30：重評使用的 fixtures 必須綁定 =="
cp "$FXJ" "$TMP/fx.orig"
python3 -c 'import json,sys
p=sys.argv[1]; d=json.load(open(p))
d["fixtures"][0]["prompt"] = "完全不同的新 prompt"
json.dump(d, open(p,"w"), ensure_ascii=False)' "$FXJ"
run_judge_src
check "改 prompt 後重評：judge 中止（exit 2）" "$([ "$JRC" = 2 ] && echo 1 || echo 0)" "rc=$JRC"
check "改 prompt 後重評：CLI 呼叫次數 = 0" "$([ "$(calls)" = 0 ] && echo 1 || echo 0)" "calls=$(calls)"
check "訊息指出 trace 不是這個 fixture 的產物" \
  "$(grep -q "不是這個 fixture 的產物" "$TMP/judge.out" && echo 1 || echo 0)"
cp "$TMP/fx.orig" "$FXJ"

BEFORE_CF=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["start"]["hashes"]["contract_fixtures"])' "$CMAN")
python3 -c 'import json,sys
p=sys.argv[1]; d=json.load(open(p))
d["fixtures"][0]["required_elements"] = ["完全不同的新條件"]
json.dump(d, open(p,"w"), ensure_ascii=False)' "$FXJ"
run_judge_src
check "只改 assertion：judge 繼續執行（有呼叫 CLI）" \
  "$([ "$(calls)" -ge 1 ] && echo 1 || echo 0)" "calls=$(calls)"
mkcontract
AFTER_CF=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["start"]["hashes"]["contract_fixtures"])' "$CMAN")
check "改 assertion 後 contract_fixtures 跟著變（不再宣稱來源 fixtures）" \
  "$([ "$BEFORE_CF" != "$AFTER_CF" ] && echo 1 || echo 0)"
cp "$TMP/fx.orig" "$FXJ"
printf '%s\n' "$GOOD_JUDGE" > "$RAW/dispatch__case-1.judge.json"
mkcontract

echo
echo "== 11. BR-F31／F32：run-rescore.sh 與證據等級 =="
fresh_manifest; snap start; mktrace; snap end; record
cp "$RUN/sim.json" "$RUN/sim-source.json"
RS="$E/runs/rescore-src"
rm -rf "$RS"; mkdir -p "$RS/raw"
cp "$RAW/dispatch__case-1.jsonl" "$RAW/dispatch__case-1.meta.json" "$RS/raw/"
printf '%s\n' "$GOOD_JUDGE" > "$RS/raw/dispatch__case-1.judge.json"
cp "$RUN/trace-manifest.json" "$RS/"
python3 -c 'import json,sys
d=json.load(open(sys.argv[1])); d["run_id"]="rescore-src"
json.dump(d, open(sys.argv[2],"w"), ensure_ascii=False)' "$RUN/sim-source.json" "$RS/rescore-src.json"

: > "$CALL_LOG"; echo "2.1.247 (Claude Code)" > "$VER"
set +e
CLAUDE_CALL_LOG="$CALL_LOG" CLAUDE_VERSION_FILE="$VER" PATH="$STUB:$PATH" \
  sh "$WORK/scripts/run-rescore.sh" "$RS" derived-1 "$FXJ" > "$TMP/rescore1.out" 2>&1
RS1=$?
set -e
check "run-rescore.sh 在版本穩定時完成（產生 derived record）" \
  "$([ -f "$RS/derived/derived-1/derived-1.json" ] && echo 1 || echo 0)" "rc=$RS1 $(tail -2 "$TMP/rescore1.out" | tr '\n' ' ')"
check "derived record 為 derived 且含十個 domain" \
  "$(python3 -c 'import json,os,sys
p=sys.argv[1]
if not os.path.exists(p): print(0); raise SystemExit
d=json.load(open(p))
print(1 if d["record_kind"]=="derived" and len(d["hashes"])==10 else 0)' "$RS/derived/derived-1/derived-1.json")"

: > "$CALL_LOG"; rm -f "$VER.n"
set +e
CLAUDE_CALL_LOG="$CALL_LOG" CLAUDE_VERSION_FILE="$VER" CLAUDE_VERSION_INCREMENT=1 \
  PATH="$STUB:$PATH" \
  sh "$WORK/scripts/run-rescore.sh" "$RS" derived-2 "$FXJ" > "$TMP/rescore2.out" 2>&1
set -e
check "重評期間 judge CLI 升版 → derived record 判 INVALID（證明 descriptor 有重新產生）" \
  "$(python3 -c 'import json,os,sys
p=sys.argv[1]
if not os.path.exists(p): print(0); raise SystemExit
d=json.load(open(p))
print(1 if d["run_status"]=="INVALID"
      and "evaluation_context" in (d["invalid_reason"] or "") else 0)' "$RS/derived/derived-2/derived-2.json")"
check "run-rescore.sh 內 judge --print-context 出現兩次" \
  "$([ "$(grep -c -- '--print-context' "$WORK/scripts/run-rescore.sh")" -ge 2 ] && echo 1 || echo 0)"

python3 -c 'import json,sys
p=sys.argv[1]; d=json.load(open(p))
d["provenance"]["trace_manifest_origin"]="reconstructed"
json.dump(d, open(p,"w"), ensure_ascii=False)' "$RS/rescore-src.json"
: > "$CALL_LOG"; echo "2.1.247 (Claude Code)" > "$VER"
set +e
CLAUDE_CALL_LOG="$CALL_LOG" CLAUDE_VERSION_FILE="$VER" PATH="$STUB:$PATH" \
  sh "$WORK/scripts/run-rescore.sh" "$RS" derived-3 "$FXJ" > "$TMP/rescore3.out" 2>&1
set -e
check "來源 trace manifest 為事後補建 → derived record 標 legacy_diagnostic 且不算契約證據" \
  "$(python3 -c 'import json,os,sys
p=sys.argv[1]
if not os.path.exists(p): print(0); raise SystemExit
d=json.load(open(p))
print(1 if d["evidence_class"]=="legacy_diagnostic"
      and d["is_contract_evidence"] is False else 0)' "$RS/derived/derived-3/derived-3.json")"

echo
echo "== 12. BR-F33／F34：重評不得寫入來源，且驗證排在花錢之前 =="
RS2="$E/runs/rescore-src2"
rm -rf "$RS2"; mkdir -p "$RS2/raw"
cp "$RAW/dispatch__case-1.jsonl" "$RAW/dispatch__case-1.meta.json" "$RS2/raw/"
# 來源的逐筆判定證據帶一個可辨識的標記：被覆蓋的話一眼看得出來。
printf '{"required":[],"forbidden":[],"overall":"PASS","_cost_usd":0.01,"note":"SOURCE-JUDGE-MARKER"}\n' \
  > "$RS2/raw/dispatch__case-1.judge.json"
cp "$RUN/trace-manifest.json" "$RS2/"
python3 -c 'import json,sys
d=json.load(open(sys.argv[1])); d["run_id"]="rescore-src2"
json.dump(d, open(sys.argv[2],"w"), ensure_ascii=False)' "$RUN/sim-source.json" "$RS2/rescore-src2.json"

src_fp() {
  find "$RS2/raw" -type f | LC_ALL=C sort | while IFS= read -r f; do
    printf '%s  %s\n' "$f" "$(shasum -a 256 "$f" | cut -d' ' -f1)"
  done | shasum -a 256 | cut -d' ' -f1
}
FP_BEFORE=$(src_fp)

: > "$CALL_LOG"; echo "2.1.247 (Claude Code)" > "$VER"
set +e
CLAUDE_CALL_LOG="$CALL_LOG" CLAUDE_VERSION_FILE="$VER" PATH="$STUB:$PATH" \
  sh "$WORK/scripts/run-rescore.sh" "$RS2" d33 "$FXJ" > "$TMP/r33.out" 2>&1
set -e
FP_AFTER=$(src_fp)
check "重評後來源 raw 目錄逐 byte 未變" \
  "$([ "$FP_BEFORE" = "$FP_AFTER" ] && echo 1 || echo 0)"
check "來源的逐筆判定證據仍在（未被 judge 覆寫）" \
  "$(grep -q 'SOURCE-JUDGE-MARKER' "$RS2/raw/dispatch__case-1.judge.json" && echo 1 || echo 0)"
check "新判定寫進 derived 目錄" \
  "$([ -f "$RS2/derived/d33/raw/dispatch__case-1.judge.json" ] && echo 1 || echo 0)"
check "derived 目錄的判定不是來源那一份" \
  "$(grep -q 'SOURCE-JUDGE-MARKER' "$RS2/derived/d33/raw/dispatch__case-1.judge.json" \
     && echo 0 || echo 1)"

# F34：provenance 不成立時，一次 judge session 都不能起
rm -rf "$RS2/derived"
python3 -c 'import json,sys
p=sys.argv[1]; d=json.load(open(p))
d["hashes"]["runner"] = None      # 來源 subject hash 壞損：零成本就判得出來
json.dump(d, open(p,"w"), ensure_ascii=False)' "$RS2/rescore-src2.json"
: > "$CALL_LOG"
set +e
CLAUDE_CALL_LOG="$CALL_LOG" CLAUDE_VERSION_FILE="$VER" PATH="$STUB:$PATH" \
  sh "$WORK/scripts/run-rescore.sh" "$RS2" d34 "$FXJ" > "$TMP/r34.out" 2>&1
R34=$?
set -e
# --print-context 會呼叫 stub 的 --version，那不是 judge session；扣掉它才是實際判定次數。
JUDGE_CALLS=$(grep -c call "$CALL_LOG" 2>/dev/null || echo 0)
check "來源 hash 壞損 → run-rescore 在 preflight 中止（exit 非 0）" \
  "$([ "$R34" -ne 0 ] && echo 1 || echo 0)" "rc=$R34"
check "來源 hash 壞損 → 未產生 derived record" \
  "$([ ! -f "$RS2/derived/d34/d34.json" ] && echo 1 || echo 0)"
check "preflight 訊息指出是 subject hash 問題" \
  "$(grep -q '64 位 hex' "$TMP/r34.out" && echo 1 || echo 0)"
check "judge 判定次數 = 0（只有 --print-context 的版本查詢）" \
  "$([ "$JUDGE_CALLS" -le 1 ] && echo 1 || echo 0)" "calls=$JUDGE_CALLS"

echo
echo "== 13. BR-F36／F37：run id 的路徑範圍與 exit code =="
RS3="$E/runs/rescore-src3"
rm -rf "$RS3"; mkdir -p "$RS3/raw"
cp "$RAW/dispatch__case-1.jsonl" "$RAW/dispatch__case-1.meta.json" "$RS3/raw/"
printf '%s\n' "$GOOD_JUDGE" > "$RS3/raw/dispatch__case-1.judge.json"
cp "$RUN/trace-manifest.json" "$RS3/"
python3 -c 'import json,sys
d=json.load(open(sys.argv[1])); d["run_id"]="rescore-src3"
json.dump(d, open(sys.argv[2],"w"), ensure_ascii=False)' "$RUN/sim-source.json" "$RS3/rescore-src3.json"

rescore() {   # rescore <run-id> [額外環境變數以 KEY=VAL 形式]
  rid="$1"; shift
  : > "$CALL_LOG"; echo "2.1.247 (Claude Code)" > "$VER"
  set +e
  env "$@" CLAUDE_CALL_LOG="$CALL_LOG" CLAUDE_VERSION_FILE="$VER" PATH="$STUB:$PATH" \
    sh "$WORK/scripts/run-rescore.sh" "$RS3" "$rid" "$FXJ" > "$TMP/rs.out" 2>&1
  RSRC=$?
  set -e
}

# --- F36：路徑逸出 ---
ESCAPE_TARGET="$E/runs/victim"
rm -rf "$ESCAPE_TARGET"
rescore "../../victim"
check "run id 含 ../ → 被拒（exit 2）" "$([ "$RSRC" = 2 ] && echo 1 || echo 0)" "rc=$RSRC"
check "run id 含 ../ → 不在 derived/ 之外建立任何東西" \
  "$([ ! -e "$ESCAPE_TARGET" ] && echo 1 || echo 0)"
check "拒絕訊息指出 run id 不合法" \
  "$(grep -q 'run id 不合法' "$TMP/rs.out" && echo 1 || echo 0)"

for bad in "a/b" ".hidden" "x;rm" "with space"; do
  rescore "$bad"
  check "run id '$bad' → 被拒（exit 2）" "$([ "$RSRC" = 2 ] && echo 1 || echo 0)" "rc=$RSRC"
done

# 控制字元：舊版用 `$(... | tr -d ...)` 判定，命令替換會剝掉尾端換行，
# 於是 `safe<LF>line` 過完 tr 只剩一個換行、被剝成空字串而放行。改用 shell pattern 後才擋得住。
NL='
'
CR=$(printf '\r')
TAB=$(printf '\t')
ESC=$(printf '\033')
rescore "$(printf 'safe\nline')"
check "run id 含 LF → 被拒（exit 2）" "$([ "$RSRC" = 2 ] && echo 1 || echo 0)" "rc=$RSRC"
rescore "$NL"
check "run id 為純 LF → 被拒（exit 2）" "$([ "$RSRC" = 2 ] && echo 1 || echo 0)" "rc=$RSRC"
rescore "a${CR}b"
check "run id 含 CR → 被拒（exit 2）" "$([ "$RSRC" = 2 ] && echo 1 || echo 0)" "rc=$RSRC"
rescore "a${TAB}b"
check "run id 含 TAB → 被拒（exit 2）" "$([ "$RSRC" = 2 ] && echo 1 || echo 0)" "rc=$RSRC"
rescore "${ESC}[31mred"
check "run id 含 ANSI escape → 被拒（exit 2）" "$([ "$RSRC" = 2 ] && echo 1 || echo 0)" "rc=$RSRC"
check "拒絕訊息不回顯原始控制字元" \
  "$(grep -q "$ESC" "$TMP/rs.out" && echo 0 || echo 1)"
check "含控制字元的 run id 不留下任何目錄" \
  "$([ -z "$(ls "$RS3/derived" 2>/dev/null)" ] && echo 1 || echo 0)"

# symlink 逸出：字元 allowlist 擋不到，靠 canonical path 複驗
SYM_OUT="$E/runs/sym-escape"
rm -rf "$SYM_OUT" "$RS3/derived"
mkdir -p "$SYM_OUT"
ln -s "$SYM_OUT" "$RS3/derived"
rescore "legit-id"
check "derived/ 是指向外部的 symlink → canonical 複驗擋下（exit 2）" \
  "$([ "$RSRC" = 2 ] && echo 1 || echo 0)" "rc=$RSRC"
check "symlink 逸出時不執行 rm -rf（外部目錄仍在）" \
  "$([ -d "$SYM_OUT" ] && echo 1 || echo 0)"
rm -f "$RS3/derived"; rm -rf "$SYM_OUT"

# --- F37：exit code 必須反映 contract 判定 ---
PASS_JSON='{"required": [{"element": "寫出派工單", "verdict": "PASS", "evidence": "有"}], "forbidden": [], "overall": "PASS"}'
FAIL_JSON='{"required": [{"element": "寫出派工單", "verdict": "FAIL", "evidence": "沒有"}], "forbidden": [], "overall": "FAIL"}'

rescore "ok-run" "CLAUDE_RESULT_JSON=$PASS_JSON"
check "judge 全 PASS → exit 0" "$([ "$RSRC" = 0 ] && echo 1 || echo 0)" \
  "rc=$RSRC $(tail -2 "$TMP/rs.out" | tr '\n' ' ')"
check "全 PASS 時 derived record 存在" \
  "$([ -f "$RS3/derived/ok-run/ok-run.json" ] && echo 1 || echo 0)"

rescore "fail-run" "CLAUDE_RESULT_JSON=$FAIL_JSON"
check "judge 判出 contract FAIL → exit 非 0" "$([ "$RSRC" -ne 0 ] && echo 1 || echo 0)" \
  "rc=$RSRC"
check "contract FAIL 時 derived record 仍保留（FAIL 是結論不是故障）" \
  "$([ -f "$RS3/derived/fail-run/fail-run.json" ] && echo 1 || echo 0)"
check "derived record 記為 FAIL" \
  "$(python3 -c 'import json,os,sys
p=sys.argv[1]
if not os.path.exists(p): print(0); raise SystemExit
print(1 if json.load(open(p))["run_status"]=="FAIL" else 0)' "$RS3/derived/fail-run/fail-run.json")"

# judge ERROR：stub 回傳不合 schema 的輸出，parser fail-closed
rescore "err-run"
check "judge 判定不可用（ERROR）→ exit 非 0" "$([ "$RSRC" -ne 0 ] && echo 1 || echo 0)" \
  "rc=$RSRC"
check "ERROR 時 derived record 記為 INVALID（未產生可用觀測）" \
  "$(python3 -c 'import json,os,sys
p=sys.argv[1]
if not os.path.exists(p): print(0); raise SystemExit
print(1 if json.load(open(p))["run_status"]=="INVALID" else 0)' "$RS3/derived/err-run/err-run.json")"

echo
echo "== 14. BR-F38：preflight 當下只有 start 快照，跨 schema 仍必須在花錢之前擋下 =="
# run-rescore.sh 的順序是 contract-snapshot start → preflight → judge → contract-snapshot end。
# 因此 preflight 讀到的 contract manifest **只有 start**。舊版 check_manifest 在 end 缺席時
# 整段早退並回傳 hash_schema=None，main() 的 cross_schema 因而恆為 False：
# 來源與現行 hash_schema 不同、又沒有 --migration-audit 時，preflight 印「通過」，
# judge 照跑照付費，INVALID 要等 judge 跑完才出現。這一節鎖住修正後的順序。
RS4="$E/runs/rescore-src4"
rm -rf "$RS4"; mkdir -p "$RS4/raw"
cp "$RAW/dispatch__case-1.jsonl" "$RAW/dispatch__case-1.meta.json" "$RS4/raw/"
printf '%s\n' "$GOOD_JUDGE" > "$RS4/raw/dispatch__case-1.judge.json"
cp "$RUN/trace-manifest.json" "$RS4/"
# 來源紀錄宣告 v3，現行是 v6：跨 schema，且不附 migration audit。
python3 -c 'import json,sys
d=json.load(open(sys.argv[1])); d["run_id"]="rescore-src4"; d["hash_schema"]="v3"
json.dump(d, open(sys.argv[2],"w"), ensure_ascii=False)' \
  "$RUN/sim-source.json" "$RS4/rescore-src4.json"

: > "$CALL_LOG"; echo "2.1.247 (Claude Code)" > "$VER"
set +e
CLAUDE_CALL_LOG="$CALL_LOG" CLAUDE_VERSION_FILE="$VER" PATH="$STUB:$PATH" \
  sh "$WORK/scripts/run-rescore.sh" "$RS4" d38 "$FXJ" > "$TMP/r38.out" 2>&1
R38=$?
set -e
CALLS38=$(grep -c call "$CALL_LOG" 2>/dev/null || echo 0)
check "跨 schema 缺 audit → run-rescore exit 2（preflight 擋下）" \
  "$([ "$R38" -eq 2 ] && echo 1 || echo 0)" "rc=$R38"
check "跨 schema 缺 audit → judge 判定次數 0（只有 --print-context 的版本查詢）" \
  "$([ "$CALLS38" -le 1 ] && echo 1 || echo 0)" "calls=$CALLS38"
check "跨 schema 缺 audit → 未產生 derived record" \
  "$([ ! -f "$RS4/derived/d38/d38.json" ] && echo 1 || echo 0)"
check "中止訊息指出缺 migration audit" \
  "$(grep -q 'migration-audit' "$TMP/r38.out" && echo 1 || echo 0)"
check "中止發生在 judge 之前（輸出未進入 judge 段）" \
  "$(grep -q '^== judge ==' "$TMP/r38.out" && echo 0 || echo 1)"

# 對照組：附上合格的 migration audit，同一份來源就應該跑完。
AUDIT38="$TMP/audit38.json"
python3 -c 'import json,sys
doms=["dispatch_skill","judgment_skill","token_preflight_skill","runner","fixtures","execution_context"]
item={"equivalent":True,"evidence":"逐檔 diff 為空","method":"逐 domain 比對 allowlist 與內容"}
json.dump({"source_hash_schema":"v3","target_hash_schema":"v6",
           "method":"逐 domain 比對","domains":{k:dict(item) for k in doms}},
          open(sys.argv[1],"w"), ensure_ascii=False)' "$AUDIT38"
: > "$CALL_LOG"
set +e
CLAUDE_CALL_LOG="$CALL_LOG" CLAUDE_VERSION_FILE="$VER" PATH="$STUB:$PATH" \
  CLAUDE_RESULT_JSON="$PASS_JSON" HARNESS_MIGRATION_AUDIT="$AUDIT38" \
  sh "$WORK/scripts/run-rescore.sh" "$RS4" d38ok "$FXJ" > "$TMP/r38ok.out" 2>&1
R38OK=$?
set -e
check "跨 schema 附合格 audit → 正常完成（exit 0）" \
  "$([ "$R38OK" -eq 0 ] && echo 1 || echo 0)" "rc=$R38OK"
check "跨 schema 附合格 audit → 產生 derived record" \
  "$([ -f "$RS4/derived/d38ok/d38ok.json" ] && echo 1 || echo 0)"

# start-only 的 contract manifest 若缺 domain，同樣必須在 judge 之前擋下。
# 直接對 record.py --validate-only 驗，避免依賴 run-rescore 內部產生的 manifest。
CMAN38="$TMP/cman38.json"
python3 "$E/manifest.py" contract-snapshot "$CMAN38" start "$CTX/judge-desc.txt" "$FXJ" >/dev/null
python3 -c 'import json,sys
p=sys.argv[1]; d=json.load(open(p)); del d["start"]["hashes"]["rescore_runner"]
json.dump(d, open(p,"w"), ensure_ascii=False)' "$CMAN38"
set +e
python3 "$E/record.py" --source "$RS4/rescore-src4.json" --migration-audit "$AUDIT38" \
  --validate-only "$RS4/raw" probe38 "$CMAN38" "$FXJ" > "$TMP/r38miss.out" 2>&1
R38MISS=$?
set -e
check "start-only contract manifest 缺 domain → validate-only 非 0" \
  "$([ "$R38MISS" -ne 0 ] && echo 1 || echo 0)" "rc=$R38MISS"
check "start-only 缺 domain 的訊息指名 rescore_runner" \
  "$(grep -q 'rescore_runner' "$TMP/r38miss.out" && echo 1 || echo 0)"
check "validate-only 不寫任何紀錄" \
  "$([ ! -f "$RS4/probe38.json" ] && echo 1 || echo 0)"

echo
echo "== 15. Batch 23a：固定 rules source、context 分項與 post-judge 綁定 =="
check "run-suite 使用 repo 內固定 rules source" \
  "$(grep -q 'RULES_SOURCE="\$BASE/context/rules.md"' "$E/run-suite.sh" \
     && grep -q 'cp "\$RULES_SOURCE" "\$RULES"' "$E/run-suite.sh" \
     && ! grep -q 'cp "\$HOME/.claude/CLAUDE.md"' "$E/run-suite.sh" \
     && echo 1 || echo 0)"
check "固定 rules source 存在" "$([ -f "$E/context/rules.md" ] && echo 1 || echo 0)"

fresh_manifest; snap start; mktrace; snap end; mkpost
cat > "$TMP/check-components.py" <<'PY'
import hashlib, json, sys


def file_hash(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


components = json.load(open(sys.argv[1]))["start"]["context_components"]
expected_execution = {
    "rules": file_hash(sys.argv[2]),
    "settings": file_hash(sys.argv[3]),
    "descriptor": file_hash(sys.argv[4]),
}
expected_evaluation = {"descriptor": file_hash(sys.argv[5])}
print(1 if components["execution_context"] == expected_execution
      and components["evaluation_context"] == expected_evaluation else 0)
PY
check "manifest 保存 execution／evaluation context 分項 hash" \
  "$(python3 "$TMP/check-components.py" "$MAN" "$CTX/rules.md" "$CTX/settings.json" \
     "$CTX/desc.txt" "$CTX/judge-desc.txt")"

set +e
python3 "$E/manifest.py" post-judge "$PJ" "$RAW" "$TM" "$FXJ" >/dev/null 2>&1
PJ_DUP_RC=$?
set -e
check "post-judge manifest 不可覆寫" "$([ "$PJ_DUP_RC" -ne 0 ] && echo 1 || echo 0)" \
  "rc=$PJ_DUP_RC"

cp "$RAW/dispatch__case-1.judge.json" "$TMP/judge.good"
printf '\n' >> "$RAW/dispatch__case-1.judge.json"
python3 "$E/record.py" "$RAW" pj-tampered "$MAN" "$FXJ" >/dev/null 2>&1 || true
check "judge 產物被更動 → record INVALID" \
  "$(python3 -c 'import json,sys
d=json.load(open(sys.argv[1])); print(1 if d["run_status"]=="INVALID" and "judge 產物 hash 不符" in (d["invalid_reason"] or "") else 0)' \
     "$RUN/pj-tampered.json")"
cp "$TMP/judge.good" "$RAW/dispatch__case-1.judge.json"

rm -f "$PJ"
python3 "$E/record.py" "$RAW" pj-missing "$MAN" "$FXJ" >/dev/null 2>&1 || true
check "缺 post-judge manifest → record INVALID" \
  "$(python3 -c 'import json,sys
d=json.load(open(sys.argv[1])); print(1 if d["run_status"]=="INVALID" and "post-judge manifest 不存在" in (d["invalid_reason"] or "") else 0)' \
     "$RUN/pj-missing.json")"
mkpost

python3 -c 'import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["trace_manifest_digest"]="b"*64
json.dump(d, open(p,"w"), ensure_ascii=False)' "$PJ"
python3 "$E/record.py" "$RAW" pj-wrong-trace "$MAN" "$FXJ" >/dev/null 2>&1 || true
check "post-judge 綁錯 trace → record INVALID" \
  "$(python3 -c 'import json,sys
d=json.load(open(sys.argv[1])); print(1 if d["run_status"]=="INVALID" and "trace digest" in (d["invalid_reason"] or "") else 0)' \
     "$RUN/pj-wrong-trace.json")"
mkpost

echo
if [ "$fails" -eq 0 ]; then
  echo "run-provenance-selftest: 全部通過（未起任何 session、未產生任何費用）"
  exit 0
fi
echo "run-provenance-selftest: FAIL $fails 項"
exit 1
