#!/usr/bin/env python3
"""ledger_check_mutants — 可重現的 mutation runner。

selftest 全綠**不代表檢查有效**：checker 的第一版把 blocked 定義成 active-released，
互斥與覆蓋檢查恆真，而當時 34 個案例全數通過。

本檔把「停用某項檢查後，至少有一個案例會失敗」變成可重跑的斷言，
而不是實作者口述的紀錄。每個 mutant 宣告預期結果：

* `killed`  — 停用後必須有案例失敗。沒有失敗代表該檢查沒有測試咬得住它。
* `implied` — 停用後不會有案例失敗，因為該檢查被其他檢查**邏輯蘊含**。
  這類 mutant 必須附理由；它們是訊息品質，不是獨立偵測能力。

**mutant 必須先通過編譯檢查**——語法壞掉的 mutant 會讓 selftest 直接崩潰，
看起來像「0 個案例失敗」，那是無效測試而不是漏檢。

exit code：0 全部符合宣告／1 有 mutant 不符宣告／2 使用方式或 mutant 無效。
"""

import os
import pathlib
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ["ledger_check.py", "run_domain_check.py", "ledger_check_selftest.py"]

# (名稱, [(檔案, 原字串, 取代字串), ...], 預期, 理由)
# 一個 mutant 可以是多處替換：只改常數卻不改呼叫端，等於沒有真正弱化該檢查。
MUTANTS = [
    # ---- narrative 區的正面表列（2026-09-06 新增）----
    # 每一支都對應第 5 次驗收實測漏檢的一種形式。
    ('equation 改回 re.search（只取第一條算式）', [('ledger_check.py', '    ms = re.findall(r"(\\d+)\\s*\\+\\s*(\\d+)\\s*=\\s*(\\d+)", block)', '    ms = [m for m in [re.search(r"(\\d+)\\s*\\+\\s*(\\d+)\\s*=\\s*(\\d+)", block)] if m]\n    ms = [m.groups() for m in ms]')], 'killed', ''),
    ('narrative 區表格檢查停用', [('ledger_check.py', '    if any(l.strip().startswith("|") for l in lines):', '    if False:')], 'killed', ''),
    ('narrative 區散文 KI-nn 檢查停用', [('ledger_check.py', '    if stray:', '    if False:')], 'killed', ''),
    ('narrative 區中文數字檢查停用', [('ledger_check.py', '    if cjk:', '    if False:')], 'killed', ''),
    ('narrative 區筆數比對整段停用', [('ledger_check.py', '    if expect is None:', '    if False:\n        pass\n    elif False:')], 'killed', ''),
    ('narrative guard 不扣除已消費的 `LABEL` N（殘餘模型失效）', [('ledger_check.py', '    residue = re.sub(r"`[A-Z_/]+`\\s*\\d+", "", block)', '    residue = block')], 'killed', ''),
    ('gate blocked 改回 active-released（恆真）', [('ledger_check.py', 'stated_blk = gate_ids(blk_block, known_path, "gate-blocked", "E_GATE_ID_DUP")', 'stated_blk = (set(active) - stated_rel)')], 'killed', ''),
    ('required domain 改由 record 聯集推導', [('run_domain_check.py', '    required = set(required)', '    required = set()\n    for _r, (_h, _s) in runs.items(): required |= set(_h)')], 'killed', ''),
    ('忽略 freeze 綁定輪次', [('run_domain_check.py', '            if stated_runs != actual[v]:', '            if False:')], 'killed', ''),
    ('distribution 不比對 ID 清單', [('ledger_check.py', '        elif ids != real:', '        elif False:')], 'killed', ''),
    ('不檢查 disposition/action 相容性', [('ledger_check.py', '        if d in COMPAT and a not in COMPAT[d]:', '        if False:')], 'killed', ''),
    ('開頭摘要不比對', [('ledger_check.py', 'bad("E_SUMMARY_MISMATCH", f"開頭摘要 {k}: 宣稱 {v}，推導 {want}")', 'pass')], 'killed', ''),
    ('STATUS exact presence 取消', [('ledger_check.py', 'bad("E_STATUS_MISSING", f"STATUS 未宣稱 {k}（推導 {want}）")', 'pass')], 'killed', ''),
    ('hash_schema 不比對', [('run_domain_check.py', '        if schema != hash_schema:', '        if False:')], 'killed', ''),
    ('多餘歷史值分支停用', [('run_domain_check.py', '                bad("E_FREEZE_VALUE_UNKNOWN",\n                    f"凍結清單 {d}: 值 {tok[:12]}… 不存在於受驗 run 集（多餘的歷史值）")', '                pass')], 'killed', ''),
    ('prefix ambiguity 分支停用', [('run_domain_check.py', '            if len(hits) > 1:', '            if False:')], 'killed', ''),
    ('run_id 不比對', [('run_domain_check.py', '        if doc.get("run_id") != rid:', '        if False:')], 'killed', ''),
    ('distribution 列重複不報', [('ledger_check.py', '        if d in seen:', '        if False:')], 'killed', ''),
    ('hash cell 錨點與 fullmatch 同時拿掉（＝修正前的 substring 搜尋）', [('run_domain_check.py', 'CELL_FULL = re.compile(r"^`([0-9a-f]{64})`$")\nCELL_PREFIX = re.compile(r"^`([0-9a-f]{8,64})`$")', 'CELL_FULL = re.compile(r"`([0-9a-f]{64})`")\nCELL_PREFIX = re.compile(r"`([0-9a-f]{8,64})`")'), ('run_domain_check.py', 'hm = pat.fullmatch(r[1].strip())', 'hm = pat.search(r[1])')], 'killed', ''),
    ('ID 清單重複不報（改回 findall+set）', [('ledger_check.py', '    dups = sorted({x for x in out if out.count(x) > 1})\n    if dups:\n        raise Fatal(dup_code, f"{path}: {where} 的 ID 清單有重複項：{dups}")', '    pass')], 'killed', ''),
    ('freeze 綁定輪次重複不報', [('run_domain_check.py', '    dups = sorted({x for x in out if out.count(x) > 1})\n    if dups:\n        raise Fatal("E_FREEZE_RUN_DUP",\n                    f"{path}: freeze domain {domain} 的綁定輪次有重複項：{dups}")', '    pass')], 'killed', ''),
    ('gate IDs: 行改回整區 findall', [('ledger_check.py', '    payload = re.sub(r"^\\**IDs\\**\\s*[:：]\\s*", "", hits[0])\n    return set(id_list(payload, path, label, dup_code))', '    return {int(x) for x in re.findall(r"KI-(\\d{2})", block)}')], 'killed', ''),
    ('gate overlap 檢查停用', [('ledger_check.py', '    if stated_rel & stated_blk:', '    if False:')], 'killed', ''),
    ('gate coverage 檢查停用', [('ledger_check.py', '    if A - (stated_rel | stated_blk):', '    if False:')], 'killed', ''),
    ('gate released 比對停用', [('ledger_check.py', '    if stated_rel != derived_rel:', '    if False:')], 'killed', ''),
    ('retired 循環分支停用', [('ledger_check.py', '        if t in retired:', '        if False:')], 'killed', ''),
    ("回歸：先 FAIL 後 runtime crash（runner 必須判 invalid）",
     [("ledger_check.py", "        if d in COMPAT and a not in COMPAT[d]:", "        if False:"),
      ("ledger_check_selftest.py", "    bad = results.count(False)",
       '    raise RuntimeError("injected crash after a failing case")\n'
       "    bad = results.count(False)")],
     "invalid", "child 先印出 FAIL 再崩潰，只數 FAIL 行會誤判為 killed"),
    ("回歸：mutant 完成但結果總數與 baseline 不同（runner 必須判 invalid）",
     [("ledger_check_selftest.py", '    case("30 缺 disposition 列", 1, "E_DIST_MISSING_ROW",\n         lambda c: L(c, known=known_doc(dist=DIST.replace("| `PENDING` | 0 | — | — |\\n", ""))))\n', "")],
     "invalid", "少跑一個案例；總數變了代表 child 沒跑完整輪，killed 判定無意義"),
    ("code 未被任何案例斷言：E_MARKER_ORDER", [('ledger_check.py', '"E_MARKER_ORDER"', '"E_MUTATED"')], "killed",
     "把發出點的 code 換成 sentinel，綁定該 code 的案例必須失敗"),
    ("code 未被任何案例斷言：E_TABLE_MISSING", [('ledger_check.py', '"E_TABLE_MISSING"', '"E_MUTATED"')], "killed",
     "把發出點的 code 換成 sentinel，綁定該 code 的案例必須失敗"),
    ("code 未被任何案例斷言：E_NO_ROWS", [('ledger_check.py', '"E_NO_ROWS"', '"E_MUTATED"')], "killed",
     "把發出點的 code 換成 sentinel，綁定該 code 的案例必須失敗"),
    ("code 未被任何案例斷言：E_ID_FORMAT", [('ledger_check.py', '"E_ID_FORMAT"', '"E_MUTATED"')], "killed",
     "把發出點的 code 換成 sentinel，綁定該 code 的案例必須失敗"),
    ("code 未被任何案例斷言：E_DISP_UNKNOWN", [('ledger_check.py', '"E_DISP_UNKNOWN"', '"E_MUTATED"')], "killed",
     "把發出點的 code 換成 sentinel，綁定該 code 的案例必須失敗"),
    ("code 未被任何案例斷言：E_ACTION_UNKNOWN", [('ledger_check.py', '"E_ACTION_UNKNOWN"', '"E_MUTATED"')], "killed",
     "把發出點的 code 換成 sentinel，綁定該 code 的案例必須失敗"),
    ("code 未被任何案例斷言：E_DIST_COUNT_CELL", [('ledger_check.py', '"E_DIST_COUNT_CELL"', '"E_MUTATED"')], "killed",
     "把發出點的 code 換成 sentinel，綁定該 code 的案例必須失敗"),
    ("code 未被任何案例斷言：E_DIST_DISP_UNKNOWN", [('ledger_check.py', '"E_DIST_DISP_UNKNOWN"', '"E_MUTATED"')], "killed",
     "把發出點的 code 換成 sentinel，綁定該 code 的案例必須失敗"),
    ("code 未被任何案例斷言：E_DIST_TOTAL", [('ledger_check.py', '"E_DIST_TOTAL"', '"E_MUTATED"')], "killed",
     "把發出點的 code 換成 sentinel，綁定該 code 的案例必須失敗"),
    ("code 未被任何案例斷言：E_DIST_ACTION", [('ledger_check.py', '"E_DIST_ACTION"', '"E_MUTATED"')], "killed",
     "把發出點的 code 換成 sentinel，綁定該 code 的案例必須失敗"),
    ("code 未被任何案例斷言：E_GATE_EMPTY", [('ledger_check.py', '"E_GATE_EMPTY"', '"E_MUTATED"')], "killed",
     "把發出點的 code 換成 sentinel，綁定該 code 的案例必須失敗"),
    ("code 未被任何案例斷言：E_RETIRED_TARGET_COUNT", [('ledger_check.py', '"E_RETIRED_TARGET_COUNT"', '"E_MUTATED"')], "killed",
     "把發出點的 code 換成 sentinel，綁定該 code 的案例必須失敗"),
    ("code 未被任何案例斷言：E_FREEZE_DOMAIN_CELL", [('run_domain_check.py', '"E_FREEZE_DOMAIN_CELL"', '"E_MUTATED"')], "killed",
     "把發出點的 code 換成 sentinel，綁定該 code 的案例必須失敗"),
    ("code 未被任何案例斷言：E_FREEZE_VALUE_DUP", [('run_domain_check.py', '"E_FREEZE_VALUE_DUP"', '"E_MUTATED"')], "killed",
     "把發出點的 code 換成 sentinel，綁定該 code 的案例必須失敗"),
    ("code 未被任何案例斷言：E_RUN_DOMAIN_EXTRA", [('run_domain_check.py', '"E_RUN_DOMAIN_EXTRA"', '"E_MUTATED"')], "killed",
     "把發出點的 code 換成 sentinel，綁定該 code 的案例必須失敗"),
    ("code 未被任何案例斷言：E_RUN_ID_DUP", [('run_domain_check.py', '"E_RUN_ID_DUP"', '"E_MUTATED"')], "killed",
     "把發出點的 code 換成 sentinel，綁定該 code 的案例必須失敗"),
    ("code 未被任何案例斷言：E_RUN_RECORD_MISSING", [('run_domain_check.py', '"E_RUN_RECORD_MISSING"', '"E_MUTATED"')], "killed",
     "把發出點的 code 換成 sentinel，綁定該 code 的案例必須失敗"),
    ("code 未被任何案例斷言：E_RUN_RECORD_PARSE", [('run_domain_check.py', '"E_RUN_RECORD_PARSE"', '"E_MUTATED"')], "killed",
     "把發出點的 code 換成 sentinel，綁定該 code 的案例必須失敗"),
    ("code 未被任何案例斷言：E_IO",
     [("ledger_check.py", "無法讀取：[E_IO] {e}", "無法讀取：[E_MUTATED] {e}")], "killed",
     "E_IO 只出現在 main 的訊息字串，改字串即可驗證案例是否綁定它"),
]


