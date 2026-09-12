# Follow-up closure 契約 — 2026-09-04 followup（KI-01 量詞修正 ＋ DE-01 preflight r2）

給**另一個 fresh-context session** 使用。執行者不得參與本次修改，也不得讀取本次修改的
推理過程；本檔已包含驗收所需的全部輸入。

本檔**不取代** [`CLOSURE-20260904.md`](CLOSURE-20260904.md)。那份是已驗收的封存契約，
本輪不修改它。本檔只涵蓋 followup cycle，並修掉上一份契約被複驗指出的缺陷（第 8 節）。

## 0. verdict 詞彙與計數

| 值 | 意義 |
|---|---|
| `PASS` | 條件成立，有可追溯證據 |
| `FAIL` | 條件不成立，有可追溯證據 |
| `UNVERIFIABLE` | 缺乏獨立於本次修改的 fingerprint，無法判真偽 |

**本契約共 20 個可判定 verdict：F1–F18 與 U1–U2。** 這是逐一列舉後的實數。
另有 3 個 **gate flag**（G1–G3，值為 `DONE`／`NOT_DONE`），**不計入整體判定**。

整體判定取 F1–F18、U1–U2 中最嚴重的單條結果。

**F 與 U 的分工（上一版的自相矛盾在此解消）：**
F15／F16 用的是**本契約發布的 fingerprint**，判的是「相對本契約發布值未變」——這可判。
U1／U2 判的是「該檔在本輪之前是否已被動過」——本契約發布的值本身也出自本輪，
無法自證，因此那一面永遠是 `UNVERIFIABLE`。兩者不衝突：F15／F16 是清單與摘要層級，
U1／U2 是來源可信度層級。

## 1. 產出物與版本標記

repo：`/Users/tinywu/Desktop/Apps/tiny-agents-skills`
HEAD：`b9cb8150a30be2b69b07a615e02f5ed8b9f21d2b`（**未 commit**，working tree dirty）
cycle 時間界線：`2026-09-04 05:00`（上一輪最後寫入 04:14，本輪最早寫入 06:26）

### 本輪寫入的檔案（共 7 個）

| # | 檔案 | SHA-256 | 類別 |
|---|---|---|---|
| 1 | `skills/discipline/judgment/evals/fixtures.json` | `8a6d99f4279db9b091f3fdd8ee41721883f50eec08d1ea72e5b578c5fbc9f109` | implementation |
| 2 | `skills/harness/evals/DE-01-arms.md` | 見 F7／F8（內容條件） | implementation |
| 3 | `skills/harness/evals/de01/armA.SKILL.md` | `45c7a7c3af9a323661da826c8e503c47bf52ccca71b540cc7a8a89377142576c` | DE-01 凍結輸入 |
| 4 | `skills/harness/evals/de01/fixtures.json` | `cc323cfdbd3279ad2f46fcf6ff1588707dc8208f025f1c59f1b5ac2c13c26f1c` | DE-01 凍結輸入 |
| 5 | `skills/harness/evals/de01/ki07-fixtures.json` | `c3f7cba76cd66d38af9deb18490660613e0b0b3ee54c6eb45f046ba51e0612d2` | DE-01 凍結輸入 |
| 6 | `skills/harness/evals/de01/routing-empty.json` | `e0208630a0a3105046e8c2dbc59e3fedac3d8759d3bd3adf0e0c7d05cc5fb642` | DE-01 凍結輸入 |
| 7 | `skills/harness/evals/DE-01-PREFLIGHT.md` | 見 F18（內容條件）；**驗收工具，非 implementation artifact** | preflight |

本檔（`CLOSURE-20260904-followup.md`）是驗收契約，**非驗收對象**，不列入上表。

## 2. 適用指示（驗收者需自行讀取）

- `skills/harness/evals/KNOWN-ISSUES.md` — 逐筆 `required_action` 與 DE-01 協定的來源。
  **判準以其原文為準，不以本契約的轉述為準；不一致時以 KNOWN-ISSUES.md 為準並記為 finding。**
- `scripts/bundle-hash.sh` — hash domain 定義（`hash_schema v6`）。
- `skills/harness/evals/routing-fixtures.json` 的 `field_definitions` — fixture schema 語意。
- `skills/harness/evals/run-suite.sh` — F18 需要它決定實際會跑幾筆、judge 是否可跳過。
- **`skills/discipline/judgment/references/verifier.md` — 適用。** 驗收報告受該檔第 9 條
  約束（Markdown source line 不超過 40 行）。第 11 節的格式在此上限**之內**執行，
  衝突時以 40 行為準，做法是縮短證據引文、不是省略條件。

