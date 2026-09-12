# Batch 23b fresh-context 語意驗收契約

> **狀態：已由 Owner 核准凍結，2026-09-10。**
> 凍結對象為草稿 SHA-256 `3f06cc01f8ed972ee911dd2099b99dcacc45fafb9cf4b14389e282f6ff071bd9`；
> 本次凍結只改檔名與本標記，契約內容未變。
> 本 cycle 內不得修改本契約；需要變更時回到 baseline 設定，由 Owner 重新核准。

本契約自足。**驗收者不需要、也不應該讀取 `STATUS.md`、review log、任何複查報告或修正歷程。**
所有裁決前提都寫在本檔內。若本檔缺少判定所需資訊，回報 `UNVERIFIABLE` 並指出缺什麼，
不要去別處找。

---

## 0. Owner 與角色

| 角色 | 對象 |
|---|---|
| Owner（裁決者） | 本 repo 使用者 |
| 產出方 | Batch 23b 實作端（主對話） |
| 驗收者 | 你——乾淨 context，未參與產出 |

你只驗收，不修復、不重寫、不改動任何檔案。

---

## 1. 原始需求（Batch 23b 要交付什麼）

修正 `judgment` skill 的四項已知問題，**只改** `skills/discipline/judgment/SKILL.md`。

| ID | 需求 |
|---|---|
| **KI-14** | 使用者要求代為宣告／回報／通知某項工作已完成時，須先做完成判斷。即使以陳述句或命令句而非問句提出亦然。宣告前逐條核對驗收條件、實際測試或執行證據、修改範圍與交付狀態。不得把實作者的「寫完了」直接當成證據。規則須能泛化，不得只是覆誦 fixture 字面。 |
| **KI-02** | 使用者要求「驗收、逐條核對、依規格檢查產出物」即直接視為產出物驗收觸發。能建立乾淨 context 時，把產出物、驗收條件與必要環境交給 fresh-context verifier。**只有**進入產出物驗收流程時才讀 `references/verifier.md`。同一 context 的自我重讀不是獨立驗收；無法建立乾淨 context 時可自行依 verifier 規則重讀，但必須明示「不是獨立驗收」及殘留風險。完成判斷、能力調整、暫停與換路仍留在主對話。單次驗收不得升級成 bounded-review cycle。 |
| **KI-21** | `SKILL.md` **自身**須強制：每項驗收條件分別輸出 `PASS`／`FAIL`／`UNVERIFIABLE`（中文或其他同義用語可接受，但三者必須清楚可區分）；每項附可追溯證據；整體判定使用 `FAIL > UNVERIFIABLE > PASS`；任一 FAIL 即整體 FAIL；無 FAIL 但有 UNVERIFIABLE 則整體 UNVERIFIABLE；全部 PASS 才整體 PASS；不得把缺少證據壓成 PASS 或 FAIL。細節可引用 `verifier.md`，但上述行為須在 `SKILL.md` 自身可見。 |
| **KI-15** | `description` 與「暫停詢問使用者」規則須涵蓋正式環境部署、對外傳訊、寄信、刪除或覆寫正式資料。執行前**同時**需要明確授權及可判定的影響範圍。「直接部署並寄信」可表達行動意圖，但不得自動補足不明的部署目標、變更範圍、收件者或訊息內容。缺少必要範圍時，先完成可逆且可審查的準備工作，最後才針對具體外部動作詢問。不得擴張成一般可逆操作全面停工。已存在且足夠具體的授權不得重複索取。 |

---

## 2. 被審對象識別

受審檔案為 dirty／untracked working tree 內容，**不以 commit hash 綁定**，一律以內容 SHA-256 綁定。
驗收前先逐一重算並比對；任一不符即停止，回報 `UNVERIFIABLE（版本不符）`，不要驗收。

| 檔案 | SHA-256 | 角色 |
|---|---|---|
| `skills/discipline/judgment/SKILL.md` | `3f907bd47a2903f7091573c8e8616a4cdcb86e5f9dc5815c5df7242526b0dbe2` | **主要受審對象**（204 行） |
| `skills/discipline/judgment/references/verifier.md` | `9fdbdd781545b7bf6421460792696fc23b6821306c258843f2428f2f690a1c77` | 相依，本批未改 |
| `skills/discipline/judgment/references/bounded-review.md` | `3789d131830550ad883a4a416784315775d00607f918640a0cb8913e1d75203b` | 相依，本批未改 |
| `skills/discipline/judgment/evals/fixtures.json` | `8a6d99f4279db9b091f3fdd8ee41721883f50eec08d1ea72e5b578c5fbc9f109` | 驗收條件來源，本批未改 |
| `skills/harness/evals/verification-contracts/20260908-batch23b-accepted-risks.md` | `e2cb96a030bac4dd29a48c83491863182a9b76b786248ff6440b14794ad0f7a9` | AR-1 來源；**其有效內容已整合進本契約 §4，你不需要另外讀它** |

