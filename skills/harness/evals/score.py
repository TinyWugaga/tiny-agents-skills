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
  5. 每個主執行緒的 `Skill` 呼叫都能對到 `tool_result`（對不到 → ERROR）
  6. 觸發的 skill 集合符合 expected

**什麼算「觸發」**：只採主執行緒（top-level `parent_tool_use_id` 為 null）發出的 `Skill`
呼叫，且其 `tool_result` 沒有 `is_error`。失敗的呼叫只算 attempted，不算觸發——skill
不存在時模型仍會去呼叫它，把那算成觸發會讓 `no-dispatch` 這種缺席環境永遠判成「有觸發」，
缺席 fixture 因此永遠不可能通過。對不到 `tool_result` 的呼叫成敗無法判定，fail-closed 記 ERROR。

任一項不成立即 ERROR，不是 PASS。這條規則的存在理由：
負向 fixture 期望「沒有觸發」，而空輸出或截斷輸出也長得像「沒有觸發」，
不 fail-closed 就會給出假綠燈。

exit code：0 = 全部 PASS；1 = 有 FAIL 但每筆都有可用觀測；
**2 = 有 ERROR / NOT_RUN，亦即有 fixture 根本沒產生可用觀測**。
2 與 1 必須分開：前者代表這一輪對 skill 沒有結論，呼叫端應據此跳過 judge——
對空的或失敗的 trace 送 judge 只會燒錢並產生假的 contract FAIL。
"""
import json, os, sys
from collections import Counter

TRACKED = {"dispatch", "judgment", "token-preflight"}


def is_main_thread(event):
    """主執行緒事件：top-level `parent_tool_use_id` 為 null（或該欄不存在）。

    與 judge.py 的同名判定同規則；兩邊各自持有一份，避免評分器相依於 judge。
    """
    return event.get("parent_tool_use_id") is None


def load_run(outdir, name):
    """回傳 (status, 成功觸發的 skill, 呼叫失敗的 skill, 可見 skill 清單, 診斷訊息)"""
    jsonl = os.path.join(outdir, name + ".jsonl")
    meta_p = os.path.join(outdir, name + ".meta.json")

    if not os.path.exists(jsonl):
        return "NOT_RUN", set(), set(), None, "無 .jsonl"
    if not os.path.exists(meta_p):
        return "ERROR", set(), set(), None, "無 .meta.json（無法確認 CLI 是否真的跑完）"
    try:
        meta = json.load(open(meta_p))
    except json.JSONDecodeError as e:
        return "ERROR", set(), set(), None, f".meta.json 壞損: {e}"
    if meta.get("exit_code") != 0:
        return "ERROR", set(), set(), None, f"CLI exit_code={meta.get('exit_code')}"

    calls, results = {}, {}   # tool_use_id -> skill 名 / tool_use_id -> is_error
    avail, has_init, result_ok = None, False, False
    for i, line in enumerate(open(jsonl), 1):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError as e:
            return "ERROR", set(), set(), None, f"第 {i} 行非合法 JSON（輸出可能截斷）: {e}"
        if d.get("type") == "system" and d.get("subtype") == "init":
            has_init, avail = True, d.get("skills")
        if d.get("type") == "result":
            result_ok = d.get("subtype") == "success"
        if d.get("type") == "assistant" and is_main_thread(d):
            for c in d.get("message", {}).get("content", []):
                if c.get("type") == "tool_use" and c.get("name") == "Skill":
                    s = (c.get("input") or {}).get("skill")
                    if s:
                        calls[c.get("id")] = s.split(":")[-1]
        if d.get("type") == "user":
            # tool_result 依 tool_use_id 對應，不分執行緒——id 全域唯一，
            # 若也依執行緒過濾，反而會製造假的「找不到 tool_result」。
            content = d.get("message", {}).get("content")
            if isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        results[b.get("tool_use_id")] = bool(b.get("is_error"))

    got = {n for k, n in calls.items() if results.get(k) is False}
    attempted = {n for k, n in calls.items() if results.get(k) is True}
    orphan = sorted({n for k, n in calls.items() if k not in results})

    if not has_init:
        return "ERROR", got, attempted, avail, "缺 system/init 事件（session 未正常啟動）"
    if not result_ok:
        return "ERROR", got, attempted, avail, "缺 result:success 事件（session 未正常結束）"
    if orphan:
        return ("ERROR", got, attempted, avail,
                "Skill 呼叫對不到 tool_result，成敗無法判定: " + ", ".join(orphan))
    return "OK", got, attempted, avail, ""


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
            status, got, attempted, avail, diag = load_run(outdir, name)
            failed = sorted(attempted & TRACKED)
            row = {"suite": suite, "id": name, "category": fx["category"],
                   "triggered": sorted(got & TRACKED), "attempted_failed": failed,
                   "available_skills": avail, "contract": "NOT_EVALUATED"}
            if status != "OK":
                row.update(routing=status, detail=diag)
            else:
                exp = expected_map(fx)
                bad = [f"{k}: 預期{'觸發' if v else '不觸發'}，"
                       f"實際{'觸發' if (k in got) else '未觸發'}"
                       for k, v in exp.items() if (k in got) != v]
                note = (f"（另有失敗的 Skill 呼叫，不計入觸發: {', '.join(failed)}）"
                        if failed else "")
                row.update(routing="PASS" if not bad else "FAIL",
                           detail="; ".join(bad) + note)
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
        if r["attempted_failed"]:
            trig += " !" + ",".join(r["attempted_failed"])
        print(f"  {mark[r['routing']]} {r['id']:<{w}}  {r['category']:<16} "
              f"觸發={trig:<24} {r['detail']}")
    c = Counter(r["routing"] for r in rows)
    unusable = c["ERROR"] + c["NOT_RUN"]
    print(f"\n  routing assertions: PASS {c['PASS']} / FAIL {c['FAIL']} / "
          f"ERROR {c['ERROR']} / NOT_RUN {c['NOT_RUN']}  (共 {len(rows)})")
    print(f"  response contract (required_elements / forbidden_elements): "
          f"NOT_EVALUATED × {len(rows)} — 本評分器不做語意判斷")
    if unusable:
        print(f"  ⚠ {unusable} 筆未產生可用觀測 → 本輪不構成契約證據")
        sys.exit(2)
    sys.exit(0 if c["PASS"] == len(rows) else 1)
