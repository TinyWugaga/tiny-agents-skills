#!/usr/bin/env python3
"""run_domain_check — identity 凍結清單與 run record 的 domain／輪次綁定一致性。

四個刻意的設計決定：

* **受驗 run 集必須由 CLI 明確傳入**，不掃描整個 runs/。
* **required domain 與 hash_schema 由 CLI 契約輸入，不從被驗 record 推導。**
  若九份 record 與凍結清單同時漏掉同一 domain，用聯集推導會一起漏然後 PASS。
* **凍結清單一個值一列，且必須列出該值綁定的輪次。** 只比對 hash 值集合的話，
  把 arm A 與 arm B 的兩個既有 hash 對調仍會 PASS。
* **綁定值欄整格嚴格比對。** 只在欄內搜尋 64 位 substring 的話，
  合法 hash 後面接一段殘留的舊 hash 仍會 PASS。

**不檢查**「來源檔敘述與 bundle-hash.sh allowlist 相符」：目前沒有可機讀的單一來源，
檢查器自己重抄 allowlist 會建立第二份真相來源。該項留人工驗收。

exit code：0 一致／1 資料不一致／2 輸入、格式或使用方式錯誤。
"""

import argparse
import json
import os
import re
import sys

from ledger_check import Fatal, region, report, split_row

FREEZE_HEADER = ["domain", "綁定值", "綁定輪次", "現算", "來源"]
FREEZE_MARKER = "ledger:freeze"
# 整格比對：整個欄位只能是一個 backtick 包住的 hash，前後不得有任何其他內容。
CELL_FULL = re.compile(r"^`([0-9a-f]{64})`$")
CELL_PREFIX = re.compile(r"^`([0-9a-f]{8,64})`$")


def run_list(cell, path, domain):
    """綁定輪次欄的 grammar：`、` 分隔的 backtick run id，整格不得有其他內容。

    **不得用 findall 掃 token 再轉 set**——重複的 run id 會被靜默吃掉，
    而 `r1、r2、r3、r1` 是 malformed claim，不是「和 r1、r2、r3 等價」。
    """
    s = cell.strip()
    if not s:
        raise Fatal("E_FREEZE_RUNS_MISSING", f"{path}: freeze domain {domain} 未列出綁定輪次")
    out = []
    for i, t in enumerate([x.strip() for x in s.split("、")]):
        m = re.fullmatch(r"`([^`]+)`", t)
        if not m:
            raise Fatal("E_FREEZE_RUNS_FORMAT",
                        f"{path}: freeze domain {domain} 綁定輪次第 {i + 1} 項不合 grammar："
                        f"{t[:24]!r}（需為以、分隔的 `run-id`）")
        out.append(m.group(1))
    dups = sorted({x for x in out if out.count(x) > 1})
    if dups:
        raise Fatal("E_FREEZE_RUN_DUP",
                    f"{path}: freeze domain {domain} 的綁定輪次有重複項：{dups}")
    return set(out)


def parse_freeze(path, allow_prefix):
    """回傳 [(domain, hash_token, {run ids})]，一個值一列。"""
    block = region(open(path, encoding="utf-8").read(), FREEZE_MARKER, path)
    lines = [l for l in block.splitlines() if l.strip().startswith("|")]
    if not lines:
        raise Fatal("E_TABLE_MISSING", f"{path}: freeze 區內找不到表格")
    rows = [split_row(l) for l in lines]
    if rows[0] != FREEZE_HEADER:
        raise Fatal("E_HEADER_MISMATCH",
                    f"{path}: freeze header 不符\n  預期 {FREEZE_HEADER}\n  實得 {rows[0]}")
    if len(rows) < 2 or len(rows[1]) != len(FREEZE_HEADER) \
            or not all(re.fullmatch(r":?-{2,}:?", c) for c in rows[1]):
        raise Fatal("E_SEPARATOR_BAD", f"{path}: freeze table 分隔列欄數或格式不合")
    out, seen = [], set()
    for r in rows[2:]:
        if len(r) != len(FREEZE_HEADER):
            raise Fatal("E_ROW_MALFORMED", f"{path}: freeze malformed row（欄數 {len(r)}）: {r[:2]}")
        dm = re.fullmatch(r"`([A-Za-z_]+)`", r[0].strip())
        if not dm:
            raise Fatal("E_FREEZE_DOMAIN_CELL",
                        f"{path}: freeze 的 domain 欄整格需為 `name`：{r[0][:40]}")
        pat = CELL_PREFIX if allow_prefix else CELL_FULL
        hm = pat.fullmatch(r[1].strip())
        if not hm:
            raise Fatal("E_FREEZE_HASH_CELL",
                        f"{path}: freeze domain {dm.group(1)} 的綁定值欄整格必須是單一 "
                        f"`{'8–64 位 hex' if allow_prefix else '完整 64 位 hex'}`，"
                        f"不得有額外文字或第二個 hash（一個值一列）：{r[1][:80]}")
        runs = run_list(r[2], path, dm.group(1))
        key = (dm.group(1), hm.group(1))
        if key in seen:
            raise Fatal("E_FREEZE_DUP_ROW",
                        f"{path}: freeze 有重複的 (domain, 值) 列：{key[0]} {key[1][:12]}…")
        seen.add(key)
        out.append((dm.group(1), hm.group(1), set(runs)))
    return out