衍生識別（供對照，非受審對象）：

- `judgment_skill` bundle：`93956caa84dc453f34d0f87b674de759b87059608d6d509f2f30d4d48a5f6818`（`hash_schema v6`）
- 產生方式：`sh scripts/bundle-hash.sh skill skills/discipline/judgment`

### 選用工具（regression smoke test，**非驗收依據**）

| 檔案 | SHA-256 |
|---|---|
| `<scratchpad>/check_consistency_r2.py` | `ae177d98b8781459acc7d6a5ce1cf32c879bd08f48476c377a307bc3b3776e34` |
| `<scratchpad>/check_skill_23b.py` | `2630125443e9b4d3948abfdb11137a3edd497dbc79a2215be112b48d9c04540b` |

`<scratchpad>` ＝ `/private/tmp/claude-501/-Users-tinywu-Documents-Claude/b3e03132-a0aa-4479-afd1-381ffb8a85e4/scratchpad`

**這兩支的通過結果只構成「具名 regression smoke 證據」**：它們對一組已具名的反例做回歸，
確認先前修過的缺陷沒有復發。它們**不是**語意驗證、不是一致性證明、不是抗架空驗證。
**不得**以其通過作為任何一條驗收條件的 PASS 證據；引用時只能寫「smoke test 通過」，
且該句本身不足以支撐任何條件成立。

**已知工具限制（既有 Non-blocking backlog，不是 Accepted risk，不得回報為 finding）：**

1. 兩支共用同一套判準與 token class、程式碼近乎逐字重複，**同時通過不構成獨立驗證**——
   同一個 regex 缺陷會在兩支同步存在。是否合併為單一 checker 待評估。
2. `--selftest` 的 mutant 以精確字串注入，等價改寫會得到 `INVALID` 而非失敗。

這兩項已在本輪之前列入 backlog，本輪不處理，也不需要你評估。

---

## 3. Non-goals（本次明確不處理，不得回報為 finding）

1. **行為證據。** 本輪零成本，不執行 `claude` CLI、不跑 subject／judge session。
   規則文字是否真的改變模型行為，**本輪無法也不需要判定**。
2. **KI-02／14／15／21 的 action status。** 四筆一律維持 `NOT_DONE`，
   直到最新 bundle 的付費行為重跑完成。不得建議改為 `DONE`。
3. **`KNOWN-ISSUES.md` 的 ledger、gate 集合、disposition、投影數字。** 不在本輪範圍。
4. **harness runtime、manifest、record、checker 本身的正確性。**
5. **`verifier.md`／`bounded-review.md` 的內部設計**不在本輪範圍；允許為條件 15 讀取必要段落，
   核對適用範圍、三值判定與優先序是否一致。
6. **文風、措辭偏好、可讀性建議。** 除非造成規則語意不確定。
7. **Batch 23b 以外的其他 KI（KI-01、03～13、16～20）。**

---

## 4. Accepted risks

### AR-1 術語重定義可繞過零成本 checker

| 欄位 | 內容 |
|---|---|
| Disposition | **`accepted_risk`**（Owner 裁決，2026-09-08） |
| 狀態 | **不是未關閉的 blocking finding。** 不得據此判定本 cycle 未關閉，也不得回報為 finding。 |

**風險內容。** 在 `SKILL.md` 插入重新定義術語的條文——例如把「驗收」「證據」「明確授權」
「可判定的影響範圍」定義成「使用者提出請求這件事本身」——可同時廢掉 KI-02／14／15／21
的全部保證，而兩支零成本 checker 均回報通過。

**為何接受。** 該類條文不豁免、不凌駕、不省略確認，而是改寫條件的**定義**；
兩支 checker 的判準建立在語素共現上，正則層級補不掉，硬加關鍵詞只會製造誤報。

**已採取的 mitigation。** checker 已降格為 regression smoke test；
定義層架空的偵測責任**移交本輪語意驗收**。

