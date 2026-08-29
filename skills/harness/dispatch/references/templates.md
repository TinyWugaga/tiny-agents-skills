# 派工 Prompt 模板

只在 `dispatch` 判定要派工、準備寫派工單時讀本檔。

用法:複製對應模板,填掉所有 `{...}` 空格後派工。**任何空格填不出來,代表你還沒想清楚,
先想清楚再派**。所有模板共用的規則:subagent 看不到主對話,一切上下文要寫進 prompt;
回報遵守 `SKILL.md` 的「回報合約」章節(結論 + `檔案:行號`,長產物落檔傳路徑,上限約 40 行)。

> **成本提醒**:內建唯讀探索 agent 現在**預設繼承主對話模型**,不再固定跑低成本 model。
> 要省額度必須 per-invocation 明寫 `model`(`Agent` tool 的 `model` 參數)。
> 細節見 [`claude-code-capabilities.md`](claude-code-capabilities.md)。

---

## 1. 搜尋 / 掃 repo（→ 唯讀探索 agent，**明寫 `model: {低成本 model 別名，查 claude-code-capabilities.md 後填入}`**）

```
目標：找出 {要找什麼，例如「所有呼叫 dispatch() 且 event type 為 'consumed' 的位置」}。
動機：{為什麼找，例如「要改 consumed event 的 payload 形狀，需知道全部影響面」}。
範圍：{目錄/檔案類型，例如「src/ 下的 .ts/.tsx，排除測試檔」}。
驗收條件：列出每個符合位置的 檔案:行號 與一行說明；若一個都沒有，明確回報「零筆」而非沉默。
    總數必須附上機械計數佐證（如 `grep -rn "dispatch(" src | grep -v "^\s*//" | wc -l` 的輸出），
    清單筆數與機械計數不符時，說明每一筆差異的原因（註解、字串、型別定義），不准直接報一個數。
回報格式：條列，每條 `路徑:行號 — 一行說明`。不要貼程式碼本體。上限 30 條，超過先回報總數再問我要哪部分。
```

⚠️ 這個 agent 跳過 CLAUDE.md 與 git status——需要它遵守的專案規則,要給**檔案路徑**。

## 2. 實作（→ 中階 model，effort 中高）

```
目標：{做什麼，例如「實作 shoppingList 的 sourceItemId 回填邏輯」}。
動機：{為什麼，這決定邊界情況的取捨方向}。
上下文：{相關檔案路徑；必讀的架構原則，例如「狀態只能經 dispatch 改，見 references/conventions.md」；已做的決策}。
不要做：{明確排除項，例如「不要動 Firestore schema、不要新增依賴」}。
驗收條件：
- {可機械檢查條件 1，例如「npm test 全綠，含新增 X.test.ts 覆蓋 A/B/C 三情境」}
- {條件 2，例如「tsc --noEmit 無錯」}
- diff 只含本任務相關檔案。
回報格式：改動檔案清單（路徑:行號範圍）、測試指令與結果、未盡事項。不要貼完整 diff。
```

## 3. 重構（→ 中階 model；模式明確的批次套用降到低成本 model）

```
目標：把 {對象} 從 {現狀} 改為 {目標形狀}。
動機：{例如「為 SyncStrategy 升級鋪路」}。
不變量（重構的定義）：對外行為不變——{列出證明方式，例如「既有測試一條都不能改、全綠」}。
步驟約束：{例如「一次一個檔案，每檔改完跑一次測試再繼續」}。
驗收條件：既有測試 0 修改、全綠；tsc 無錯；{其他}。
回報格式：改動清單 + 測試結果。若中途發現不改測試無法完成，停下回報，不要擅自改測試。
```

## 4. 研究（→ 可連網的通用 agent）

```
問題：{要回答的具體問題，例如「vite-plugin-pwa 在 iOS Safari 的離線快取限制」}。
動機：{要做什麼決定}。
來源要求：優先官方文件與 issue tracker；每個結論附來源 URL 與查閱日期；區分「文件明說」與「社群經驗」。
驗收條件：直接回答問題本身，含 {例如「限制清單、各自的 workaround、對本專案的建議」}；查不到就寫查不到，不要推測補完。
回報格式：結論先行（≤10 行），來源列表附後。完整筆記若超過 40 行，落檔到 {路徑} 只回傳路徑。
```

## 5. 審查（→ 中階 model；高風險升旗艦）

