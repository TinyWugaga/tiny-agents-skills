#!/usr/bin/env python3
"""transport_selftest.py — encode/decode 的往返自測,零成本、不起 session。

用法: python3 transport_selftest.py      (exit 0 通過 / 1 失敗)

覆蓋 BR-F6 的攻擊面:換行、空白行、引號、反斜線、路徑逸出片段,以及編碼後不得殘留換行。
"""
import importlib.util, os, sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("transport", os.path.join(_HERE, "transport.py"))
t = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(t)

CASES = {
    "單行": "幫我看一下這段 diff",
    "換行": "第一行\n第二行",
    "空白行": "段落一\n\n段落二",
    "引號": 'expected "say ""hi"""  actual "say \\"hi\\""',
    "反斜線": "C:\\\\tmp\\\\x  正則 /\\\"/g",
    "字面反斜線 n": "這裡有字面的 \\n 不是換行",
    "路徑逸出": "修改範圍:../../etc/passwd\n下一行",
    "結尾換行": "最後一行\n",
    "定位字元": "a\tb\tc",
    "非 ASCII": "凍結基準:匯出必須支援 CSV\n明確排除 XLSX",
}


def main():
    fails = []

    def check(label, cond):
        print(("  ok   " if cond else "  FAIL ") + label)
        if not cond:
            fails.append(label)

    print("round-trip")
    for name, s in CASES.items():
        check("往返一致:" + name, t.decode(t.encode(s)) == s)

    print("單行不變式")
    for name, s in CASES.items():
        e = t.encode(s)
        check("編碼後無換行:" + name, "\n" not in e and "\r" not in e)

    print()
    if fails:
        print("transport_selftest: FAIL %d 項" % len(fails))
        return 1
    print("transport_selftest: 全部通過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
