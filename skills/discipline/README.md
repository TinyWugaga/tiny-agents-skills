# discipline

任務執行紀律。兩個獨立 standalone skill,各自保持 self-contained runtime 契約:

| Skill | 職責 | 觸發 |
|---|---|---|
| [`token-preflight`](token-preflight) | 動手前評估成本量級,只因 token 成本攔截 | 大型任務(未指明範圍的讀取、多檔變更、10+ 工具呼叫) |
| [`judgment`](judgment) | 升級 / 完成 / 停損 / 換路 / 品質底線的判準 | 宣告完成前、同一問題重試失敗後 |

分界:`token-preflight` 只以可量測成本訊號判級,需求歧義本身不觸發 pre-flight;
`judgment` 處理執行中的升級、完成、暫停、換路與驗收決策。

## verifier(內部參照,非獨立 skill)

`judgment/references/verifier.md` 是驗收員規則:逐條 PASS / FAIL / UNVERIFIABLE + 證據,只
判定不修復。它不是獨立可觸發的 skill 或 agent,只在 judgment 的 fresh-context 驗收段落
被載入,由 judgment 依當前環境能力(可派發 subagent、只能單一 context、或請使用者開新對話)
決定怎麼用它。不對外單獨部署,不出現在任何平台的 skill 清單裡。

## Fixture schema

兩份 `evals/fixtures.json` 自 v2.0 起移除頂層 `canonical_name` 與每筆 fixture 的 `platform`,
並將 `coverage` 改為各檔 `field_definitions` 定義的固定值。從 v1.0 遷移時刪除前述欄位,
再依各 skill 的 coverage 定義更新既有值。

## Source of truth

`token-preflight/SKILL.md` 與 `judgment/SKILL.md` 是各自 runtime 契約的唯一源頭;
`judgment/references/verifier.md` 是驗收規則的唯一源頭。這些檔案只在此 repo 維護,其他發佈通路
(Claude、Codex、ChatGPT 的 skill 上傳等)一律從這裡同步,不准分叉。

runtime skill 內文不重複安裝方式、canonical name 或 source-of-truth 維護說明。
實際部署方式見下。

## 安裝與更新

`token-preflight/` 與 `judgment/` 各自是一個完整、獨立的 skill 資料夾(`SKILL.md` + 選用的
`references/`、`evals/`)。安裝這兩個資料夾,不要安裝外層 `discipline/`,也不要把
`judgment/references/verifier.md` 當成獨立 skill 安裝。

### Codex 與 Claude Code

需要 Node.js 與 npm。先確認 CLI 能從 repository 找到兩個 skills:

```bash
npx skills@latest add TinyWugaga/tiny-agents-skills --list
```

全域安裝到 Codex 與 Claude Code:

```bash
npx skills@latest add TinyWugaga/tiny-agents-skills \
  --skill token-preflight \
  --skill judgment \
  --global \
  --agent codex \
  --agent claude-code
```

互動選項選 `Symlink`,讓兩個 agent 共用 `npx skills` 管理的 canonical copy;不要加
`--copy`。安裝後驗證:

```bash
npx skills@latest list --global --agent codex
npx skills@latest list --global --agent claude-code
```

repository 的 `main` 更新後,同步已安裝版本:

```bash
npx skills@latest update token-preflight judgment --global
```

只更新其中一個 skill 時,把另一個名稱從指令移除。不要用 `sudo npm` 或 `sudo npx`;如果 npm
回報 cache 內有 root-owned files,先修正 npm cache 的擁有者再重試。

### Claude Cowork 與 Claude Chat

`npx skills` 只安裝本機 agent,不能寫入 Claude 帳號的 Skills。將兩個 skill 分別打包:

```bash
cd skills/discipline
zip -r /tmp/token-preflight.zip token-preflight -x '*/.DS_Store'
zip -r /tmp/judgment.zip judgment -x '*/.DS_Store'
```

到 `Customize > Skills`,選 `+` > `Create skill` > `Upload a skill`,分別上傳兩個 ZIP 並啟用。
更新時重新打包並上傳新版。`judgment.zip` 已包含 verifier 規則,不需要第三個 ZIP。

### ChatGPT

`npx skills` 不安裝 ChatGPT Chat / Work 帳號層級的 skill。ChatGPT Desktop 的 Codex session
使用前述 `--agent codex` 安裝;其他 session 是否能使用 standalone skill,以該產品當下提供的
Skills UI 為準。

不論在哪個平台,runtime canonical name 都固定是裸名稱 `token-preflight` 與 `judgment`,
不會出現 `discipline:*`、`discipline/*` 或其他 namespace 前綴形式。
