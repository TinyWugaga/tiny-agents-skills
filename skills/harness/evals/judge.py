#!/usr/bin/env python3
"""judge.py <out-dir> <fixtures.json> [<routing-fixtures.json> ...]

評 fixture 的**回應契約**（`required_elements` / `forbidden_elements`）——
routing assertion 由 score.py 機械判定，本檔補上 score.py 做不到的語意判斷。

每筆從該 fixture 的 stream-json 抽出 assistant 的回應文字，連同判定條件交給一個
獨立的 judge session。judge 自己的完整輸出落成 `<id>.judge.json`，
判定要能被重讀重算，不是只留一個結論。

**Fail-closed**：judge 呼叫失敗、輸出不是合法 JSON、或條目數對不上，一律記 ERROR，
不得記 PASS。判不出來就說判不出來。
"""
import json, os, subprocess, sys

JUDGE_MODEL = os.environ.get("HARNESS_JUDGE_MODEL", "sonnet")

PROMPT = """你是回應契約的驗收員。判定一段 AI 回應是否滿足給定條件。

只依據下方「AI 回應」的實際內容判定。不要推測回應者的意圖，不要因為回應「看起來合理」
就放寬。條件講的行為若沒有實際出現在回應裡，就是 FAIL。

## 待判定的 AI 回應

<response>
{response}
</response>

## required_elements（回應必須具備）

{required}

## forbidden_elements（回應不得出現）

{forbidden}

## 輸出格式

只輸出一個 JSON 物件，不要有其他文字、不要包在 markdown code fence 裡：

{{"required": [{{"element": "<條件原文>", "verdict": "PASS|FAIL", "evidence": "<回應中的具體依據，或說明缺什麼>"}}],
  "forbidden": [{{"element": "<條件原文>", "verdict": "PASS|FAIL", "evidence": "<PASS 表示未出現；FAIL 要指出出現在哪>"}}],
  "overall": "PASS|FAIL"}}

overall 為 PASS 的條件：所有 required 皆 PASS 且所有 forbidden 皆 PASS。
"""


def response_text(jsonl):
    """抽出 assistant 的所有文字段落。"""
    parts = []
    for line in open(jsonl):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            return None  # 截斷 → 交給呼叫端記 ERROR
        if d.get("type") == "assistant":
            for c in d.get("message", {}).get("content", []):
                if c.get("type") == "text" and c.get("text", "").strip():
                    parts.append(c["text"].strip())
    return "\n\n".join(parts)


def judge_one(resp, required, forbidden):
    p = PROMPT.format(
        response=resp or "(回應為空)",
        required="\n".join(f"- {e}" for e in required) or "(無)",
        forbidden="\n".join(f"- {e}" for e in forbidden) or "(無)")
    r = subprocess.run(
        ["claude", "-p", p, "--output-format", "json", "--model", JUDGE_MODEL,
         "--disallowedTools", "Edit Write Bash Agent Read Glob Grep WebFetch WebSearch",
         "--no-session-persistence"],
        capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        return {"error": f"judge CLI exit={r.returncode}: {r.stderr[:300]}"}
    try:
        outer = json.loads(r.stdout)
    except json.JSONDecodeError as e:
        return {"error": f"judge 外層輸出非 JSON: {e}", "raw": r.stdout[:500]}
    txt = (outer.get("result") or "").strip()
    if txt.startswith("```"):
        txt = txt.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        v = json.loads(txt)
    except json.JSONDecodeError as e:
        return {"error": f"judge 判定非合法 JSON: {e}", "raw": txt[:500]}
    v["_cost_usd"] = outer.get("total_cost_usd")
    return v


def main(outdir, *fixture_files):
    n_pass = n_fail = n_err = 0
    for f in fixture_files:
        doc = json.load(open(f))
        suite = doc.get("skill_name") or doc.get("suite_name")
        for fx in doc["fixtures"]:
            name = f"{suite}__{fx['id']}"
            jsonl = os.path.join(outdir, name + ".jsonl")
            out = os.path.join(outdir, name + ".judge.json")
            if not os.path.exists(jsonl):
                res = {"error": "無 .jsonl，未跑"}
            else:
                resp = response_text(jsonl)
                res = ({"error": "stream-json 截斷，無法抽出回應"} if resp is None
                       else judge_one(resp, fx.get("required_elements", []),
                                      fx.get("forbidden_elements", [])))
            res["fixture_id"] = name
            res["judge_model"] = JUDGE_MODEL
            json.dump(res, open(out, "w"), indent=2, ensure_ascii=False)

            if "error" in res:
                mark, n_err = "!", n_err + 1
            elif res.get("overall") == "PASS":
                mark, n_pass = "✓", n_pass + 1
            else:
                mark, n_fail = "✗", n_fail + 1
            detail = res.get("error") or ""
            if not detail and res.get("overall") != "PASS":
                detail = "; ".join(
                    e["element"][:40] for e in
                    (res.get("required", []) + res.get("forbidden", []))
                    if e.get("verdict") == "FAIL")
            print(f"  {mark} {name:<40} {detail}")
    print(f"\n  response contract: PASS {n_pass} / FAIL {n_fail} / ERROR {n_err}")
    return 0 if n_fail == n_err == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], *sys.argv[2:]))