## 3. 可判定條件（F1–F18）

### A. 本輪實作

| # | 條件 |
|---|---|
| F1 | `judgment__positive-2` 的 `required_elements[2]` 以「所有條件均通過才是整體通過」表述整體通過的成立條件，**不含任何固定條數的量詞**（如「三條」）。判準：該句的通過門檻與該 fixture 實際 assertion 條數無關 |
| F2 | 同一 entry 其餘語意未退化：仍以「取最嚴重的單條結果」描述優先序，仍不出現 `PASS`／`FAIL`／`UNVERIFIABLE` 字面，也不出現 `FAIL > UNVERIFIABLE > PASS` |
| F3 | `judgment/evals/fixtures.json` 本輪唯一改動就是 F1 那一處。判法：repo 外副本把「所有條件均通過」改回「三條全部通過」，該檔 SHA-256 應等於 `bee44a23678ff8742f6e277ed3ac5d55e09aa7ad915577d340e52439427a938d`，`fixtures`(judgment) 應等於 `d635c98e5d2959b3b15d72bdbdb5ffc40c6cc847b6da7d445e07602f3a75944c` |
| F4 | `judgment/SKILL.md` 未變（`10a88e48…`）且 `judgment_skill` domain 未變（`a26b4368…`）。**description 本輪不得再動**——它已是 DE-01 的 arm B 定稿 |
| F5 | `CLOSURE-20260904.md` 未變（`e77c9502e18e2b43b7b7bf3aa59ff42de57192f04f6880531173846d0d21b01f`） |
| F6 | `routing-fixtures.json` 未變（`79d0997390f7f934b977b46d434570b97dd237e8953aeffcd639f29f4c8458c4`） |

### B. DE-01 凍結輸入

| # | 條件 |
|---|---|
| F7 | `DE-01-arms.md` 記載的每個雜湊都可重現：arm A 來源檔 `4f465d66…`、修改前 SKILL.md 全檔 `57f277f0…`、修改前區塊全文／純值 `cede102f…`／`85e73291…`、修改後區塊全文／純值 `f18afdd0…`／`78acf313…`、修改前後 `judgment_skill` `0c5a3dea…`／`a26b4368…` |
| F8 | `DE-01-arms.md` 的 `fixtures` 血緣表列出三代值，且把 `3d225afc58e479eef05efc156d599c94b57684bcd729e754411831889bad3d4f` 標為 DE-01 綁定值 |
| F9 | `de01/armA.SKILL.md` 與現行 `SKILL.md` **只差 description 區塊**：body 逐字相同，且其 description 區塊全文 SHA-256 等於 `f85de9b22643770b3455b83c0d380d8280285d93e2397a853e154b931146a13a` |
| F10 | 四個 DE-01 輸入檔內容正確：`de01/fixtures.json` 恰含 `positive-1/2/4/5`；`de01/ki07-fixtures.json` 恰含 `ambiguous-1`；兩檔 `schema_version` 為 `2.1` 且各 fixture 與現行主 fixtures 檔逐字相同；`de01/routing-empty.json` 的 `fixtures` 為空陣列且 `schema_version` 為 `2.1` |

### C. Domain 邊界

| # | 條件 |
|---|---|
| F11 | 五個不變 domain：`evaluator 65bc6c07…`、`runner 005ed2f7…`、`rescore_runner 2301a9da…`、`dispatch_skill 2d6c0d99…`、`token_preflight_skill be72017e…` |
| F12 | `fixtures`(default) 未變：`867d247699a03c32ae0a3892992931102fe26f24d76b25ce04b5f80b462175f0` |
| F13 | `fixtures`(judgment) 為 `3d225afc58e479eef05efc156d599c94b57684bcd729e754411831889bad3d4f` |

### D. 未發生 ／ preflight 可執行性

