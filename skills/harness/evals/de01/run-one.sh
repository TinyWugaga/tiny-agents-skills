#!/bin/sh
# run-one.sh <run-id> <fixtures-json> <expected-judgment_skill-hash>
#
# DE-01／KI-07 專用：跑「一次」run-suite.sh，並在事前與事後逐項設閘門。
# 刻意不提供迴圈——每一次 paid run 都要由呼叫端單獨下指令、單獨看結果。
#
# ## 為什麼不用 run-suite.sh 的 exit code 當停止條件
#
# `score.py` 的離開碼有三種語意（score.py:171-172）：
#   rc 0 = 全部 fixture routing PASS
#   rc 1 = 觀測全部可用，但有 fixture 未觸發   ← **這是資料，不是失敗**
#   rc 2 = 有 ERROR／NOT_RUN，未產生可用觀測   ← 這才是失敗
# `run-suite.sh` 把 rc 1 併進 SUITE_RC=1。DE-01 量的就是「arm B 是否不觸發」，
# 若以 SUITE_RC != 0 當停止條件，第一輪 arm B 就會中止整個 A/B，錢花了卻拿不到對照。
# 因此本檔改依來源 rc 分流。
#
# 閘門（任一不過即 exit != 0，呼叫端必須停止後續 paid run）：
#   事前：時間 cutoff、預算 cutoff、fixtures 檔存在、judgment_skill domain 等於預期 arm
#   事後：CLI 失敗數 = 0、routing rc != 2、record rc = 0、run_status != INVALID、
#         record 內的 domain 與預期逐一相同、成本累計寫入帳本
set -eu

BASE="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="$(cd "$BASE/../../.." && pwd)"
LEDGER="${DE01_LEDGER:?需要 DE01_LEDGER（帳本路徑，置於 repo 外）}"
LAUNCH_CUTOFF_USD="${DE01_LAUNCH_CUTOFF_USD:-6.00}"
LAUNCH_DEADLINE="${DE01_LAUNCH_DEADLINE:?需要 DE01_LAUNCH_DEADLINE（epoch 秒）}"

RUN_ID="${1:?run-id}"; FXREL="${2:?fixtures json（相對 evals/）}"; WANT_JS="${3:?預期 judgment_skill hash}"

fail() { echo "GATE-FAIL: $*" >&2; exit 9; }

# --- 事前閘門 ---
NOW=$(date +%s)
[ "$NOW" -lt "$LAUNCH_DEADLINE" ] || fail "已過 launch deadline，不啟動新的 paid session"

[ -f "$LEDGER" ] || : > "$LEDGER"
SPENT=$(awk -F'\t' '{s+=$2} END{printf "%.4f", s+0}' "$LEDGER")
UNDER=$(awk -v a="$SPENT" -v b="$LAUNCH_CUTOFF_USD" 'BEGIN{print (a<b)?1:0}')
[ "$UNDER" -eq 1 ] || fail "累計 USD $SPENT 已達 launch cutoff USD $LAUNCH_CUTOFF_USD"

[ -f "$BASE/$FXREL" ] || fail "找不到 fixtures: $BASE/$FXREL"
[ -e "$BASE/runs/$RUN_ID" ] && fail "run id 已存在，拒絕覆寫: $RUN_ID"

GOT_JS=$(sh "$ROOT/scripts/bundle-hash.sh" skill "$ROOT/skills/discipline/judgment")
[ "$GOT_JS" = "$WANT_JS" ] || fail "judgment_skill 不是預期 arm: got $GOT_JS want $WANT_JS"

echo "== gate ok | run=$RUN_ID fx=$FXREL arm=$WANT_JS spent=\$$SPENT =="

# --- 執行（不吞 rc）---
LOG=$(mktemp "${TMPDIR:-/tmp}/de01-$RUN_ID.XXXXXX")
set +e
( cd "$BASE" && HARNESS_FX="$FXREL" HARNESS_RT=de01/routing-empty.json \
    HARNESS_SUBJECT_MODEL=sonnet sh run-suite.sh "$RUN_ID" ) 2>&1 | tee "$LOG"
set -e

VERDICT=$(grep -E '^== suite 判定:' "$LOG" | tail -1)
[ -n "$VERDICT" ] || fail "找不到 suite 判定行，執行未走完"
CLIF=$(echo "$VERDICT" | sed -E 's/.*CLI 失敗 ([0-9-]+).*/\1/')
SRC=$( echo "$VERDICT" | sed -E 's/.*routing rc ([0-9-]+).*/\1/')
RRC=$( echo "$VERDICT" | sed -E 's/.*record rc ([0-9-]+).*/\1/')
echo "== 解析: CLI失敗=$CLIF routing_rc=$SRC record_rc=$RRC =="

[ "$CLIF" = "0" ] || fail "有 $CLIF 筆 CLI 失敗"
[ "$SRC" != "2" ] || fail "routing rc 2：未產生可用觀測"
[ "$RRC" = "0" ]  || fail "record rc $RRC：無有效 run record"

# --- 事後閘門：run record ---
REC="$BASE/runs/$RUN_ID/$RUN_ID.json"
[ -f "$REC" ] || fail "缺 run record: $REC"
python3 - "$REC" "$WANT_JS" "$LEDGER" "$RUN_ID" <<'PY'
import json,sys
rec,want_js,ledger,rid=sys.argv[1:5]
d=json.load(open(rec))
st=d.get("run_status")
if st=="INVALID": raise SystemExit(f"GATE-FAIL: run_status INVALID — {d.get('invalid_reason')}")
if st not in ("PASS","FAIL"): raise SystemExit(f"GATE-FAIL: run_status {st!r}")
h=d.get("hashes") or {}
exp={"evaluator":"65bc6c07d058697cda34045637d3223568cf09626cc38b8385bac46d41157480",
     "runner":"005ed2f71ac49a8b6747dd1c43f42c8ee67315a9fb3ec8ce395f921ccf6cee3c",
     "dispatch_skill":"2d6c0d99b1c4ca927e2c06c82e065c389fa6a6b8ddbc325b0e9bde9bc071c4fc",
     "token_preflight_skill":"be72017e9fc7952e9a403cf90e951669496b08f4339938bc73a2829d44ef592a",
     "judgment_skill":want_js}
drift=[f"{k}: got {h.get(k)} want {v}" for k,v in exp.items() if h.get(k) and h[k]!=v]
if drift: raise SystemExit("GATE-FAIL: domain drift — "+"; ".join(drift))
c=d.get("cost") or {}
tot=c.get("total_usd")
if tot is None:
    tot=sum(v for k,v in c.items() if k.endswith("_usd") and isinstance(v,(int,float)))
open(ledger,"a").write(f"{rid}\t{tot:.6f}\t{st}\t{h.get('fixtures')}\n")
trig={r["id"]:r.get("routing") for r in d.get("results",[])}
print(f"== record ok | status={st} cost=${tot:.4f} fixtures_domain={h.get('fixtures')}")
print(f"== routing: {trig}")
PY
SPENT=$(awk -F'\t' '{s+=$2} END{printf "%.4f", s+0}' "$LEDGER")
echo "== 累計 USD $SPENT =="
