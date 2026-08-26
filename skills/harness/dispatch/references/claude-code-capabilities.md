# Claude Code 能力事實（dispatch 的易變事實層）

只在 `dispatch` 需要具體的 model 別名、effort 級別、fast mode 計費、巢狀深度或內建 agent
行為時讀本檔。`SKILL.md` 只放決策流程,所有會過期的數值都在這裡。

## 使用規則

本檔分兩欄,**兩欄回答不同的問題,彼此不互相覆蓋**:

| 欄 | 回答什麼 |
|---|---|
| **官方支援** | 平台契約:這個能力存不存在、怎麼運作。來源為官方文件。 |
| **本機觀測** | 當前版本／帳號／組織政策下**實際可不可用**。來源為本機指令與選單。 |

- **當下要執行什麼,依本機觀測;描述平台支援怎麼運作,依官方文件。**
  兩者不一致時**兩邊都保留並標示 scope**,不要用其中一邊蓋掉另一邊。
- **只要某條能力事實會影響當次決策,就在執行前重查。** 無法查證時標為「未驗證」並明說,
  不用訓練記憶補完。
- 查閱日期**只是複查提醒,不構成「還在有效期內就可以直接引用」的授權**。
  本檔在 2026-08-24 至 08-26 之間就親歷過一次 48 小時內的文件改寫(見 fast mode 一節)。

---

## 官方支援（來源:code.claude.com，查閱日期 2026-08-26）

### Model 別名

適用 surface:`model` 設定、`/model`、`--model`、subagent frontmatter 的 `model`、
`Agent` tool 的 `model` 參數。
來源:<https://code.claude.com/docs/en/model-config>

| 別名 | 行為 |
|---|---|
| `default` | 清除 model override,回到帳號的 runtime 預設。本身不是別名 |
| `best` | 組織有權限時用 Fable 5,否則用最新的 Opus |
| `fable` | Claude Fable 5,給最難、最長時間的任務 |
| `opus` | 最新的 Opus,複雜推理 |
| `sonnet` | 最新的 Sonnet,日常 coding |
| `haiku` | 快速省成本的 Haiku,簡單任務 |
| `sonnet[1m]` / `opus[1m]` | 1M token context window |
| `opusplan` | plan mode 用 `opus`,執行時切 `sonnet` |

`opus` / `sonnet` 實際解析到哪一版依 provider 而定。

### Effort 級別

適用 surface:`/effort`、`--effort`、`CLAUDE_CODE_EFFORT_LEVEL`。
來源:<https://code.claude.com/docs/en/model-config>

| Model | 可用級別 |
|---|---|
| Fable 5 | `low` `medium` `high` `xhigh` `max` |
| Opus 5、Sonnet 5、Opus 4.8、Opus 4.7 | `low` `medium` `high` `xhigh` `max` |
| Opus 4.6、Sonnet 4.6 | `low` `medium` `high` `max` |

- 未列出的 model 不支援 effort。設了不支援的級別會**降到該 model 支援的最高級別**
  (例:`xhigh` 在 Opus 4.6 上以 `high` 執行)。
- **預設 effort 是 `high`**,唯一例外是 Opus 4.7 預設 `xhigh`。
- `low` / `medium` / `high` / `xhigh` 在互動式 session 設定後**跨 session 保留**;
  **`max` 只在當前 session 有效**,除非用 `CLAUDE_CODE_EFFORT_LEVEL` 設定。
- 組織可以對每個 model 設定 effort 上限。

### Fast mode

適用 surface:CLI 的 `/fast`、`fastMode` 設定、**VS Code extension**。
來源:<https://code.claude.com/docs/en/fast-mode>

- 支援 **Opus 5 與 Opus 4.8**;Sonnet、Haiku 與其他 model 不支援。
- **不是不同的 model**。同樣的 Opus 換一組偏重速度的 API 設定,官方描述為
  「identical quality and capabilities with faster responses」,最快約 2.5x。
  → **fast mode 不加深也不減弱推理,只影響延遲與成本。**
