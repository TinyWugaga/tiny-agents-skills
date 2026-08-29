#!/usr/bin/env python3
"""score_selftest.py — score.py 觸發判定的零成本自測

只測 load_run() / score() 的 Skill 觸發判定，不起任何 session、不產生費用。

用法: python3 score_selftest.py      (exit 0 通過 / 1 失敗)

repo 內既有 trace 全部只有「主執行緒 + 成功」這一種組合，驗不到失敗呼叫、subagent
呼叫、缺 tool_result 三條分支。合成事件直接寫在本檔裡而不另存 .jsonl，是為了讓它跟
score.py 一起落在 suite bundle 的 allowlist（evals/*.py）內——測試材料若能在不動
suite hash 的情況下被改掉，這個測試就沒有版本綁定的意義。
"""
import importlib.util, json, os, sys, tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("score", os.path.join(_HERE, "score.py"))
score = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(score)

INIT = {"type": "system", "subtype": "init", "skills": ["dispatch", "judgment"]}
DONE = {"type": "result", "subtype": "success"}


def skill_call(tuid, skill, parent=None):
    return {"type": "assistant", "parent_tool_use_id": parent,
            "message": {"content": [{"type": "tool_use", "name": "Skill",
                                     "id": tuid, "input": {"skill": skill}}]}}


def tool_result(tuid, is_error=False, parent=None):
    b = {"type": "tool_result", "tool_use_id": tuid,
         "content": "Skill not found" if is_error else "Launching skill: dispatch"}
    if is_error:
        b["is_error"] = True
    return {"type": "user", "parent_tool_use_id": parent, "message": {"content": [b]}}


def _write(outdir, name, events):
    with open(os.path.join(outdir, name + ".jsonl"), "w") as fh:
        for e in events:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    with open(os.path.join(outdir, name + ".meta.json"), "w") as fh:
        json.dump({"exit_code": 0}, fh)


CASES = {
    # 成功呼叫：主執行緒 Skill + 無 is_error 的 tool_result → 算觸發
    "ok": [INIT, skill_call("t1", "dispatch"), tool_result("t1"), DONE],
    # 失敗呼叫：tool_result is_error=true → 只算 attempted，不算觸發
    "failed": [INIT, skill_call("t1", "dispatch"), tool_result("t1", is_error=True), DONE],
    # child 呼叫：subagent 執行緒發出的 Skill → 兩邊都不算
    "child": [INIT, skill_call("t9", "dispatch", parent="toolu_agent_1"),
              tool_result("t9", parent="toolu_agent_1"), DONE],
    # 缺 tool_result：成敗無法判定 → fail-closed ERROR
    "orphan": [INIT, skill_call("t1", "dispatch"), DONE],
}


def main():
    fails = []

    def check(label, cond):
        print(("  ok   " if cond else "  FAIL ") + label)
        if not cond:
            fails.append(label)

    with tempfile.TemporaryDirectory() as d:
        for name, events in CASES.items():
            _write(d, name, events)
        res = {n: score.load_run(d, n) for n in CASES}

        print("load_run")
        st, got, att, _, _ = res["ok"]
        check("成功呼叫算觸發", (st, got, att) == ("OK", {"dispatch"}, set()))
        st, got, att, _, diag = res["failed"]
        check("失敗呼叫只算 attempted，不算觸發", (st, got, att) == ("OK", set(), {"dispatch"}))
        st, got, att, _, _ = res["child"]
        check("subagent 的 Skill 呼叫兩邊都不算", (st, got, att) == ("OK", set(), set()))
        st, _, _, _, diag = res["orphan"]
        check("缺 tool_result → fail-closed ERROR", st == "ERROR" and "tool_result" in diag)

        # 端到端：缺席環境下模型仍去呼叫 dispatch 但失敗，routing 應判 PASS 不是 FAIL。
        fx = {"suite_name": "selftest", "fixtures": [
            {"id": "absent-1", "category": "positive", "expected_route": {"dispatch": False}}]}
        _write(d, "selftest__absent-1", CASES["failed"])
        fxp = os.path.join(d, "fx.json")
        json.dump(fx, open(fxp, "w"))
        row = score.score(d, fxp)[0]

        print("score（缺席環境端到端）")
        check("routing PASS（失敗呼叫不構成觸發）", row["routing"] == "PASS")
        check("triggered 為空", row["triggered"] == [])
        check("attempted_failed 記錄該次失敗呼叫", row["attempted_failed"] == ["dispatch"])
        check("detail 說明有失敗呼叫", "失敗的 Skill 呼叫" in row["detail"])

    print()
    if fails:
        print("score_selftest: FAIL %d 項" % len(fails))
        return 1
    print("score_selftest: 全部通過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
