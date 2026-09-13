# tiny-agents-skills

自用的 skill 收藏庫。`creative/`、`discipline/`、`productivity/` 採跨平台設計，
不代表已在所有平台驗證。`harness/` 的設計目標僅為 Claude Code。

開發規則以 [AGENTS.md](AGENTS.md) 為準；[CLAUDE.md](CLAUDE.md) 只匯入該檔。

## 分支

| 分支 | 用途 |
|---|---|
| `main`（本分支） | skill 安裝來源：只含 runtime skill、plugin 安裝檔與必要文件；不含 `evals/`、`tests/` 與開發測試工具 |
| `develop` | 完整開發來源：evals、測試工具、契約、帳本與歷史證據；新開發與測試都在這裡進行 |

`main` 代表安裝內容，不代表所有 skill 已驗收通過，也不代表已發布。目前已知限制：

- Batch 23b（`judgment` 的 KI-02／14／15／21 修正）已暫停：已完成的語意驗收不重開，但修正後的行為重跑證據仍為零，相關 KI 維持未完成，`judgment` 的這部分行為尚未完成驗收。
- 未完成的 KI 與發布 gate 維持原狀；有執行紀錄不代表發布 gate 已通過。

開發、測試、狀態與證據入口都在 `develop`：
[develop 分支](https://github.com/TinyWugaga/tiny-agents-skills/tree/develop)、
[開發規範測試計畫](https://github.com/TinyWugaga/tiny-agents-skills/blob/develop/tests/agent-instructions.md)、
[harness STATUS.md](https://github.com/TinyWugaga/tiny-agents-skills/blob/develop/skills/harness/evals/STATUS.md)、
[harness KNOWN-ISSUES.md](https://github.com/TinyWugaga/tiny-agents-skills/blob/develop/skills/harness/evals/KNOWN-ISSUES.md)。

> `develop` 尚未推送到遠端；本檔與各 collection README 中指向 `develop` 的連結，推送後才會生效。

## 平台狀態

| 狀態 | 意義與記錄位置 |
|---|---|
| 設計目標平台 | 希望適用的平台與 session，見下表；不等於已驗證或發布承諾 |
| 本次發布支援平台 | 在該次發布工作單中固定的承諾範圍；必須逐平台完成適用 fixture 驗證，不能為了通過移除失敗平台 |
| 已驗證平台／版本 | 以實際紀錄中的平台、session、受測 identity、案例與結果為準；不得外推到其他版本或平台 |

| Collection | 設計目標與限制 | 驗證證據入口（`develop`，推送後生效） |
|---|---|---|
| `creative/` | Claude、Codex 等可載入 skill 的 agentic session；所需繪圖能力依各 skill 契約 | 依各 skill 的實測紀錄確認；本 README 未宣稱完成逐平台驗證 |
| `discipline/` | Claude、Codex 等可載入 skill 的 agentic session | judgment 的部分驗證見 [STATUS.md](https://github.com/TinyWugaga/tiny-agents-skills/blob/develop/skills/harness/evals/STATUS.md)，結果不能推及整個 collection |
| `productivity/` | Claude、Codex 等可載入 skill 的 agentic session | 依各 skill 的實測紀錄確認；本 README 未宣稱完成逐平台驗證 |
| `harness/` | 僅 Claude Code | [STATUS.md](https://github.com/TinyWugaga/tiny-agents-skills/blob/develop/skills/harness/evals/STATUS.md) 與 [KNOWN-ISSUES.md](https://github.com/TinyWugaga/tiny-agents-skills/blob/develop/skills/harness/evals/KNOWN-ISSUES.md)；有執行紀錄不代表發布 gate 已通過 |

本 README 不另行指定發布批次或支援清單；以該次已核准工作單為準。設計目標中未納入本次支援的平台，應在該次發布說明標示未驗證。純 chat 不假設會自動載入 repository 中的 skill。

現有 harness runner 的 subject 執行入口是 `claude -p`，runner 只在 `develop`。其他目標平台沒有自動 runner 時，可依原案例與判準在實際目標環境人工執行，保存輸入、輸出與版本證據；只做文件審閱或模擬回答不算該平台的行為驗證。

本機另有被 `.gitignore` 排除的 `skills/codex/`，其 collection README 限定具備所需 UI 工具的 Codex Desktop。該目錄不隨此儲存庫的版本控制內容交付，但仍受根 AGENTS.md 的開發與安全規範約束。

## 結構

```
skills/
  creative/                       跨平台設計目標，驗證狀態見上表
    redraw-from-references/       依參考圖重繪
      SKILL.md
      references/
      agents/openai.yaml
    character-consistent-drawing/ 依設計檔繪製角色一致性繪圖
      SKILL.md
      references/character-drawing-rules.md
      references/character-registry.md
      references/characters/
      agents/openai.yaml
  discipline/                     跨平台設計目標；任務執行紀律(見下)
    README.md
    judgment/
      SKILL.md
      references/verifier.md      僅 judgment fresh-context 驗收段落載入,非獨立 skill
      references/bounded-review.md
    token-preflight/
      SKILL.md
  harness/                        平台專屬:僅 Claude Code(見下)
    README.md
    dispatch/
      SKILL.md
      references/templates.md
      references/claude-code-capabilities.md   易變平台事實,官方/本機兩欄
      references/plan-and-quota.md             額度與消耗事實,同樣分兩欄
  productivity/                   跨平台設計目標
    README.md
    grill-me/                     持續追問直到收斂,產出 pre-ADR 決策文件
      SKILL.md
scripts/
  bundle-hash.sh                  identity hash(hash schema v6);dispatch 的
                                  references/templates.md 仍引用,因此保留在 main
```

版本標記工具刻意放在 repo root 而非某個 skill 的 `scripts/` 下:skill allowlist 含
`scripts/**`,量測工具若住在裡面,改一次工具就會改變被量測 skill 的 identity,
把 evaluator 混進 runtime skill 的識別範圍。其餘 selftest、重新評分與帳本工具只在 `develop`。

每個 `<category>/<skill-name>/` 都是獨立的 standalone skill，不掛在任何
plugin 或 namespace 之下；可安裝的結構不等於已滿足發布條件。各目標平台以自己的 skill 載入機制安裝；同一 skill 在各目標平台上的
runtime canonical name 一律是裸資料夾名稱本身,不會出現 `<collection>:<skill>` 或其他
namespace 前綴。安裝與更新方式由各 collection 的 README 維護；安裝內容不含 `evals/`。

## discipline

| Skill                                                  | 職責                                       | 觸發                                               |
| ------------------------------------------------------ | ------------------------------------------ | -------------------------------------------------- |
| [`token-preflight`](skills/discipline/token-preflight) | 動手前評估成本量級,只因 token 成本攔截     | 大型任務(未指明範圍的讀取、多檔變更、10+ 工具呼叫) |
| [`judgment`](skills/discipline/judgment)               | 升級 / 完成 / 停損 / 換路 / 品質底線的判準 | 宣告完成前、同一問題重試失敗後                     |

兩者都是獨立 standalone skill,canonical name 固定為裸名稱 `token-preflight` / `judgment`。
`judgment/references/verifier.md` 是 judgment fresh-context 驗收段落的內部規則參照,只在
該分支被載入,不是獨立 skill 或 agent,不對外部署。細節見
[`skills/discipline/README.md`](skills/discipline/README.md),包含安裝與更新方法。

## harness（平台專屬:僅 Claude Code）

| Skill                                 | 職責                                                        | 觸發                                      |
| ------------------------------------- | ----------------------------------------------------------- | ----------------------------------------- |
| [`dispatch`](skills/harness/dispatch) | 要不要派 subagent、派給誰、怎麼寫派工單、失敗了怎麼調整能力 | 即將派工、選 model／effort、寫派工 prompt |

`dispatch` 只管派工調度;**完成判斷與驗收判準屬於 `judgment`**,兩者不重疊也不分叉。
易變的平台數值集中在 `dispatch/references/claude-code-capabilities.md`,分「官方支援」與
「本機觀測」兩欄。細節與安裝見
[`skills/harness/README.md`](skills/harness/README.md)。

## productivity

| Skill                                      | 職責                                                | 觸發                                                             |
| ------------------------------------------ | --------------------------------------------------- | ---------------------------------------------------------------- |
| [`grill-me`](skills/productivity/grill-me) | 連續訪談,逐一釐清不可逆決策,收斂成 pre-ADR 決策文件 | 使用者明確要求被訪談(「拷問我」「壓力測試這個設計」「grill me」) |

只處理明確要求的多輪訪談;一次性 review 與文件撰寫都不觸發。與 `judgment` 的分界是時序:
`grill-me` 在開工前釐清決策,`judgment` 在執行中判斷完成與停損。安裝與更新見
[`skills/productivity/README.md`](skills/productivity/README.md)。

## 跨平台設計原則

**適用於 `creative/`、`discipline/`、`productivity/`:** skill 內文不寫平台專屬的呼叫語法與
模型名稱,交棒寫成「接著執行 X skill」,能力差異寫成「支援 subagent 時」這類條件。
平台專屬的部署方式只放各 skill 所屬 collection 的 README。

**`harness/` 是明確例外。** 它處理的就是 Claude Code harness 本身的調度問題,因此**必須**
指名該平台的機制(`Agent` tool、subagent frontmatter、`/model`、`/effort`、`/fast`、
`settings.json` 環境變數)。harness 的 skill 不要安裝到其他平台——那裡沒有對應機制,
規則會變成誤導。

因為平台事實會過期(實證:`fast-mode` 文件在 2026-08-24 至 08-26 之間就改寫過一次),
harness 的 skill 把易變事實與決策流程分檔存放,並要求「會影響當次決策的事實,執行前重查」。
