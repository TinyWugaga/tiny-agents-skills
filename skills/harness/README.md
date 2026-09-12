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

## 執行機制（fixture session 怎麼跑）

`evals/run-fixture.sh` 每筆 fixture 起一個真實的 fresh session。三件事決定它看得到什麼:

| 手段 | 作用 |
|---|---|
| `--setting-sources project,local` | 排除 user 層設定與 user 層 skills;session 的 cwd 是拋棄式 seed 副本 |
| `--plugin-dir <變體>` | 只餵入該變體要測的 skill 集合。plugin skill 仍是 model-invoked,名稱帶 namespace(`score.py` 以 `split(":")[-1]` 正規化) |
| `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` + `--append-system-prompt-file` | 不自動載入任何 CLAUDE.md,改以 repo 內固定的 `evals/context/rules.md` 注入 |

**不使用 `CLAUDE_CONFIG_DIR`。** 換 config dir 會連 host 的登入狀態一起切掉。

**憑證一律不搬運**——不讀取、不複製、不匯出、不輸出、不建立連結、不留存於 repo 或暫存目錄。
登入沿用 host 預設路徑。`--settings` 只帶消毒後的單一鍵
`env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`,絕不整份帶入 user `settings.json`
(那裡面有 `enabledPlugins` 與 marketplace 設定)。

work dir 與 plugin 變體建在 `mktemp -d`(repo 外,mode 700),複製的 skill 與規則檔設為唯讀,
收尾清除。seed 一旦夾帶 `CLAUDE.md` 或 `.claude/`,`project,local` 會讀進去而安靜破壞隔離,
因此 runner 有 fail-closed 防呆會直接中止。

### fail-closed 的四道關卡

1. **preflight**——18 筆迴圈之前,先用**完全相同的隔離執行路徑**跑一筆真實 session。
   不通過就 `exit 2`,不跑任何 fixture、不呼叫 judge。這道關卡的存在理由:前置檢查只驗得到
   「`claude` 這支指令在」,驗不到 session 能不能推論;少了它,一次登入或設定問題要跑完 18 筆才發現。
2. **`score.py` 三值 exit**——`0` 全過 / `1` 有 FAIL 但每筆都有可用觀測 /
   **`2` 有 ERROR 或 NOT_RUN**,亦即有 fixture 根本沒產生可用觀測。
3. **routing 不可用時完全跳過 judge**——`score.py` 回 2 就不呼叫 judge。
   對空的或失敗的 trace 送 judge 只會燒錢並產生假的 contract FAIL(實際發生過)。
4. **suite exit code 聚合**——CLI 失敗數、routing rc、contract rc、record rc 任一非 0,
   整支 suite 即非 0。

### run record 的三值判定

`record.py` 產生的 `run_status` 是 **PASS / FAIL / INVALID** 三值,另有 `is_contract_evidence`:

- **FAIL** = 每一筆都產生了可用觀測,而其中有觀測不符預期 → 這是關於 skill 的證據。
- **INVALID** = 有 fixture 根本沒產生可用觀測(CLI 失敗、逾時、未跑、judge 無法判定)
  → 這一輪對 skill 什麼都沒說,**不得被當成契約證據**。

少了這個區分,一輪「登入過期、全部在推論前就失敗」的執行會被記成 FAIL,日後讀起來像是 skill 沒通過。
成本欄位取自 session 自報的 `total_cost_usd`,任一來源缺漏就寫 `null`,不以推估補完。

## Evals

兩層:

- `dispatch/evals/fixtures.json` — 驗 `dispatch` 自身觸發(schema v2 五欄)
- `evals/routing-fixtures.json` — harness 整合測試:`judgment ↔ dispatch` 邊界與交棒、
  任一 skill 缺席時的 fallback、`Agent` tool 不可用時的行為。
  除 schema v2.1 六欄(含 `env`)外,每筆另有可機器判定的 `expected_route`

`skill-absent-fallback` 這類案例**必須**放在 routing 這層:skill 不存在時,它自己的
fixtures 也載入不了,無法自我驗證。

執行結果摘要落檔到 `evals/runs/<RUN_ID>/<RUN_ID>.{json,md}`。失敗的 run 必須保留
摘要與判定所需的最小證據；`raw/` 內的完整 trace 只存本機 archive 或 CI artifact，
不進版本控制。每筆摘要記錄 Claude Code 版本、`hash_schema`、八個 identity domain 的 hash、
**run 前後各量一次的 provenance manifest**、context component hash、raw trace manifest 與
post-judge manifest 的 deterministic digest,以及本次實際載入的 fixture 檔清單,供 regression 比對。