CHILD_TIMEOUT = 300
FOOTER = re.compile(r"^SELFTEST_RESULT total=(\d+) failed=(\d+)$", re.M)


def classify(r):
    """把 child 的執行結果分成 ok / invalid。回傳 (status, detail)。

    ok 時 detail = (total, failed)；invalid 時 detail = 原因字串。

    **只數 stdout 裡的 FAIL 行是不夠的**：child 可能先印出一個 FAIL、
    然後在跑完前崩潰，那樣看起來像「殺掉了一個案例」，實際上整輪根本沒跑完。
    因此要求 child 印出恰好一筆機讀完成摘要（且必須是最後一行），
    並讓摘要與人可讀輸出彼此印證：`total` 必須等於 ok 行數加 FAIL 行數。
    """
    hits = FOOTER.findall(r.stdout)
    if len(hits) != 1:
        return "invalid", f"完成摘要出現 {len(hits)} 次（需恰好 1）；child rc={r.returncode}"
    if "Traceback (most recent call last)" in r.stderr:
        return "invalid", f"child 有 traceback；rc={r.returncode}"
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    if not lines or not FOOTER.match(lines[-1]):
        return "invalid", f"完成摘要不是最後一行；rc={r.returncode}"
    total, failed = int(hits[0][0]), int(hits[0][1])
    if total <= 0:
        return "invalid", "摘要 total=0"
    if not 0 <= failed <= total:
        return "invalid", f"摘要 failed={failed} 不在 0..{total} 範圍內"
    n_ok = sum(1 for l in r.stdout.splitlines() if l.startswith("  ok "))
    n_fail = sum(1 for l in r.stdout.splitlines() if l.startswith("  FAIL "))
    if n_ok + n_fail != total:
        return "invalid", (f"摘要 total={total} 與實際結果行數 {n_ok + n_fail}"
                           f"（ok {n_ok}＋FAIL {n_fail}）不符")
    if n_fail != failed:
        return "invalid", f"摘要 failed={failed} 與 stdout 的 FAIL 行數 {n_fail} 不符"
    if failed == 0 and r.returncode != 0:
        return "invalid", f"摘要 failed=0 但 rc={r.returncode}"
    if failed > 0 and r.returncode != 1:
        return "invalid", f"摘要 failed={failed} 但 rc={r.returncode}"
    if r.returncode not in (0, 1):
        return "invalid", f"非預期的 rc={r.returncode}"
    return "ok", (total, failed)


