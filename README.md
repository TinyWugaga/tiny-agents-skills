# tiny-agents-skills

自用的跨平台 skill 收藏庫,收錄提供給 Claude、Codex、ChatGPT 等 AI 平台使用的 standalone skills。

## 結構

```
skills/
  creative/
    redraw-from-references/     依參考圖重繪
  discipline/                   任務執行紀律(見下)
    README.md
    judgment/
      SKILL.md
      references/verifier.md    僅 judgment fresh-context 驗收段落載入,非獨立 skill
      evals/fixtures.json
    token-preflight/
      SKILL.md
      evals/fixtures.json
  productivity/
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

## 跨平台原則

skill 內文不寫平台專屬的呼叫語法與模型名稱,交棒寫成「接著執行 X skill」,能力差異寫成
「支援 subagent 時」這類條件。平台專屬的部署方式只放各 skill 所屬 collection 的 README。
