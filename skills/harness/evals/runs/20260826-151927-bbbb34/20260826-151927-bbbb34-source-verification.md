# Release gate 段二：capabilities.md 官方欄來源核對

核對方式：由主對話以 WebFetch 實抓官方文件，逐條比對「文件是否真的支持該主張」，
非僅檢查「有沒有附 URL」。核對日期 2026-08-26。

| # | capabilities.md 的主張 | 來源 | 核對結果 |
|---|---|---|---|
| 1 | model 別名表（best/fable/opus/sonnet/haiku/opusplan/[1m]） | model-config | ✅ 與文件表格逐列一致 |
| 2 | effort 級別表：Opus 5 / Sonnet 5 / Opus 4.8 / Opus 4.7 皆 low–max；Opus 4.6 / Sonnet 4.6 無 xhigh | model-config | ✅ 一致 |
| 3 | 預設 effort 為 `high`，唯一例外 Opus 4.7 為 `xhigh` | model-config | ✅ 原文：「The default effort is `high` on every model that supports effort, except Opus 4.7」 |
| 4 | low/medium/high/xhigh 跨 session 保留；`max` 僅當前 session，除非用 `CLAUDE_CODE_EFFORT_LEVEL` | model-config | ✅ 一致 |
| 5 | 設了不支援的級別會降到該 model 支援的最高級別 | model-config | ✅ 一致（xhigh 在 Opus 4.6 上以 high 執行） |
| 6 | fast mode 支援 Opus 5 與 Opus 4.8，不支援 Sonnet/Haiku | fast-mode | ✅ 一致 |
| 7 | fast mode 不是不同的 model，「identical quality and capabilities」，最快約 2.5x | fast-mode | ✅ 原文可對應 |
| 8 | 計費 $10/$50 per MTok，跨完整 1M context 為單一費率 | fast-mode | ✅ 一致 |
| 9 | **訂閱方案上走 usage credits，not included in the subscription rate limits** | fast-mode | ✅ 原文可對應。**這條推翻了 legacy 規則檔「fast mode 省額度」的說法** |
| 10 | 第一次開啟要以 fast 價格支付整段既有 context；同對話關掉再開不重複收費 | fast-mode | ✅ 一致 |
| 11 | **VS Code extension 跟隨 `fastMode` 設定並提供 Toggle fast mode 指令** | fast-mode | ✅ 2026-08-26 版一致。⚠️ 08-24 版為「not supported in the VS Code extension」，48 小時內反轉 |
| 12 | fast mode vs 降 effort 的差別（同品質低延遲高成本 vs 少思考可能降品質） | fast-mode | ✅ 一致 |
| 13 | fast mode 為 research preview | fast-mode | ✅ 一致 |
| 14 | subagent 預設可巢狀，上限主對話以下三層 | sub-agents | ✅ 一致 |
| 15 | `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` 設 1 等於停用巢狀 | sub-agents | ✅ 一致 |
| 16 | 到達深度上限時對 subagent 收回 `Agent` tool（fork 除外） | sub-agents | ✅ 一致 |
| 17 | `Explore` 繼承主對話模型，Claude API 上以 Opus 封頂；v2.1.198 起不再固定 Haiku | sub-agents | ✅ 一致 |
| 18 | 其他 provider 無 Opus 封頂，直接繼承 | sub-agents | ✅ 一致 |
| 19 | `Explore`/`Plan` 唯讀（Write/Edit 被拒）；`general-purpose` 有 subagent 可用的全部工具 | sub-agents | ✅ 一致 |
| 20 | `Explore`/`Plan` 跳過 CLAUDE.md 與 parent git status，且**無 frontmatter 可逐 agent 改**；其餘 agent 兩者都載入 | sub-agents | ✅ 原文：「There is no frontmatter field to change this behavior per-agent」 |
| 21 | `isolation: worktree` 從 default branch 而非 parent HEAD 分出，無改動時自動清理 | sub-agents | ✅ 一致 |

來源：
- https://code.claude.com/docs/en/model-config （2026-08-26 抓取）
- https://code.claude.com/docs/en/fast-mode （2026-08-26 抓取）
- https://code.claude.com/docs/en/sub-agents （2026-08-26 抓取）

**判定：21/21 PASS。**

誠實聲明：本段由主對話執行（需要 Web 能力，唯讀驗收 agent 依派工限制不可連網），
因此不是獨立 context 驗證。殘留風險為主對話的推理污染；
但本段檢查性質是「文件字面是否支持主張」，屬機械比對，污染風險低於判斷型驗收。

本機觀測欄的 `/model`、`/effort`、`/fast`、`/usage` 四項標為**未驗證**——
需互動式 session 才能取得，本 session 為非互動式。這是誠實標註，不是遺漏。
