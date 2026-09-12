#!/usr/bin/env python3
"""ledger_check_selftest — 兩支 checker 的正向與負向案例。

**每個案例同時核對 exit code 與 error code。** 只比對 exit code 不夠：
案例可能因為另一條 invariant 被攔下而「因錯誤的原因通過」。這實際發生過——
舊版的「前綴模稜兩可」案例其實兩個 hash 前綴並不相同，它是因為漏列第二個值
才回 1，ambiguity 分支從未被執行，而測試顯示綠燈。

**負向案例是本檔的重點。** checker 的第一版把 blocked 定義成 active-released，
互斥與覆蓋檢查恆真，而當時 34 個案例全數通過。因此每項 invariant 都必須有一個
能讓它失敗、且**命中該 invariant 自己的 error code** 的案例。

用合成 fixture，不依賴 repo 內的正式文件——在 marker 尚未落地前即可完整跑綠。
"""

import io
import json
import os
import re
import shutil
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ledger_check          # noqa: E402
import run_domain_check      # noqa: E402

HA, HB, HC = "a" * 64, "b" * 64, "c" * 64
SCHEMA = "v6"
DOMAINS = ["skill_x", "fixtures"]

SUMMARY = """<!-- BEGIN ledger:summary -->
另有 `NOT_DONE` 1 筆待修，`NEEDS_EVIDENCE` 1 筆待證。
<!-- END ledger:summary -->"""

ACTIVE = """<!-- BEGIN ledger:active -->
| ID | fixture | dimension | proposed classification | 阻擋於 | required_action | Owner disposition | action status |
|---|---|---|---|---|---|---|---|
| KI-01 | `f-a` | contract | `fixture_invalid` | — | 改 fixture 並重跑 | FIX_FIXTURE | DONE |
| KI-02 | `f-a` | contract | `skill_defect`（由 X 改判） | — | 改 SKILL.md | FIX_SKILL | NOT_DONE |
| KI-03 | `f-b` | routing | `stochastic_known_issue` | — | 容許 | ACCEPT_AS_KNOWN | N/A |
| KI-05 | `f-c` | routing | `harness_error` | — | 3/3 重跑 | NEEDS_EVIDENCE | N/A |
<!-- END ledger:active -->"""

RETIRED = """<!-- BEGIN ledger:retired -->
| ID | 去向 | 說明 |
|---|---|---|
| KI-04 | **併入 KI-01** | 非獨立缺陷 |
<!-- END ledger:retired -->"""

DIST = """<!-- BEGIN ledger:distribution -->
| disposition | 筆數 | ID | action status |
|---|---|---|---|
| `FIX_FIXTURE` | 1 | KI-01 | `DONE` 1 |
| `FIX_SKILL` | 1 | KI-02 | `NOT_DONE` 1 |
| `ACCEPT_AS_KNOWN` | 1 | KI-03 | `N/A` 1 |
| `NEEDS_EVIDENCE` | 1 | KI-05 | `N/A` 1 |
| `PENDING` | 0 | — | — |

合計 4 筆。
<!-- END ledger:distribution -->"""

GATE = """<!-- BEGIN ledger:gate-released -->
個別放行（2 筆）。逐筆依據見 ledger 對應列，此處不重列。
IDs: KI-01、KI-03
<!-- END ledger:gate-released -->

<!-- BEGIN ledger:gate-blocked -->
仍擋住。
IDs: KI-02、KI-05
<!-- END ledger:gate-blocked -->

<!-- BEGIN ledger:gate-totals -->
2 + 2 = 4，與 active ledger 筆數相符。
<!-- END ledger:gate-totals -->"""

FREEZE = f"""<!-- BEGIN ledger:freeze -->
| domain | 綁定值 | 綁定輪次 | 現算 | 來源 |
|---|---|---|---|---|
| `skill_x` | `{HA}` | `r1`、`r2`、`r3` | 相符 | 某處 |
| `fixtures` | `{HB}` | `r1`、`r2` | 相符 | 某處 |
| `fixtures` | `{HC}` | `r3` | 相符 | 某處 |
<!-- END ledger:freeze -->"""

STATUS = """歷史段（不該被解析）：合計 99 筆、`DONE` 7、9 + 9 = 18。

<!-- BEGIN status:current-summary -->
分佈 `FIX_FIXTURE` 1／`FIX_SKILL` 1／`ACCEPT_AS_KNOWN` 1／`NEEDS_EVIDENCE` 1／`PENDING` 0。
現況：`DONE` 1、`NOT_DONE` 1、`N/A` 2。放行 2、阻擋 2，2 + 2 = 4。
<!-- END status:current-summary -->"""

