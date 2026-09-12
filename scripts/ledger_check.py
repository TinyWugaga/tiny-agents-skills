#!/usr/bin/env python3
"""ledger_check — KNOWN-ISSUES.md / STATUS.md 的結構與跨文件一致性檢查。

設計原則（見 scripts/LEDGER-CHECK-SPEC.md）：

* **不硬編任何數字或 ID 清單。** 全部從 active ledger 推導；文件內的彙總數字是
  被檢查的對象，不是檢查的依據。
* **只解析 marker 內的內容。** 兩份文件都保留大量歷史數字，全檔搜尋會發生
  「現值錯了，但歷史段剛好有正確數字而通過」。
* **不得有恆真檢查。** 文件宣稱的集合必須各自獨立解析，再與推導值比對。
* **每個錯誤都有穩定 error code。** selftest 據此確認案例是因為預期的 invariant
  被違反而失敗，而不是碰巧被別條攔下——只比對 exit code 無法分辨這兩者。
* **fail closed。** marker／表格／header 缺失或重複一律 usage error(2)，不靜默跳過。

exit code：0 一致／1 資料不一致／2 輸入、格式或使用方式錯誤。
"""

import argparse
import re
import sys

CLASSIFICATIONS = {
    "fixture_invalid", "skill_defect", "stochastic_known_issue",
    "description_dilution", "harness_error",
}
DISPOSITIONS = {
    "ACCEPT_AS_KNOWN", "FIX_FIXTURE", "FIX_SKILL", "NEEDS_EVIDENCE", "PENDING",
}
ACTIONS = {"DONE", "NOT_DONE", "N/A"}
COMPAT = {
    "ACCEPT_AS_KNOWN": {"N/A"}, "NEEDS_EVIDENCE": {"N/A"}, "PENDING": {"N/A"},
    "FIX_FIXTURE": {"DONE", "NOT_DONE"}, "FIX_SKILL": {"DONE", "NOT_DONE"},
}
RELEASING = {"ACCEPT_AS_KNOWN"}
CONDITIONAL = {"FIX_FIXTURE", "FIX_SKILL"}

ACTIVE_HEADER = ["ID", "fixture", "dimension", "proposed classification",
                 "阻擋於", "required_action", "Owner disposition", "action status"]
RETIRED_HEADER = ["ID", "去向", "說明"]
DIST_HEADER = ["disposition", "筆數", "ID", "action status"]

M_SUMMARY = "ledger:summary"
M_ACTIVE = "ledger:active"
M_RETIRED = "ledger:retired"
M_DIST = "ledger:distribution"
M_RELEASED = "ledger:gate-released"
M_BLOCKED = "ledger:gate-blocked"
M_TOTALS = "ledger:gate-totals"
M_STATUS = "status:current-summary"


class Fatal(Exception):
    """格式／使用方式錯誤 → exit 2。code 供 selftest 精確比對。"""

    def __init__(self, code, msg):
        self.code = code
        super().__init__(msg)


def region(text, name, path):
    b, e = f"<!-- BEGIN {name} -->", f"<!-- END {name} -->"
    nb, ne = text.count(b), text.count(e)
    if nb == 0 or ne == 0:
        raise Fatal("E_MARKER_MISSING", f"{path}: marker {name} 缺失（BEGIN {nb}、END {ne}）")
    if nb > 1 or ne > 1:
        raise Fatal("E_MARKER_DUP", f"{path}: marker {name} 重複（BEGIN {nb}、END {ne}）")
    i, j = text.index(b) + len(b), text.index(e)
    if j < i:
        raise Fatal("E_MARKER_ORDER", f"{path}: marker {name} 的 END 在 BEGIN 之前")
    return text[i:j]


def split_row(line):
    """以未跳脫的 | 切欄；支援 \\| 轉義。"""
    parts = re.split(r"(?<!\\)\|", line.strip())
    if len(parts) < 3 or parts[0].strip() or parts[-1].strip():
        raise Fatal("E_ROW_MALFORMED", f"表格列必須以 | 起訖: {line.strip()[:70]}")
    return [c.strip().replace("\\|", "|") for c in parts[1:-1]]