```
審查對象：{diff 範圍或檔案清單；用 git diff 指令描述，例如 `git diff main...feature-x`}。
審查重點：{例如「dispatch-only 紀律、hook cleanup、breaking change 影響面」——當前環境有專案專屬的 review skill 時指名套用，並附該 skill 名稱}。
明確不審：{排除項，避免發散}。
驗收條件：每個發現附 檔案:行號、嚴重度（blocker/should/nit）、一行修法建議；沒有發現就明說「無發現」並列出你檢查過哪些面向。
回報格式：按嚴重度分組條列。不要貼大段原始碼，引用 ≤3 行為限。
```

## 6. 驗收（→ 唯讀探索 agent；判準來自 judgment，不是本檔）

**前提**:驗收要不要做、做到什麼程度,由 `judgment` 決定。本模板只負責把 judgment 判定要做的
fresh-context 驗收正確地派出去。

派唯讀探索 agent。它**跳過 CLAUDE.md 與 git status**,所以下列六項**每一項都要顯式填寫**,
少任一項,verifier 規則要求該條回報 UNVERIFIABLE。

```
第一步：先讀 {judgment 的 verifier 規則檔完整路徑——依實際安裝位置填入，不要留佔位符}，依該檔規則執行本次驗收。

1. 產出物：{要驗的檔案或內容的完整路徑清單}
2. 驗收條件（逐條可判定）：
   1) {條件}
   2) {條件}
3. 適用指示：{必須一併對照的專案規則、安全限制}
   —— 給**檔案路徑**，例如 /Users/xxx/.claude/CLAUDE.md、docs/conventions.md。
      你讀不到 CLAUDE.md，不要假設你知道專案規則。
4. 版本標記：{commit hash 或 SHA-256，取得方式見下}
5. 允許的驗證方式：{可讀哪些資源、可跑哪些指令，例如「可跑 npm test 與 tsc --noEmit；不可連網」}
6. 環境限制：{權限、網路、sandbox、唯讀掛載等已知限制}

判定規則：每條回報 PASS / FAIL / UNVERIFIABLE + 證據（檔案:行號 或指令輸出摘要）。
整體判定優先序 FAIL > UNVERIFIABLE > PASS。只依產出物實際內容判定，不接受「應該有」的推論。
不要修復，只回報。
```

**版本標記怎麼取（commit hash 與 SHA-256 不可互換）**:

```bash
git ls-files --error-unmatch -- <path>   # 先確認檔案已被 track
git diff --quiet HEAD -- <path>          # 同時涵蓋 staged 與 unstaged 差異
```

- 兩個指令都通過 → 用 `git rev-parse HEAD` 的 commit hash
- 檔案 untracked,或任一指令失敗(表示與 HEAD 有差異) → 用 deterministic 的內容 bundle hash

⚠️ **內容 hash 必須路徑無關**。不要用 `find … | xargs shasum | shasum` 這種寫法——
`shasum` 的輸出含絕對路徑,派工方經 symlink 算、驗收方經實體路徑算就會得到不同值,
驗收會卡在版本綁定階段直接中止(本專案實際踩過)。
skill bundle 一律用現成腳本:

```bash
skills/harness/dispatch/scripts/bundle-hash.sh <skill 目錄>
```

其他產出物要自己算時,同樣以「**相對路徑 + 各檔內容 hash**」的組合為摘要對象,
不要把絕對路徑餵進摘要。**派工方與驗收方必須用同一個腳本或同一段指令**,
並把該指令原文寫進派工單的「版本標記」欄,讓驗收方能重算比對。

**絕對不給的一項**:執行者的推理過程。不提供、也不索取——這是 fresh-context 驗證的前提,
不是遺漏。

---

## 填好的完整範例（實作類）

```
目標：為 freshness 模組實作 deriveFreshness(item, now) 純函式。
動機：freshness 是推導值不落庫（架構原則 1），UI 與成就系統都會呼叫，正確性優先於效能。
上下文：型別定義在 src/types/item.ts；分級規則見 plugin references/architecture.md 的
freshness 段：fresh / near-expiry(≤2天) / expired。專案禁止在函式內讀取全域狀態。
不要做：不要碰 store、不要加快取。
驗收條件：
- 新增 src/domain/freshness.ts 與 freshness.test.ts，測試覆蓋三分級 + 邊界（剛好 2 天）+ 無效日期輸入
- npm test 全綠、tsc --noEmit 無錯
- 函式無副作用：不 import store、不讀 Date.now()（now 由參數傳入）
回報格式：檔案路徑:行號範圍、測試結果摘要。
```