GOOD_RUNS = {
    "r1": {"skill_x": HA, "fixtures": HB},
    "r2": {"skill_x": HA, "fixtures": HB},
    "r3": {"skill_x": HA, "fixtures": HC},
}


def known_doc(summary=SUMMARY, active=ACTIVE, retired=RETIRED,
              dist=DIST, gate=GATE, freeze=FREEZE):
    return ("# 合成 fixture\n\n歷史段：舊表曾記 合計 99 筆、`DONE` 7、5 + 5 = 10。\n\n"
            + "\n\n".join([summary, active, retired, dist, gate, freeze]) + "\n")


class Case:
    def __init__(self, tmp):
        self.tmp = tmp

    def write(self, known=None, status=None):
        k = os.path.join(self.tmp, "KNOWN.md")
        s = os.path.join(self.tmp, "STATUS.md")
        open(k, "w", encoding="utf-8").write(known if known is not None else known_doc())
        open(s, "w", encoding="utf-8").write(status if status is not None else STATUS)
        return k, s

    def runs(self, spec, schema=SCHEMA, run_id=None):
        dirs = []
        for rid, hashes in spec.items():
            d = os.path.join(self.tmp, "runs", rid)
            os.makedirs(d, exist_ok=True)
            json.dump({"run_id": rid if run_id is None else run_id,
                       "hashes": hashes, "hash_schema": schema},
                      open(os.path.join(d, f"{rid}.json"), "w"))
            dirs.append(d)
        return dirs


def run(fn, *a):
    """回傳 (exit code, 出現過的 error code 集合)。"""
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        rc = fn(*a)
    return rc, set(re.findall(r"\[([A-Z_]+)\]", buf.getvalue()))