def parse_table(block, header, path, label):
    lines = [l for l in block.splitlines() if l.strip().startswith("|")]
    if not lines:
        raise Fatal("E_TABLE_MISSING", f"{path}: {label} 區內找不到表格")
    rows = [split_row(l) for l in lines]
    if rows[0] != header:
        raise Fatal("E_HEADER_MISMATCH",
                    f"{path}: {label} header 不符\n  預期 {header}\n  實得 {rows[0]}")
    if len(rows) < 2 or len(rows[1]) != len(header) \
            or not all(re.fullmatch(r":?-{2,}:?", c) for c in rows[1]):
        raise Fatal("E_SEPARATOR_BAD", f"{path}: {label} 的分隔列欄數或格式不合")
    out = []
    for r in rows[2:]:
        if len(r) != len(header):
            raise Fatal("E_ROW_MALFORMED",
                        f"{path}: {label} malformed row（欄數 {len(r)}≠{len(header)}）: {r[:2]}")
        out.append(r)
    if not out:
        raise Fatal("E_NO_ROWS", f"{path}: {label} 沒有資料列")
    return out


def canonical_code(cell, path, ki):
    m = re.search(r"`([^`]+)`", cell)
    if not m:
        raise Fatal("E_CANON_AMBIGUOUS",
                    f"{path}: {ki} 的 classification 無 inline-code token")
    if cell[:m.start()].strip():
        raise Fatal("E_CANON_AMBIGUOUS",
                    f"{path}: {ki} 的 classification 在 canonical token 前有文字："
                    f"{cell[:m.start()].strip()[:40]}")
    return m.group(1)


def ki_num(cell, path, label):
    m = re.fullmatch(r"KI-(\d{2})", cell.strip())
    if not m:
        raise Fatal("E_ID_FORMAT", f"{path}: {label} 的 ID 欄需為 KI-nn: {cell[:30]}")
    return int(m.group(1))


def id_list(cell, path, where, dup_code):
    """KI-nn 清單的欄位 grammar：`、` 分隔；首項須帶 `KI-` 前綴，其後可省略前綴。

    **不得用 findall 掃 token 再轉 set**——那會靜默吃掉重複項，
    而重複本身就是 malformed claim；也會把散文欄位裡順帶提到的 ID 算進來。
    """
    s = cell.strip().replace("*", "").rstrip("。.")
    if s in ("—", "-", "–", ""):
        return []
    out = []
    for i, t in enumerate([x.strip() for x in s.split("、")]):
        m = re.fullmatch(r"KI-(\d{2})", t)
        if not m and i:
            m = re.fullmatch(r"(\d{2})", t)
        if not m:
            raise Fatal("E_ID_LIST_FORMAT",
                        f"{path}: {where} 的 ID 清單第 {i + 1} 項不合 grammar："
                        f"{t[:20]!r}（首項需 KI-nn，其後可為 nn，以、分隔）")
        out.append(int(m.group(1)))
    dups = sorted({x for x in out if out.count(x) > 1})
    if dups:
        raise Fatal(dup_code, f"{path}: {where} 的 ID 清單有重複項：{dups}")
    return out


def gate_ids(block, path, label, dup_code):
    """gate 區必須有恰好一行 `IDs: …` 承載集合本身。

    其餘散文（依據、備註）常會提到別的 KI-nn——整區 findall 會把那些算進集合。
    """
    hits = [l.strip() for l in block.splitlines()
            if re.match(r"^\**IDs\**\s*[:：]", l.strip())]
    if len(hits) != 1:
        raise Fatal("E_GATE_IDS_LINE",
                    f"{path}: {label} 需恰好一行以 `IDs:` 起始的清單（實得 {len(hits)}）")
    payload = re.sub(r"^\**IDs\**\s*[:：]\s*", "", hits[0])
    return set(id_list(payload, path, label, dup_code))