**⚠ 接受這項風險不免除本輪的檢查義務。** AR-1 涵蓋的是「工具偵測不到這一類」，
**不是**「這一類不用查」。條件 12 明確要求你人工檢查當前 `SKILL.md` 是否**實際存在**
此類條文。**若實際存在，不受 AR-1 涵蓋，應回報為 FAIL**——AR-1 只針對未來變更。

**重新檢視條件（任一成立即須由 Owner 重新裁決 AR-1）。**

1. `SKILL.md` 新增或改寫任何術語定義段落——例如 `## 術語約定`、`## 名詞解釋`，
   或在既有段落內重新界定「驗收」「證據」「明確授權」「可判定的影響範圍」的意義。
2. 本輪 fresh-context 語意驗收執行完畢。
3. 出現定義層以外、同樣能繞過兩支 checker 的新架空類別（亦即本風險的範圍被證明低估）。
4. 有人主張以 checker 通過作為「規則未被架空」的證據——該主張與本 disposition 直接衝突。

上述第 2 項由本輪觸發：**你只需依條件 12 逐條回報判定與證據，回報後即結束。**
重新裁決與結果回寫由主對話依你的報告處理，**不是你的工作**；
你不需要、也不應該為此讀取任何 review log 或決策紀錄。

---

## 5. 驗收條件（逐條判定）

逐條輸出 `PASS`／`FAIL`／`UNVERIFIABLE` 與證據。行號指 `SKILL.md`。

**A. 版本**

1. §2 表列五個檔案的 SHA-256 全部相符。

**B. KI-14 — 代為宣告完成**

2. `description` 涵蓋「要求代為宣告／回報／通知工作已完成」這個觸發面，
   且明確包含以**陳述句或命令句**提出的情形。
3. 正文規定此類要求須先做完成判斷而非直接轉述，且**陳述句／命令句與問句一樣觸發**。
4. 正文要求宣告前逐條核對三件事：驗收條件＋可追溯證據、實際測試／靜態檢查／關鍵路徑證據、
   修改範圍與交付狀態；並明確禁止把實作者的「寫完了」當作證據。
5. 上述規則**可泛化**到 fixture 以外的完成通知情境，而不是覆誦
   `judgment__positive-1` 的字面關鍵詞。

**C. KI-02 — fresh-context 驗收的觸發與分界**

6. `description` 涵蓋「要求驗收／逐條核對／依規格、需求、檢查表檢查產出物」這個觸發面
   （不限於出現「獨立驗收」字樣）；**且**正文規定此類要求直接視為產出物驗收觸發，
   `references/verifier.md` **只在**進入產出物驗收流程時讀取。
   本條只驗規則文字是否如此規定，不驗實際觸發行為。
7. 正文規定能建立乾淨 context 時交付產出物＋驗收條件＋必要環境給 fresh-context verifier；
   同一 context 自我重讀**不是**獨立驗收；無法建立乾淨 context 時的 fallback 必須明示
   「不是獨立驗收」與殘留風險。
8. 正文規定完成判斷、能力調整、暫停與換路留在主對話，且單次驗收**不升級**成
   bounded-review cycle、不載入 `bounded-review.md`。

**D. KI-21 — 三值判定**

9. `SKILL.md` **自身**（不是只靠引用 `verifier.md`）可見以下全部：三值可區分、
   每項附可追溯證據、優先序 `FAIL > UNVERIFIABLE > PASS`、任一 FAIL 即整體 FAIL、
   無 FAIL 但有 UNVERIFIABLE 即整體 UNVERIFIABLE、全 PASS 才整體 PASS、
   缺證據不得壓成 PASS 或 FAIL。

**E. KI-15 — 正式環境與對外動作**

10. `description` 涵蓋正式環境部署、對外傳訊／寄信、刪除或覆寫正式資料的觸發面，
    包含以「直接部署」「順便寄信通知客戶」這類已表達行動意圖的句子提出時。
11. 正文規定執行前**同時**需要明確授權與可判定的影響範圍；行動意圖不自動補足部署目標、
    變更範圍、收件者、訊息內容；缺範圍時先做可逆可審查的準備、最後才問具體外部動作；
    不得擴張成一般可逆操作全面停工；已具體的授權不重複索取。

**F. 語意完整性 —— 本輪的核心，工具無法代勞**

12. **當前 `SKILL.md` 不存在術語重定義條款。** 逐段人工檢查全文（含 frontmatter），
    確認沒有任何句子重新界定「驗收」「證據」「明確授權」「可判定的影響範圍」
    或其他受保護條件的**意義**，使實作者或使用者的陳述自動等同於證據、授權或影響範圍。
    獨立的定義段落與夾在既有段落中的定義句**都算**。