### identity domain（hash schema v6）

**hash 一律用 [`scripts/bundle-hash.sh`](../../scripts/bundle-hash.sh) 計算,不要自己拼指令。**

v1 只有 `skill` 與 `suite` 兩個 mode,把 evaluator 程式、runner 腳本與 fixture 全塞進同一個
`harness_test_suite`,`skill` mode 又納入 `evals/fixtures.json`。後果是 evaluator 工具被錯誤
納入 runtime skill 的 identity domain:改一行 `judge.py` 的解析邏輯,就作廢所有 skill
observation,即使那個改動不可能影響那些判定。v2 拆成四個互斥 domain,之後逐版補上
第五到第八個:

| domain | 傳入 | allowlist | 變更後作廢什麼 |
|---|---|---|---|
| `skill` | skill 目錄 | `SKILL.md` + `references/**` + `scripts/**` + `assets/**` + `agents/**`(**排除 `evals/**`**) | 該 subject 的 skill 行為證據 |
| `fixtures` | 明列檔案／目錄 | 只有呼叫端傳入的 fixture 檔與 seed | 對應案例的 observation |
| `runner` | collection 目錄 | `evals/run-suite.sh` + `run-fixture.sh` + `transport.py` + `manifest.py` | subject trace |
| `evaluator` | collection 目錄 | `evals/judge.py` + `score.py` + `record.py`(**排除 `*_selftest.py`**) | routing／contract 判定;**保留的 raw trace 可重新評分,不必重跑付費 subject session** |
| `execution-context` | rules／settings／descriptor 三個檔 | 三者的**內容** hash(不含路徑) | subject 行為證據——同一份 skill 在不同注入規則、不同 model 與 deny list 下行為不同 |
| `evaluation-context` | judge descriptor 一個檔 | judge model、實際 `claude --version`、judge CLI flags、structured-output 設定 | **只作廢 contract 判定**;保留的 raw trace 可重新評分 |
| `contract_fixtures` | judge 實際載入的 fixture 檔 | 與 `fixtures` 同演算法,差別在量的時機與歸屬 | **只作廢 contract 判定** |
| `rescore_runner` | 無引數 | `scripts/run-rescore.sh` | **只作廢 derived record** |

`rescore_runner` 是 v6 新增的。先前把重評編排腳本排除在 identity 之外,理由是「它只負責
依正確順序呼叫」——那個理由被兩件事推翻:它決定 judge 的**輸出寫到哪裡**(寫回來源目錄
會蓋掉原始逐筆判定證據,而 trace manifest 不涵蓋 `.judge.json`,偵測不到),
也決定**驗證的先後順序**(把付費 judge 排在 provenance 驗證之前)。
能決定證據寫到哪裡、以什麼順序驗證的東西,就是 identity 的一部分。

`fixtures` 與 `contract_fixtures` 指向同一種檔案卻是兩個 domain,因為同一份檔案承載兩件
不同的東西:`prompt` 決定 subject 看到什麼(subject 側),`required_elements` 決定判定依據
(contract 側)。重新評分時 subject 的 `fixtures` 沿用來源 run,而 judge 用的是**現在**這份
——少了 `contract_fixtures`,改掉 assertion 再重評舊 trace,紀錄仍會宣稱使用來源 fixtures。

改 `prompt` 是另一回事:那份 trace 就不再是這個 fixture 的產物。`judge.py` 在重新評分時
逐筆比對 fixture 的 prompt 與 `.meta.json` 記下的實際 prompt,不符即在**呼叫 CLI 之前**中止。

`evaluation-context` 與 `execution-context` **必須分開**。judge 是另一個 model 的另一個
session:換 `HARNESS_JUDGE_MODEL`、換 judge 的 flags、host 的 `claude` 一升版,contract
判定就可能翻轉。混進同一個 domain 的話,「換 judge model」會看起來像「受測環境變了」,
把只需要重新評分(judge 費用)的情況誤判成必須重跑付費 subject session。

`agents/**` 是 v3 才納入的:`agents/openai.yaml` 的 `default_prompt` 在 OpenAI 平台上
直接決定 agent 的開場行為,改它卻不動 skill hash,等於宣稱行為證據仍有效而受測物已變。
本 repo 現有三份 `agents/openai.yaml` 都不在 dispatch／judgment／token-preflight 底下,
因此**這次 allowlist 擴張沒有改變任何一個現行 skill hash 的值**——
但 allowlist 變了就必須提版,值相同只是因為新規則目前沒 match 到檔案。