def selfcheck_classify():
    """runner 自身的 fail-closed 邊界測試。

    這些斷言必須是程式的一部分而不是實作者紀錄：`classify()` 是本 runner 唯一
    分辨「child 跑完了」與「child 崩在半路」的地方，它一鬆掉，
    所有 mutant 的 killed 判定就同時失去意義。
    """
    import types

    def mk(n_ok, n_fail, total, failed, rc=None, after="", tb=False, foot=1):
        out = "".join(f"  ok   案例{i}\n" for i in range(n_ok))
        out += "".join(f"  FAIL 案例{i}\n" for i in range(n_fail))
        out += f"SELFTEST_RESULT total={total} failed={failed}\n" * foot
        out += after
        if rc is None:
            rc = 1 if failed else 0
        return types.SimpleNamespace(
            stdout=out, stderr="Traceback (most recent call last)\n" if tb else "", returncode=rc)

    cases = [
        ("缺 footer（先 FAIL 後 crash）", mk(0, 1, 3, 1, rc=1, tb=True, foot=0), "invalid"),
        ("footer 出現兩次", mk(3, 0, 3, 0, foot=2), "invalid"),
        ("failed=0 但 rc=1", mk(3, 0, 3, 0, rc=1), "invalid"),
        ("failed>0 但 rc=0", mk(1, 2, 3, 2, rc=0), "invalid"),
        ("footer 正常但有 traceback", mk(3, 0, 3, 0, tb=True), "invalid"),
        ("非預期 rc", mk(1, 2, 3, 2, rc=137), "invalid"),
        ("total=0", mk(0, 0, 0, 0), "invalid"),
        ("footer 之後仍有輸出", mk(3, 0, 3, 0, after="之後又崩了\n"), "invalid"),
        ("failed 超出 total", mk(0, 9, 5, 9, rc=1), "invalid"),
        ("FAIL 行數與 failed 不符", mk(1, 2, 3, 1, rc=1), "invalid"),
        ("total 大於實際結果數", mk(2, 0, 5, 0), "invalid"),
        ("total 小於實際結果數", mk(5, 0, 3, 0), "invalid"),
        ("正常完成、無失敗", mk(3, 0, 3, 0), "ok"),
        ("正常完成、2 個失敗", mk(1, 2, 3, 2), "ok"),
    ]
    bad = 0
    for name, r, want in cases:
        got, _ = classify(r)
        if got != want:
            print(f"  FAIL classify 自檢：{name} → {got}（預期 {want}）", file=sys.stderr)
            bad += 1
    print(f"  classify 自檢 {len(cases)} 條{'全部通過' if not bad else f'，{bad} 條不符'}")
    return bad