def declared(block):
    out = {}
    for m in re.finditer(r"`([A-Z_/]+)`\s*(\d+)", block):
        out.setdefault(m.group(1), []).append(int(m.group(2)))
    return out


def equation(block, path, label):
    """區內必須恰好一條算式。

    舊版用 `re.search` 只取第一條：在同一區補第二條錯的算式完全不會被發現。
    「取第一個 match」對承載現值的欄位一律是漏檢，不是寬容。
    """
    ms = re.findall(r"(\d+)\s*\+\s*(\d+)\s*=\s*(\d+)", block)
    if not ms:
        raise Fatal("E_EQUATION_MISSING", f"{path}: {label} 區內找不到「a + b = c」算式")
    if len(ms) > 1:
        raise Fatal("E_EQUATION_DUP",
                    f"{path}: {label} 區內有 {len(ms)} 條算式，只允許一條：{ms}")
    return tuple(int(x) for x in ms[0])


CJK_NUM = "零一二三四五六七八九十百"


def narrative_guard(block, path, label, expect, ids_line, bad):
    """narrative 區的**正面表列**：只准出現 checker 讀得懂的計數形式。

    背景：這些區原本放著整張表格與大量散文現值，而 parser 一格都沒讀——
    實測在 gate-released 區把一筆 disposition 從 ACCEPT_AS_KNOWN 翻成
    FIX_SKILL／DONE、在 blocker 表塞進不存在的 KI-99、再補一條
    `9 + 99 = 108`，checker 仍然回「一致」。

    對「承載現值的措辭」做黑名單是自然語言問題，換一種寫法就繞過去。
    因此改成白名單：區內允許的計數形式只有 `IDs:` 行、``LABEL` N`、
    `N 筆` 與算式，這四種都各自被比對；其餘一律 fail closed。
    """
    lines = block.splitlines()
    if any(l.strip().startswith("|") for l in lines):
        raise Fatal("E_REGION_TABLE",
                    f"{path}: {label} 區內不得有表格——表格只屬於 ledger:active／"
                    f"retired／distribution，其餘區的表格不會被解析，等同未受檢的現值宣稱")

    hits = [l for l in lines if re.match(r"^\**IDs\**\s*[:：]", l.strip())]
    stray = []
    for l in lines:
        if ids_line and l in hits:
            continue
        stray += re.findall(r"KI-\d{2}", l)
    if stray:
        where = "只允許出現在 `IDs:` 行" if ids_line else "不得出現"
        raise Fatal("E_REGION_STRAY_ID",
                    f"{path}: {label} 區內的 KI-nn {where}（實得 {sorted(set(stray))}）"
                    f"——散文裡的 ID 不進集合，會變成未受檢的宣稱")

    # `LABEL` N 這種形式由 declared() 消費並逐一比對，先扣掉再看殘餘。
    # 判準是「區內每一個計數都必須被某個 parser 消費」，不是「某些措辭不准出現」——
    # 後者是黑名單，換個寫法就繞過去。
    residue = re.sub(r"`[A-Z_/]+`\s*\d+", "", block)

    cjk = re.findall(rf"[{CJK_NUM}]+\s*筆", residue)
    if cjk:
        raise Fatal("E_REGION_CJK_COUNT",
                    f"{path}: {label} 區內以中文數字表示筆數：{cjk}"
                    f"——請改用阿拉伯數字，否則不受檢查")

    counts = [int(x) for x in re.findall(r"(\d+)\s*筆", residue)]
    if expect is None:
        if counts:
            raise Fatal("E_REGION_COUNT_FORBIDDEN",
                        f"{path}: {label} 區不得直接寫「N 筆」（實得 {counts}）"
                        f"——該區的計數由算式承載，另寫一份就是無人比對的重複宣稱")
    else:
        for c in counts:
            if c != expect:
                bad("E_REGION_COUNT_MISMATCH",
                    f"{label}: 區內宣稱 {c} 筆，推導 {expect} 筆")