兩個 context 的 descriptor 各由產生它的那支程式輸出:`run-fixture.sh --print-context`
與 `judge.py --print-context`,都不在 run-suite.sh 手抄。deny list 與 CLI flags 只有那兩支
程式知道,抄一份必然漂移,漂移後 hash 會宣稱環境沒變而實際上變了。這也意味著改
run-fixture.sh 的 deny list 會同時改變 `runner` 與 `execution-context`(改 judge.py 的 flags
同時改變 `evaluator` 與 `evaluation-context`)——那是正確的,deny list 既是程式內容,
也是執行環境的一部分。

```bash
scripts/bundle-hash.sh schema-version
scripts/bundle-hash.sh skill     skills/harness/dispatch
scripts/bundle-hash.sh evaluator skills/harness
scripts/bundle-hash.sh runner    skills/harness
scripts/bundle-hash.sh fixtures  skills/harness/dispatch/evals/fixtures.json skills/harness/evals/seed
scripts/bundle-hash.sh execution-context <rules> <settings|-> <descriptor|->
scripts/bundle-hash.sh evaluation-context <judge descriptor>
scripts/bundle-hash.sh fixtures  <judge 載入的 fixture 檔…>   # contract_fixtures 用同一個 mode
scripts/bundle-hash.sh rescore-runner
```

`fixtures` 只 hash **本次實際載入的**檔案,不掃全 repo——否則改一個無關 skill 的 fixture
會污染所有案例的 observation。

未列出的路徑一律不影響 hash——包含 `evals/runs/`(結果檔不得反過來改變被測版本)、
selftest、STATUS.md／KNOWN-ISSUES.md 這類紀錄文件、暫存檔與編輯器產物;
`.DS_Store` 另外明確排除。以上每一條都有機械測試:

```bash
sh scripts/hash-domain-selftest.sh
```

該測試逐一改動單一檔案,斷言**恰好一個** domain 變動。domain 互斥性是 v2／v3 的核心主張,
沒有這支測試就只是註解裡的宣稱。

### provenance:run 前後各量一次

hash 分好 domain 還不夠。v2 是在整輪跑完之後由 `record.py` 現算——那個值回答的是
「錄紀錄的當下 repo 長什麼樣」,不是「這輪 subject session 跑在什麼版本上」。
兩者在 run 期間有任何一次編輯就會分歧,而分歧完全不可見。

v3 改成 [`evals/manifest.py`](evals/manifest.py) 在 **run 開始前**與 **run 結束後**各量一次,
兩份都寫進 `runs/<RUN_ID>/manifest.json`,`record.py` **只讀不算**並比對:

⚠️ **end 的 descriptor 必須重新產生,不能重用 start 那兩份。** 重用等於事先宣告 execution／
evaluation context 不可能 drift:judge CLI 在 run 期間升版、`HARNESS_JUDGE_MODEL` 被改掉,
兩種情況下 end 都會算出與 start 一模一樣的 hash,「重新量測」變成一句空話。
⚠️ **同名 phase 不可覆寫**,寫第二次即 exit 3。否則 start 會被第二次 start 蓋掉,
比對變成拿 end 跟 end 比,drift 完全隱形而紀錄看起來通過了比對。

| 情況 | 判定 |
|---|---|
| manifest 缺失、壞損、缺 start | `INVALID` |
| 缺 end(整輪紀錄時) | `INVALID`;`--validate-only` preflight 例外,見下 |
| `manifest_version` 缺失或不是支援值 | `INVALID` |
| `kind` 不是 `full`／`contract` | `INVALID` |
| start／end 的 domain 集合不是**恰好**該 kind 要求的那組 | `INVALID` |
| 重新評分時來源紀錄的 subject hash 不是合法 64 位 hex | `INVALID` |
| `manifest_version` 不是 3（Batch 23a 起另帶 `context_components`，結構已改） | `INVALID` |
| `hash_schema` 缺失／空值／格式不合法／前後不一致 | `INVALID` |
| 任一 domain hash 前後不同(drift) | `INVALID` |
| 本次載入的 fixture **檔案清單**前後不同 | `INVALID` |
| start 缺 `fixture_files`(不知道實際載入了哪些 fixture 檔) | `INVALID` |

