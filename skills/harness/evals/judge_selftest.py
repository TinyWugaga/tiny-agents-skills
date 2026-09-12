#!/usr/bin/env python3
"""judge_selftest.py — judge.py 事件抽取與判定解析的零成本自測

測 response_text() / is_main_thread() 的執行緒邊界，以及 parse_verdict() 的 fail-closed
契約：fence 完整性、尾端殘餘、schema、逐條比對原始條件、未知 key、以及「任何輸入都不拋例外」。
不呼叫 claude CLI、不花費用。

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

    def check(label, cond, detail=None):
        print(("  ok   " if cond else "  FAIL ") + label)
        if not cond:
            if detail is not None:
                print(f"         detail: {detail}")
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

    # --- parse_verdict（Batch 13：fail-closed 解析；13f：完整 fence 比對與逐條比對）---
    from judge import parse_verdict as pv
    REQ, FRB = ["a"], ["b"]
    ok = ('{"required": [{"element": "a", "verdict": "PASS", "evidence": "e"}], '
          '"forbidden": [{"element": "b", "verdict": "PASS", "evidence": "e"}], '
          '"overall": "PASS"}')
    print("parse_verdict")
    v, an = pv(ok, REQ, FRB)
    check("合規輸出通過且無異常", v is not None and an is None)
    v, an = pv("```json\n" + ok + "\n```", REQ, FRB)
    check("markdown fence 仍可解析", v is not None and an is None)

    # 真實故障重現：negative-2 的形狀——第一份 JSON 含多餘 key，接著散文，再接被截斷的第二份。
    real = (ok[:-1] + ', "forbidden_note": null}'
            + "\n\nWait, I need to fix the JSON format — remove the stray key.\n\n"
            + '{"required": [{"elemen')
    v, an = pv(real, REQ, FRB)
    check("尾端有內容一律不可用", v is None and an["kind"] == "extra_data")
    check("記錄第二個 JSON 起點", an["has_second_json_start"] is True)
    check("記錄第二個 JSON 不完整", an["second_json_complete"] is False)

    v, an = pv(ok + "\n\n以上是我的判定。", REQ, FRB)
    check("純散文尾端也不可用（不得只當雜訊丟掉）", v is None and an["kind"] == "extra_data")

    v, an = pv(ok + " " + ok, REQ, FRB)
    check("兩份完整 JSON 不可用", v is None and an["kind"] == "extra_data"
          and an["second_json_complete"] is True)

    # --- 13f-1：fence 之後的殘餘（舊 rsplit 會整段丟棄，回傳可用判定且不記異常）---
    v, an = pv("```json\n" + ok + "\n```\n\nI retract this verdict.", REQ, FRB)
    check("fence 後接撤回散文 → 不可用",
          v is None and an["kind"] == "fence_trailing_content")
    check("fence 殘餘留下可診斷的內容", "retract" in an["trailing_head"])
    v, an = pv("```json\n" + ok + "\n```\n```json\n" + ok + "\n```", REQ, FRB)
    check("fence 後接第二份 fenced JSON → 不可用",
          v is None and an["kind"] == "fence_trailing_content")

    # --- 13f-1：截斷 fence（舊版在此拋 IndexError，會中斷整輪並失去後面每一筆證據）---
    for trunc in ("```", "```json"):
        v, an = pv(trunc, REQ, FRB)
        check(f"截斷 fence {trunc!r} 不拋例外且不可用",
              v is None and an["kind"] == "fence_unterminated")
    v, an = pv("```json\n" + ok, REQ, FRB)
    check("缺 closing fence → 不可用", v is None and an["kind"] == "fence_unterminated")
    v, an = pv("```json\n```", REQ, FRB)
    check("fence body 為空 → 走 not_json 而非例外",
          v is None and an["kind"] == "not_json")

    # --- 13f-2：element 內容比對（舊版只驗數量，以下三種都會被誤放行）---
    swapped = ok.replace('"element": "a"', '"element": "完全不同的條件"')
    v, an = pv(swapped, REQ, FRB)
    check("element 被整條替換 → 不可用", v is None and an["kind"] == "schema_violation")
    check("指出是哪一條對不上",
          any("element 與原始條件不符" in p for p in an["problems"]))

    dup = ('{"required": [{"element": "a", "verdict": "PASS", "evidence": "e"}, '
           '{"element": "a", "verdict": "PASS", "evidence": "e"}], '
           '"forbidden": [], "overall": "PASS"}')
    v, an = pv(dup, ["a", "c"], [])
    check("同一條重複兩次充數 → 不可用", v is None and an["kind"] == "schema_violation")

    miss = ('{"required": [{"element": "a", "verdict": "PASS", "evidence": "e"}, '
            '{"element": "a", "verdict": "PASS", "evidence": "e"}, '
            '{"element": "c", "verdict": "PASS", "evidence": "e"}], '
            '"forbidden": [], "overall": "PASS"}')
    v, an = pv(miss, ["a", "b", "c"], [])
    check("漏判一條而以他條補位 → 不可用", v is None and an["kind"] == "schema_violation")

    wrapped = ok.replace('"element": "a"', '"element": "a  "')
    v, an = pv(wrapped, REQ, FRB)
    check("僅空白差異仍可用（正規化只吸收空白重排）", v is not None and an is None)

    v, an = pv(ok, ["a", "extra"], FRB)
    check("required 條目數不符 → 不可用", v is None and an["kind"] == "schema_violation")
    v, an = pv(ok, REQ, ["b", "extra"])
    check("forbidden 條目數不符 → 不可用", v is None and an["kind"] == "schema_violation")

    bad_verdict = ok.replace('"verdict": "PASS"', '"verdict": "MAYBE"', 1)
    v, an = pv(bad_verdict, REQ, FRB)
    check("verdict 值不合法 → 不可用", v is None and an["kind"] == "schema_violation")

    no_ev = ok.replace(', "evidence": "e"', '', 1)
    v, an = pv(no_ev, REQ, FRB)
    check("缺 evidence → 不可用", v is None and an["kind"] == "schema_violation")

    inconsistent = ok.replace('"overall": "PASS"', '"overall": "FAIL"')
    v, an = pv(inconsistent, REQ, FRB)
    check("overall 與逐條判定矛盾 → 不可用",
          v is None and an["kind"] == "overall_inconsistent")

    # --- 13f-2：未知 top-level key 一律不可用（先前放行，corrected_overall 即可承載撤回）---
    extra = ok[:-1] + ', "note": "x"}'
    v, an = pv(extra, REQ, FRB)
    check("多餘 key → 不可用", v is None and an["kind"] == "unknown_keys"
          and an["extra_keys"] == ["note"])
    corrected = ok[:-1] + ', "corrected_overall": "FAIL"}'
    v, an = pv(corrected, REQ, FRB)
    check("以多餘 key 承載撤回 → 不可用",
          v is None and an["kind"] == "unknown_keys")

    # --- Batch 14：逐條項目的未知 key（只擋 top-level 時，撤回往下挪一層即可繞過）---
    nested = ok.replace('{"element": "a", "verdict": "PASS", "evidence": "e"}',
                        '{"element": "a", "verdict": "PASS", "evidence": "e", '
                        '"corrected_verdict": "FAIL"}')
    v, an = pv(nested, REQ, FRB)
    check("required 項目內的 corrected_verdict → 不可用",
          v is None and an["kind"] == "schema_violation")
    check("指出是哪一項多出 key",
          any("required[0] 多出 schema 外的 key" in p and "corrected_verdict" in p
              for p in an["problems"]))

    nested_f = ok.replace('{"element": "b", "verdict": "PASS", "evidence": "e"}',
                          '{"element": "b", "verdict": "PASS", "evidence": "e", '
                          '"note": "其實我不確定"}')
    v, an = pv(nested_f, REQ, FRB)
    check("forbidden 項目內的多餘 key → 不可用",
          v is None and an["kind"] == "schema_violation")
    check("指出是 forbidden 那一項",
          any("forbidden[0] 多出 schema 外的 key" in p for p in an["problems"]))

    # 逐條項目內放 schema 的 top-level 名稱，同樣不得放行——它不在 ITEM_KEYS 內。
    nested_overall = ok.replace('{"element": "a", "verdict": "PASS", "evidence": "e"}',
                                '{"element": "a", "verdict": "PASS", "evidence": "e", '
                                '"overall": "FAIL"}')
    v, an = pv(nested_overall, REQ, FRB)
    check("項目內混入 top-level 名稱的 key → 不可用",
          v is None and an["kind"] == "schema_violation")

    # 多筆條件時，只有出問題的那一項被指名，不得整批連坐或漏報。
    two = ('{"required": [{"element": "a", "verdict": "PASS", "evidence": "e"}, '
           '{"element": "c", "verdict": "PASS", "evidence": "e", "confidence": 0.4}], '
           '"forbidden": [{"element": "b", "verdict": "PASS", "evidence": "e"}], '
           '"overall": "PASS"}')
    v, an = pv(two, ["a", "c"], FRB)
    check("多筆條件中只指名出問題的那一項",
          v is None and an["kind"] == "schema_violation"
          and any("required[1] 多出" in p for p in an["problems"])
          and not any("required[0] 多出" in p for p in an["problems"]))

    # 對照組：三個合法 key 齊全且無多餘 key，必須仍然通過（收緊不得誤傷正常輸出）。
    v, an = pv(ok, REQ, FRB)
    check("合法三 key 項目不受收緊影響", v is not None and an is None)

    v, an = pv("不是 JSON", REQ, FRB)
    check("非 JSON → not_json", v is None and an["kind"] == "not_json")
    v, an = pv("[1,2]", REQ, FRB)
    check("頂層不是物件 → not_object", v is None and an["kind"] == "not_object")

    # --- 13f-1：任何輸入都不得讓 parser 拋例外（例外會中斷整輪 judge）---
    hostile = ["", " ", "`", "``", "```", "```\n", "\n```", "```json\n```\n```",
               "{", "{}", "null", '"x"', "```json", "``` \n{}\n ```", ok[:-1]]
    raised = []
    for h in hostile:
        try:
            r = pv(h, REQ, FRB)
            if not (isinstance(r, tuple) and len(r) == 2):
                raised.append((h, "非 (verdict, anomaly) tuple"))
        except Exception as exc:
            raised.append((h, f"{type(exc).__name__}: {exc}"))
    check(f"畸形輸入 {len(hostile)} 例全不拋例外", not raised, raised[:3])
    print()
    if fails:
        print("judge_selftest: FAIL %d 項" % len(fails))
        return 1
    print("judge_selftest: 全部通過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