- 計費 $10 / $50 per MTok(input / output),Opus 5 與 4.8 相同,且**跨完整 1M context 為單一費率**。
- **訂閱方案(Pro/Max/Team/Enterprise)上,fast mode 走 usage credits,
  `not included in the subscription rate limits`。** 需先開啟 usage credits 才能用。
  → **fast mode 不是省額度手段,是額外付費買延遲。**
- 一段對話中**第一次**開啟 fast mode 時,要以 fast mode 的未快取價格支付整段既有 context;
  對話越深越貴,所以要開就一開始開。同一對話關掉再開不會重複收費。
- CLI 用 `/fast` 切換;**VS Code extension 跟隨 `fastMode` 設定,並在支援的 model 上
  提供 Toggle fast mode 指令**。
  ⚠️ 這一項在 2026-08-24 的文件版本是「not supported in the VS Code extension」,
  08-26 已改寫。引用前務必重查。
- 與 effort 的差別:fast mode = 同品質、低延遲、高成本;降 effort = 少思考、較快、
  複雜任務品質可能下降。兩者可併用。
- 目前為 research preview,功能、定價與供應狀況都可能變動。

### Subagent 巢狀深度

適用 surface:`settings.json` 的 `env`。
來源:<https://code.claude.com/docs/en/sub-agents>

- **平台預設:subagent 可以再派 subagent,上限為主對話以下三層。**
- 用 `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` 調整;設為 `1` 等於停用巢狀。
- 到達深度上限時,Claude Code 會**對 subagent 收回 `Agent` tool**(fork 除外),
  逼它自己做完並回傳一份摘要。

### 內建 agent

來源:<https://code.claude.com/docs/en/sub-agents>

| Agent | Model | 工具範圍 | CLAUDE.md / git status |
|---|---|---|---|
| `Explore` | **繼承主對話**;Claude API 上**以 Opus 封頂** | 唯讀(Write/Edit 被拒) | **跳過** |
| `Plan` | 繼承主對話 | 唯讀(Write/Edit 被拒) | **跳過** |
| `general-purpose` | 繼承主對話 | **subagent 可用的全部工具** | 載入 |

- **v2.1.198 起 `Explore` 不再固定跑 Haiku**,改為繼承主對話模型。
  → 要讓掃描跑在低成本 model,必須**明寫 `model`**(per-invocation 用 `Agent` tool 的
  `model` 參數,或自建同名 subagent 定義並設 `model: haiku`)。不寫就是用主對話的價格跑掃描。
- Claude API 以外的 provider(Bedrock、Google Cloud Agent Platform、Microsoft Foundry、
  Claude Platform on AWS)沒有 Opus 封頂,直接繼承。
- `Explore` / `Plan` 跳過 CLAUDE.md 與 parent git status 是為了讓研究快而便宜,
  **沒有 frontmatter 可以逐 agent 改掉這個行為**。
  → 派給它們的 prompt 必須自帶專案規則的**檔案路徑**。

### `isolation: worktree`

來源:<https://code.claude.com/docs/en/sub-agents>

- subagent frontmatter 設 `isolation: worktree`,讓它在暫時的 git worktree 執行,
  預設從 default branch 而非 parent session 的 `HEAD` 分出。
- subagent 沒有任何改動時,worktree 自動清理。
- 會把 git 導回主 checkout、或 Claude Code 無法確認留在 worktree 內的指令,一律失敗。

---

## 本機觀測

| 項目 | 值 | 觀測日期 | 方法 |
|---|---|---|---|
| Claude Code 版本 | `2.1.221` | 2026-08-26 | `claude --version` |
| `/model` 實際選單 | **未驗證** | — | 需互動式 session |
| `/effort` 實際選單 | **未驗證** | — | 需互動式 session |
| `/fast` 可用性與 usage credits 狀態 | **未驗證** | — | 需互動式 session,`/fast` 或 `/status` |
| 方案與額度 | **未驗證** | — | 需互動式 session,`/usage` |

**未驗證項目不得當成已知事實引用。** 需要據此決策時,請在互動式 session 執行對應指令後
回填本表,並註明觀測日期。

觀測方式:

```bash
claude --version
```

`/model`、`/effort`、`/fast`、`/status`、`/usage` 都是互動式終端面板,只能在互動式
`claude` session 內執行,無法從非互動式 session 或 Bash 取得。
