# tiny-agents-skills

自用的 skill 收藏庫。**多數 collection 是跨平台的**(Claude、Codex、ChatGPT 等),
**`harness/` 是平台專屬的例外**(僅 Claude Code)——差別見下方「跨平台原則」。

## 結構

```
skills/
  creative/                     跨平台
    redraw-from-references/     依參考圖重繪
  discipline/                   跨平台。任務執行紀律(見下)
    README.md
    judgment/
      SKILL.md
      references/verifier.md    僅 judgment fresh-context 驗收段落載入,非獨立 skill
      evals/fixtures.json
    token-preflight/
      SKILL.md
      evals/fixtures.json
  harness/                      平台專屬:僅 Claude Code(見下)
    README.md
    dispatch/
      SKILL.md
      references/templates.md
      references/claude-code-capabilities.md   易變平台事實,官方/本機兩欄
      evals/fixtures.json
    evals/routing-fixtures.json  harness 整合測試:skill 間邊界與缺席 fallback
  productivity/                 跨平台
    grill-me/                   持續追問直到收斂
  dev-workflow.zip              封存,不在使用中
```

每個 `<category>/<skill-name>/` 都是一個獨立、可直接部署的 standalone skill,不掛在任何
plugin 或 namespace 之下。各平台以自己的 skill 載入機制安裝;同一 skill 在所有平台上的
runtime canonical name 一律是裸資料夾名稱本身,不會出現 `<collection>:<skill>` 或其他
namespace 前綴。安裝與更新方式由各 collection 的 README 維護。

## discipline

| Skill | 職責 | 觸發 |
|---|---|---|
| [`token-preflight`](skills/discipline/token-preflight) | 動手前評估成本量級,只因 token 成本攔截 | 大型任務(未指明範圍的讀取、多檔變更、10+ 工具呼叫) |
| [`judgment`](skills/discipline/judgment) | 升級 / 完成 / 停損 / 換路 / 品質底線的判準 | 宣告完成前、同一問題重試失敗後 |

兩者都是獨立 standalone skill,canonical name 固定為裸名稱 `token-preflight` / `judgment`。
`judgment/references/verifier.md` 是 judgment fresh-context 驗收段落的內部規則參照,只在
該分支被載入,不是獨立 skill 或 agent,不對外部署。細節見
[`skills/discipline/README.md`](skills/discipline/README.md),包含安裝、驗證與更新方法。

## harness（平台專屬:僅 Claude Code）

| Skill | 職責 | 觸發 |
|---|---|---|
| [`dispatch`](skills/harness/dispatch) | 要不要派 subagent、派給誰、怎麼寫派工單、失敗了怎麼調整能力 | 即將派工、選 model／effort、寫派工 prompt |

`dispatch` 只管派工調度;**完成判斷與驗收判準屬於 `judgment`**,兩者不重疊也不分叉。
易變的平台數值集中在 `dispatch/references/claude-code-capabilities.md`,分「官方支援」與
「本機觀測」兩欄。細節、安裝與 evals 分層見
[`skills/harness/README.md`](skills/harness/README.md)。

## 跨平台原則

**適用於 `creative/`、`discipline/`、`productivity/`:** skill 內文不寫平台專屬的呼叫語法與
模型名稱,交棒寫成「接著執行 X skill」,能力差異寫成「支援 subagent 時」這類條件。
平台專屬的部署方式只放各 skill 所屬 collection 的 README。

**`harness/` 是明確例外。** 它處理的就是 Claude Code harness 本身的調度問題,因此**必須**
指名該平台的機制(`Agent` tool、subagent frontmatter、`/model`、`/effort`、`/fast`、
`settings.json` 環境變數)。harness 的 skill 不要安裝到其他平台——那裡沒有對應機制,
規則會變成誤導。

因為平台事實會過期(實證:`fast-mode` 文件在 2026-08-24 至 08-26 之間就改寫過一次),
harness 的 skill 把易變事實與決策流程分檔存放,並要求「會影響當次決策的事實,執行前重查」。
