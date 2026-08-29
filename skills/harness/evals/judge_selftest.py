#!/usr/bin/env python3
"""judge_selftest.py — judge.py 事件抽取的零成本自測

只測 response_text() / is_main_thread() 的執行緒邊界，不呼叫 claude CLI、不花費用。

用法: python3 judge_selftest.py      (exit 0 通過 / 1 失敗)

repo 內既有的三份 run trace 每一筆 assistant 事件的 parent_tool_use_id 都是 null，
驗不到「非 null 要被排除」這條分支。合成 trace 直接寫在本檔裡而不另存 .jsonl，
是為了讓它跟 judge.py 一起落在 suite bundle 的 allowlist（evals/*.py）內——
測試材料若能在不動 suite hash 的情況下被改掉，這個測試就沒有版本綁定的意義。
"""
import importlib.util, os, sys, tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("judge", os.path.join(_HERE, "judge.py"))
judge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(judge)

# 一次主執行緒派工：主執行緒說明 + Agent 呼叫 + subagent 內部 Bash/Read/敘述 + 主執行緒收尾。
TWO_THREAD_TRACE = """
{"type":"assistant","parent_tool_use_id":null,"message":{"content":[{"type":"text","text":"MAIN-OPEN 先確認 dispatch skill 是否存在。"}]}}
{"type":"assistant","parent_tool_use_id":null,"message":{"content":[{"type":"tool_use","name":"Agent","id":"toolu_agent_1","input":{"subagent_type":"Explore","model":"haiku","prompt":"掃描 src/ 下 useCart 的使用點"}}]}}
{"type":"assistant","parent_tool_use_id":"toolu_agent_1","message":{"content":[{"type":"tool_use","name":"Bash","id":"toolu_bash_1","input":{"command":"grep -rn CHILD-BASH-MARKER src/"}}]}}
{"type":"assistant","parent_tool_use_id":"toolu_agent_1","message":{"content":[{"type":"tool_use","name":"Read","id":"toolu_read_1","input":{"file_path":"src/CHILD-READ-MARKER.ts"}}]}}
{"type":"assistant","parent_tool_use_id":"toolu_agent_1","message":{"content":[{"type":"text","text":"CHILD-TEXT-MARKER subagent 內部敘述"}]}}
{"type":"assistant","parent_tool_use_id":null,"message":{"content":[{"type":"text","text":"MAIN-CLOSE 掃描完成，共 3 處使用點。"}]}}
""".strip()

# 舊版 stream-json 沒有 parent_tool_use_id 這個欄位，必須仍視為主執行緒。
NO_KEY_TRACE = """
{"type":"assistant","message":{"content":[{"type":"text","text":"LEGACY-NO-KEY 事件"}]}}
""".strip()


def _extract(text):
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(text + "\n")
        return judge.response_text(path)
    finally:
        os.unlink(path)


def main():
    fails = []

    def check(label, cond):
        print(("  ok   " if cond else "  FAIL ") + label)
        if not cond:
            fails.append(label)

    print("is_main_thread")
    check("parent_tool_use_id=null 是主執行緒", judge.is_main_thread({"parent_tool_use_id": None}))
    check("欄位不存在視為主執行緒", judge.is_main_thread({}))
    check("parent_tool_use_id 非 null 不是主執行緒",
          not judge.is_main_thread({"parent_tool_use_id": "toolu_agent_1"}))

    out = _extract(TWO_THREAD_TRACE)
    print("response_text（一主一子執行緒）")
    check("保留主執行緒開場文字", "MAIN-OPEN" in out)
    check("保留主執行緒收尾文字", "MAIN-CLOSE" in out)
    check("保留主執行緒 Agent 派工證據", "[tool_use] Agent(" in out)
    check("Agent 參數仍可判讀（subagent_type/model）",
          "subagent_type=Explore" in out and "model=haiku" in out)
    check("排除 subagent 的 Bash", "CHILD-BASH-MARKER" not in out and "[tool_use] Bash" not in out)
    check("排除 subagent 的 Read", "CHILD-READ-MARKER" not in out and "[tool_use] Read" not in out)
    check("排除 subagent 的敘述文字", "CHILD-TEXT-MARKER" not in out)

    legacy = _extract(NO_KEY_TRACE)
    print("response_text（無 parent_tool_use_id 欄位）")
    check("舊格式事件不被整份濾掉", "LEGACY-NO-KEY" in legacy)

    print()
    if fails:
        print("judge_selftest: FAIL %d 項" % len(fails))
        return 1
    print("judge_selftest: 全部通過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
