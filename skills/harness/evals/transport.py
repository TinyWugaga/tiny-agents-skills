#!/usr/bin/env python3
"""transport.py — fixture prompt 的單行傳輸編碼。

`run-suite.sh` 用 `read` 逐行取 fixture 記錄。prompt 含換行時,續行會被當成新的一筆,
第一欄還會成為 `SUITE` 並拼進輸出檔名——含 `/` 會產生巢狀路徑,含 `../` 可逸出輸出目錄。
因此 prompt 在進入 TSV 前一律編碼成單行,read 之後、送進受測 session 之前完整解碼。

編碼只處理三個字元,且解碼是單次左到右掃描而非連續 replace:連續 replace 會把原文中的
字面 `\\n` 與編碼產生的 `\\n` 混為一談。

CLI: stdin 讀編碼字串,stdout 寫解碼結果(給 shell 呼叫)。
"""
import sys


def encode(s):
    return s.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")


def decode(s):
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == "\\" and i + 1 < n:
            nxt = s[i + 1]
            if nxt == "n":
                out.append("\n"); i += 2; continue
            if nxt == "r":
                out.append("\r"); i += 2; continue
            if nxt == "\\":
                out.append("\\"); i += 2; continue
        out.append(c); i += 1
    return "".join(out)


if __name__ == "__main__":
    sys.stdout.write(decode(sys.stdin.read()))
