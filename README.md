# tiny-agents-skills

自用的 Claude plugin marketplace,收錄提供給 AI 平台使用的 skills、agents 與規範。

## Plugins

| Plugin | 內容 |
|---|---|
| [`discipline`](plugins/discipline) | `token-preflight`(成本 pre-flight)、`judgment`(判斷力守則)、`verifier` agent |
| [`dev-workflow`](plugins/dev-workflow) | 前端開發 SOP 七個 skill(init / architecture / ui-design / implement / testing / acceptance / review)+ 共用 `reference/` |

兩者分工:`dev-workflow` 管「怎麼做」的流程,`discipline` 管「做到什麼程度算數、什麼時候該停」的判準,跨任務類型通用。

## 結構

```
.claude-plugin/marketplace.json   marketplace 定義
plugins/<name>/
  .claude-plugin/plugin.json      plugin metadata
  skills/<skill>/SKILL.md
  agents/<agent>.md               (選用)
  reference/                      (選用)共用規範層
  README.md
```

## 使用

```
/plugin marketplace add <此 repo 的路徑或 git URL>
/plugin install discipline@tiny-agents-skills
/plugin install dev-workflow@tiny-agents-skills
```