`--validate-only` 是唯一允許缺 end 的模式:它跑在 judge 之前,end 本來就還沒寫。
其餘每一列在 preflight 當下都照樣判——start 那半不因 end 缺席而免驗。

「恰好」而不是「至少」的理由:只比對前後是否一致的話,一份只含 `fixtures` 一個 domain 的
manifest 會完美通過——start 等於 end、沒有 drift、整輪記成有效證據,而 skill、runner、
evaluator、兩個 context 全都沒有版本綁定。**少到看不出來的紀錄比沒有紀錄更危險,
因為它看起來像有。** 多出未知 domain 同樣擋掉:那代表產生 manifest 的工具與 `record.py`
對「要量什麼」的認知已經不同,此時任何比對結論都不可信。

同時,subject 迴圈一結束就立刻對每一筆 `.jsonl`／`.meta.json` 取 SHA-256,寫成
`runs/<RUN_ID>/trace-manifest.json`。「evaluator 變更後重新評分既有 trace 而不重跑付費
session」這條省錢路徑,前提就是那份 trace 與當初產生的逐 byte 相同:

- **manifest 缺失、壞損或為空 → `judge.py` 在進 fixture loop 之前 `exit 2`,一次 CLI
  都不呼叫**;`run-suite.sh` 在 trace manifest 產生失敗時也直接跳過 judge。
  判不了就不要花錢判——先前是印一行警告然後照常判定,錢花完才由 record 判 INVALID。
- manifest 在但某筆 `.jsonl` 對不上或不在 manifest 內,該筆記 ERROR
  (`anomaly.kind = trace_hash_mismatch`)且不送 judge。
- `record.py` 也核對一次,不符或缺 manifest 一律 `INVALID`。

`manifest.py trace` **預設不覆寫既有檔案**,目標存在即 exit 3。允許覆寫的話逐檔比對形同
虛設:改 trace、重跑一次 `trace`,新 manifest 裡每一筆 hash 都會對得上。要重建就必須先
明確刪除,而刪除重建後的 digest 會與原始 run record 保存的值對不上——那才是真正的關卡。

Batch 23a 起，full／contract manifest 同時保存 context 的分項內容 hash。`execution_context`
分成 `rules`／`settings`／`descriptor`，`evaluation_context` 保存 `descriptor`；`record.py`
會獨立重算合併值並比對 start／end，缺分項、分項 drift 或合併值不一致皆為 `INVALID`。
原生 run 的 rules 固定取自 [`evals/context/rules.md`](evals/context/rules.md)，不再受 host
`~/.claude/CLAUDE.md` 的後續變動影響。

judge 完成後另由 `manifest.py post-judge` 建立不可覆寫的
`runs/<RUN_ID>/post-judge-manifest.json`。它精確列出 fixture 對應的 `.judge.json`，並綁定
trace manifest digest 與同一個 run nonce；缺檔、多檔、hash 不符、trace 綁定不符或 nonce
不符時，`record.py` 一律判 `INVALID`。trace manifest 仍只負責 subject 產物，兩者不可合併。

#### 重新評分既有 run

**用 [`scripts/run-rescore.sh`](../../scripts/run-rescore.sh),不要手動打這幾步。**

```bash
scripts/run-rescore.sh <來源 run 目錄> <新 run id> <fixtures.json> [...]
# 選填: HARNESS_MIGRATION_AUDIT=<audit.json>  HARNESS_JUDGE_MODEL=sonnet
```

**run id 只允許 `A-Za-z0-9._-`,不得為空、以 `.` 開頭或含 `/`。** 它會被拼進輸出路徑,
而失敗路徑上有 `rm -rf`;`../../victim` 會解析到 `derived/` 之外。字元 allowlist 擋字面
逸出,建立目錄前後再用 canonical path 複驗兩次(`derived/` 本身不得是 symlink、
目標必須是它的直接子目錄)擋 symlink 逸出。**containment 未確認前不對任何路徑執行 `rm -rf`。**

⚠️ 字元檢查一律用 shell pattern(`*[!A-Za-z0-9._-]*`),**不用命令替換**。
`x=$(printf %s "$id" | tr -d 'A-Za-z0-9._-')` 看起來等價,實際上有洞:命令替換會剝掉
尾端換行,`safe<LF>line` 過完 `tr` 只剩一個 `\n`、被剝成空字串,於是判定成「沒有非法字元」
而放行。LF／CR／TAB／ANSI escape 因此都能進到檔名與 log。

