# 規格：ledger-consistency checker（零成本 tooling batch）

**狀態**：第 4 次 fresh-context 驗收已於 2026-09-05 **達到門檻**
（無 FAIL；`UNVERIFIABLE` 僅第 16 條；正式 verdict `UNVERIFIABLE`）。
排序：本批 → 才進第 2 批 runtime 實作。
本規格已隨 2a 落地於 `scripts/`，**但尚未納入版本控制**（整個 `scripts/` 目錄目前為
untracked）。**第 4 次驗收的 verification record 於 2b 才建立**——2a 不產生任何
verification record，也不宣稱已納入版控。

## 本批拆成 2a／2b

凍結的三個文件在 2b 才會被改動，因此 2a 可立即開工而不破壞現行凍結。

| 階段 | 內容 | 是否動到凍結檔 |
|---|---|---|
| **2a** | 寫兩支 checker 與 selftest（只動 repo 根目錄 `scripts/`），規格一併落檔。selftest 用合成 fixture，不依賴真實文件，因此在 marker 尚未插入前即可完整跑綠。**完成界線：只能宣告「checker 核心與 synthetic tests 完成」，不得宣告工具已能驗證正式文件**——正式整合要等 2b 的 marker 落地 | 否 |
| **2b** | 插入 marker（並把 marker 區內的散文數字改為引用表格，使區內無自由浮動的數字）；建立 `verification-records/`；把驗收歷程自 RECHECK 移除；首次以 checker 驗真實文件 → **重新凍結 → 再驗一次** | 是 |

## 2b 必須一併處理：驗收狀態的自我指涉

RECHECK 目前**在自己內部記錄自己的驗收狀態**（§7 的歷程表與「尚缺第 N 次」）。
這造成無解的回歸：**寫入第 N 次的結果就會改動剛被第 N 次驗證的檔案，於是又需要第 N+1 次。**
第 4 次的結果因此刻意**未**寫入 RECHECK，暫存於 `ROUND4-RESULT.md`。

**修法**（2026-09-05 修訂：單一 mutable log 的版本已否決——
排除版本鎖定等於可被任意修改而不觸發任何警示，不能作為 authoritative evidence）：

1. RECHECK **移除**「尚缺第 N 次」與自身的驗收歷程，只保留穩定的判定與證據。
2. 每輪產生**獨立、不可覆寫**的紀錄：
   `verification-records/<YYYYMMDD>-round<N>-<subject-digest>.md`
   （`subject-digest` = 被驗三檔 SHA-256 的 canonical digest，寫進檔名使內容與身分綁定）。
3. 每份紀錄**必須**包含：被驗三檔的完整 SHA-256、HEAD、**驗收契約本身的 hash**、
   正式 verdict 與門檻結果、verifier 的 session／task ID
   （**取不到時必須明示「無法證明 freshness」**，不得省略）、原始輸出的 digest。
4. `VERIFICATION-LOG.md` 若保留，**只作為這些 immutable records 的索引**，
   **不得作為 gate 的唯一依據**。
5. 由實作者抄錄的紀錄**只能算 archive**，不因落檔而取得獨立 provenance——
   這一點必須寫在每份紀錄裡，與 closure §6 的自述同一標準。

## 放置與 identity

repo 根目錄 `scripts/`。已確認**不在任何 subject identity allowlist 內**：
`bundle-hash.sh` 的 skill／evaluator／runner 三個 mode 都先 `cd` 進傳入目錄再 emit 相對路徑
（skill = 該 skill 目錄下的 `SKILL.md`＋`references/**`＋`scripts/**`＋`assets/**`＋`agents/**`；
evaluator = `evals/{judge,score,record}.py`；
runner = `evals/{run-suite.sh,run-fixture.sh,transport.py,manifest.py}`）。
因此新增本工具**不會作廢九輪證據**。

## 產出形態

**兩支獨立的 Python checker ＋ 一支 selftest。不要用一支腳本混合兩種資料模型。**

