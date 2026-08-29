# harness

**平台專屬 collection——僅供 Claude Code 使用。**

本 collection 是 repo 根 README「跨平台原則」的明確例外。`discipline`、`creative`、
`productivity` 底下的 skill 刻意不寫平台專屬語法與模型名稱;`harness` 底下的 skill 反過來
**必須**談 Claude Code 的具體機制(`Agent` tool、subagent frontmatter、`/model`、`/effort`、
`/fast`、`settings.json` 環境變數、方案額度),因為它處理的就是這個 harness 本身的調度問題。

因此 harness 的 skill **不要**安裝到 Codex、ChatGPT 或其他平台——那裡沒有對應機制,規則會變成
誤導。

| Skill | 職責 | 觸發 |
|---|---|---|
| [`dispatch`](dispatch) | 要不要派 subagent、派給誰、怎麼寫派工單、失敗了怎麼調整能力 | 即將派工、選 model／effort、寫派工 prompt |

## 與 discipline 的分界

`dispatch` 只管**派工調度**。**完成判斷、驗收判準、停損與換路屬於 `judgment`**
(見 [`../discipline`](../discipline)),`dispatch` 不重述也不分叉:

| 情境 | 先觸發 | 後續 |
|---|---|---|
| 準備派 subagent／平行派工 | `dispatch` | 執行派工 |
| 直接問 model／effort 配對 | `dispatch` | 給 Claude Code 執行路徑 |
| 驗收、準備宣告完成 | `judgment` | 需要 fresh context 時才交給 `dispatch` |
| 同一問題兩輪失敗 | `judgment` | 判定要調整能力後才交給 `dispatch` |
| 一般實作 | 都不觸發 | 主對話直接完成 |

`dispatch` 的「驗證交棒」章節只提供 Claude Code 的執行機制(派唯讀探索 agent、
六項輸入怎麼給、版本標記怎麼取),**不產生任何完成條件**。

## 易變事實的處理

`dispatch/references/claude-code-capabilities.md` 是 harness 特有的設計:
所有會過期的平台數值(model 別名、effort 級別、fast mode 計費、巢狀深度、內建 agent 行為)
都集中在該檔,分**「官方支援」**與**「本機觀測」**兩欄,兩欄不互相覆蓋。
`dispatch/references/plan-and-quota.md` 用同一套規則處理**額度與消耗**事實
(跨 surface 共用池、並行倍增、Cowork 的相反預設),同樣分兩欄。
`SKILL.md` 只留決策流程,不內嵌會過期的數字。

這個切法有實證理由:2026-08-24 官方文件寫「fast mode 不支援 VS Code extension」,
08-26 重抓已改為「extension 跟隨 `fastMode` 設定並提供 Toggle 指令」。**48 小時內就變了。**
因此該檔的規則是「會影響當次決策的事實,執行前重查」,而不是任何形式的固定有效期。

## Source of truth

`dispatch/SKILL.md`、其 `references/` 與 `scripts/` 是 runtime 契約的唯一源頭,只在此 repo 維護。
`scripts/bundle-hash.sh` 是驗收雙方必須共用的同一份實作,屬契約物件而非輔助腳本。
其他發佈通路一律從這裡同步,不准分叉。runtime skill 內文不重複安裝方式與 source-of-truth
維護說明。

## 執行機制（fixture session 怎麼跑）

`evals/run-fixture.sh` 每筆 fixture 起一個真實的 fresh session。三件事決定它看得到什麼:

| 手段 | 作用 |
|---|---|
| `--setting-sources project,local` | 排除 user 層設定與 user 層 skills;session 的 cwd 是拋棄式 seed 副本 |
| `--plugin-dir <變體>` | 只餵入該變體要測的 skill 集合。plugin skill 仍是 model-invoked,名稱帶 namespace(`score.py` 以 `split(":")[-1]` 正規化) |
| `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` + `--append-system-prompt-file` | 不自動載入任何 CLAUDE.md,改以明確複製的規則檔注入 |

**不使用 `CLAUDE_CONFIG_DIR`。** 換 config dir 會連 host 的登入狀態一起切掉。

**憑證一律不搬運**——不讀取、不複製、不匯出、不輸出、不建立連結、不留存於 repo 或暫存目錄。
登入沿用 host 預設路徑。`--settings` 只帶消毒後的單一鍵
`env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`,絕不整份帶入 user `settings.json`
(那裡面有 `enabledPlugins` 與 marketplace 設定)。

work dir 與 plugin 變體建在 `mktemp -d`(repo 外,mode 700),複製的 skill 與規則檔設為唯讀,
收尾清除。seed 一旦夾帶 `CLAUDE.md` 或 `.claude/`,`project,local` 會讀進去而安靜破壞隔離,
因此 runner 有 fail-closed 防呆會直接中止。

### fail-closed 的四道關卡

1. **preflight**——18 筆迴圈之前,先用**完全相同的隔離執行路徑**跑一筆真實 session。
   不通過就 `exit 2`,不跑任何 fixture、不呼叫 judge。這道關卡的存在理由:前置檢查只驗得到
   「`claude` 這支指令在」,驗不到 session 能不能推論;少了它,一次登入或設定問題要跑完 18 筆才發現。
