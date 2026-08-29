#!/usr/bin/env python3
"""record.py <run-dir> <run-id> <fixtures.json> [<routing-fixtures.json> ...]

產生 run record：`<run-dir>/<run-id>.json` 與 `.md`。

**這份檔案的用途是讓第三方能重算、能比對。** 因此每個數字都必須可回溯：
hash 用 bundle-hash.sh 現算（並記下算法與腳本路徑），逐筆判定取自 raw trace 與
`.judge.json`，成本取自 session 自己回報的 `total_cost_usd`。
沒有實測來源的欄位一律寫 null，不以推估補完。

環境變數（由 run-suite.sh 傳入，缺了就記 null）：
  HARNESS_RUN_STARTED / HARNESS_RUN_ENDED   epoch 秒
  HARNESS_SUBJECT_MODEL / HARNESS_JUDGE_MODEL
  HARNESS_CLI_FAILED                        CLI 失敗筆數
"""
import json, os, subprocess, sys, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
HASH_SH = os.path.join(BASE, "..", "dispatch", "scripts", "bundle-hash.sh")
HASH_REL = "skills/harness/dispatch/scripts/bundle-hash.sh"


def bundle_hash(target, mode="skill"):
    try:
        r = subprocess.run(["sh", HASH_SH, target, mode],
                           capture_output=True, text=True, timeout=120)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def claude_version():
    try:
        r = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=60)
        return r.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def subject_cost(jsonl):
    """從 result 事件取 session 自報成本；取不到回 None，不推估。"""
    try:
        for line in open(jsonl):
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if d.get("type") == "result" and d.get("total_cost_usd") is not None:
                return float(d["total_cost_usd"])
    except (OSError, ValueError):
        pass
    return None


def collect(outdir, fixture_files):
    sys.path.insert(0, BASE)
    import score as scorer
    rows = scorer.score(outdir, *fixture_files)
    subj_cost, judge_cost, n_subject, n_judge = 0.0, 0.0, 0, 0
    subj_missing = judge_missing = False
    for r in rows:
        jl = os.path.join(outdir, r["id"] + ".jsonl")
        if os.path.exists(jl):
            n_subject += 1
            c = subject_cost(jl)
            if c is None:
                subj_missing = True
            else:
                subj_cost += c
        jf = os.path.join(outdir, r["id"] + ".judge.json")
        if os.path.exists(jf):
            n_judge += 1
            try:
                jd = json.load(open(jf))
            except (OSError, ValueError):
                jd = {"error": "judge 檔壞損"}
            r["contract"] = jd.get("error") and "ERROR" or jd.get("overall", "ERROR")
            r["contract_detail"] = jd.get("error", "")
            c = jd.get("_cost_usd")
            if c is None:
                judge_missing = True
            else:
                judge_cost += float(c)
        else:
            r["contract"] = "NOT_RUN"
            r["contract_detail"] = "無 .judge.json"
    # preflight 也是真實 session，成本要算進來，否則紀錄少報。
    pf = os.path.join(outdir, "_preflight.jsonl")
    pf_cost = subject_cost(pf) if os.path.exists(pf) else None
    cost = {
        "preflight_usd": pf_cost,
        "preflight_sessions": 1 if os.path.exists(pf) else 0,
        "subject_usd": None if subj_missing else round(subj_cost, 4),
        "judge_usd": None if judge_missing else round(judge_cost, 4),
        "subject_sessions": n_subject,
        "judge_sessions": n_judge,
    }
    parts = [cost["subject_usd"], cost["judge_usd"]]
    if cost["preflight_sessions"]:
        parts.append(cost["preflight_usd"])
    cost["total_usd"] = (None if any(x is None for x in parts) else round(sum(parts), 4))
    return rows, cost