def selfcheck_coverage():
    """每個 checker 會發出的 error code，都必須至少有一個 selftest 案例斷言它。

    2a 的 fresh-context 驗收就是卡在這裡：73 個 code 裡有 19 個沒有任何案例覆蓋。
    那些檢查本身沒壞，壞的是「沒有東西證明它們還活著」——
    這正是本 runner docstring 寫的「沒有失敗代表該檢查沒有測試咬得住它，不得默認」。

    逐條補案例只能修好當下這一次；沒有這個結構性檢查，
    下次新增一個 code 又會悄悄沒有測試。
    """
    here = pathlib.Path(HERE)
    src = "".join((here / f).read_text(encoding="utf-8")
                  for f in ("ledger_check.py", "run_domain_check.py"))
    emitted = set(re.findall(r'"(E_[A-Z_]+)"', src)) | set(re.findall(r"\[(E_[A-Z_]+)\]", src))
    asserted = set(re.findall(r'"(E_[A-Z_]+)"',
                              (here / "ledger_check_selftest.py").read_text(encoding="utf-8")))
    missing = sorted(emitted - asserted)
    stale = sorted(asserted - emitted)
    if missing:
        print(f"  FAIL error code 覆蓋：{len(missing)} 個 code 沒有任何案例斷言："
              f"{missing}", file=sys.stderr)
    if stale:
        print(f"  FAIL error code 覆蓋：{len(stale)} 個案例斷言了 checker 不會發出的 code："
              f"{stale}", file=sys.stderr)
    if not missing and not stale:
        print(f"  error code 覆蓋 {len(emitted)} 個，全部有案例斷言")
    return len(missing) + len(stale)