def load_runs(run_dirs):
    if not run_dirs:
        raise Fatal("E_RUNSET_EMPTY", "受驗 run 集為空；請以 --run 傳入至少一個 run 目錄")
    runs = {}
    for d in run_dirs:
        rid = os.path.basename(os.path.normpath(d))
        if rid in runs:
            raise Fatal("E_RUN_ID_DUP", f"run ID 重複：{rid}")
        p = os.path.join(d, f"{rid}.json")
        if not os.path.isfile(p):
            raise Fatal("E_RUN_RECORD_MISSING", f"找不到 run record：{p}")
        try:
            doc = json.load(open(p, encoding="utf-8"))
        except (ValueError, OSError) as e:
            raise Fatal("E_RUN_RECORD_PARSE", f"{p}: 無法解析（{e}）")
        h = doc.get("hashes")
        if not isinstance(h, dict) or not h:
            raise Fatal("E_RUN_HASHES_MISSING", f"{p}: run record 缺少 hashes")
        # 只比對目錄 basename 等於「run ID 唯一」只驗到路徑別名；
        # record 內的 run_id 必須存在且一致，才算真的綁到那一輪。
        if doc.get("run_id") != rid:
            raise Fatal("E_RUN_ID_MISMATCH",
                        f"{p}: record 的 run_id {doc.get('run_id')!r} 與目錄名 {rid!r} 不符")
        runs[rid] = (h, doc.get("hash_schema"))
    return runs


def check(known_path, run_dirs, required, hash_schema, allow_prefix):
    problems, info = [], []

    def bad(code, msg):
        problems.append((code, msg))

    runs = load_runs(run_dirs)
    freeze = parse_freeze(known_path, allow_prefix)
    required = set(required)

    for rid, (h, schema) in sorted(runs.items()):
        if schema != hash_schema:
            bad("E_SCHEMA_MISMATCH", f"{rid}: hash_schema {schema!r}，契約要求 {hash_schema!r}")
        if required - set(h):
            bad("E_RUN_DOMAIN_MISSING", f"{rid}: 缺少契約 domain {sorted(required - set(h))}")
        if set(h) - required:
            bad("E_RUN_DOMAIN_EXTRA", f"{rid}: 有契約未列的 domain {sorted(set(h) - required)}")

    ftab = {}
    for d, tok, rset in freeze:
        ftab.setdefault(d, []).append((tok, rset))
    if required - set(ftab):
        bad("E_FREEZE_DOMAIN_MISSING", f"凍結清單缺少 domain：{sorted(required - set(ftab))}")
    if set(ftab) - required:
        bad("E_FREEZE_DOMAIN_EXTRA", f"凍結清單有契約未列的 domain：{sorted(set(ftab) - required)}")

    for d in sorted(required):
        actual = {}
        for rid, (h, _) in runs.items():
            v = h.get(d)
            if v is None:
                continue
            if not re.fullmatch(r"[0-9a-f]{64}", str(v)):
                bad("E_HASH_FORMAT", f"{rid}/{d}: hash 格式錯誤：{str(v)[:24]}")
                continue
            actual.setdefault(v, set()).add(rid)
        if d not in ftab:
            continue
        matched = {}
        for tok, stated_runs in ftab[d]:
            hits = [v for v in actual if v.startswith(tok)]
            if not hits:
                bad("E_FREEZE_VALUE_UNKNOWN",
                    f"凍結清單 {d}: 值 {tok[:12]}… 不存在於受驗 run 集（多餘的歷史值）")
                continue
            if len(hits) > 1:
                bad("E_HASH_PREFIX_AMBIGUOUS",
                    f"凍結清單 {d}: 前綴 {tok}… 同時符合 {len(hits)} 個不同值")
                continue
            v = hits[0]
            if v in matched:
                bad("E_FREEZE_VALUE_DUP", f"凍結清單 {d}: 同一個值列了兩次（{v[:12]}…）")
                continue
            matched[v] = stated_runs
            if stated_runs != actual[v]:
                bad("E_FREEZE_RUNS_MISMATCH",
                    f"凍結清單 {d} 值 {v[:12]}… 綁定輪次不符："
                    f"宣稱 {sorted(stated_runs)}，實際 {sorted(actual[v])}")
        for v, rids in actual.items():
            if v not in matched:
                bad("E_FREEZE_VALUE_MISSING",
                    f"凍結清單 {d}: 漏列值 {v[:12]}…（綁定 {sorted(rids)}）")
        if len(actual) > 1:
            info.append(f"{d}: 多值 {len(actual)} 個 — " +
                        "／".join(f"{v[:8]}… {len(r)} 輪" for v, r in sorted(actual.items())))

    info.insert(0, f"受驗 run {len(runs)} 個、契約 domain {len(required)} 個"
                   f"、hash_schema {hash_schema}")
    return problems, info


def main(argv=None):
    ap = argparse.ArgumentParser(description="凍結清單與 run record 的 domain／輪次綁定一致性")
    ap.add_argument("--known-issues", required=True)
    ap.add_argument("--run", action="append", default=[])
    ap.add_argument("--required-domain", action="append", default=[], required=True)
    ap.add_argument("--hash-schema", required=True)
    ap.add_argument("--allow-prefix", action="store_true",
                    help="允許凍結清單使用可辨識的 hash 前綴（預設要求完整 64 位 hex）")
    args = ap.parse_args(argv)
    try:
        problems, info = check(args.known_issues, args.run, args.required_domain,
                               args.hash_schema, args.allow_prefix)
    except Fatal as e:
        print(f"格式／使用方式錯誤：[{e.code}] {e}", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"無法讀取：[E_IO] {e}", file=sys.stderr)
        return 2
    rc = report(problems, info)
    if rc == 0:
        print("run_domain_check: 一致")
    return rc


if __name__ == "__main__":
    sys.exit(main())
