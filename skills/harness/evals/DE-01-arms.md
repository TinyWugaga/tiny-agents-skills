# DE-01 description arms — 凍結記錄

本檔只保存 DE-01 A/B 所需的兩份 description 原文與 SHA-256。**A/B 尚未執行**，
本檔不含任何觸發率或判定結果。它不屬於任何 identity domain（`skills/harness/evals/`
下的說明文件不在 evaluator／runner allowlist 內），因此新增本檔不改變任何 hash；
`hash-domain-selftest.sh` 的「改 STATUS.md／KNOWN-ISSUES.md → none」案例是同一條路徑的機械證據。

日期：2026-09-04｜HEAD：`b9cb8150a30be2b69b07a615e02f5ed8b9f21d2b`｜hash_schema：v6

量測定義（兩個 arm 一致，不得混用）：

- **區塊全文** = 從 `description: >` 這一行起、到最後一行縮排內容為止（含各行尾端換行），
  不含前後的 `---` 與 `name:` 行。
- **純值** = 同上但不含 `description: >` 這一行。
- 一律 UTF-8、LF、不做正規化。

## arm A — 11g 基準的舊 description（pre-bounded）

來源檔：[`runs/20260901-batch11-ab-old-desc/inputs/old-description.SKILL.md`](runs/20260901-batch11-ab-old-desc/inputs/old-description.SKILL.md)
（該 run 的 old 側變體 bundle `610dbea83a82`，hash_schema v1，與現行 v6 的值不可直接比較）

| 量測對象 | SHA-256 |
|---|---|
| 區塊全文 | `f85de9b22643770b3455b83c0d380d8280285d93e2397a853e154b931146a13a` |
| 純值 | `25120b42861022dc6d65dbbebfec5c1733f278e2a0dfd5088da4466785f7ba8d` |
| 來源 SKILL.md 全檔 | `4f465d6629160411399c3bc6539769dee3c52721aa8d48dc3727ad8ab62d3fdb` |

```
description: >
  在任務執行中判斷何時調高模型能力或 reasoning effort、何時可以宣告完成、何時應該暫停
  詢問使用者、何時換路,以及如何獨立驗收產出物。用於使用者要求「獨立驗收產出物」
  「逐條檢查產出物有沒有做到」、提到「算完成了嗎」「完成了嗎」「卡住了」「一直修不好」
  「該問使用者嗎」「要不要換模型或做法」「這樣品質夠嗎」、多步驟任務即將宣告完成,
  或同一問題重複失敗。
  不用於沒有出現上述決策點的一般實作。
```

## arm B 對照基準 — KI-07 修改**前**的現行 description

來源檔：`skills/discipline/judgment/SKILL.md`，本 cycle 修改前的狀態。

| 量測對象 | SHA-256 |
|---|---|
| 區塊全文 | `cede102f4a12fd175f7ee894b4c724eb88ae6b6eec4563a9345448cec4223470` |
| 純值 | `85e73291f6133ca4ec92c4b76f0b576e62a689fccc8d827f84f2fb473c617b83` |
| 修改前 SKILL.md 全檔 | `57f277f03fbb03570677ac76ed5b3d24203a39f634d5bc597e24dde3edeeba5a` |
| 修改前 `judgment_skill` domain hash（v6） | `0c5a3deaec63cb3c39c1aea4b0b6417784a734d33b3b1ad3edf84334738de7ac` |

