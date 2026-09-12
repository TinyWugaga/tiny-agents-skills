# 更正附錄 1 — 第 9 次 fresh-context 語意驗收的 output digest

**本檔不可覆寫，且不修改被更正的原紀錄。** 依 verification-record 的既有原則，
已落檔的紀錄不得就地改寫；更正以獨立、可追溯的附錄承載，原紀錄保持原狀。

**本附錄由實作者抄錄，屬 archive，不因落檔而取得獨立 provenance。**

## 1. 被更正的紀錄

| 項目 | 值 |
|---|---|
| 路徑 | `skills/harness/evals/verification-records/20260910-round9-bdac1ff80e349878.md` |
| SHA-256 | `d548412590891966aea97461847bfce6a9e8316605851c6f02f5afdf39f24f1d` |
| 狀態 | **未修改，仍為有效紀錄。** 本附錄只更正其 §4 對 output digest 的標示 |

## 2. 更正對象與來源

| 項目 | 值 |
|---|---|
| Codex thread ID | `01a08845-8053-7d10-aa1a-c2e5d3a693f6` |
| Codex task ID | `task-mtuo17nc-qbkm4w` |
| 來源 | 該 task 的 final message（job log） |

## 3. 事實

原始 task final message 為 **18 行**，其中 **15 行帶有兩個半形空格的尾端空白**
（分布：L1，以及 L4–L17；L2、L3、L18 無尾端空白）。

原紀錄 §4 抄錄該輸出時**移除了尾端空白**，並對移除後的內容計算 digest。
因此原紀錄標為「原始輸出 SHA-256」的值，實際上是**正規化後**的值。

| digest | 值 | 對應內容 |
|---|---|---|
| **原始 task-output digest** | `3ce8a9d440b1ede1af24de1adc0b396d832e95aadbf58fa82e9454f5414776d3` | task final message 逐 byte，含尾端空白，無尾換行 |
| **normalized archived-output digest** | `eed58ab8e165784b828956a9d86e07c612512ba739a98828ad5be76894aec4dd` | 每行去除尾端空白後的內容，無尾換行；即原紀錄 §4 code block 的實際內容 |

兩者的差異**僅為 15 行各兩個尾端空格**，可由前者機械推導至後者（逐行 `rstrip`）。

## 4. 更正內容

原紀錄 §4 的敘述「原始輸出。18 行……SHA-256：`eed58ab8…`（對下列 code block 內容逐 byte
計算，無尾換行）」應理解為：

* 該 code block 的內容是**正規化後**的抄錄，非逐 byte 原文；
* `eed58ab8…` 是 **normalized archived-output digest**，不是原始 task-output digest；
* 原始 task-output digest 為 `3ce8a9d4…`，見 §3。

原紀錄其餘各節不受影響。

## 5. 對 verdict 的影響：無

本更正**不影響**下列任何一項：

* 15 條驗收條件的逐條結果——全部 PASS，無 FAIL、無 UNVERIFIABLE；
* 整體語意驗收 verdict——**PASS**；
* 被驗四檔的 SHA-256 與 canonical subject digest
  `bdac1ff80e349878b3fbc1369dae0cb8bfedd59cb07ddd23e0a9e174a849d661`；
* 凍結契約 `20260910-batch23b-semantic.md`（`50bdc175…`）；
* 原紀錄 §6 所列「本輪不構成的證據」四項限制。

差異純屬**抄錄時的空白正規化**，不涉及任何判定內容、證據或條件結果。
輸出文字在去除尾端空白後逐字元相同。

## 6. 未改動

`KNOWN-ISSUES.md`、active ledger、gate 集合、disposition、KI-02／14／15／21 的
action status、凍結契約、契約 §2 綁定的五個檔案，以及被更正的原紀錄本身，全部未修改。
本輪**未重跑** fresh-context 驗收。