| 檔案 | 職責 |
|---|---|
| `scripts/ledger_check.py` | ledger 結構與跨文件數字一致性 |
| `scripts/run_domain_check.py` | run record 的 domain 完整性與 freeze table 綁定 |
| `scripts/ledger_check_selftest.py` | 兩者的正向與**負向**案例 |
| `scripts/ledger_check_mutants.py` | 可重現的 mutation runner |

檔名使用底線而非連字號：selftest 需要直接 `import` 兩支 checker。

## CLI 契約

* stdout：人可讀的逐項結果；stderr：僅錯誤與診斷。
* exit code：**`0` 一致／`1` 資料不一致／`2` 輸入、格式或使用方式錯誤**。
* `run_domain_check.py` **不掃描整個 `runs/`**。受驗 run 集必須由參數或 manifest
  明確傳入，避免混入無關 run。空 run 集為 `2`。

## 硬性設計約束

1. **不得硬編 `20`、`15`、`5` 或任何 KI ID 清單。** 全部從 ledger 推導。
   文件內的彙總數字是**被檢查的對象**，不是檢查的依據。
2. **固定 marker 界定解析範圍。** `KNOWN-ISSUES.md` 與 `STATUS.md` 都保留大量歷史數字，
   全檔搜尋會發生「現值錯了，但歷史段剛好有正確數字而通過」。
   需加 marker 的區域（實作後定案）：`ledger:summary`（開頭摘要）／`ledger:active`／
   `ledger:retired`／`ledger:distribution`／**`ledger:gate-released`／`ledger:gate-blocked`
   （兩個具名集合必須各自成區，不得只留一個再取補集）**／`ledger:gate-totals`／
   `ledger:freeze`／`status:current-summary`。
   **每個 marker 必須恰好出現一次**；解析只在 marker 內進行；缺失或重複一律 fail closed。
   ⚠ 插入 marker 會改動 `KNOWN-ISSUES.md` 與 `STATUS.md`，
   **因此本批完成後必須重新凍結 hash 並再跑一次驗收。**
3. **受限 Markdown grammar**：每列必須是單一 physical line；支援 `\|` 轉義；
   header 名稱與順序必須精確比對；marker／table／header 缺失或重複一律 fail closed。
   `classification` 的 canonical value 明定為**第一個 inline-code token**，
   沿革註記只能出現在其後。canonical token 不明確時報 `2`。

4. **narrative 區採正面表列（2026-09-06 新增，第 5 次驗收 FAIL 後）。**
   `ledger:summary`／`gate-released`／`gate-blocked`／`gate-totals`／
   `status:current-summary` 這五個區**不是表格區**，早期只挑幾個 pattern 解析，
   其餘內容一格都沒讀。實測後果：在 `gate-released` 補一張表把一筆 disposition
   從 `ACCEPT_AS_KNOWN` 翻成 `FIX_SKILL`／`DONE`、在 blocker 表塞入不存在的
   `KI-99`、再補一條 `9 + 99 = 108`，checker 仍回「一致」`rc=0`。

   對「承載現值的措辭」做黑名單是自然語言問題——換一種寫法就繞過去，
   每輪各補一條 regex 只是在增加特例。因此改為**白名單＋殘餘檢查**：
   區內允許的計數形式只有 `` `LABEL` N ``、`IDs:` 行、`N 筆` 與算式，
   四種都各自被比對；把已消費的 `` `LABEL` N `` 扣掉之後，
   殘餘不得再出現任何計數或 `KI-nn`。具體規則：

   - 區內**不得有表格**（表格只屬於 `ledger:active`／`retired`／`distribution`）
   - `KI-nn` 在 gate 兩區**只能出現在 `IDs:` 行**，其餘三區**完全不得出現**
   - 算式必須**恰好一條**（舊版 `re.search` 只取第一條，第二條錯的完全不看）
   - `N 筆`：gate 兩區必須等於推導值；其餘三區一律不得出現（計數由算式承載）
   - **中文數字計數**（「四筆」）一律 fail closed——不受檢查的寫法不得存在

   ⚠ **殘留風險：把現值宣稱搬到 marker 之外，依構造偵測不到。**
   解析範圍限定在 marker 內是刻意的（見上方第 2 點：全檔搜尋會被歷史段的正確數字
   矇混過關），因此「搬出去躲檢查」無法用同一個機制擋住。這是 review 紀律，
   不是機械保證；**驗收契約應有一條要求人工掃 marker 外新增的現值宣稱**。