def main():
    results = []

    def case(name, expect_rc, expect_codes, fn, only=False):
        want = {expect_codes} if isinstance(expect_codes, str) else set(expect_codes)
        tmp = tempfile.mkdtemp(prefix="ledgerchk-")
        try:
            rc, codes = fn(Case(tmp))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        miss = want - codes
        extra = (codes - want) if only else set()
        ok = rc == expect_rc and not miss and not extra
        results.append(ok)
        detail = f"rc={rc}"
        if miss:
            detail += f" 缺 code {sorted(miss)}"
        if extra:
            detail += f" 多出 code {sorted(extra)}"
        if not want and codes:
            detail += f" 意外出現 code {sorted(codes)}"
            ok = ok and not codes
            results[-1] = ok
        print(f"  {'ok  ' if ok else 'FAIL'} {name}（預期 rc={expect_rc}"
              f"{'、code ' + '+'.join(sorted(want)) if want else '、無 code'}；{detail}）")

    def L(c, **kw):
        k, s = c.write(**kw)
        return run(ledger_check.main, ["--known-issues", k, "--status", s])

    def D(c, runs=None, known=None, prefix=False, domains=None, schema=SCHEMA,
          run_schema=SCHEMA, run_id=None):
        k, _ = c.write(known=known)
        dirs = c.runs(GOOD_RUNS if runs is None else runs, schema=run_schema, run_id=run_id)
        argv = ["--known-issues", k, "--hash-schema", schema]
        for d in dirs:
            argv += ["--run", d]
        for d in (DOMAINS if domains is None else domains):
            argv += ["--required-domain", d]
        if prefix:
            argv.append("--allow-prefix")
        return run(run_domain_check.main, argv)


    def Draw(c, argv_extra, known=None, runs=None, make=None):
        """直接組 argv，供 CLI／IO 層的案例使用。"""
        k, _ = c.write(known=known)
        dirs = c.runs(GOOD_RUNS if runs is None else runs) if make is None else make(c)
        argv = ["--known-issues", k, "--hash-schema", SCHEMA]
        for d in dirs:
            argv += ["--run", d]
        for d in DOMAINS:
            argv += ["--required-domain", d]
        return run(run_domain_check.main, argv + argv_extra)

    print("正向（必須 rc=0 且完全沒有 error code）")
    case("ledger_check 一致的文件", 0, [], lambda c: L(c))
    case("run_domain_check 一致的綁定", 0, [], lambda c: D(c))
    case("歷史段的錯誤數字不被解析", 0, [],
         lambda c: L(c, status="合計 99 筆、`DONE` 7、9 + 9 = 18\n\n" + STATUS))
    case("欄內 \\| 轉義可正確解析", 0, [],
         lambda c: L(c, known=known_doc(active=ACTIVE.replace(
             "| 改 fixture 並重跑 |", r"| 改 fixture \| 並重跑 |"))))
    case("--allow-prefix 下的縮寫", 0, [],
         lambda c: D(c, prefix=True, known=known_doc(freeze=FREEZE
                                                     .replace(HA, HA[:8])
                                                     .replace(HB, HB[:8])
                                                     .replace(HC, HC[:8]))))

    print("\n負向 — marker 與格式（rc=2）")
    case("1 marker 缺失", 2, "E_MARKER_MISSING",
         lambda c: L(c, known=known_doc().replace("<!-- BEGIN ledger:gate-totals -->", "")))
    case("2 marker 重複", 2, "E_MARKER_DUP",
         lambda c: L(c, known=known_doc() +
                     "\n<!-- BEGIN ledger:summary -->\n`DONE` 1\n<!-- END ledger:summary -->\n"))
    case("3 malformed row", 2, "E_ROW_MALFORMED",
         lambda c: L(c, known=known_doc(active=ACTIVE.replace(
             "| KI-03 | `f-b` | routing | `stochastic_known_issue` | — | 容許 | ACCEPT_AS_KNOWN | N/A |",
             "| KI-03 | `f-b` | routing | ACCEPT_AS_KNOWN | N/A |"))))
    case("4 header 不符", 2, "E_HEADER_MISMATCH",
         lambda c: L(c, known=known_doc(active=ACTIVE.replace("| ID | fixture |", "| fixture | ID |"))))
    case("5 分隔列欄數錯誤", 2, "E_SEPARATOR_BAD",
         lambda c: L(c, known=known_doc(active=ACTIVE.replace(
             "|---|---|---|---|---|---|---|---|", "|---|---|---|"))))
    case("6 canonical token 缺失", 2, "E_CANON_AMBIGUOUS",
         lambda c: L(c, known=known_doc(active=ACTIVE.replace("`fixture_invalid`", "下游，非獨立缺陷"))))
    case("7 canonical token 前有文字", 2, "E_CANON_AMBIGUOUS",
         lambda c: L(c, known=known_doc(active=ACTIVE.replace("| `fixture_invalid` |",
                                                              "| 下游 `fixture_invalid` |"))))
    case("8 缺少「合計 N 筆」", 2, "E_TOTAL_MISSING",
         lambda c: L(c, known=known_doc(dist=DIST.replace("合計 4 筆。", "總數若干。"))))
    case("9 gate totals 缺算式", 2, "E_EQUATION_MISSING",
         lambda c: L(c, known=known_doc(gate=GATE.replace("2 + 2 = 4，", ""))))
    case("10 STATUS 缺算式", 2, "E_EQUATION_MISSING",
         lambda c: L(c, status=STATUS.replace("2 + 2 = 4", "見上表")))
    case("11 開頭摘要無可檢查宣稱", 2, "E_SUMMARY_NO_CLAIM",
         lambda c: L(c, known=known_doc(summary=SUMMARY.replace(
             "另有 `NOT_DONE` 1 筆待修，`NEEDS_EVIDENCE` 1 筆待證。", "摘要從略。"))))
    case("12 gate 缺少 IDs: 行", 2, "E_GATE_IDS_LINE",
         lambda c: L(c, known=known_doc(gate=GATE.replace("IDs: KI-01、KI-03", "略"))))
    case("12b gate 有兩行 IDs:", 2, "E_GATE_IDS_LINE",
         lambda c: L(c, known=known_doc(gate=GATE.replace(
             "IDs: KI-01、KI-03", "IDs: KI-01\nIDs: KI-03"))))
    case("12c gate ID 清單 grammar 不合", 2, "E_ID_LIST_FORMAT",
         lambda c: L(c, known=known_doc(gate=GATE.replace("IDs: KI-01、KI-03",
                                                          "IDs: KI-01, KI-03"))))

    print("\n負向 — ID invariant（rc=1）")
    case("13 active ID 重複", 1, "E_ACTIVE_DUP",
         lambda c: L(c, known=known_doc(active=ACTIVE.replace("| KI-05 |", "| KI-03 |"))))
    case("14 retired ID 重複", 1, "E_RETIRED_DUP",
         lambda c: L(c, known=known_doc(retired=RETIRED.replace(
             "| KI-04 | **併入 KI-01** | 非獨立缺陷 |",
             "| KI-04 | **併入 KI-01** | 非獨立缺陷 |\n| KI-04 | **併入 KI-01** | 重複 |"))))
    case("15 active 與 retired 重疊", 1, "E_ID_OVERLAP",
         lambda c: L(c, known=known_doc(retired=RETIRED.replace("| KI-04 |", "| KI-03 |"))))
    case("16 retired target 不存在", 1, "E_RETIRED_TARGET",
         lambda c: L(c, known=known_doc(retired=RETIRED.replace("併入 KI-01", "併入 KI-99"))))
    case("17 retired 循環", 1, "E_RETIRED_CYCLE",
         lambda c: L(c, known=known_doc(retired=RETIRED.replace(
             "| KI-04 | **併入 KI-01** | 非獨立缺陷 |",
             "| KI-04 | **併入 KI-06** | x |\n| KI-06 | **併入 KI-04** | y |"))))
    case("18 聯集缺號", 1, "E_ID_GAP",
         lambda c: L(c, known=known_doc(retired=RETIRED.replace("| KI-04 |", "| KI-06 |"))))

    print("\n負向 — gate 具名集合（rc=1；恆真檢查會漏掉這些）")
    case("19 放行集合少列", 1, "E_GATE_RELEASED_MISMATCH",
         lambda c: L(c, known=known_doc(gate=GATE.replace("IDs: KI-01、KI-03", "IDs: KI-01")
                                        .replace("IDs: KI-02、KI-05", "IDs: KI-02、KI-05、KI-03"))))
    case("20 阻擋集合多列", 1, "E_GATE_BLOCKED_MISMATCH",
         lambda c: L(c, known=known_doc(gate=GATE.replace("IDs: KI-02、KI-05", "IDs: KI-02、KI-05、KI-01"))))
    case("21 同一 ID 同列兩側", 1, "E_GATE_OVERLAP",
         lambda c: L(c, known=known_doc(gate=GATE.replace("IDs: KI-02、KI-05", "IDs: KI-02、KI-05、KI-03"))))
    case("22 漏列 ID（不覆蓋 active）", 1, "E_GATE_UNCOVERED",
         lambda c: L(c, known=known_doc(gate=GATE.replace("IDs: KI-02、KI-05", "IDs: KI-02"))))
    case("23 gate 列出不存在的 ID", 1, "E_GATE_GHOST",
         lambda c: L(c, known=known_doc(gate=GATE.replace("IDs: KI-02、KI-05", "IDs: KI-02、KI-05、KI-77"))))
    case("24 gate 算式不符", 1, "E_GATE_TOTALS",
         lambda c: L(c, known=known_doc(gate=GATE.replace("2 + 2 = 4", "3 + 1 = 4"))))

    print("\n負向 — 值域、分佈與跨文件同步（rc=1）")
    case("25 unknown classification", 1, "E_CLASS_UNKNOWN",
         lambda c: L(c, known=known_doc(active=ACTIVE.replace("`harness_error`",
                                                              "`downstream_resolved`"))))
    case("26 只違反相容性（其餘全部同步）", 1, "E_COMPAT",
         lambda c: L(c,
                     known=known_doc(
                         active=ACTIVE.replace("| NEEDS_EVIDENCE | N/A |", "| NEEDS_EVIDENCE | DONE |"),
                         dist=DIST.replace("| `NEEDS_EVIDENCE` | 1 | KI-05 | `N/A` 1 |",
                                           "| `NEEDS_EVIDENCE` | 1 | KI-05 | `DONE` 1 |")),
                     status=STATUS.replace("`DONE` 1、`NOT_DONE` 1、`N/A` 2",
                                           "`DONE` 2、`NOT_DONE` 1、`N/A` 1")), only=True)
    case("27 distribution 筆數不符", 1, "E_DIST_COUNT",
         lambda c: L(c, known=known_doc(dist=DIST.replace("| `FIX_SKILL` | 1 |",
                                                          "| `FIX_SKILL` | 2 |"))))
    case("28 distribution 列重複", 1, "E_DIST_DUP_ROW",
         lambda c: L(c, known=known_doc(dist=DIST.replace(
             "| `PENDING` | 0 | — | — |",
             "| `PENDING` | 0 | — | — |\n| `FIX_SKILL` | 1 | KI-02 | `NOT_DONE` 1 |"))))
    case("29 筆數>0 卻未列 ID", 1, "E_DIST_IDS_EMPTY",
         lambda c: L(c, known=known_doc(dist=DIST.replace("| `FIX_SKILL` | 1 | KI-02 |",
                                                          "| `FIX_SKILL` | 1 | — |"))))
    case("29b ID 清單非空但錯誤", 1, "E_DIST_IDS",
         lambda c: L(c, known=known_doc(dist=DIST.replace("| `FIX_SKILL` | 1 | KI-02 |",
                                                          "| `FIX_SKILL` | 1 | KI-03 |"))))
    case("30 缺 disposition 列", 1, "E_DIST_MISSING_ROW",
         lambda c: L(c, known=known_doc(dist=DIST.replace("| `PENDING` | 0 | — | — |\n", ""))))
    case("31 未宣稱應有的 action status", 1, "E_DIST_ACTION_MISSING",
         lambda c: L(c, known=known_doc(dist=DIST.replace("| KI-02 | `NOT_DONE` 1 |", "| KI-02 | — |"))))
    case("32 開頭摘要數字錯誤", 1, "E_SUMMARY_MISMATCH",
         lambda c: L(c, known=known_doc(summary=SUMMARY.replace("`NOT_DONE` 1", "`NOT_DONE` 9"))),
         only=True)
    case("33 current summary 錯誤但歷史段正確", 1, "E_STATUS_EQUATION",
         lambda c: L(c, status="正確的歷史段：2 + 2 = 4、`DONE` 1、`NOT_DONE` 1、`N/A` 2\n\n" +
                     STATUS.replace("2 + 2 = 4", "3 + 1 = 4")), only=True)
    case("34 STATUS action 計數不同步", 1, "E_STATUS_MISMATCH",
         lambda c: L(c, status=STATUS.replace("`DONE` 1、`NOT_DONE` 1", "`DONE` 2、`NOT_DONE` 0")),
         only=True)
    case("35 STATUS 缺 disposition 數字", 1, "E_STATUS_MISSING",
         lambda c: L(c, status=STATUS.replace("／`NEEDS_EVIDENCE` 1", "")), only=True)
    case("36 STATUS 缺 action 數字", 1, "E_STATUS_MISSING",
         lambda c: L(c, status=STATUS.replace("、`N/A` 2", "")), only=True)

    print("\n負向 — run domain")
    case("37 空 run 集", 2, "E_RUNSET_EMPTY", lambda c: D(c, runs={}))
    case("38 record 缺 hashes", 2, "E_RUN_HASHES_MISSING", lambda c: (
        c.write(),
        os.makedirs(os.path.join(c.tmp, "runs", "rx"), exist_ok=True),
        json.dump({"run_id": "rx", "hash_schema": SCHEMA},
                  open(os.path.join(c.tmp, "runs", "rx", "rx.json"), "w")),
        run(run_domain_check.main,
            ["--known-issues", os.path.join(c.tmp, "KNOWN.md"), "--hash-schema", SCHEMA,
             "--required-domain", "skill_x", "--run", os.path.join(c.tmp, "runs", "rx")]))[-1])
    case("38b record 的 run_id 與目錄名不符", 2, "E_RUN_ID_MISMATCH",
         lambda c: D(c, run_id="別的名字"))
    case("39 預設模式下使用縮寫", 2, "E_FREEZE_HASH_CELL",
         lambda c: D(c, known=known_doc(freeze=FREEZE.replace(HA, HA[:8]))))
    case("39b 合法 hash 後接殘留字串", 2, "E_FREEZE_HASH_CELL",
         lambda c: D(c, known=known_doc(freeze=FREEZE.replace(
             f"| `{HA}` |", f"| `{HA}` deadbeef |"))))
    case("39c 一格內兩個完整 hash", 2, "E_FREEZE_HASH_CELL",
         lambda c: D(c, known=known_doc(freeze=FREEZE.replace(
             f"| `{HB}` | `r1`、`r2` |", f"| `{HB}`／`{HC}` | `r1`、`r2` |"))))
    case("40 freeze 重複 (domain,值) 列", 2, "E_FREEZE_DUP_ROW",
         lambda c: D(c, known=known_doc(freeze=FREEZE.replace(
             "<!-- END ledger:freeze -->",
             f"| `skill_x` | `{HA}` | `r1` | 相符 | 重複 |\n<!-- END ledger:freeze -->"))))
    case("41 freeze 綁定輪次欄為空", 2, "E_FREEZE_RUNS_MISSING",
         lambda c: D(c, known=known_doc(freeze=FREEZE.replace("| `r1`、`r2`、`r3` |", "|  |"))))
    case("43 record hash 格式錯誤", 1, "E_HASH_FORMAT",
         lambda c: D(c, runs={"r1": {"skill_x": "ZZZZ", "fixtures": HB},
                              "r2": {"skill_x": HA, "fixtures": HB},
                              "r3": {"skill_x": HA, "fixtures": HC}}))
    case("44 hash_schema 不符契約", 1, "E_SCHEMA_MISMATCH", lambda c: D(c, run_schema="v5"))
    case("45 所有 record 同時漏契約 domain", 1, "E_RUN_DOMAIN_MISSING",
         lambda c: D(c, runs={k: {"skill_x": v["skill_x"]} for k, v in GOOD_RUNS.items()},
                     known=known_doc(freeze=FREEZE.split("| `fixtures`")[0] +
                                     "<!-- END ledger:freeze -->")))
    case("46 凍結清單漏列 domain", 1, "E_FREEZE_DOMAIN_MISSING",
         lambda c: D(c, known=known_doc(freeze=FREEZE.replace(
             f"| `fixtures` | `{HB}` | `r1`、`r2` | 相符 | 某處 |\n"
             f"| `fixtures` | `{HC}` | `r3` | 相符 | 某處 |\n", ""))))
    case("47 凍結清單多出 domain", 1, "E_FREEZE_DOMAIN_EXTRA",
         lambda c: D(c, known=known_doc(freeze=FREEZE.replace(
             "<!-- END ledger:freeze -->",
             f"| `ghost` | `{'d' * 64}` | `r1` | 相符 | 某處 |\n<!-- END ledger:freeze -->"))))
    case("48 多餘的歷史值", 1, "E_FREEZE_VALUE_UNKNOWN",
         lambda c: D(c, known=known_doc(freeze=FREEZE.replace(
             "<!-- END ledger:freeze -->",
             f"| `skill_x` | `{'e' * 64}` | `r0` | 舊值 | 某處 |\n<!-- END ledger:freeze -->"))))
    case("49 多值 domain 漏列其中一值", 1, "E_FREEZE_VALUE_MISSING",
         lambda c: D(c, known=known_doc(freeze=FREEZE.replace(
             f"| `fixtures` | `{HC}` | `r3` | 相符 | 某處 |\n", ""))))
    case("50 兩個 hash 的綁定輪次對調", 1, "E_FREEZE_RUNS_MISMATCH",
         lambda c: D(c, known=known_doc(freeze=FREEZE.replace(
             f"| `fixtures` | `{HB}` | `r1`、`r2` | 相符 | 某處 |\n"
             f"| `fixtures` | `{HC}` | `r3` | 相符 | 某處 |",
             f"| `fixtures` | `{HB}` | `r3` | 相符 | 某處 |\n"
             f"| `fixtures` | `{HC}` | `r1`、`r2` | 相符 | 某處 |"))), only=True)
    case("51 綁定輪次多一個 run", 1, "E_FREEZE_RUNS_MISMATCH",
         lambda c: D(c, known=known_doc(freeze=FREEZE.replace("| `r3` | 相符 |",
                                                             "| `r3`、`r9` | 相符 |"))), only=True)
    case("52 綁定輪次少一個 run", 1, "E_FREEZE_RUNS_MISMATCH",
         lambda c: D(c, known=known_doc(freeze=FREEZE.replace("| `r1`、`r2` | 相符 |",
                                                             "| `r1` | 相符 |"))), only=True)
    # 兩個實際 hash 共用同一個 8 字元前綴，清單以該前綴列出 → 必須命中 ambiguity。
    # 舊版此案例的兩個 hash 前綴其實不同，是因為漏列第二個值才回 1，
    # ambiguity 分支從未被執行——只驗 exit code 看不出來。
    case("53 --allow-prefix 下前綴真的模稜兩可", 1, "E_HASH_PREFIX_AMBIGUOUS",
         lambda c: D(c, prefix=True,
                     runs={"r1": {"skill_x": HA, "fixtures": "abababab" + "1" * 56},
                           "r2": {"skill_x": HA, "fixtures": "abababab" + "2" * 56}},
                     known=known_doc(freeze=FREEZE
                                     .replace("`r1`、`r2`、`r3`", "`r1`、`r2`")
                                     .replace(f"| `fixtures` | `{HB}` | `r1`、`r2` | 相符 | 某處 |\n"
                                              f"| `fixtures` | `{HC}` | `r3` | 相符 | 某處 |",
                                              "| `fixtures` | `abababab` | `r1`、`r2` | 相符 | 某處 |")
                                     .replace(HA, HA[:8]))))

    print("\n負向 — 清單重複項（Codex 注入的三個反例；集合化前必須拒絕）")
    case("54 distribution ID 清單重複", 2, "E_DIST_ID_DUP",
         lambda c: L(c, known=known_doc(dist=DIST.replace("| `FIX_SKILL` | 1 | KI-02 |",
                                                          "| `FIX_SKILL` | 1 | KI-02、KI-02 |"))))
    case("55 gate released ID 重複", 2, "E_GATE_ID_DUP",
         lambda c: L(c, known=known_doc(gate=GATE.replace("IDs: KI-01、KI-03",
                                                          "IDs: KI-01、KI-03、KI-03"))))
    case("56 freeze 綁定輪次重複", 2, "E_FREEZE_RUN_DUP",
         lambda c: D(c, known=known_doc(freeze=FREEZE.replace(
             "| `r1`、`r2`、`r3` |", "| `r1`、`r2`、`r3`、`r1` |"))))
    case("57 freeze 綁定輪次 grammar 不合", 2, "E_FREEZE_RUNS_FORMAT",
         lambda c: D(c, known=known_doc(freeze=FREEZE.replace("| `r1`、`r2`、`r3` |",
                                                             "| r1, r2, r3 |"))))
    case("58 distribution ID 欄混入非 KI 數字", 2, "E_ID_LIST_FORMAT",
         lambda c: L(c, known=known_doc(dist=DIST.replace("| `FIX_SKILL` | 1 | KI-02 |",
                                                          "| `FIX_SKILL` | 1 | 共 1 筆 |"))))


    print("\n負向 — 補齊未覆蓋的 error code")
    case("59 marker 的 END 在 BEGIN 之前", 2, "E_MARKER_ORDER",
         lambda c: L(c, known=known_doc(summary=SUMMARY
                                        .replace("<!-- BEGIN ledger:summary -->", "@B@")
                                        .replace("<!-- END ledger:summary -->",
                                                 "<!-- BEGIN ledger:summary -->")
                                        .replace("@B@", "<!-- END ledger:summary -->"))))
    case("60 marker 區內沒有表格", 2, "E_TABLE_MISSING",
         lambda c: L(c, known=known_doc(retired="<!-- BEGIN ledger:retired -->\n"
                                                "本輪沒有退役 ID。\n"
                                                "<!-- END ledger:retired -->")))
    case("61 表格只有 header 與分隔列", 2, "E_NO_ROWS",
         lambda c: L(c, known=known_doc(retired="<!-- BEGIN ledger:retired -->\n"
                                                "| ID | 去向 | 說明 |\n|---|---|---|\n"
                                                "<!-- END ledger:retired -->")))
    case("62 active ledger 的 ID 欄格式不合", 2, "E_ID_FORMAT",
         lambda c: L(c, known=known_doc(active=ACTIVE.replace("| KI-05 |", "| KI-5 |"))))
    case("63 disposition 不在值域內", 1, "E_DISP_UNKNOWN",
         lambda c: L(c, known=known_doc(active=ACTIVE.replace("| NEEDS_EVIDENCE | N/A |",
                                                              "| FIX_EVERYTHING | N/A |"))))
    case("64 action status 不在值域內", 1, "E_ACTION_UNKNOWN",
         lambda c: L(c, known=known_doc(active=ACTIVE.replace("| ACCEPT_AS_KNOWN | N/A |",
                                                              "| ACCEPT_AS_KNOWN | MAYBE |"))))
    case("65 distribution 筆數欄非整數", 2, "E_DIST_COUNT_CELL",
         lambda c: L(c, known=known_doc(dist=DIST.replace("| `PENDING` | 0 |", "| `PENDING` | 零 |"))))
    case("66 distribution 的 disposition 不在值域內", 1, "E_DIST_DISP_UNKNOWN",
         lambda c: L(c, known=known_doc(dist=DIST.replace("| `PENDING` | 0 | — | — |",
                                                          "| `FIX_UNKNOWN` | 0 | — | — |"))))
    case("67 distribution 合計數字錯誤", 1, "E_DIST_TOTAL",
         lambda c: L(c, known=known_doc(dist=DIST.replace("合計 4 筆。", "合計 9 筆。"))), only=True)
    case("68 distribution 的 action 計數錯誤", 1, "E_DIST_ACTION",
         lambda c: L(c, known=known_doc(dist=DIST.replace("| KI-01 | `DONE` 1 |",
                                                          "| KI-01 | `DONE` 5 |"))), only=True)
    case("69 gate 兩側 IDs 皆為空", 2, "E_GATE_EMPTY",
         lambda c: L(c, known=known_doc(gate=GATE.replace("IDs: KI-01、KI-03", "IDs: —")
                                        .replace("IDs: KI-02、KI-05", "IDs: —"))))
    case("70 retired 去向未指向任何 KI-nn", 1, "E_RETIRED_TARGET_COUNT",
         lambda c: L(c, known=known_doc(retired=RETIRED.replace("**併入 KI-01**", "**已刪除**"))))
    case("71 freeze 的 domain 欄非 inline-code", 2, "E_FREEZE_DOMAIN_CELL",
         lambda c: D(c, known=known_doc(freeze=FREEZE.replace("| `skill_x` |", "| skill_x |"))))
    case("72 freeze 同一值被兩列以不同前綴列出", 1, "E_FREEZE_VALUE_DUP",
         lambda c: D(c, prefix=True, known=known_doc(freeze=FREEZE.replace(
             "<!-- END ledger:freeze -->",
             "| `skill_x` | `" + HA[:8] + "` | `r1`、`r2`、`r3` | 相符 | 同值不同前綴 |\n"
             "<!-- END ledger:freeze -->").replace("| `" + HA + "` |", "| `" + HA[:10] + "` |"))))
    case("73 record 有契約未列的 domain", 1, "E_RUN_DOMAIN_EXTRA",
         lambda c: D(c, runs={k: dict(v, ghost=HA) for k, v in GOOD_RUNS.items()}))
    case("74 同一個 run 目錄傳入兩次", 2, "E_RUN_ID_DUP",
         lambda c: Draw(c, [], make=lambda cc: (lambda d: d + d[:1])(cc.runs(GOOD_RUNS))))
    case("75 run 目錄內找不到 record", 2, "E_RUN_RECORD_MISSING",
         lambda c: Draw(c, [], make=lambda cc: cc.runs(GOOD_RUNS) + [
             (os.makedirs(os.path.join(cc.tmp, "runs", "rzz"), exist_ok=True),
              os.path.join(cc.tmp, "runs", "rzz"))[1]]))
    case("76 record 無法解析", 2, "E_RUN_RECORD_PARSE",
         lambda c: Draw(c, [], make=lambda cc: cc.runs(GOOD_RUNS) + [
             (os.makedirs(os.path.join(cc.tmp, "runs", "rbad"), exist_ok=True),
              open(os.path.join(cc.tmp, "runs", "rbad", "rbad.json"), "w").write("{ not json"),
              os.path.join(cc.tmp, "runs", "rbad"))[2]]))
    case("77 檔案不存在", 2, "E_IO", lambda c: (
        c.write(),
        run(ledger_check.main, ["--known-issues", os.path.join(c.tmp, "沒有這個檔.md"),
                                "--status", os.path.join(c.tmp, "STATUS.md")]))[-1])

    # ---- narrative 區的正面表列（2026-09-06 新增）----
    # 這些區原本完全未受解析：實測在 gate-released 補一張表把 KI-03 從
    # ACCEPT_AS_KNOWN 翻成 FIX_SKILL／DONE、在 blocker 表塞入不存在的 ID、
    # 再補一條錯算式，checker 全部回「一致」。以下每一支對應一種當時漏掉的形式。
    case("78 gate 區出現表格（未受解析的現值宣稱）", 2, "E_REGION_TABLE",
         lambda c: L(c, known=known_doc(gate=GATE.replace(
             "IDs: KI-01、KI-03",
             "IDs: KI-01、KI-03\n\n| KI | disposition |\n|---|---|\n| KI-03 | `FIX_SKILL` |"))))
    case("79 gate 散文出現 IDs: 行以外的 KI-nn", 2, "E_REGION_STRAY_ID",
         lambda c: L(c, known=known_doc(gate=GATE.replace(
             "仍擋住。", "仍擋住。另註 KI-99 待處理。"))))
    case("80 gate-totals 出現第二條算式", 2, "E_EQUATION_DUP",
         lambda c: L(c, known=known_doc(gate=GATE.replace(
             "2 + 2 = 4，", "2 + 2 = 4，另記 9 + 99 = 108，"))))
    case("81 released 筆數與推導不符", 1, "E_REGION_COUNT_MISMATCH",
         lambda c: L(c, known=known_doc(gate=GATE.replace(
             "個別放行（2 筆）", "個別放行（9 筆）"))))
    case("82 STATUS 以中文數字寫筆數", 2, "E_REGION_CJK_COUNT",
         lambda c: L(c, status=STATUS.replace("現況：", "合計二十筆。現況：")))
    case("83 STATUS 出現未受檢的 N 筆", 2, "E_REGION_COUNT_FORBIDDEN",
         lambda c: L(c, status=STATUS.replace("現況：", "另有 7 筆待辦。現況：")))
    case("84 summary 散文出現 KI-nn", 2, "E_REGION_STRAY_ID",
         lambda c: L(c, known=known_doc(summary=SUMMARY.replace(
             "另有", "另有（KI-11 除外）"))))
    # 正向：marker 外的歷史數字不得因新規則而誤判。
    # known_doc() 與 STATUS 的檔頭都帶「合計 99 筆」「9 + 9 = 18」「`DONE` 7」。
    case("85 marker 外歷史數字不受影響", 0, set(), lambda c: L(c), only=True)

    bad = results.count(False)
    print(f"\nledger_check_selftest: {len(results)} 案例，"
          f"{'全部通過' if not bad else str(bad) + ' 項未達預期'}")
    # 機讀完成摘要：必須是最後一行，且恰好出現一次。
    # mutation runner 靠它分辨「跑完且有案例失敗」與「跑到一半就崩潰」——
    # 只數 stdout 裡的 FAIL 行，會把「先失敗、後 crash」誤判成 killed。
    print(f"SELFTEST_RESULT total={len(results)} failed={bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