exit code:

| code | 意義 |
|---|---|
| 0 | judge 全數通過且 derived record 正常寫出 |
| 1 | judge 判出 contract FAIL／ERROR,或 record 寫出失敗(**derived record 仍保留**) |
| 2 | preflight 或 containment 不通過(未進入付費 judge,或未產生可信輸出) |

contract FAIL 是結論不是故障,所以紀錄要留著;但 exit code 不得說成功,
否則 CI 或發布流程會把 contract FAIL 讀成通過。

它負責三件不是「純便利」的事,因此**本身也在 identity 內**(`rescore_runner`):

1. **判定寫到哪裡。** judge 會把 `<fixture>.judge.json` 寫進它被指到的目錄。直接把來源
   `raw/` 交給它會覆蓋來源 run 的逐筆判定證據,而 trace manifest 只涵蓋
   `.jsonl`／`.meta.json`,這種破壞偵測不到。腳本改為把 subject 產物複製到
   `<來源>/derived/<新 id>/raw/`,judge 只寫那裡,結束前再核對來源目錄逐 byte 未變。
2. **驗證的先後順序。** 凡是零成本就判得出來的條件,一律排在付費 judge **之前**:
   `record.py --validate-only` 驗來源紀錄、trace digest、subject hash 格式與 migration audit,
   `judge.py --preflight` 驗 trace manifest 與 prompt 對應。
   先跑 judge 再驗,等於保留「判不了仍先花錢」的路徑。

   preflight 當下 contract manifest **只有 start**(end 要等 judge 跑完才寫),因此
   `check_manifest(doc, require_end=False)` 把兩半分開:`manifest_version`、`kind`、
   start 的 `hash_schema`、start 的 domain 集合、start 每個 hash 的格式、
   start 的 `fixture_files` 都在**這時候**驗完並回傳 start identity;
   只有「end 是否存在」、start/end domain 集合一致、hash drift 與 fixture 清單 drift
   延後到 judge 之後。

   ⚠️ 這一分界不是可有可無的整理。v6 初版在 end 缺席時整段早退並回傳 `hash_schema=None`,
   而跨 schema 的 `--migration-audit` 那道閘以 `hash_schema` 為前提——值為 None 時
   `cross_schema` 恆為 False,於是那道閘在 preflight 期間**完全不觸發**,judge 的錢照花,
   `INVALID` 要等付費之後才出現(Batch 21／BR-F38 實測複現)。
   同時被跳過的還有 `manifest_version`、domain 集合、hash 格式與 fixture 清單,
   亦即 preflight 期間 contract manifest 實質未受任何驗證。
   修正後不得再用「先製造缺 end 的錯誤、再按訊息文字濾掉」的寫法,
   也**不得在 judge 前提早寫入 end 快照**——那會讓 drift 比對變成拿 end 跟 end 比。
3. **descriptor 每次重新產生。** judge 前後各量一次 contract identity,兩次都重新執行
   `judge.py --print-context`。

derived record 的 identity **由兩半組成,各有各的來源**:

| 半邊 | domain | 取自 |
|---|---|---|
| subject identity | skill × 3、`runner`、`fixtures`、`execution_context` | **來源 run 的紀錄** |
| contract identity | `evaluator`、`evaluation_context`、`contract_fixtures`、`rescore_runner` | **本次現量** |

五個硬性要求:

1. 現在這份 trace manifest 的 digest 必須等於原始紀錄保存的
   `provenance.trace_manifest_digest`。
2. **不得覆寫原始 run record**,也不得寫入來源 `raw/`。
3. 來源紀錄必須提供全部六個 subject domain,而且每個都是**合法的 64 位 hex**。
   只檢查 key 在不在是不夠的:六個值全填 `null` 也會通過,而那份紀錄對 subject
   什麼都沒綁定,卻換到一個 `is_contract_evidence: true`。
4. 每筆 fixture 的 `prompt` 必須與 `.meta.json` 記下的實際 prompt 逐字相同。
5. **跨 schema 不得直接比較 hash。** 來源與現行 `hash_schema` 不同時必須另附
   `--migration-audit`。稽核檔採固定 schema,逐 domain 要求:

   ```json
   {"source_hash_schema": "v3", "target_hash_schema": "v6",
    "method": "整體比對方法", "reviewed_at": "2026-09-02",
    "domains": {"dispatch_skill": {"equivalent": true,
                                   "evidence": "逐檔 diff 為空",
                                   "method": "diff"}}}
   ```

   `equivalent` 不是 `true`、`evidence` 或 `method` 為空、缺 domain、多出未知 domain 或
   未知欄位,一律 `INVALID`。`record.py` 驗的是「這份文件確實逐條做出了可歸責的主張」,
   **不驗主張為真**——那是人的責任。

