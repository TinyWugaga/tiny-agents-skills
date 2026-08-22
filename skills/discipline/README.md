# discipline

任務執行紀律。兩個獨立 standalone skill,分工明確,不互相夾帶:

| Skill | 職責 | 觸發 |
|---|---|---|
| [`token-preflight`](token-preflight) | 動手前評估成本量級,只因 token 成本攔截 | 大型任務(未指明範圍的讀取、多檔變更、10+ 工具呼叫) |
| [`judgment`](judgment) | 升級 / 完成 / 停損 / 換路 / 品質底線的判準 | 宣告完成前、同一問題重試失敗後 |

分界:成本問題找 token-preflight,需求歧義與品質判斷找 judgment。
pre-flight 報告不得夾帶需求澄清問題。

## verifier(內部參照,非獨立 skill)

`judgment/references/verifier.md` 是驗收員規則:逐條 PASS / FAIL / UNVERIFIABLE + 證據,只
判定不修復。它不是獨立可觸發的 skill 或 agent,只在 judgment §5 的 fresh-context 驗證分支
被載入,由 judgment 依當前環境能力(可派發 subagent、只能單一 context、或請使用者開新對話)
決定怎麼用它。不對外單獨部署,不出現在任何平台的 skill 清單裡。

## Source of truth

`judgment/SKILL.md` 是判斷力守則與 verifier 分派邏輯的唯一源頭,`judgment/references/
verifier.md` 是驗收規則的唯一源頭。兩者都只在此 repo 維護一份,其他發佈通路(Claude、
Codex、ChatGPT 的 skill 上傳等)一律從這裡同步,不准分叉。

skill 內文不寫任何平台專屬的呼叫語法,交棒一律寫成「接著執行 X skill」。實際部署方式見下。

## 跨平台部署

`token-preflight/` 與 `judgment/` 各自是一個完整、獨立的 skill 資料夾(`SKILL.md` + 選用的
`references/`、`evals/`),用各平台原生支援的 skill 載入機制部署,不透過任何 plugin 或
marketplace 機制:

- Claude(Code / Cowork):放進平台的 skills 目錄,依平台的 skill 掃描機制載入。
- Codex:`cp -r skills/discipline/token-preflight ~/.codex/skills/`、
  `cp -r skills/discipline/judgment ~/.codex/skills/`,以 `/skills` 選單或平台的呼叫語法觸發。
- ChatGPT:每個 skill 資料夾各自打包成 zip(單一頂層資料夾、單一 `SKILL.md`)上傳。

不論在哪個平台,runtime canonical name 都固定是裸名稱 `token-preflight` 與 `judgment`,
不會出現 `discipline:*`、`discipline/*` 或其他 namespace 前綴形式。