def check(known_path, status_path):
    problems, info = [], []

    def bad(code, msg):
        problems.append((code, msg))

    text = open(known_path, encoding="utf-8").read()
    stext = open(status_path, encoding="utf-8").read()

    active_rows = parse_table(region(text, M_ACTIVE, known_path),
                              ACTIVE_HEADER, known_path, "active ledger")
    retired_rows = parse_table(region(text, M_RETIRED, known_path),
                               RETIRED_HEADER, known_path, "retired IDs")
    dist_rows = parse_table(region(text, M_DIST, known_path),
                            DIST_HEADER, known_path, "current distribution")

    active, disp, act = [], {}, {}
    for r in active_rows:
        n = ki_num(r[0], known_path, "active ledger")
        active.append(n)
        cls = canonical_code(r[3], known_path, r[0])
        if cls not in CLASSIFICATIONS:
            bad("E_CLASS_UNKNOWN", f"{r[0]}: classification `{cls}` 不在五值域內")
        d, a = r[6].strip(), r[7].strip()
        if d not in DISPOSITIONS:
            bad("E_DISP_UNKNOWN", f"{r[0]}: disposition `{d}` 不在值域內")
        if a not in ACTIONS:
            bad("E_ACTION_UNKNOWN", f"{r[0]}: action status `{a}` 不在值域內")
        if d in COMPAT and a not in COMPAT[d]:
            bad("E_COMPAT", f"{r[0]}: {d} 與 {a} 不相容（允許 {sorted(COMPAT[d])}）")
        disp[n], act[n] = d, a
    retired = [ki_num(r[0], known_path, "retired IDs") for r in retired_rows]

    # ---------- ID invariant ----------
    if len(set(active)) != len(active):
        bad("E_ACTIVE_DUP",
            f"active ID 重複：{sorted(x for x in set(active) if active.count(x) > 1)}")
    if len(set(retired)) != len(retired):
        bad("E_RETIRED_DUP",
            f"retired ID 重複：{sorted(x for x in set(retired) if retired.count(x) > 1)}")
    if set(active) & set(retired):
        bad("E_ID_OVERLAP", f"active 與 retired 同時含有：{sorted(set(active) & set(retired))}")
    union = sorted(set(active) | set(retired))
    if union and union != list(range(1, max(union) + 1)):
        bad("E_ID_GAP", f"active ∪ retired 非 1..{max(union)} 連續，"
                        f"缺號：{sorted(set(range(1, max(union) + 1)) - set(union))}")

    for r in retired_rows:
        src = ki_num(r[0], known_path, "retired IDs")
        tgt = re.findall(r"KI-(\d{2})", r[1])
        if len(tgt) != 1:
            bad("E_RETIRED_TARGET_COUNT",
                f"KI-{src:02d}: 退役去向需恰好一個 KI-nn（實得 {len(tgt)}）")
            continue
        t = int(tgt[0])
        # 循環必然同時滿足「target 不在 active」（active 與 retired 已驗互斥），
        # 但兩者的 error code 不同，因此仍可獨立驗證：停用本支會讓案例 17
        # 因缺少 E_RETIRED_CYCLE 而失敗。
        if t in retired:
            bad("E_RETIRED_CYCLE", f"KI-{src:02d}: 去向 KI-{t:02d} 也是退役 ID（循環）")
        elif t not in active:
            bad("E_RETIRED_TARGET", f"KI-{src:02d}: 去向 KI-{t:02d} 不在 active ledger")

    A = set(active)
    derived_rel = {n for n in A if disp[n] in RELEASING
                   or (disp[n] in CONDITIONAL and act[n] == "DONE")}
    derived_blk = A - derived_rel
    d_disp = {d: sum(1 for n in A if disp[n] == d) for d in DISPOSITIONS}
    d_act = {a: sum(1 for n in A if act[n] == a) for a in ACTIONS}
    info.append(f"active {len(A)}／放行 {len(derived_rel)}／阻擋 {len(derived_blk)}")
    info.append("disposition " + "、".join(f"{k} {v}" for k, v in sorted(d_disp.items()) if v))
    info.append("action " + "、".join(f"{k} {v}" for k, v in sorted(d_act.items()) if v))

    # ---------- gate ----------
    # 兩個集合各自從文件解析，不得把其中一個定義成另一個的補集——那會讓互斥與
    # 覆蓋檢查恆真。
    # 早期版本認為 overlap／uncovered／ghost／released 比對「被 blocked 比對蘊含」，
    # 那個結論來自只比對 exit code 的測試。改成同時斷言 error code 之後，
    # 每一支都能被單獨殺掉（見 ledger_check_mutants.py），因此都是可獨立驗證的檢查。
    rel_block = region(text, M_RELEASED, known_path)
    blk_block = region(text, M_BLOCKED, known_path)
    narrative_guard(rel_block, known_path, "gate-released",
                    len(derived_rel), True, bad)
    narrative_guard(blk_block, known_path, "gate-blocked",
                    len(derived_blk), True, bad)
    stated_rel = gate_ids(rel_block, known_path, "gate-released", "E_GATE_ID_DUP")
    stated_blk = gate_ids(blk_block, known_path, "gate-blocked", "E_GATE_ID_DUP")
    if not stated_rel and not stated_blk:
        raise Fatal("E_GATE_EMPTY", f"{known_path}: gate 兩個集合區都沒有列出 KI-nn")
    if stated_rel & stated_blk:
        bad("E_GATE_OVERLAP", f"gate: 同一 ID 同列放行與阻擋：{sorted(stated_rel & stated_blk)}")
    if A - (stated_rel | stated_blk):
        bad("E_GATE_UNCOVERED", f"gate: 未出現在任一側的 active ID："
                                f"{sorted(A - (stated_rel | stated_blk))}")
    if (stated_rel | stated_blk) - A:
        bad("E_GATE_GHOST", f"gate: 列出不在 active 內的 ID：{sorted((stated_rel | stated_blk) - A)}")
    if stated_rel != derived_rel:
        bad("E_GATE_RELEASED_MISMATCH",
            f"gate 放行：宣稱 {sorted(stated_rel)}，推導 {sorted(derived_rel)}")
    if stated_blk != derived_blk:
        bad("E_GATE_BLOCKED_MISMATCH",
            f"gate 阻擋：宣稱 {sorted(stated_blk)}，推導 {sorted(derived_blk)}")

    tot_block = region(text, M_TOTALS, known_path)
    narrative_guard(tot_block, known_path, "gate-totals", None, False, bad)
    eq = equation(tot_block, known_path, "gate totals")
    if eq != (len(derived_rel), len(derived_blk), len(A)):
        bad("E_GATE_TOTALS", f"gate 算式：宣稱 {eq[0]}+{eq[1]}={eq[2]}，"
                             f"推導 {len(derived_rel)}+{len(derived_blk)}={len(A)}")

    # ---------- distribution ----------
    seen = set()
    for r in dist_rows:
        d = canonical_code(r[0], known_path, "distribution")
        if d not in DISPOSITIONS:
            bad("E_DIST_DISP_UNKNOWN", f"distribution: `{d}` 不在 disposition 值域內")
            continue
        if d in seen:
            bad("E_DIST_DUP_ROW", f"distribution: {d} 出現重複列")
            continue
        seen.add(d)
        nums = [int(x) for x in re.findall(r"\d+", r[1])]
        if len(nums) != 1:
            raise Fatal("E_DIST_COUNT_CELL",
                        f"{known_path}: distribution 筆數欄需恰一個整數：{r[1][:30]}")
        if nums[0] != d_disp[d]:
            bad("E_DIST_COUNT", f"distribution {d}: 宣稱 {nums[0]}，推導 {d_disp[d]}")
        real = {x for x in A if disp[x] == d}
        ids = set(id_list(r[2], known_path, f"distribution {d}", "E_DIST_ID_DUP"))
        if real and not ids:
            bad("E_DIST_IDS_EMPTY", f"distribution {d}: 筆數 {len(real)} 卻未列 ID")
        elif ids != real:
            bad("E_DIST_IDS", f"distribution {d}: ID {sorted(ids)} ≠ 推導 {sorted(real)}")
        got = declared(r[3])
        for a, vs in got.items():
            if a not in ACTIONS:
                continue
            want = sum(1 for x in real if act[x] == a)
            if len(vs) != 1 or vs[0] != want:
                bad("E_DIST_ACTION", f"distribution {d}/{a}: 宣稱 {vs}，推導 {want}")
        for a in ACTIONS:
            want = sum(1 for x in real if act[x] == a)
            if want and a not in got:
                bad("E_DIST_ACTION_MISSING",
                    f"distribution {d}: 未宣稱 action status {a}（推導 {want}）")
    for d in DISPOSITIONS - seen:
        bad("E_DIST_MISSING_ROW", f"distribution 缺少 disposition 列：{d}")

    tot = re.search(r"合計\s*\*{0,2}(\d+)\s*筆", region(text, M_DIST, known_path))
    if not tot:
        raise Fatal("E_TOTAL_MISSING", f"{known_path}: distribution 區內無「合計 N 筆」")
    if int(tot.group(1)) != len(A):
        bad("E_DIST_TOTAL", f"distribution 合計：宣稱 {tot.group(1)}，推導 {len(A)}")

    # ---------- 開頭摘要 ----------
    sum_block = region(text, M_SUMMARY, known_path)
    narrative_guard(sum_block, known_path, "ledger:summary", None, False, bad)
    sd = declared(sum_block)
    checkable = {k: v for k, v in sd.items() if k in DISPOSITIONS or k in ACTIONS}
    if not checkable:
        raise Fatal("E_SUMMARY_NO_CLAIM",
                    f"{known_path}: 開頭摘要區內沒有可檢查的 `LABEL` N 宣稱")
    for k, vs in checkable.items():
        want = d_disp[k] if k in DISPOSITIONS else d_act[k]
        for v in vs:
            if v != want:
                bad("E_SUMMARY_MISMATCH", f"開頭摘要 {k}: 宣稱 {v}，推導 {want}")

    # ---------- STATUS ----------
    s = region(stext, M_STATUS, status_path)
    narrative_guard(s, status_path, "status:current-summary", None, False, bad)
    s_eq = equation(s, status_path, "STATUS current summary")
    if s_eq != (len(derived_rel), len(derived_blk), len(A)):
        bad("E_STATUS_EQUATION", f"STATUS 算式：宣稱 {s_eq[0]}+{s_eq[1]}={s_eq[2]}，"
                                 f"推導 {len(derived_rel)}+{len(derived_blk)}={len(A)}")
    s_dec = declared(s)
    for k in sorted(DISPOSITIONS | ACTIONS):
        want = d_disp[k] if k in DISPOSITIONS else d_act[k]
        if k not in s_dec:
            bad("E_STATUS_MISSING", f"STATUS 未宣稱 {k}（推導 {want}）")
            continue
        for v in s_dec[k]:
            if v != want:
                bad("E_STATUS_MISMATCH", f"STATUS {k}: 宣稱 {v}，推導 {want}")

    return problems, info


def report(problems, info):
    for line in info:
        print("  " + line)
    if problems:
        print(f"\n不一致 {len(problems)} 項：", file=sys.stderr)
        for code, msg in problems:
            print(f"  - [{code}] {msg}", file=sys.stderr)
        return 1
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="ledger 結構與跨文件一致性檢查")
    ap.add_argument("--known-issues", required=True)
    ap.add_argument("--status", required=True)
    args = ap.parse_args(argv)
    try:
        problems, info = check(args.known_issues, args.status)
    except Fatal as e:
        print(f"格式／使用方式錯誤：[{e.code}] {e}", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"無法讀取：[E_IO] {e}", file=sys.stderr)
        return 2
    rc = report(problems, info)
    if rc == 0:
        print("ledger_check: 一致")
    return rc


if __name__ == "__main__":
    sys.exit(main())