#### 證據等級:`evidence_class`

`run_status` 與 `evidence_class` 是兩個獨立的軸:

| 欄位 | 回答的問題 |
|---|---|
| `run_status` | 這一輪的觀測可不可用(`PASS`／`FAIL`／`INVALID`) |
| `evidence_class` | 這些觀測能不能當契約證據(`contract_evidence`／`legacy_diagnostic`) |

只有 trace manifest 在 subject 迴圈結束**當下**產生的紀錄才是 `contract_evidence`。
先前這件事由一個環境變數宣告、`record.py` 直接採信——那不是證明,是自述:
對任何事後湊出來的目錄設一次環境變數就能升格,實測確實如此。

v6 改成一條**必須四方一致的 run nonce 鏈**:

1. `snapshot start` 在跑任何 session 之前產生一次性的 `run_nonce`(128-bit)。
2. `run-suite.sh` 把它傳給每個 subject session,`run-fixture.sh` 寫進 `.meta.json`。
3. `manifest.py trace` 逐檔核對每份 meta,並把 nonce 寫進 trace manifest。
4. `record.py` 要求三者一致才判 `contemporaneous`;任一環缺失或不符即 `legacy_diagnostic`。

這擋不住能同時改寫全部四樣東西的人——沒有外部錨定(commit、可信封存)的方案都擋不住。
它擋掉的是「補一份 manifest 或設一個環境變數就升格」,門檻從一個字串變成一整條鏈。

**事後補一份 manifest 只能證明「目前檔案」的內容,不能證明它從產生到現在沒被改過。**
那種來源一律降為 `legacy_diagnostic`,`is_contract_evidence` 為 false——否則「補一份
manifest」就等於把任何舊檔案升格成證據。derived record 的等級取自**來源**紀錄的宣告:
本輪重新產生的 manifest 再怎麼「當下」,也只是重算了同一批舊檔案。

### hash_schema_version

所有 hash 值綁定 `hash_schema`(目前 `v6`)。演算法或任一 domain 的 allowlist 變動時必須提版;
**不同 schema 版本的 hash 不得直接比較**,也不得把差異讀成「內容變了」。
v1 紀錄一律標 `hash_schema: v1` 保留,不覆寫、不宣告失效。

腳本的四個設計要求都有實測驗證,自己拼指令很容易踩到第一項:

1. **路徑無關**——同一份內容,經 symlink 或實體路徑存取必須得到相同值。
   直接對 `shasum` 輸出再摘要**會失敗**,因為它的輸出含絕對路徑;
   本專案就曾因此讓驗收員在版本綁定階段中止(派工方算 symlink 路徑、驗收方算 repo 路徑)。
2. **檔名敏感**——改檔名要改變 hash,所以摘要對象是「相對路徑 + 內容 hash」的組合。
3. **allowlist**——未列出的檔案不影響 hash,`evals/runs/` 由此自然排除。
4. **傳錯目錄不得回傳值**——allowlist 一筆都沒 match 時以 `exit 3` 中止,不回傳結果。
   空輸入的 SHA-256 是個看起來完全正常的值,是版本綁定最危險的失敗模式。

⚠️ v1 時期 `bundle-hash.sh` 位於 `dispatch/scripts/`,而 `scripts/**` 在 skill allowlist 內,
因此**修改量測工具會改變被量測 skill 的 identity**。v2 把腳本移到 repo root 解掉這件事;
移動本身是 v1 的最後一次污染,dispatch 的 skill hash 因此變動一次。

⚠️ `fixtures` 是**整檔**的 domain。改任何一筆 fixture 的 `required_elements`,同一檔內
其他所有案例的 observation 一併失去「fixtures 未變」這個重新評分前提。因此修 fixture 必須
排在既有 trace 重新評分**之後**(見 [`evals/KNOWN-ISSUES.md`](evals/KNOWN-ISSUES.md)
「執行順序的硬約束」)。

## 安裝

需要 Node.js 與 npm。**只裝 `--agent claude-code`**:

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