## `ledger_check.py` 必驗項

**ID invariant**（退役後的正確形式；「active 無缺號」是錯的判準）
- active IDs 無重複；retired IDs 無重複；**兩者互斥**
- **active ∪ retired == `1..max_id` 連續集合，不得缺號**
- retired ID 不計入 active 的任何統計
- 每個 retired 條目的「去向」指向**存在的 active ID**，且不得形成循環

**結構與值域**
- 每列欄數正確；malformed row 必須報錯，不得靜默跳過
- `classification` 落在五值域內（canonical token 判定）
- `Owner disposition`／`action status` 各自落在值域內
- 相容性：`ACCEPT_AS_KNOWN`／`NEEDS_EVIDENCE`／`PENDING` ⇒ `N/A`；
  `FIX_FIXTURE`／`FIX_SKILL` ⇒ `DONE` 或 `NOT_DONE`

**集合與同步**
- 放行與阻擋**互斥**，且**聯集等於 active 全集**
- 從 ledger 推導的分佈，與 marker 內的分佈表、gate summary、開頭摘要**逐格一致**
- `KNOWN-ISSUES.md` 與 `STATUS.md` 的 current summary 逐格一致

## `run_domain_check.py` 必驗項

- **required domain 集合與 `hash_schema` 由 CLI 契約輸入**（`--required-domain`、
  `--hash-schema`），**不得由被驗 record 推導**——否則九份 record 與凍結清單
  同時漏掉同一 domain 時會一起漏然後 PASS
- 每個 hash 值為 **64 位 hex**
- freeze table **一個值一列**，欄位為 `domain | 綁定值 | 綁定輪次 | 現算 | 來源`；
  綁定值預設為**完整 64 位 hex**，縮寫需顯式 `--allow-prefix`（較弱模式不得為預設）
- freeze table 與 run record 的 **value→run 綁定雙向一致**（含輪次集合本身，
  否則把 arm A／arm B 的兩個既有 hash 對調仍會 PASS）
- freeze table 無多餘列、無漏列，**無多餘的歷史值或歷史 run**
- run ID 唯一；每份 record 可解析且含 `hashes`

**明確不自動化**：「來源檔敘述與 `bundle-hash.sh` allowlist 相符」。
目前沒有可機讀的單一來源，檢查器自己重抄 allowlist 會建立第二份真相來源。
**本項留人工驗收**，且**不得為此修改 `bundle-hash.sh`**——那會讓本批擴張成 hash 工具介面變更。

## Mutation test（新增或修改檢查時必跑）

selftest 全綠**不代表檢查有效**：本工具的第一版把 `blocked` 定義成 `active - released`，
於是互斥與覆蓋檢查恆真，而當時的 34 個案例全數通過。

因此 mutation test 本身也是交付物：`scripts/ledger_check_mutants.py` 把
「停用某項檢查後至少有一個案例失敗」變成**可重跑的斷言**，不是實作者口述的紀錄。
每個 mutant 宣告 `killed`（必須殺掉案例）或 `implied`（被其他檢查邏輯蘊含，必須附理由）。

五個設計要點：

* **child 必須印出唯一的機讀完成摘要** `SELFTEST_RESULT total=N failed=M`，
  且必須是 stdout 的**最後一行**。runner 核對：摘要恰好一次、`total > 0`、
  `0 ≤ failed ≤ total`、**`total` 等於 stdout 的 ok 行數加 FAIL 行數**、
  **`failed` 等於 FAIL 行數**、`failed=0` ⇒ rc 0、`failed>0` ⇒ rc 1。
  缺摘要、重複摘要、摘要後仍有輸出、traceback、逾時、其他 rc 一律判 invalid。
  **只數 stdout 的 FAIL 行會把「先失敗、後崩潰」誤判成 killed；
  只核對 rc 則會漏掉「印完摘要之後才出事」。** 人可讀輸出與機讀摘要必須彼此印證，
  只信其中一邊時另一邊壞掉不會有人發現。