```
description: >
  在任務執行中判斷何時調高模型能力或 reasoning effort、何時可以宣告完成、何時應該暫停
  詢問使用者、何時換路,以及如何獨立驗收產出物。用於使用者要求「獨立驗收產出物」
  「逐條檢查產出物有沒有做到」、提到「算完成了嗎」「完成了嗎」「卡住了」「一直修不好」
  「該問使用者嗎」「要不要換模型或做法」「這樣品質夠嗎」、多步驟任務即將宣告完成,
  或同一問題重複失敗。
  也用於多模型交叉複查、要求第二意見、裁決 reviewer 意見或 findings 的 disposition、
  對既有 findings 做 closure verification,
  或複查來回多輪、範圍持續擴張而無法收斂時。要求第二意見時,即使尚未提供待驗產出物,
  仍先由 judgment 確認產出物與驗收條件,但不啟動有界複查 cycle。
  不用於沒有出現上述決策點的一般實作,也不用於一般一次性 code review 或文件審閱。
```

## 對 DE-01 的效力

依 DE-01 協定第 1 條，arm B 必須是**最終要發布的那一份** description。KI-07 會改寫
description，因此上表的「修改前現行 description」**不是** DE-01 的 arm B，只作為
變更前後的對照基準。DE-01 執行時 arm B 需重新量測 KI-07 定稿後的 description 與
`judgment_skill` hash。

arm A 已凍結於本檔，DE-01 執行時直接沿用上方原文，不再從 run 目錄重新推導。

## arm B 候選 — KI-07 修改**後**（2026-09-04 本 cycle 產出，含 closure 第 1 筆 finding 的 KI-09 修正）

只有在 KI-07 之後沒有再改動 description 的前提下，這一份才是 DE-01 的 arm B。
A/B **尚未執行**，本節只提供凍結量測值，不含任何觸發率。

| 量測對象 | SHA-256 |
|---|---|
| 區塊全文 | `f18afdd0c145c5551f77797cff085f238c886654f537659c21d1ffb7ee5eed36` |
| 純值 | `78acf3135a458cb6c22051d644d94f67be2622197c11ddc97978c1476a3fde2f` |
| 修改後 SKILL.md 全檔 | `10a88e48388811d5bc957055ee960ae81b92fecc5bd3faaaeabdadd1ac36439e` |
| 修改後 `judgment_skill` domain hash（v6） | `a26b436888d81e7181199932590ca29f21e58ff9b8066eb792458e68ed5b3d47` |

本次新增的觸發面（相對 arm A 與修改前的現行版）：

```
  也用於在兩個以上互斥方案之間取捨、且選錯代價高的提問,包含以徵詢語氣提出時
  (如「照 A 方案還是不相容的 B 方案」「選錯會讓已有用戶必須重寫」「你覺得呢」)。
```

依 DE-01 協定第 1 條，跑 A/B 時除 description 外的所有 domain 必須逐 hash 相同：
`fixtures`、`runner`、`evaluator`、`execution_context`。**注意 judgment 的 fixtures 已連改兩輪**
（judgment fixtures domain hash `c7559b71…` → `d635c98e…` → `3d225afc…`），A/B 兩個 arm 必須
都跑在**最後一版**上。

| 版本 | judgment `fixtures` domain hash（v6） | 說明 |
|---|---|---|
| batch-12 定稿 | `c7559b7168d92ceba6304cefa78a234185b07e640eb51a179d87dd4d759de52c` | DE-01 **不得**使用 |
| 20260904 cycle | `d635c98e5d2959b3b15d72bdbdb5ffc40c6cc847b6da7d445e07602f3a75944c` | DE-01 **不得**使用 |
| 20260904-followup（現行） | `3d225afc58e479eef05efc156d599c94b57684bcd729e754411831889bad3d4f` | **DE-01 綁定此值** |

`skills/discipline/judgment/evals/fixtures.json` 全檔 SHA-256：
`8a6d99f4279db9b091f3fdd8ee41721883f50eec08d1ea72e5b578c5fbc9f109`。
DE-01 若改用縮減版 fixture 檔，該檔的 `fixtures` domain hash 須另行凍結並記於
[`DE-01-PREFLIGHT.md`](DE-01-PREFLIGHT.md)，兩個 arm 一致；此時本表的值只作為血緣註記，
不得宣稱該輪與 batch-12 的絕對觸發率可直接比較。