def main(outdir, run_id, *fixture_files):
    rundir = os.path.dirname(os.path.abspath(outdir))
    rows, cost = collect(outdir, fixture_files)

    started = os.environ.get("HARNESS_RUN_STARTED")
    ended = os.environ.get("HARNESS_RUN_ENDED")
    dur = (int(ended) - int(started)) if (started and ended) else None
    cli_failed = os.environ.get("HARNESS_CLI_FAILED")
    cli_failed = int(cli_failed) if cli_failed is not None else None

    skills = os.path.join(BASE, "..", "..")
    # 三值判定。**FAIL 與 INVALID 必須分開**：
    #   FAIL    = 每一筆都產生了可用觀測，而其中有觀測不符預期 → 這是關於 skill 的證據。
    #   INVALID = 有 fixture 根本沒產生可用觀測（CLI 失敗、逾時、未跑、judge 無法判定）
    #             → 這一輪對 skill 什麼都沒說,不得被當成契約證據。
    # 少了這個區分,一輪「登入過期、18 筆全部在推論前就失敗」的執行會被記成 FAIL,
    # 日後讀起來像是 skill 沒通過。
    USABLE = ("PASS", "FAIL")
    unusable = [r for r in rows
                if r["routing"] not in USABLE or r["contract"] not in USABLE]
    bad = [r for r in rows if r["routing"] == "FAIL" or r["contract"] == "FAIL"]
    if not rows:
        status, evidence = "INVALID", False
        reason = "沒有任何 fixture"
    elif unusable:
        status, evidence = "INVALID", False
        reason = (f"{len(unusable)}/{len(rows)} 筆未產生可用觀測"
                  f"（CLI 失敗 {cli_failed if cli_failed is not None else '?'}）"
                  f"；樣本：{unusable[0]['id']} — "
                  f"routing={unusable[0]['routing']} {unusable[0]['detail']} / "
                  f"contract={unusable[0]['contract']} {unusable[0]['contract_detail']}")
    elif bad:
        status, evidence, reason = "FAIL", True, ""
    else:
        status, evidence, reason = "PASS", True, ""

    doc = {
        "run_id": run_id,
        "recorded_at": datetime.datetime.now().astimezone().isoformat(),
        "run_status": status,
        "is_contract_evidence": evidence,
        "invalid_reason": reason or None,
        "claude_code_version": claude_version(),
        "subject_model": os.environ.get("HARNESS_SUBJECT_MODEL"),
        "judge_model": os.environ.get("HARNESS_JUDGE_MODEL"),
        "duration_s": dur,
        "cli_failed": cli_failed,
        "cost": cost,
        "hashes": {
            "dispatch_bundle": bundle_hash(os.path.join(skills, "harness", "dispatch")),
            "judgment_bundle": bundle_hash(os.path.join(skills, "discipline", "judgment")),
            "harness_test_suite": bundle_hash(os.path.join(skills, "harness"), "suite"),
        },
        "hash_method": (f"{HASH_REL} — allowlist、路徑無關（相對路徑+內容 hash）、"
                        f"排除未列出路徑與 .DS_Store；skill 模式傳 skill 目錄，suite 模式傳 collection 目錄"),
        "totals": {
            "fixtures": len(rows),
            "routing_pass": sum(1 for r in rows if r["routing"] == "PASS"),
            "contract_pass": sum(1 for r in rows if r["contract"] == "PASS"),
        },
        "results": [{"id": r["id"], "category": r["category"], "routing": r["routing"],
                     "routing_detail": r["detail"], "contract": r["contract"],
                     "contract_detail": r["contract_detail"],
                     "triggered": r["triggered"]} for r in rows],
    }
    jpath = os.path.join(rundir, run_id + ".json")
    json.dump(doc, open(jpath, "w"), ensure_ascii=False, indent=2)

    def cell(v):
        return "—" if v is None else str(v)

    banner = ([f"> **本輪不構成契約證據（run_status: INVALID）。** {reason}", ""]
              if not evidence else [])
    md = [f"# harness run {run_id}", ""] + banner + [
          f"- 狀態：**{status}**",
          f"- Claude Code 版本：{cell(doc['claude_code_version'])}",
          f"- 受測 model：{cell(doc['subject_model'])}　judge model：{cell(doc['judge_model'])}",
          f"- 耗時：{cell(dur)} 秒　CLI 失敗：{cell(doc['cli_failed'])} 筆",
          f"- session 數：preflight {cost['preflight_sessions']}／受測 {cost['subject_sessions']}"
          f"／judge {cost['judge_sessions']}",
          f"- 成本 USD：preflight {cell(cost['preflight_usd'])}／受測 {cell(cost['subject_usd'])}"
          f"／judge {cell(cost['judge_usd'])}／"
          f"合計 {cell(cost['total_usd'])}　（null 表示該來源未回報，未以推估補完）",
          "", "## bundle hashes", "",
          "| bundle | sha256 |", "|---|---|"]
    for k, v in doc["hashes"].items():
        md.append(f"| `{k}` | `{cell(v)}` |")
    md += ["", f"重算方式：`{HASH_REL} <目錄> [skill|suite]`", "",
           "## 逐筆判定", "",
           "| fixture | 類別 | routing | contract | 觸發 | 說明 |", "|---|---|---|---|---|---|"]
    for r in doc["results"]:
        detail = (r["routing_detail"] or r["contract_detail"] or "").replace("|", "/")
        md.append(f"| `{r['id']}` | {r['category']} | {r['routing']} | {r['contract']} | "
                  f"{','.join(r['triggered']) or '（無）'} | {detail} |")
    open(os.path.join(rundir, run_id + ".md"), "w").write("\n".join(md) + "\n")
    print(f"  run record: {jpath}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2], *sys.argv[3:]))