* **baseline child 走與 mutant 完全相同的邊界檢查，並記錄 `total`。**
  只看 baseline 的 rc 的話，baseline 若崩在半路而 rc 剛好落在 0／1，
  後面每個 mutant 的判定都建立在一個沒跑完的基準上。
  **每個有效 mutant 的 `total` 必須等於 baseline 的 `total`**——
  mutant 只該改變「案例通不通過」，改變案例總數代表 child 少跑或多跑了案例，
  那時 killed／survived 都沒有意義。
* `classify()` 有 **14 條內建自檢**（含 `total` 大於／小於實際結果數），任何一條不符 runner 直接 rc=2——
  它是唯一分辨「跑完」與「崩在半路」的地方，鬆掉的話所有 killed 判定同時失效。
  mutant 表另含兩個 `invalid` 期望的回歸項：先 FAIL 再 crash、以及完成但結果總數與 baseline 不同。
  另有 19 個 **code-sentinel mutant**：把某個 error code 的發出點換成 sentinel，
  綁定該 code 的案例必須失敗——驗證「該發出點確實被某個案例觸及」，
  比純文字的覆蓋比對更強。

* mutant **先過編譯檢查**——語法壞掉的 mutant 會讓 selftest 崩潰，看起來像
  「0 個案例失敗」，那是無效測試不是漏檢。
* mutant 可以是**多處替換**：只改常數卻不改呼叫端等於沒有弱化該檢查
  （hash cell 同時有錨點與 `fullmatch` 兩層保護，只拿掉一層測不出東西）。
* anchor 必須恰好命中一次，否則判定為無效 mutant。

**目前 20 個 mutant 全部宣告 `killed` 且全部被殺掉，沒有 `implied` 項目。**
早期版本曾把 gate 的 overlap／coverage／ghost／`stated_rel` 比對與 retired 循環分支
標為「被蘊含」——那個結論來自只比對 exit code 的測試。改成同時斷言 error code 後，
每一支都能被單獨殺掉，因此都是可獨立驗證的檢查。

## 負向 selftest（缺一不可）

marker 缺失／marker 重複／current summary 錯誤但歷史段有正確數字／
malformed row／active ID 重複／retired ID 重複／active 與 retired 同時出現同一 ID／
retired target 不存在／retired 形成循環／ID 從兩表同時消失（聯集缺號）／
unknown enum／disposition 與 action status 不相容／放行與阻擋重疊／聯集不等於全集／
KNOWN 與 STATUS 不同步／domain 缺失／domain 多出／freeze table 多餘舊 hash／
value 綁錯 run／record 缺 `hashes`／hash 格式錯誤／空 run 集／
classification canonical token 不明確。

每個負向案例都必須**同時核對 exit code 與 error code**。只比對 exit code 不夠：
案例可能因為另一條 invariant 被攔下而「因錯誤的原因通過」——舊版的「前綴模稜兩可」
案例其實兩個 hash 前綴並不相同，它是因為漏列第二個值才回 1，ambiguity 分支從未被執行。
`only=True` 的案例另外確認**沒有其他 error code**。

## 為什麼負向 selftest 是重點

本輪四次 fresh-context 驗收中，第 2、3、4 次抓到的都是同一形狀的缺陷——
主文改了、鏡像沒改。實作者的臨時檢查式則連續栽在同一種寫法上：
單行 substring、看不到「遺漏」、分不出歷史值與現值，
以及**用全檔 regex 掃 `| KI-nn |` 會把退役列算成 active**
（先前靠「欄數 == 8」意外排除，那是巧合不是設計——正是約束 2 要根除的）。
這些全是「正向通過但抓不到缺陷」。只跑正向案例的檢查器會原封不動複製同一個盲點。