| # | 條件 |
|---|---|
| F14 | 第 4 節的零成本驗證全部通過，**且對 working tree 逐 byte 中性**（全樹指紋比對為空） |
| F15 | `skills/harness/evals/runs/` 的檔案清單未變：`find skills/harness/evals/runs -type f \| sort \| shasum -a 256` 等於 `bfe7d56604fea7964114be6c903853c1247ba5866497cbd6c4345d7a089ea86f`，檔案數 922。**這證明本輪未新增 run 目錄，不證明既有檔內容未變**（後者見 U1） |
| F16 | `KNOWN-ISSUES.md` SHA-256 為 `401b7f63e199bc768c1de800cb6e80924cff4702124d454c2fd77af5eb6cbc00`、`STATUS.md` 為 `b16261c8ee91ee94a24c371a355a131201fd957ce7a42514a02344bbb1074aa6`。無 disposition 改判、gate 現況未更新 |
| F17 | 十筆 `NEEDS_EVIDENCE`（KI-02／03／05／08／11／12／14／15／16／18）未被實作。判法：`de01/*.json` 是**新增的縮減副本**，不是對主 fixture 檔的改動；主檔除 F1 外未動（F3），SKILL.md 未動（F4） |
| F18 | `DE-01-PREFLIGHT.md` 是**可執行**的：① 其執行指令同時覆寫 `HARNESS_FX` 與 `HARNESS_RT`，且 dry-run 實測 DE-01 批次每輪 **4 筆**、KI-07 批次每輪 **1 筆**；② 不含任何「routing-only／可跳過 judge」的宣稱（`run-suite.sh:385` 之後必呼叫 judge，repo 無 skip-judge 開關）；③ 判定門檻逐字等同 `KNOWN-ISSUES.md` 的 DE-01 協定第 3 條「arm A 至少 2/3、arm B 至多 1/3」，且明文禁止跨 fixture 外推；④ 成本表計入每次 `run-suite.sh` 呼叫額外的 1 筆 preflight session（`run-suite.sh:316`） |

## 4. 允許的驗證方式（零成本，**不得起任何付費 session**）

**一律加 `PYTHONDONTWRITEBYTECODE=1`**，讓驗證本身不寫檔：

```
export PYTHONDONTWRITEBYTECODE=1
python3 skills/harness/evals/{judge,score,record,transport}_selftest.py
sh scripts/hash-domain-selftest.sh
sh skills/harness/evals/run-suite.sh --dry-run
cd skills/harness/evals && HARNESS_FX=../../discipline/judgment/evals/fixtures.json sh run-suite.sh --dry-run
cd skills/harness/evals && HARNESS_FX=de01/fixtures.json HARNESS_RT=de01/routing-empty.json sh run-suite.sh --dry-run
cd skills/harness/evals && HARNESS_FX=de01/ki07-fixtures.json HARNESS_RT=de01/routing-empty.json sh run-suite.sh --dry-run
sh scripts/bundle-hash.sh <mode> ...
git status --short ; git diff
```

F14 的 byte 中性以全樹指紋比對驗證：

```
manifest() { find . -path ./.git -prune -o -type f -print0 | sort -z | xargs -0 shasum -a 256; }
manifest > /tmp/before ; <跑完上列全部驗證> ; manifest > /tmp/after ; diff /tmp/before /tmp/after
```

預期值：四支 Python selftest 全通過；`hash-domain-selftest` 36 案例全通過；
default dry-run 18 筆、judgment dry-run 28 筆、**DE-01 dry-run 4 筆、KI-07 dry-run 1 筆**；
每筆 dry-run 解碼後的 prompt 與 JSON 逐 byte 相同；全樹 diff 為空。
**全樹檔案數以當次實測為準**（本契約寫成時為 1020）——上一版把它寫死成 1014，
在同一輪內就因新增檔案而失效。

## 5. mtime 探針（分開下指令）

```
# (a) runs/ 全深度 —— 支撐 F15
find skills/harness/evals/runs -type f -newermt "2026-09-04 05:00"
# 預期：無輸出

# (b) evals/ 直層 —— 支撐 U2
find skills/harness/evals -maxdepth 1 -type f -newermt "2026-09-04 05:00"
# 預期：恰為 DE-01-arms.md、DE-01-PREFLIGHT.md、CLOSURE-20260904-followup.md
```

**mtime 的證據力上限：** 只能提供反證（列出不該出現的檔），
**不得單獨用來判 PASS，也不得單獨用來判 FAIL**。

## 6. 先驗 UNVERIFIABLE（U1–U2）

| # | 對象 | 值 |
|---|---|---|
| U1 | `skills/harness/evals/runs/**` 既有檔案的**內容**在本輪之前是否被改（清單層級見 F15） | `UNVERIFIABLE` |
| U2 | `skills/harness/evals/` 下不屬任何 identity domain 的說明文件（`STATUS.md`／`KNOWN-ISSUES.md`／`ACCEPTANCE-r2.md` 等）在本輪之前的內容（摘要層級見 F16） | `UNVERIFIABLE` |

**判定規則：** 沒有 pre-cycle fingerprint 的 untracked／gitignored／衍生檔
（含 `__pycache__/*.pyc`）**只能判 `UNVERIFIABLE`**。mtime 落在時間界線之後
**不構成 FAIL**。要升為 `PASS` 需獨立於本次修改的可信 fingerprint（commit、封存 digest
或第三方快照）；升為 `FAIL` 需實際的內容差異證據。

