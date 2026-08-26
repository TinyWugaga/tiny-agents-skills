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
`SKILL.md` 只留決策流程,不內嵌會過期的數字。

這個切法有實證理由:2026-08-24 官方文件寫「fast mode 不支援 VS Code extension」,
08-26 重抓已改為「extension 跟隨 `fastMode` 設定並提供 Toggle 指令」。**48 小時內就變了。**
因此該檔的規則是「會影響當次決策的事實,執行前重查」,而不是任何形式的固定有效期。

## Source of truth

`dispatch/SKILL.md` 與其 `references/` 是 runtime 契約的唯一源頭,只在此 repo 維護。
其他發佈通路一律從這裡同步,不准分叉。runtime skill 內文不重複安裝方式與 source-of-truth
維護說明。

## Evals

兩層:

- `dispatch/evals/fixtures.json` — 驗 `dispatch` 自身觸發(schema v2 五欄)
- `evals/routing-fixtures.json` — harness 整合測試:`judgment ↔ dispatch` 邊界與交棒、
  任一 skill 缺席時的 fallback、`Agent` tool 不可用時的行為。
  除 schema v2 五欄外,每筆另有可機器判定的 `expected_route`

`skill-absent-fallback` 這類案例**必須**放在 routing 這層:skill 不存在時,它自己的
fixtures 也載入不了,無法自我驗證。

執行結果摘要落檔到 `evals/runs/<RUN_ID>/<RUN_ID>.{json,md}`。失敗的 run 必須保留
摘要與判定所需的最小證據；`raw/` 內的完整 trace 只存本機 archive 或 CI artifact，
不進版本控制。每筆摘要記錄 Claude Code 版本、各 bundle 的 hash 與
`harness_test_suite_hash`,供 regression 比對。

**bundle hash 一律用 [`dispatch/scripts/bundle-hash.sh`](dispatch/scripts/bundle-hash.sh) 計算,
不要自己拼指令。**

```bash
skills/harness/dispatch/scripts/bundle-hash.sh <skill 目錄>
```

涵蓋 `SKILL.md` + `references/**` + `evals/fixtures.json`,**排除 `evals/runs/`**
(避免結果檔反過來改變被測版本)。

腳本的三個設計要求都有實測驗證,自己拼指令很容易踩到第一項:

1. **路徑無關**——同一份內容,經 symlink 或實體路徑存取必須得到相同值。
   直接對 `shasum` 輸出再摘要**會失敗**,因為它的輸出含絕對路徑;
   本專案就曾因此讓驗收員在版本綁定階段中止(派工方算 symlink 路徑、驗收方算 repo 路徑)。
2. **檔名敏感**——改檔名要改變 hash,所以摘要對象是「相對路徑 + 內容 hash」的組合。
3. **排除 `evals/runs/`**。

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