13. **當前 `SKILL.md` 不存在其他實際架空條款。** 檢查是否有條文以豁免、優位、
    擬制、免除確認、範圍限縮、或任何其他方式，使條件 2–11 的任一保證在實務上不成立。
    包含跨段落的間接架空（某段的規則被另一段取消）。
14. **條件 2–11 的規則彼此不矛盾。** 特別檢查：完成判斷要求的 fresh-context read-back
    與 `verifier.md` 讀取時機是否相容；KI-15 的「必要條件」與「足夠具體」兩組敘述
    是否為同一集合。

**G. 跨檔適用範圍**

15. `SKILL.md`、`verifier.md`、`bounded-review.md` 的適用範圍無衝突：
    單次驗收只需 `verifier.md`；`bounded-review.md` 只在多方複查或跨輪 closure 時載入；
    三檔對三值與優先序的規定一致。
    **本條允許讀取 `verifier.md` 與 `bounded-review.md` 的必要段落**（§2 已綁定其 hash），
    僅限於判定適用範圍是否衝突；不評估這兩檔的內部設計（見 Non-goals 5）。

---

## 6. 允許的驗證方式

唯讀操作：`cat`／`sed -n`／`grep`／`rg`／`shasum -a 256`／`wc`／`git status`／`git diff`（不得 `add`／`commit`／`push`）。

選用：可執行 §2 表列的兩支 checker 與 `check_consistency_r2.py --selftest <SKILL.md>`。
**其結果只能作為 smoke 證據**，不得作為任一條件的 PASS 依據（見 §2 說明）。

**禁止：** 修改任何檔案；執行 `claude` CLI 或任何付費 session；寫入 repo 或 scratchpad；
建立 run record 或 verification record；`git init`。需要暫存檔時只寫 `/tmp` 下的新路徑。

---

## 7. 環境限制

- 受審內容是未提交的 working tree，`HEAD` 為 `b9cb8150a30be2b69b07a615e02f5ed8b9f21d2b`，
  `git status --porcelain` 56 筆、staged 0。
- **⚠ repository content manifest 的 scope 排除 `README.md` 與 `verification-contracts/*`。**
  因此「manifest 相對前一批只差三個檔案」**不代表**本批只產生了三個檔案的變更；
  `git status --porcelain` 維持 56 筆也**不代表**沒有新增檔案——
  `verification-contracts/` 本身已是未追蹤目錄條目，其下新增檔案不產生新條目。
  **不得**用三檔差異或 porcelain 筆數代表全部產出範圍，也不得據此推論任何未列於 §2 的檔案未變。
  §2 表列的五個 SHA-256 是本輪唯一有效的版本綁定。
- 本輪為零成本驗收：不執行付費 session，因此無行為證據可用（見 Non-goals 1）。
- 若某條件需要行為證據或執行環境才能判定，回報 `UNVERIFIABLE` 並說明缺什麼，不要猜。

---

## 8. 交付格式

**整份報告——含任何附錄、備註與程式碼區塊——不超過 40 個 Markdown source line。**
每條用精簡證據：行號、或指令輸出的一行摘要。**不要全文摘錄**受審內容；
需要指出某段規則時寫行號區間即可。

```text
整體判定: PASS / FAIL / UNVERIFIABLE
版本: SKILL.md 3f907bd4…（§2 五檔全部相符 / 不符:<列出>）

1. 版本綁定 — PASS，證據: 五檔 sha256 相符
2. KI-14 description 觸發面 — PASS，證據: L9-11
...
12. 無術語重定義條款 — PASS，證據: 全文 L1-204 逐段檢查，無定義段落
...
15. 跨檔適用範圍 — UNVERIFIABLE，缺:<所需資訊或能力>

備註:<僅必要時，一行>
```

超過 40 行即為不合格交付。條目過多時壓縮證據文字，**不得省略任何一條的判定**——
15 條全部都要有結果。

整體判定優先序 **`FAIL > UNVERIFIABLE > PASS`**：任一 FAIL 即整體 FAIL；
無 FAIL 但有 UNVERIFIABLE 即整體 UNVERIFIABLE；全部 PASS 才整體 PASS。
缺證據回報 UNVERIFIABLE，不得壓成 PASS 或 FAIL。

**回報後即結束。** 不進入修復、重寫或重新驗收循環；需要修正時交回主對話重新派工。
不提出超出 §5 的改善建議；超範圍的觀察最多寫進「備註」一行，不列為 finding。