**第 1 節「本輪寫入七個檔」的邊界只涵蓋 tracked 與 source 檔**，不涵蓋衍生檔。

## 7. Gate flag（G1–G3，不計入整體判定）

| # | 對象 | 值 | 依據 |
|---|---|---|---|
| G1 | KI-07 前半：description 寫入「互斥方案 ＋ 選錯成本高 ＋ 徵詢語氣」觸發面 | `DONE` | 上一 cycle 完成，F4 證明未再改動 |
| G2 | KI-07 後半：與 DE-01 的 A/B 同批進行，且重跑 `ambiguous-1`（`FIX_SKILL`） | `NOT_DONE` | 本輪明示不執行；`DE-01-PREFLIGHT.md` 已備妥未跑 |
| G3 | KI-01：移除逐字措辭要求、優先序條目不綁字面 | `DONE`（見 F1／F2） | — |

**G2 為 `NOT_DONE` ⇒ KI-07 不得記為 closed，發布 gate 維持關閉。**

## 8. 本契約修掉的缺陷

對 `CLOSURE-20260904.md` 的複驗findings：

| 缺陷 | 修正 |
|---|---|
| 宣稱 16 條、實際 17 個 verdict | §0 逐一列舉，實數 20（F1–F18、U1–U2） |
| A11 把「description 寫入」與「A/B 完成」綁成一條 | 拆為 G1／G2 |
| `DE-01-arms.md` 無驗收條件 | F7／F8；`DE-01-PREFLIGHT.md` 降級為驗收工具並由 F18 覆蓋 |
| 無 fingerprint 的衍生檔可能被 mtime 判 FAIL | §6 明訂只能判 `UNVERIFIABLE`；驗證改用 `PYTHONDONTWRITEBYTECODE=1` |
| `-maxdepth 1` 使 `runs/**` 未被掃描、預期值漏列 | §5 拆兩條指令 |
| `verifier.md` 40 行上限是否適用不明 | §2 明文列為適用指示 |

對本契約 r1 自身的 findings（同一輪修正）：

| 缺陷 | 修正 |
|---|---|
| F15／F16 宣稱「未新增／未變」，卻與 U1／U2 的「只能 UNVERIFIABLE」矛盾 | §0 說明 F 與 U 的分工；F15／F16 改為對本契約發布 fingerprint 的比對，U1／U2 承載來源可信度 |
| 全樹檔案數寫死 1014，實測 1020 | §4 改為「以當次實測為準」並註明撰寫時的值 |
| preflight 不可執行（未覆寫 `HARNESS_RT`、誤稱可 routing-only、擅改判定門檻、KI-08 宣稱錯誤） | 新增 F18 四款逐項驗證；preflight 已改 r2 |

## 9. 明確排除範圍（超出者記入 backlog）

- **不執行 DE-01 A/B、不執行 KI-07 重跑**、不起 subject／judge session、
  不驗證 routing／contract 會不會 PASS。任何「fixture 已修好所以會通過」的推論
  不得作為 closure 依據。
- 不改動任何 KI 的 Owner disposition，不更新發布 gate。
- 不 commit、不 push、不發布、不更新已安裝的 skill 副本。
- 不評 fixture 的文風或行數。**但 assertion 內容的正確性不在此列**——
  F1 就是一個量詞錯誤，上一輪被誤歸為文風問題而漏判。
- 已知未修、不在本輪範圍：`KNOWN-ISSUES.md` 第 236 行與第 250 行互相矛盾
  （步驟 F 只能產生 `legacy_diagnostic` vs `FIX_FIXTURE` 必須排在 F 之後）。
  不得因此判任何 F／U 條件 FAIL。

## 10. 環境限制

- working tree 在 HEAD 之外本來就有大量與本次無關的 dirty 變更。**必須原樣保留**。
  比對對象是「本輪修改前的 working tree」，不是 HEAD。
- `skills/harness/evals/runs/**` 是證據封存，唯讀。
- 需要產生檔案的驗證一律在 repo 外的暫存目錄用副本做。

## 11. 回報格式

逐條回報 F1–F18、U1–U2 的 verdict 與可追溯證據（檔案路徑＋行號，或指令與其輸出），
再列 G1–G3。整體判定取 F／U 中最嚴重者。
**全文不超過 40 個 Markdown source lines**（§2）。回報後結束，不進入修復或重新驗收循環。
