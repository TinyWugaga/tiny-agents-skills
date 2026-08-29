# productivity

跨平台的日常工作流 skill。目前一個 standalone skill:

| Skill | 職責 | 觸發 |
|---|---|---|
| [`grill-me`](grill-me) | 連續訪談,逐一釐清不可逆決策,收斂成 pre-ADR 決策文件 | 使用者明確要求被訪談(「拷問我」「壓力測試這個設計」「連續問我到收斂」「grill me」) |

分界:`grill-me` 只處理**使用者明確要求的多輪訪談**,產出是決策集而非散文文件。
一次性 review 一份計畫、diff 或文件不觸發;協助撰寫或潤飾文件內容也不觸發,那是文件協作
skill(如各平台內建的 doc-coauthoring)的範圍。與 `judgment` 不重疊:`judgment` 判斷任務
何時算完成、何時該停,`grill-me` 只在開工前釐清決策。

## Fixture schema

`grill-me/evals/fixtures.json` 使用與 `discipline` 相同的 schema 2.0:無頂層 `canonical_name`、
每筆 fixture 無 `platform`,`coverage` 取自該檔 `field_definitions` 定義的固定值。

## Source of truth

`grill-me/SKILL.md` 是其 runtime 契約的唯一源頭,只在此 repo 維護;其他發佈通路
(Claude、Codex、ChatGPT 的 skill 上傳等)一律從這裡同步,不准分叉。
runtime skill 內文不重複安裝方式、canonical name 或 source-of-truth 維護說明。

## 安裝與更新

`grill-me/` 本身是一個完整、獨立的 skill 資料夾(`SKILL.md` + `evals/`)。安裝這個資料夾,
不要安裝外層 `productivity/`。

### Codex 與 Claude Code

需要 Node.js 與 npm。先確認 CLI 能從 repository 找到這個 skill:

```bash
npx skills@latest add TinyWugaga/tiny-agents-skills --list
```

全域安裝到 Codex 與 Claude Code:

```bash
npx skills@latest add TinyWugaga/tiny-agents-skills \
  --skill grill-me \
  --global \
  --agent codex \
  --agent claude-code
```

互動選項選 `Symlink`,讓兩個 agent 共用 `npx skills` 管理的 canonical copy;不要加 `--copy`。
安裝後驗證:

```bash
npx skills@latest list --global --agent codex
npx skills@latest list --global --agent claude-code
```

repository 的 `main` 更新後,同步已安裝版本:

```bash
npx skills@latest update grill-me --global
```

不要用 `sudo npm` 或 `sudo npx`;如果 npm 回報 cache 內有 root-owned files,先修正 npm cache
的擁有者再重試。

### Claude Cowork 與 Claude Chat

`npx skills` 只安裝本機 agent,不能寫入 Claude 帳號的 Skills。打包後上傳:

```bash
cd skills/productivity
zip -r /tmp/grill-me.zip grill-me -x '*/.DS_Store'
```

到 `Customize > Skills`,選 `+` > `Create skill` > `Upload a skill`,上傳 ZIP 並啟用。
更新時重新打包並上傳新版。

### ChatGPT

`npx skills` 不安裝 ChatGPT Chat / Work 帳號層級的 skill。ChatGPT Desktop 的 Codex session
使用前述 `--agent codex` 安裝;其他 session 是否能使用 standalone skill,以該產品當下提供的
Skills UI 為準。

不論在哪個平台,runtime canonical name 都固定是裸名稱 `grill-me`,不會出現 `productivity:*`、
`productivity/*` 或其他 namespace 前綴形式。