2. **`score.py` 三值 exit**——`0` 全過 / `1` 有 FAIL 但每筆都有可用觀測 /
   **`2` 有 ERROR 或 NOT_RUN**,亦即有 fixture 根本沒產生可用觀測。
3. **routing 不可用時完全跳過 judge**——`score.py` 回 2 就不呼叫 judge。
   對空的或失敗的 trace 送 judge 只會燒錢並產生假的 contract FAIL(實際發生過)。
4. **suite exit code 聚合**——CLI 失敗數、routing rc、contract rc、record rc 任一非 0,
   整支 suite 即非 0。

### run record 的三值判定

`record.py` 產生的 `run_status` 是 **PASS / FAIL / INVALID** 三值,另有 `is_contract_evidence`:

- **FAIL** = 每一筆都產生了可用觀測,而其中有觀測不符預期 → 這是關於 skill 的證據。
- **INVALID** = 有 fixture 根本沒產生可用觀測(CLI 失敗、逾時、未跑、judge 無法判定)
  → 這一輪對 skill 什麼都沒說,**不得被當成契約證據**。

少了這個區分,一輪「登入過期、全部在推論前就失敗」的執行會被記成 FAIL,日後讀起來像是 skill 沒通過。
成本欄位取自 session 自報的 `total_cost_usd`,任一來源缺漏就寫 `null`,不以推估補完。

## Evals

兩層:

- `dispatch/evals/fixtures.json` — 驗 `dispatch` 自身觸發(schema v2 五欄)
- `evals/routing-fixtures.json` — harness 整合測試:`judgment ↔ dispatch` 邊界與交棒、
  任一 skill 缺席時的 fallback、`Agent` tool 不可用時的行為。
  除 schema v2.1 六欄(含 `env`)外,每筆另有可機器判定的 `expected_route`

`skill-absent-fallback` 這類案例**必須**放在 routing 這層:skill 不存在時,它自己的
fixtures 也載入不了,無法自我驗證。

執行結果摘要落檔到 `evals/runs/<RUN_ID>/<RUN_ID>.{json,md}`。失敗的 run 必須保留
摘要與判定所需的最小證據；`raw/` 內的完整 trace 只存本機 archive 或 CI artifact，
不進版本控制。每筆摘要記錄 Claude Code 版本、各 bundle 的 hash 與
`harness_test_suite_hash`,供 regression 比對。

**bundle hash 一律用 [`dispatch/scripts/bundle-hash.sh`](dispatch/scripts/bundle-hash.sh) 計算,
不要自己拼指令。**

```bash
# skill bundle：傳 skill 目錄
skills/harness/dispatch/scripts/bundle-hash.sh skills/harness/dispatch

# suite bundle：傳 collection 目錄
skills/harness/dispatch/scripts/bundle-hash.sh skills/harness suite
```

涵蓋範圍是 **allowlist**,只有明列路徑進入摘要:

| mode | 傳入目錄 | allowlist |
|---|---|---|
| `skill`(預設) | skill 目錄 | `SKILL.md` + `references/**` + `scripts/**` + `evals/fixtures.json` |
| `suite` | collection 目錄 | `evals/*.py` + `evals/*.sh` + `evals/routing-fixtures.json` + `evals/seed/**` |

未列出的路徑一律不影響 hash——包含 `evals/runs/`(結果檔不得反過來改變被測版本)、
暫存檔與編輯器產物;`.DS_Store` 另外明確排除。

腳本的四個設計要求都有實測驗證,自己拼指令很容易踩到第一項:

1. **路徑無關**——同一份內容,經 symlink 或實體路徑存取必須得到相同值。
   直接對 `shasum` 輸出再摘要**會失敗**,因為它的輸出含絕對路徑;
   本專案就曾因此讓驗收員在版本綁定階段中止(派工方算 symlink 路徑、驗收方算 repo 路徑)。
2. **檔名敏感**——改檔名要改變 hash,所以摘要對象是「相對路徑 + 內容 hash」的組合。
3. **allowlist**——未列出的檔案不影響 hash,`evals/runs/` 由此自然排除。
4. **傳錯目錄不得回傳值**——allowlist 一筆都沒 match 時以 `exit 3` 中止,不回傳結果。
   空輸入的 SHA-256 是個看起來完全正常的值,是版本綁定最危險的失敗模式。

⚠️ `scripts/**` 納入 skill bundle 之後,**修改 `bundle-hash.sh` 自己會改變 `dispatch` 的
bundle hash**(舊版不會)。既有 run record 記錄的 hash baseline 因此全部失效。

## 安裝

需要 Node.js 與 npm。**只裝 `--agent claude-code`**:

```bash
npx skills@latest add TinyWugaga/tiny-agents-skills \
  --skill dispatch \
  --global \
  --agent claude-code
```

互動選項選 `Symlink`,不要加 `--copy`。安裝後驗證:

```bash
npx skills@latest list --global --agent claude-code
```

`main` 更新後同步:

```bash
npx skills@latest update dispatch --global
```

不要用 `sudo npm` 或 `sudo npx`。

runtime canonical name 固定為裸名稱 `dispatch`,不會出現 `harness:dispatch`、`harness/dispatch`
這類 namespace 前綴形式。
