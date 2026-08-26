#!/usr/bin/env python3
"""score.py <out-dir> <fixtures.json> [<routing-fixtures.json> ...]

**Fail-closed 評分器。** 只評 routing assertion（哪個 skill 被觸發），
不評 required_elements / forbidden_elements——那需要語意判斷，本檔不做，
一律標記為 NOT_EVALUATED，不得被當成「fixture 完整通過」。

一筆要記 PASS，必須全部成立：
  1. `<id>.meta.json` 存在且 exit_code == 0（CLI 真的跑完，不是被吞掉的失敗）
  2. `<id>.jsonl` 每一行都是合法 JSON（截斷或壞行 → ERROR）
  3. 有 `system/init` 事件（session 真的起來了）
  4. 有 `result` 事件且 subtype == "success"（session 正常結束）
  5. 觸發的 skill 集合符合 expected

任一項不成立即 ERROR，不是 PASS。這條規則的存在理由：
負向 fixture 期望「沒有觸發」，而空輸出或截斷輸出也長得像「沒有觸發」，
不 fail-closed 就會給出假綠燈。

exit code：有任何 FAIL / ERROR / NOT_RUN 都回 1。全部 PASS 才回 0。
"""
import json, os, sys
from collections import Counter

TRACKED = {"dispatch", "judgment", "token-preflight"}


def load_run(outdir, name):
    """回傳 (status, 觸發的 skill 集合, 可見 skill 清單, 診斷訊息)"""
    jsonl = os.path.join(outdir, name + ".jsonl")
    meta_p = os.path.join(outdir, name + ".meta.json")

    if not os.path.exists(jsonl):
        return "NOT_RUN", set(), None, "無 .jsonl"
    if not os.path.exists(meta_p):
        return "ERROR", set(), None, "無 .meta.json（無法確認 CLI 是否真的跑完）"
    try:
        meta = json.load(open(meta_p))
    except json.JSONDecodeError as e:
        return "ERROR", set(), None, f".meta.json 壞損: {e}"
    if meta.get("exit_code") != 0:
        return "ERROR", set(), None, f"CLI exit_code={meta.get('exit_code')}"

    got, avail, has_init, result_ok = set(), None, False, False
    for i, line in enumerate(open(jsonl), 1):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError as e:
            return "ERROR", set(), None, f"第 {i} 行非合法 JSON（輸出可能截斷）: {e}"
        if d.get("type") == "system" and d.get("subtype") == "init":
            has_init, avail = True, d.get("skills")
        if d.get("type") == "result":
            result_ok = d.get("subtype") == "success"
        if d.get("type") == "assistant":
            for c in d.get("message", {}).get("content", []):
                if c.get("type") == "tool_use" and c.get("name") == "Skill":
                    s = (c.get("input") or {}).get("skill")
                    if s:
                        got.add(s.split(":")[-1])

    if not has_init:
        return "ERROR", got, avail, "缺 system/init 事件（session 未正常啟動）"
    if not result_ok:
        return "ERROR", got, avail, "缺 result:success 事件（session 未正常結束）"
    return "OK", got, avail, ""


def expected_map(fx):
    """fixture -> {skill: bool}。dispatch fixtures 只約束 dispatch。"""
    if "expected_route" in fx:
        return {k.split(":")[-1]: v for k, v in fx["expected_route"].items()}
    return {"dispatch": bool(fx["expected_trigger"])}


def score(outdir, *fixture_files):
    rows = []
    for f in fixture_files:
        doc = json.load(open(f))
        suite = doc.get("skill_name") or doc.get("suite_name")
        for fx in doc["fixtures"]:
            name = f"{suite}__{fx['id']}"
            status, got, avail, diag = load_run(outdir, name)
            row = {"suite": suite, "id": name, "category": fx["category"],
                   "triggered": sorted(got & TRACKED), "available_skills": avail,
                   "contract": "NOT_EVALUATED"}
            if status != "OK":
                row.update(routing=status, detail=diag)
            else:
                exp = expected_map(fx)
                bad = [f"{k}: 預期{'觸發' if v else '不觸發'}，"
                       f"實際{'觸發' if (k in got) else '未觸發'}"
                       for k, v in exp.items() if (k in got) != v]
                row.update(routing="PASS" if not bad else "FAIL", detail="; ".join(bad))
            rows.append(row)
    return rows


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    rows = score(sys.argv[1], *sys.argv[2:])
    w = max((len(r["id"]) for r in rows), default=10)
    mark = {"PASS": "✓", "FAIL": "✗", "ERROR": "!", "NOT_RUN": "·"}
    for r in rows:
        trig = ",".join(r["triggered"]) or "(無)"
        print(f"  {mark[r['routing']]} {r['id']:<{w}}  {r['category']:<16} "
              f"觸發={trig:<24} {r['detail']}")
    c = Counter(r["routing"] for r in rows)
    print(f"\n  routing assertions: PASS {c['PASS']} / FAIL {c['FAIL']} / "
          f"ERROR {c['ERROR']} / NOT_RUN {c['NOT_RUN']}  (共 {len(rows)})")
    print(f"  response contract (required_elements / forbidden_elements): "
          f"NOT_EVALUATED × {len(rows)} — 本評分器不做語意判斷")
    sys.exit(0 if c["PASS"] == len(rows) else 1)