def run_mutant(name, edits):
    """回傳 (狀態, 失敗案例數)。狀態: ok / anchor / syntax。"""
    tmp = tempfile.mkdtemp(prefix="mutant-")
    try:
        for f in FILES:
            shutil.copy(os.path.join(HERE, f), os.path.join(tmp, f))
        for fname, old, new in edits:
            p = os.path.join(tmp, fname)
            with open(p, encoding="utf-8") as fh:
                src = fh.read()
            if src.count(old) != 1:
                return "anchor", src.count(old)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(src.replace(old, new))
        for f in FILES:
            try:
                py_compile.compile(os.path.join(tmp, f), doraise=True,
                                   cfile=os.path.join(tmp, f + "c"))
            except py_compile.PyCompileError:
                return "syntax", 0
        try:
            r = subprocess.run([sys.executable, "ledger_check_selftest.py"], cwd=tmp,
                               capture_output=True, text=True, timeout=CHILD_TIMEOUT,
                               env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        except subprocess.TimeoutExpired:
            return "invalid", "child 逾時"
        return classify(r)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    if selfcheck_classify():
        print("runner 自身的 fail-closed 邊界壞了，mutant 結果不可信。", file=sys.stderr)
        return 2
    if selfcheck_coverage():
        print("有 error code 缺少案例覆蓋；先補齊再談 mutant 結果。", file=sys.stderr)
        return 2
    # baseline 必須走與 mutant child 完全相同的邊界檢查。
    # 只看 rc 的話，baseline 若崩在半路（rc 剛好是 1、又沒被判 invalid），
    # 後面每個 mutant 的 killed／survived 判定都建立在一個沒跑完的基準上。
    try:
        base = subprocess.run([sys.executable, "ledger_check_selftest.py"], cwd=HERE,
                              capture_output=True, text=True, timeout=CHILD_TIMEOUT,
                              env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    except subprocess.TimeoutExpired:
        print("baseline selftest 逾時。", file=sys.stderr)
        return 2
    b_status, b_detail = classify(base)
    if b_status != "ok":
        print(f"baseline selftest 未正常完成（{b_detail}），mutant 結果不可信。",
              file=sys.stderr)
        return 2
    base_total, b_failed = b_detail
    if b_failed != 0:
        print(f"未 mutate 的 selftest 就有 {b_failed} 個案例失敗，先修好它再跑 mutation。",
              file=sys.stderr)
        return 2
    print(f"  baseline：total={base_total}、failed={b_failed}，邊界檢查通過")

    problems = 0
    for name, edits, expect, why in MUTANTS:
        status, n = run_mutant(name, edits)
        if status == "ok":
            m_total, m_failed = n
            # mutant 只該改變「案例通不通過」，不該改變案例總數。
            # 總數變了代表 child 少跑或多跑了案例，那時 killed/survived 都沒有意義。
            if m_total != base_total:
                status = "invalid"
                n = (f"結果總數 {m_total} 與 baseline {base_total} 不同"
                     f"（mutant 改變了案例數，killed 判定無意義）")
            else:
                n = m_failed
        if status in ("anchor", "syntax", "invalid"):
            reason = {"anchor": f"anchor 命中 {n} 次（需恰好 1）",
                      "syntax": "mutant 語法錯誤，不構成有效測試"}.get(status, str(n))
            good = expect == "invalid"
            print(f"  {'ok  ' if good else '無效'} [{expect:7s}] {name} → 判為 invalid：{reason}")
            if not good:
                problems += 1
            continue
        if expect == "invalid":
            print(f"  FAIL [invalid] {name} → 竟被判為有效（{n} 個案例失敗）")
            print("       ↑ runner 沒能偵測到 child 未正常完成，fail-closed 邊界有缺口。",
                  file=sys.stderr)
            problems += 1
            continue
        killed = n > 0
        good = killed if expect == "killed" else not killed
        tag = "ok  " if good else "FAIL"
        note = f"（{why}）" if expect == "implied" else ""
        print(f"  {tag} [{expect:7s}] {name} → {n} 個案例失敗{note}")
        if not good:
            problems += 1
            if expect == "killed":
                print("       ↑ 停用此檢查沒有任何案例失敗：不是測試沒覆蓋，"
                      "就是它被別的檢查蘊含。兩者都必須處理，不得默認。", file=sys.stderr)

    total = len(MUTANTS)
    k = sum(1 for m in MUTANTS if m[2] == "killed")
    inv = sum(1 for m in MUTANTS if m[2] == "invalid")
    print(f"\nledger_check_mutants: {total} 個 mutant（{k} killed、{inv} invalid、"
          f"{total - k - inv} implied），"
          f"{'全部符合宣告' if not problems else str(problems) + ' 個不符'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
