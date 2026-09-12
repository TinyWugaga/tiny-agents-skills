# Batch 23b — Accepted risks 帶入項（供下一輪 fresh-context 驗收契約引用）

本檔不是完整驗收契約。它承載 Batch 23b bounded-review cycle 結束時由 Owner 裁決為
`accepted_risk` 的項目，**必須併入下一輪 fresh-context 驗收契約的 `Accepted risks` 段**。

權威決策紀錄在 [`../STATUS.md`](../STATUS.md) 的「Owner disposition：術語重定義 finding」段；
本檔與該段不一致時，以 `STATUS.md` 為準。

## AR-1 術語重定義可繞過零成本 checker

| 欄位 | 內容 |
|---|---|
| Disposition | `accepted_risk` |
| 裁決者／日期 | Owner，2026-09-08 |
| 來源 | Codex round 5 提出、round 6 覆核確認並重現 |
| 狀態 | **不是未關閉的 blocking finding**，不得據此判定本 cycle 未關閉 |

**風險內容。** 在 `SKILL.md` 插入重新定義術語的條文（例如把「驗收」「證據」「明確授權」
「可判定的影響範圍」定義成「使用者提出請求這件事本身」），可同時廢掉 KI-02／14／15／21
的全部保證，而兩支零成本 checker 均回報通過。可重現樣本：`/tmp/r5probe-termredef.md`。

**為何接受而非修復。** 該類別不豁免、不凌駕、不省略確認，而是改寫條件的**定義**；
兩支 checker 的判準全部建立在語素共現上，正則層級補不掉。硬加關鍵詞只會製造新的誤報——
r6 開發過程中已實際發生一次自傷誤報（「覆蓋要求的審查範圍」被誤判為推翻條款）。

**已採取的 mitigation。** 兩支 checker 已明定為 regression smoke test，
不再被引用為語意或抗架空驗證；偵測責任移交本輪 fresh-context 語意驗收。

## 對本輪 verifier 的要求

接受這項風險**不等於**免除檢查。本輪驗收仍須逐條確認並回報：

1. 當前 `SKILL.md`（`3f907bd47a2903f7091573c8e8616a4cdcb86e5f9dc5815c5df7242526b0dbe2`）
   **沒有**任何實際的術語架空條款——包含獨立的術語定義段落，以及在既有段落內重新界定
   「驗收」「證據」「明確授權」「可判定的影響範圍」意義的句子。
2. KI-02／14／15／21 的規則文字在語意上確實成立，而不只是通過了 regression smoke test。
3. 若發現定義層架空實際存在於當前產出物，該項**不受本 accepted risk 涵蓋**——
   本風險只針對未來變更，當前產出物含有此類條文即為新的 blocking finding。

## 重新檢視條件（任一成立即須重新裁決 AR-1）

1. `SKILL.md` 新增或改寫任何術語定義段落。
2. 本輪 fresh-context 語意驗收執行完畢——結果須寫回 `STATUS.md` 的 disposition 段。
3. 出現定義層以外、同樣能繞過兩支 checker 的新架空類別。
4. 有人主張以 checker 通過作為「規則未被架空」的證據。

## Non-blocking backlog（不延長本 cycle，不列入本輪驗收條件）

- mutation harness 以精確字串 `replace()` 注入 mutant，等價改寫得到 `INVALID` 而非失敗。
- 兩支 checker 的 detector 近乎逐字重複，對 regex／token-class 漏洞無額外偵測力；
  是否合併為單一 canonical checker 待評估。

## 未受本裁決影響

KI-02／14／15／21 維持 `FIX_SKILL`／`NOT_DONE`，直到最新 bundle
`93956caa84dc453f34d0f87b674de759b87059608d6d509f2f30d4d48a5f6818` 的付費行為重跑完成。
本輪驗收為零成本，不得據以將任一 KI 改為 `DONE`。
