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

`dispatch/SKILL.md` 與其 `references/` 是 runtime 契約的唯一源頭,只在此 repo 維護。
版本標記工具 [`scripts/bundle-hash.sh`](../../scripts/bundle-hash.sh) 已移到 **repo root**:
放在 skill 的 `scripts/` 下會讓量測工具本身成為 skill identity 的一部分,
改一次工具就作廢一次 skill observation。
其他發佈通路一律從這裡同步,不准分叉。runtime skill 內文不重複安裝方式與 source-of-truth
維護說明。

## 開發、測試與證據

fixture 執行機制、evals 分層、identity domain（hash schema v6）、provenance、重新評分與
證據等級的說明，以及 `evals/` 與其餘 repo 層工具，只在 `develop` 分支：
[develop 的 harness README](https://github.com/TinyWugaga/tiny-agents-skills/blob/develop/skills/harness/README.md)、
[STATUS.md](https://github.com/TinyWugaga/tiny-agents-skills/blob/develop/skills/harness/evals/STATUS.md)、
[KNOWN-ISSUES.md](https://github.com/TinyWugaga/tiny-agents-skills/blob/develop/skills/harness/evals/KNOWN-ISSUES.md)。

本分支保留 [`scripts/bundle-hash.sh`](../../scripts/bundle-hash.sh)，因為
`dispatch/references/templates.md` 仍指示在本 repo 內用它計算 skill hash。
未完成的 KI 與發布 gate 維持原狀；有執行紀錄不代表發布 gate 已通過。

## 安裝

安裝來源是 `main`,安裝內容不含 `evals/`。需要 Node.js 與 npm。**只裝 `--agent claude-code`**:

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
