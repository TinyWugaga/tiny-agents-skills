# harness evals — 現況

**Batch 6（run record）狀態：STOPPED / NOT COMPLETE。不是 PASS。**
不補跑 Batch 6 的完整 suite；後續縮減重跑另立 batch 與 run record，不覆寫既有紀錄。

## 基礎設施狀態

runner、score、judge 與 record 已實作；各元件的驗證結果分別記錄於後續 Batch，
機制說明見 [`../README.md`](../README.md) 的「執行機制」章節。
**現行 v6 的完整 `run-suite.sh` 控制流與 nonce runner 鏈尚未完成原生 subject run，
維持 `UNVERIFIABLE／NOT_RUN`**（見「Batch 21f」）。早期 host run、selftest 與 dry-run
不構成現行全鏈路證據。

以下描述目前的實作與 `--dry-run` 可觀測的行為，**不代表現行 v6 全鏈路已通過**：
`run-suite.sh` 會依 fixtures JSON 依序展開 **18 筆**（`dispatch` 9 + `harness-routing` 9），
prompt 的唯一來源是那兩個 JSON，腳本內不含任何 prompt 字面。plugin 變體直接從本 repo 的
`skills/harness/dispatch`、`skills/discipline/judgment`、`skills/discipline/token-preflight`
複製，不讀已安裝副本；付費 preflight 前會以 `diff -r` 與 bundle hash 雙重確認每份副本。

## 執行紀錄

| run | 位置 | 結論 |
|---|---|---|
| `20260826-151927-bbbb34` | repo 內 | **SUPERSEDED**。harness 有 fail-open 缺陷，不作為憑據。其記錄的 bundle hash 於 Batch 2 改用 allowlist 後全部失效 |
| `20260827-191514-fdb1fd` | repo 內 | **INVALID**。host 登入過期，18 筆全部在推論前 `authentication_failed`，routing/contract ERROR 18/18 |
| `20260827-193053-a2b802` | repo 內 | **INVALID**。登入正常，但當時的 `CLAUDE_CONFIG_DIR` 隔離連帶隱藏 host OAuth；subject ERROR 18/18、judge 在 3 筆後人工中止（白花 USD 0.144） |
| `20260829-152748-9c` | repo 內 | **FAIL（有效證據）**。2 筆 CLI 全成功；routing PASS 1 / FAIL 1、contract PASS 2 / FAIL 0、cost USD 0.4074 |
| `20260829-225157-9d` | repo 內 | **FAIL（有效證據）**。3 筆 targeted validation；routing PASS 3/3、contract PASS 2/3；`positive-3` 缺「既有測試不得修改」約束；精確成本 USD 0.5590437 |
| `20260830-000907-9e` | repo 內 | **PASS（有效證據）**。只重跑 `positive-3`；routing／contract 皆 PASS；精確成本 USD 0.3095729。單筆 regression，不是完整 suite |
| `validate-003` | host `/private/tmp/...`，未進 repo | 單筆驗證。routing PASS 1/1、contract FAIL 0/1、cost USD 0.2618 |
| `batch6-5-regression-001` | host `/private/tmp/...`，未進 repo | 三筆迴歸。CLI 0/3 failed、routing PASS 2 / FAIL 1、contract PASS 1 / FAIL 2、cost USD 0.4184、`dispatch_bundle 13f0a79b…`、`suite f9d86cde…` |

前兩筆 INVALID 是環境問題，對 skill 沒有任何結論——這正是 `run_status` 要把 FAIL 與 INVALID 分開的理由。

## Batch 6.5 後續

`positive-1` 的 contract 兩輪都 FAIL。第二輪證據排除了「規則沒送到」：Skill tool 回傳內容
**逐字包含** Batch 6.5 新增的優先權段落，模型仍以「9 個檔派 agent 純浪費額度」拒絕派工。

診斷：fixture 要求模型在 9 檔 repo 派工，那在客觀上是錯的決定；模型拒絕一條與自身正確判斷
衝突的規則屬正常行為。問題在 fixture 的受測環境，不在模型也不在措辭。

Batch 9c 已採決策測試方向：成本否決時必須主動告知使用者仍可要求派工；使用者要求後即照做。
`positive-1` 以最終 `dispatch_bundle 6c9d922d…` 重跑，routing 與 contract 皆 PASS。

`ambiguous-1` 另有兩個獨立缺陷：description 缺「要不要拆出去跑」這類字面觸發詞導致 routing 不觸發；
required_elements 要求複誦內部規則表名，違反 `tool-checklist` 的「不綁定措辭／內部名稱」。

## Batch 9：judge 執行緒邊界（9a + 9b′，2026-08-29）

**9a。** `judge.py` 的 `response_text()` 原本把所有 assistant 事件攤平，subagent 內部的
Bash / Read / 敘述會被當成主執行緒自己做的事，「派工出去、由 subagent 去掃描」因而被讀成
「主執行緒靜默自己做」。現改為只採信 top-level `parent_tool_use_id` 為 null 的事件
（新增 `is_main_thread()`）。主執行緒發出的 `Agent(...)` 呼叫本身 parent 為 null，
派工證據不受過濾影響。

`judge_selftest.py` 是零成本自測，不呼叫 claude CLI、不產生費用。repo 內三份 trace 的
assistant 事件 parent 全為 null，驗不到「非 null 要被排除」這條分支，所以合成 trace
直接寫在該檔內而不另存 `.jsonl`——測試材料若能在不動 suite hash 的情況下被改掉，
這個測試就沒有版本綁定的意義；寫在 `evals/*.py` 裡它就跟 `judge.py` 一起進 allowlist。

已驗證（2026-08-29，全部零成本，未起任何真實 session）：

- `python3 -m py_compile judge.py judge_selftest.py` 通過。
- 迴歸：53 份 repo raw trace，新舊 `response_text()` 輸出逐字相同，差異 0 筆。
- 缺陷分支：同一份合成 trace，pre-9a 輸出含全部三個 subagent marker，post-9a 全數排除，
  `[tool_use] Agent(` 與其 `subagent_type` / `model` 參數兩者皆保留。

bundle hash：`dispatch_bundle` 不變（`a4f2e713e464d7f05aab38b3218c563de317226ab0832b5fa35e23a20b65db6c`）；
`harness_test_suite` 由 `29dfb386c8dd519aeab5db7c50b324e87c9fd0d10b02592aba6e957430c8f230`
變更為 `0233336ec3091d99fd6206ee9f1579e92cedb087bfa19716aeb292bfbbf13219`。

**9b′。** `harness-routing__dispatch-absent-1` 在 `batch6-5-regression-001` 的 contract FAIL
受上述攤平缺陷影響：該次判 FAIL 的依據包含被誤歸到主執行緒的 subagent 工具呼叫。
來源 trace 於 2026-08-29 在 host 端檢視，SHA-256
`6827ccbb04bd4f58a39630268839b40867ab83d5db30a0dcb0abb0d4c1ef9470`；該檔只存在於 host
`mktemp`，未複製進 repo，也未建立任何衍生證據檔。

**這不是人工佐證的 PASS。** 手上的證據只能支撐「該 FAIL 的判定依據不成立」，
支撐不了「該回應滿足 required_elements」——後者需要主執行緒回應全文，未取用亦未留存。
既有 run 紀錄一字未動；本段是重跑前狀態，正式判定見下節 Batch 9c。

## Batch 9c：最小真實重跑（2026-08-29）

正式紀錄：[`runs/20260829-152748-9c/`](runs/20260829-152748-9c/)，狀態 **FAIL（有效證據）**。
兩筆 subject、兩筆 judge 與 preflight 全部成功，CLI 失敗 0 筆；`positive-1` routing／contract
皆 PASS，`dispatch-absent-1` contract PASS、routing FAIL。

`dispatch-absent-1` 的 routing FAIL 是可重現的契約衝突：主執行緒呼叫 `Skill(dispatch)`，
收到 `Unknown skill: dispatch` 後才依 fallback 派出唯讀 Explore agent。`score.py` 把這次失敗的
Skill 呼叫計為「dispatch 已觸發」，而 fixture 的 `expected_route.dispatch` 要求 false。
這是 9c 當時的判定；9d 已修正 scorer，只把主執行緒中有成功 `tool_result` 的 Skill 呼叫計為觸發，
失敗呼叫另列 `attempted_failed`。9c 保留為修正前的有效 FAIL，不代表現行 scorer 結果。

真實 trace 首次覆蓋 9a 的非 null 分支：12 個 child assistant 事件共用 Agent tool-use id 作為
`parent_tool_use_id`，包含 Bash 與 Read；post-9a judge 排除這些 child 事件，同時保留主執行緒的
Agent 派工證據，`dispatch-absent-1` contract 因而 PASS。repo 內只保存 `.json`／`.md` run record，
raw trace 留在 repo 外暫存目錄。

成本（observation，metric=Claude Code session 自報 cost，unit=USD）：preflight 0.063963、
subject 0.2408、judge 0.1026、合計 0.4074，低於本輪 target USD 0.55。
hash：`dispatch_bundle 6c9d922dcdac30fa500201504de58d030dc35d7522db802be06756409e7e2149`；
`harness_test_suite 0233336ec3091d99fd6206ee9f1579e92cedb087bfa19716aeb292bfbbf13219`。

## Batch 9d：scorer 修正與三筆 targeted validation（2026-08-29）

正式紀錄：[`runs/20260829-225157-9d/`](runs/20260829-225157-9d/)，狀態 **FAIL（有效證據）**。
`score.py` 現在以主執行緒 `Skill` tool-use 與對應的成功 `tool_result` 成對判定觸發；失敗呼叫不再
算成觸發，缺少對應 result 則 fail-closed 為 ERROR。`score_selftest.py` 以合成事件覆蓋成功、失敗、
child 與缺 result 分支；真實資料仍未覆蓋「失敗 Skill 呼叫」分支。

三筆 routing 全部 PASS；`dispatch-absent-1`、`ambiguous-1` contract PASS，`positive-3` contract FAIL。
FAIL 的可觀察原因是派工單沒有明確禁止修改或刪除既有測試。精確成本 observation 為
USD 0.5590437。hash：`dispatch_bundle 6c9d922d…`、`judgment_bundle 5b043ab7…`、
`harness_test_suite a79d663a…`。

## Batch 9e：`positive-3` regression（2026-08-30）

正式紀錄：[`runs/20260830-000907-9e/`](runs/20260830-000907-9e/)，狀態 **PASS（有效證據）**。
`dispatch/SKILL.md` 已明列「寫派工 prompt 前先讀 `references/templates.md` 並保留模板下限」；
新 bundle 下單筆重跑 routing／contract 皆 PASS，judge 的 required 3 條與 forbidden 2 條全部 PASS。

這是單筆 observation，支持修正有效，但不證明統計穩定性，也不是完整 suite PASS。精確成本為
USD 0.3095729。9e 綁定 `dispatch_bundle fd139f25…`、`judgment_bundle 5b043ab7…`、
`harness_test_suite a79d663a…`；9d 的 FAIL 紀錄保留且未覆寫。

## Batch 10：runner source-of-truth（2026-08-30）

`run-suite.sh` 不再從 `~/.claude/skills` 複製受測內容，改為直接使用 repo 三個 canonical source。
每個 plugin 變體在付費 preflight 前都要通過逐檔 `diff -r` 與 bundle hash 比對；
`no-dispatch`／`no-judgment` 也會機械確認缺席 skill 沒有混入。`--dry-run` 會在建立
WORK／plugin 暫存目錄前結束，不再留下兩個未清理的空 `mktemp` 目錄。future run record
同時記錄三個實際載入 skill 的 bundle hash；任一 repo 或 plugin hash 無法計算時會先清理暫存目錄，
再以 `exit 2` 停在付費 preflight 之前。若 hash 在執行途中失效，`record.py` 會把紀錄標為 INVALID
並回傳 `2`，suite 不會誤報成功。

現行 hash：`dispatch_bundle fd139f25b7e5745df7c5ab6aa1d20629e40edcb8a807f5277c11acf433eddcae`；
`judgment_bundle 5b043ab762b7c610ae885225532104248268e70b6fb3bf3652d94816f24a18b0`；
`token-preflight_bundle a705ca101d56f27a6ff7addc66eb6fa80375a4e6b85286422fca8463e4982de1`；
`harness_test_suite cef985d0b64449c0053345f931fab3a188bfe31f05734ac861a28ac468796aa4`。
suite hash 因 runner 修改而改變；**這個現行 suite 尚未執行完整 18 筆真實驗證。**

## Batch 11：bounded-review 導入與兩個評分／傳輸缺陷（2026-08-31）

在 `judgment` 加入有界複查（`references/bounded-review.md` + `SKILL.md` 路由 + 6 筆新 fixtures）
的過程中修掉兩個既有缺陷。**兩者都只完成 selftest 與 `--dry-run`，真實 session 一律 `NOT_RUN`。**

本批所有 observation 綁定下列 bundle（以當時的 `dispatch/scripts/bundle-hash.sh` 現算，
**`hash_schema: v1`**）。v1 值與 v2 值不可直接比較，見「Batch 13f」：

| bundle | sha256 前 12 |
|---|---|
| `judgment_bundle` | `3f4e14ce8071` |
| `harness_test_suite` | `bac3abd9efa7` |

任一 bundle 變動後，本批的 dry-run 筆數與 selftest 結果即失效，須重新量測。

### 11a `score.py` 預期值寫死 dispatch

`expected_map(fx)` 沒有 `expected_route` 時一律回 `{"dispatch": bool(expected_trigger)}`。單一 skill
的 fixture 其對象本來就由頂層 `skill_name` 決定。六份 fixture 檔 58 筆中 **40 筆**判定錯誤
（judgment 12、token-preflight 12、grill-me 10、claude-collaboration 6）；dispatch 9 筆碰巧正確；
`routing-fixtures.json` 9 筆全用 `expected_route`，不受影響。

`runs/` 內沒有 `judgment__*` / `token-preflight__*` / `grill-me__*` 紀錄，因此**不能**說過去的 PASS
已失效；只能說若曾用舊 scorer 跑過該 suite，其 routing 結果不可信。

修法：`expected_map(fx, skill_name=None)`——`expected_route` 優先且去 namespace；否則用頂層
`skill_name`；兩者皆無回 `None`，`score()` 判 `ERROR` fail-closed。不採「在 fixtures 補
`expected_route`」：與 `expected_trigger` 重複表達會 drift，且只改 judgment 的話其餘 28 筆仍錯。
`score_selftest.py` 補 9 項。

`expected_route` 維持現行分工，**不**寫進 `AGENTS.md` 的通用 fixture schema：單一 skill fixture 用
`skill_name` + `expected_trigger`，跨 skill routing fixture 才用 `expected_route`。寫進 AGENTS.md
會被誤讀為每筆都必填。

### 11b runner 逐行讀取，多行 prompt 被拆散（BR-F6）

`run-suite.sh` 用 `while IFS=US read -r SUITE ID CFGNAME DENYX PROMPT` 讀 loader 的 TSV。prompt 含
換行時續行成為新記錄，**續行第一欄會成為 `SUITE`**，再拼進 `"${SUITE}__${ID}"` 當輸出檔名——含
`/` 產生巢狀路徑，含 `../` 可逸出 `$OUT`。judgment 27 筆邏輯 fixture 被展開成 53 筆
（`positive-8` 23 個實體行、`negative-3` 5 個）。既有 fixtures 全是單行 prompt，所以到此才暴露。

修法限在 serialization 邊界：新增 `transport.py`（`encode`/`decode`，只處理 `\` `\n` `\r`，解碼是
單次左到右掃描而非連續 replace）；loader 輸出前 encode，`read` 之後、送進 `run-fixture.sh` 之前
decode，尾端 sentinel `X` 擋掉命令替換吃掉結尾換行；加 fail-closed 檢查「transport 記錄數 ==
JSON fixture 數」，不一致 `exit 2`。新增 `transport_selftest.py`（往返 + 單行不變式各 10 例，含
字面 `\n`、結尾換行、`../`、非 ASCII）。未動 `run-fixture.sh` / `judge.py` / `record.py`，未併入
Batch 6.5／7。

### 11c host 上要跑的（第 5、6 步合併）

Cowork VM 跑不了真 session，本批只有 `--dry-run` 與兩支 selftest 的結果。

**底部「要接手的話」列的預設命令只跑 `dispatch 9 + harness-routing 9 = 18 筆`，不含 judgment。**
本批的核心驗證必須另外指定 `HARNESS_FX`，兩個命令都要跑：

```sh
# (1) judgment 19 + harness-routing 9 = 28 筆 —— 本批的核心驗證
HARNESS_FX=skills/discipline/judgment/evals/fixtures.json \
  sh skills/harness/evals/run-suite.sh

# (2) dispatch 9 + harness-routing 9 = 18 筆 —— 既有 suite 的 regression
sh skills/harness/evals/run-suite.sh
```

兩者都會帶到 `harness-routing` 9 筆（`HARNESS_RT` 未覆寫時固定載入），因此該 suite 會跑兩次；
以 (2) 的結果為 regression 判準即可。筆數不符就是 transport 或 fixtures 有問題，先查再跑。

重點是量 `judgment` description 擴張後對其他 skill 的 routing 影響，不只看新增 6 筆是否 PASS。

判讀規則：**既有 PASS 變 FAIL 才是 regression**；既有 FAIL（如 `harness-routing__boundary-3`）維持
或改善都不構成 regression，但也不得據以宣稱完整 suite PASS。兩次 run 的 `harness-routing` 結果若
不一致，記為 session variance 並調查，不得只採其中一次。

不要用 `| head -1` 取筆數：`head` 關閉管道會送出 SIGPIPE，開 `pipefail` 時 exit 141，未開時又被
`head` 的成功狀態掩蓋。直接跑完整 `--dry-run`。

### 11e 發布前置（順序不可調換）

已安裝副本是 `npx skills` 從 GitHub `TinyWugaga/tiny-agents-skills` 裝的 symlink，**不會**反映
working tree。因此在發布前執行 `npx skills update` 只會取回舊版。正確順序：

1. 跑 11c 的兩組真實 suite。
2. 對整份 `references/bounded-review.md` 做 fresh-context 獨立驗收。這不是選配——`judgment` 的
   完成判斷表規定「文件或規則變更」必須完成 fresh-context read-back，而本批改的正是 judgment
   自己。真實 fixture suite 只驗得到觸發與已覆蓋的行為，取代不了整份規則的獨立讀回。
3. commit 核准的變更並發布到來源 repository。
4. `npx skills@latest update judgment --global`。
5. 驗證已安裝 bundle 等於發布後重新量測的 `judgment_bundle`。
6. 重新打包並上傳 Claude Cowork／Chat 的 `judgment.zip`。

未驗證項要分開記，不合併成籠統限制：跨 session closure 連續性、Codex Desktop 的
`claude-collaboration` composition、Cowork 平台一致性。

### 11d 測試 backlog（下一個 cycle）

現有 fixtures 沒有覆蓋 `bounded-review.md` 的兩條規則，即使第 6 步全數通過也不得宣稱已驗證：

- 基準爭議閥門（只能在 full review 提出、必附三欄、Owner 駁回後同一 baseline 不得重提）。
- baseline vNext audit 逐條重新確認 non-goals 與 accepted risks，不預設繼承。

另有一筆 Non-blocking 未處理：`bounded-review.md` 未明寫 baseline 的草擬者（契約只規定 Owner
核准並凍結、產出方不得單方面認定）。建議補「任何角色可草擬，Owner 對完整性與凍結負責」。

### 11f Host 執行結果（2026-09-01）

兩個 run 都在 `runs/` 內：`20260901-batch11-judgment-full`、`20260901-batch11-default-full`。

**judgment suite：`run_status: INVALID`**。27 筆 subject 全部跑完、CLI 失敗 0，但
`harness-routing__boundary-1` 的 judge 回了「合法 JSON 之後還有多餘內容」
（`Extra data: line 3 column 1 (char 639)`），該筆 contract 記 ERROR，整輪因此不得宣稱 PASS。
逐筆觀測仍然有效——這是 UNVERIFIABLE 一筆，不是全部作廢。

routing 19 PASS / 8 FAIL，FAIL 清單：`judgment__positive-1`、`positive-2`、`positive-4`、
`positive-5`、`ambiguous-1`、`ambiguous-2`、`ambiguous-3`、`harness-routing__boundary-3`。
contract 15 PASS / 11 FAIL / 1 ERROR。已知成本下限 USD 4.393918（`judge_usd` 缺一筆）。

新增六筆：`positive-7`、`positive-8`、`positive-9`、`negative-3` routing 與 contract 皆 PASS；
`ambiguous-3` routing FAIL（行為正確地要求先提供產出物，但未觸發 judgment）；
`explicit_mention-3` routing PASS、contract FAIL（漏掉「finding 必須指名 Violated criterion」）。
trace 顯示 `explicit_mention-3` 與 `positive-8` 都實際讀取了 `bounded-review.md`（各 1 次 Read
tool-use;raw trace 內的檔名字串各出現 6 次），
因此 `explicit_mention-3` 不是路由缺陷，屬 reference 顯著性或 fixture 要求過度具體。

**default suite：有效 FAIL**。18 筆 subject 全跑完，routing 16 PASS / 2 FAIL，
contract 13 PASS / 5 FAIL，成本 USD 2.7726。對照既有 baseline：
`dispatch__ambiguous-1` routing PASS→FAIL、`dispatch__explicit-mention-1` contract PASS→FAIL 為
退化；`dispatch__positive-2` 與 `harness-routing__judgment-absent-1` contract FAIL→PASS 為改善；
`boundary-3` 維持既有 FAIL。兩輪已知總成本下限 USD 7.166518。

判讀邊界：**judgment 的 18 筆是 scorer 修正後第一次被正確量測，只能記為 baseline observation，
不得稱為 regression**；`harness-routing` 的 9 筆有有效歷史基準（一直使用 `expected_route`，不受
舊 scorer 的 dispatch fallback 影響），其中 `boundary-3` 是既有缺陷。

### 11g 待補資料與已裁決項目

需要的資料：

1. `boundary-1` 單獨重判，結果另存，不覆寫原始 INVALID run。
2. 單獨重跑 `dispatch__ambiguous-1` 與 `dispatch__explicit-mention-1`，只判斷可重現性——重跑
   證明不了因果，要歸因到 description 擴張需要 old/new description 的 A/B。
3. **未決的因果問題**：既有 6 筆 judgment positive／ambiguous 沒有觸發 judgment。因為修正前沒有
   有效量測，無法判斷這是本來就如此，還是 description 擴張稀釋了觸發。這 6 筆才是
   dilution A/B 對象：比較 pre-bounded description 與 current description，且除非有可重現的多次量測與
   預先定義的判準，結果只能記為 A/B observation，不得宣稱因果。`ambiguous-3` 是新增觸發面，
   另作 current description 的邊界驗證，不納入 dilution 指標。

已裁決並實作：

- `ambiguous-3` 維持 `expected_trigger: true`;description 與路由明列第二意見的前置輸入不完整時,
  仍由 judgment 索取產出物與驗收條件,但不載入 `bounded-review.md`、不啟動 cycle。
- `explicit_mention-3` 保留 `Violated criterion` 要求,並把 prompt 改成明確要求說明哪些意見
  能列為 Blocking;不為了讓 fixture PASS 而調高 reference 顯著性。
- Finding schema 收掉弱化句：指不出 `Violated criterion` 的不得列為 Blocking 或
  Non-blocking finding;只有主張 baseline 缺需求時改列 `Scope proposal`,證據或推論無效時不保留。
- judgment description 與路由補上 Owner 裁決 reviewer 意見或 finding disposition;
  disposition 只需足以裁決的 baseline 與 finding 內容,不被 full review 的完整產出物前置擋住。
- `positive-10` 新增行為驗證：指不出 `Violated criterion` 的意見不得列為 finding;
  主張 baseline 缺少需求時改列 `Scope proposal`,不在本 cycle 處理。

修正後 observation 綁定 `judgment_bundle e2a9d915cb9d`;內部檔案 hash 為
`SKILL.md 57f277f03fbb`、`bounded-review.md a4be6d627aa5`、`fixtures.json 68d28a1c8343`。
19 筆 judgment fixtures 與 9 筆 harness-routing 的 dry-run 正確展開為 28 筆,兩支 selftest 通過;
真實 routing 與 contract 仍為 `NOT_RUN`。

## Batch 12：host 驗證、fresh-context 驗收與 default fixture 校正（2026-09-01）

### 12a 完整 suite observation（舊 bundle `e2a9d915cb9d`）

judgment 完整 run：[`runs/20260901-215156-0fe73d/`](runs/20260901-215156-0fe73d/)，有效
**FAIL**。28 筆 CLI 全成功；routing 23 PASS / 5 FAIL，contract 20 PASS / 8 FAIL，cost
USD 3.8779。新增的 bounded-review 案例 `positive-7`、`positive-8`、`positive-9`、`negative-3`、
`ambiguous-3`、`explicit_mention-3`、`positive-10` 的 routing 與 contract 全部 PASS。
`harness-routing__boundary-1` 的 judge 亦 PASS，先前「合法 JSON 後多出內容」沒有重現。

default 完整 run：[`runs/20260901-222543-ccd5f1/`](runs/20260901-222543-ccd5f1/)，有效
**FAIL**。18 筆 CLI 全成功；routing 15 PASS / 3 FAIL，contract 13 PASS / 5 FAIL，cost
USD 2.4934。相對前一輪，`dispatch__ambiguous-1` routing FAIL 可重現；
`dispatch__explicit-mention-1` contract 改為 PASS，舊 FAIL 未重現。另出現兩筆退化候選：
`dispatch__positive-4` routing／contract FAIL、`dispatch__negative-3` contract FAIL。

兩輪合計 cost observation 為 USD 6.3713。之後 `bounded-review.md` 已修改，現行
`judgment_bundle` 不再是 `e2a9d915cb9d`，因此這兩輪只能作歷史 observation，不能授權發布現行 bundle。

### 12b 六筆既有 judgment fixture 的單次 old/new description A/B

舊 description 變體綁定 `judgment_bundle 610dbea83a82`，證據在
[`runs/20260901-batch11-ab-old-desc/`](runs/20260901-batch11-ab-old-desc/)。current side 沿用
12a 的 judgment 完整 run。六筆中五筆 old/new 結果相同；只有 `positive-1` 為 old 觸發、new
未觸發。這是單次 observation，不支撐 description 擴張造成稀釋的因果結論。old side 六個
subject session cost USD 0.496889。

### 12c fresh-context 獨立驗收與 closure

乾淨 context 對 `judgment/SKILL.md` 與整份 `references/bounded-review.md` 做 full review，找到三筆
accepted Blocking：Finding schema 與 New blocker 的邊界不清、closure 模板漏掉 regression 的
同案例修正前後對照、in-scope blocking 沒要求指明原始需求範圍。修正後由另一個乾淨 context
只做 closure verification，三筆皆 PASS，沒有 New blocker。

修正後 `bounded-review.md` hash 為 `3789d1318305`，現行 `judgment_bundle` 為
`00ebf628116c`。靜態檢查、`transport_selftest.py`、`score_selftest.py` 與 28 筆 dry-run 都通過；
但 12a 的真實 suite observation 已因 bundle 變更失效，現行 bundle 仍需重新跑完整 suite。

### 12d default 兩筆退化候選的診斷與量尺校正

[`runs/20260901-batch11-default-regression/`](runs/20260901-batch11-default-regression/) 以原 fixture
重跑兩筆，兩個 FAIL 都可重現，cost USD 0.2815。檢視 subject 回應後判定問題在 fixture：

- `positive-4` 的 prompt 只有「這件事」，缺少 `dispatch` description 明列的必要輸入「當前任務
  描述與範圍」。模型先索取任務內容是正確行為，原 fixture 卻把它判成 routing／contract FAIL。
- `negative-3` 正確地未觸發 dispatch，並直接依 `SPEC.md` 驗收 `docs/api.md`；原 contract 卻要求
  回應主動複述「這不屬 dispatch」，測到的是內部職責措辭而非使用者可觀察行為。

最小校正只改 `dispatch/evals/fixtures.json`：`positive-4` 改成包含三個具體工作項目的自足 prompt；
`negative-3` 改為要求直接依既有 SPEC 驗收，並禁止新增 SPEC 未定義的條件。未修改
`dispatch/SKILL.md`。

第一次 targeted 重跑在付費 fixture 前被 preflight 中止：
[`runs/20260901-batch12-default-fixture-correction/`](runs/20260901-batch12-default-fixture-correction/)
記錄 host `claude auth status` 為 `loggedIn: false`。兩筆 fixture 與 judge 都未執行，該次不構成
契約證據。

恢復 host OAuth 後，兩筆正式重跑見
[`runs/20260901-batch12-default-fixture-correction-rerun/`](runs/20260901-batch12-default-fixture-correction-rerun/)：
routing 2/2 PASS，`negative-3` contract PASS；`positive-4` contract 唯一 FAIL 是要求同時宣告
「預設依序」，但案例已滿足規則明列的平行例外（兩項彼此獨立且都必要、上限 2）。subject 已
明確說明倍增成本、上限、必要性及依賴時改為依序，原 required element 把 general default 與
exception decision 綁成互斥要求。該輪 cost USD 0.3249，綁定 `dispatch_bundle 272ffc605ed8`。

移除互斥的「預設依序」措辭後，只重跑 `positive-4`：
[`runs/20260901-batch12-positive4-contract-correction/`](runs/20260901-batch12-positive4-contract-correction/)
routing 與 contract 皆 PASS，cost USD 0.1983。現行 `dispatch_bundle` 為 `2cf168c664e9`；
`judgment_bundle` 為 `00ebf628116c`；`harness_test_suite` 仍為 `bac3abd9efa7`。這是 targeted
observation，不取代最終完整 suite。

### 12e 目前發布閘門

發布流程停在 11e 第 1 步。fresh-context 驗收已完成，但最終完整 suite 未通過；不得 commit、push、
更新已安裝 skill 或上傳 Cowork／Chat ZIP。

judgment 最終 run：
[`runs/20260901-batch12-judgment-final/`](runs/20260901-batch12-judgment-final/)，綁定
`judgment_bundle 00ebf628116c`、`dispatch_bundle 2cf168c664e9`、`harness_test_suite bac3abd9efa7`。
狀態為有效 **FAIL**：CLI 0/28 failed、routing 21 PASS / 7 FAIL、contract 16 PASS / 12 FAIL / 0
ERROR，cost USD 5.6512。

相對 12a 的同組 observation，新差異為：`judgment__positive-2` routing PASS→FAIL；
`positive-9` contract PASS→FAIL；`ambiguous-3` routing PASS→FAIL；`explicit_mention-3` contract
PASS→FAIL；`boundary-2` routing／contract PASS→FAIL；`judgment-absent-1` contract PASS→FAIL；
`boundary-3` routing FAIL→PASS。bounded-review 新案例中 `positive-7`、`positive-8`、`negative-3`、
`positive-10` 仍維持 routing／contract PASS。

default 最終 run：
[`runs/20260902-batch12-default-final/`](runs/20260902-batch12-default-final/)，bundle 綁定同上。
狀態 **INVALID**：CLI 0/18 failed、routing 16 PASS / 2 FAIL；contract 13 PASS / 4 FAIL / 1 ERROR。
`dispatch__negative-2` 的 judge 先輸出一份合法 PASS JSON，又附加說明與第二份 JSON，parser 以
`Extra data` fail-closed；因此整輪不得作完整契約證據。校正過的 `dispatch__positive-4` 與
`negative-3` routing／contract 都 PASS。

兩組 run 對相同 bundle 的 routing boundary 出現相反 observation：`boundary-2` 在 judgment run
FAIL、default run PASS；`boundary-3` 在 judgment run PASS、default run FAIL。這證明單次翻轉不能
直接歸因到 skill 變更，至少包含 session variance。`positive-9`、`ambiguous-3`、
`explicit_mention-3` 也都是前一輪 PASS、本輪 FAIL，下一步應先 targeted repeat，再決定要不要改
`SKILL.md` 的 reference 路由；不得直接為單次 FAIL 改契約。

本 cycle 在最終完整 suite 前已知成本為 USD 7.672889。這次完整驗證新增：judgment USD 5.6512；
default 已知成本下限 USD 2.2773639（preflight + subject + 17 筆有成本資料的 judge；錯誤 judge 成本
缺失）。cycle 累計已知下限為 **USD 15.6014529**。原增量 estimate 約 USD 6.4，實際已知下限
USD 7.9285639，至少高出約 24%。依成本閘門，下一次付費 targeted repeat 或完整 suite 必須另行
估算並取得放行。

## Batch 13：發布判準、known-issue ledger 與 judge 紀錄鏈（2026-09-02）

本批全部零成本：無真實 session、無付費執行、未 commit／push、未更新已安裝 skill、未上傳 ZIP。

### 13a 發布判準與重跑優先序

先前 11e 只寫「跑兩組真實 suite」，沒有定義什麼結果算通過，因此即使重測全數翻回 PASS，
gate 仍不可判定。本節定義判準；**三條全部成立才可進入 11e 第 3 步（commit 與發布）**：

1. 本批新增七筆（`positive-7`、`positive-8`、`positive-9`、`positive-10`、`negative-3`、
   `ambiguous-3`、`explicit_mention-3`）的 routing 與 contract 全部 PASS。
2. [`KNOWN-ISSUES.md`](KNOWN-ISSUES.md) 中每一筆 disposition 都不是 `PENDING`。
3. 相對前一輪**同 skill hash 且同 fixture hash** 的 observation，沒有新的 PASS→FAIL 退化。
   （13f 之前寫的是「同 bundle」，在單一 `harness_test_suite` 下無法區分是 skill 變了、
   fixture 變了、還是只有 evaluator 變嚴；hash schema v2 拆開後這條才可判定。）

判準 2 不要求所有既有 FAIL 都修好——`fixture_invalid` 可裁決為改 fixture，
`stochastic_known_issue` 可裁決為容許——但**不得留在未裁決狀態**。

**重跑判準的優先序（較嚴格者優先）：**

- 本批新增七筆：**3/3**。它們是本批的產出物，對自己的產出物降低門檻沒有正當理由。
  `ambiguous-3` 同時是新增案例與已觀測翻轉案例，依此規則適用 3/3。
- 只有「本批開始前即存在、且已觀測到同 bundle 翻轉」的案例才適用 **2/3**：目前僅
  `harness-routing__boundary-2`、`harness-routing__boundary-3`。
- 2/3 通過**不得記為 fixture PASS**，只能記為「release gate 容許的 known flaky」，
  並在 `KNOWN-ISSUES.md` 保留條目。

2/3 是降噪門檻，不是穩定性證據：真實通過率 p=0.5 的案例有 50% 機率通過 2/3。
不得用它宣稱任何案例已驗證穩定，也不得套用到未預先指定的 fixture。

### 13b judge 解析與紀錄鏈（已實作，selftest 通過）

`judge.py` 的 docstring 早已宣稱「輸出不是合法 JSON、或條目數對不上，一律記 ERROR」，
但 `judge_one()` 只做 `json.loads`，**沒有實作條目數與 schema 驗證**。本批補上：

- 新增 `parse_verdict()`：條目數（對 `required_elements`／`forbidden_elements` 逐一比對）、
  每項 `element`／`verdict`／`evidence` 的型別與值域、`overall` 與逐條判定的一致性。
- **不採 `raw_decode` 取第一個物件的救援。** `dispatch__negative-2` 的實際輸出是：一份含多餘
  key 的 JSON → 散文「Wait, I need to fix the JSON format — remove the stray key.」→ 一份被截斷
  的第二份 JSON。取第一個物件等於採信 judge 自己已宣告作廢的判定，是 fail-open。
  尾端只要有非空白內容一律不可用，並記下 `has_second_json_start`、`second_json_complete`、
  `trailing_chars` 供診斷。
- 唯一放行的異常是「僅多出無關 key」：判定可用，但記 `anomaly.kind = extra_keys`。
  **此條已於 13f 推翻**：`corrected_overall: FAIL` 這種 key 就承載撤回語意，「無關」無法事先
  斷言，現改為未知 top-level key 一律 ERROR（`anomaly.kind = unknown_keys`）。
- 判定不可用時仍保留 `_cost_usd`。11f 的「`judge_usd` 缺一筆、只能記成本下限」就是這個路徑
  造成的，修正後 ERROR 筆的成本仍會計入。

`record.py`：逐筆新增 `contract_anomaly`，run record 新增 run 層級 `warnings`（含
`fixture_id`／`source`／`kind`／`usable`／完整 detail），`.md` 在有異常時多一張「parser 警告」表。
異常不改變 INVALID 判定——那仍由既有的 unusable 檢查負責——只補可追溯性。

新增 `record_selftest.py`（零成本）。四支 selftest 於 2026-09-02 在 Cowork VM 全部通過：
`judge_selftest.py`（含 14 項新 parser 案例，逐字重現 `negative-2` 的輸出形狀）、
`record_selftest.py`、`score_selftest.py`、`transport_selftest.py`；
`py_compile` 對 `judge.py`／`record.py` 通過。

**未驗證：** 本機 Claude CLI 2.1.247 的 `--json-schema` structured output 尚未評估。Cowork VM 的
CLI 受限（只支援 `claude -p`，`--help` 不含該旗標），無法在此判定；須在 host 上評估。
若可用，它比 parser 端防禦更根本——但那是下一批的事，不在本批範圍。

### 13c known-issue ledger

[`KNOWN-ISSUES.md`](KNOWN-ISSUES.md) 逐筆列出 Batch 12 最終兩輪的 12 筆 contract FAIL 與
7 筆 routing FAIL，各附證據與 proposed 分類；`Owner disposition` 全部為 `PENDING`。
分類分布：`fixture_invalid` 5、`stochastic_known_issue` 4、`skill_defect` 3（contract 部分）。
沒有任何一筆歸為 `harness_error`——唯一的 harness_error 是 judge parser，已於 13b 修正。

值得注意的是 `harness-routing__agent-unavailable-1`：`env.deny_extra: ["Agent"]` 設定正確，
但 prompt 缺掃描範圍，模型先索取輸入而從未嘗試呼叫 Agent，因此永遠到不了「被拒」的受測分支。
這與 12d 的 `dispatch__positive-4` 同型——**fixture 缺必要輸入時，測到的是索取輸入的行為，
不是宣稱要測的行為**。ledger 中 5 筆 `fixture_invalid` 有 4 筆屬這一型。

### 13d 下一步與成本估算

順序（第 1–3 步零成本；13b／13c 這兩個**章節**已完成，步驟 1–3 本身尚未執行）：

1. Owner 逐筆裁決 `KNOWN-ISSUES.md` 的 disposition（13f 原子化後為 **20 筆**，
   合法值與發布效果見該檔「詞彙」節）。
2. 依裁決修 fixture（`fixture_invalid`）並重算 `fixtures` domain hash。
3. host 上評估 `--json-schema`；五支 selftest 重跑（含 13f 新增的
   `scripts/hash-domain-selftest.sh`）。
4. 重新評分 `positive-7`／`positive-8`／`positive-10`／`negative-3` 的既有 trace
   （judge 費用，非 subject 費用；見 13f）。
5. 付費 targeted repeat：五筆各 3 次。

第 5 步的成本 estimate（metric = session 自報 cost，unit = USD；依據為 12d 的
兩筆含 preflight USD 0.2815 與單筆含 preflight USD 0.1983，推得邊際每筆 0.08–0.14、
preflight 約 0.04）：

```
3 × (0.04 + 5 × 0.08~0.14) = USD 1.32 ~ 2.22
```

**建議預算取 USD 2.3**，高於公式上界的部分是緩衝，理由有二：本 cycle 原 estimate 已低估
24%；`boundary-2`／`boundary-3` 的 session variance 意味著單筆成本分布本身不穩。
這是預算，不是由公式直接推得的區間——公式區間就是上式的 1.32–2.22。

另一個先決條件：`20260901-batch12-judgment-final` 的 trace 顯示 `seven_day`
rate limit utilization 已達 0.94。付費重跑前先確認額度，否則可能在中途中斷並浪費已花的部分。

### 13e 本批未做的事

- 未修改任何 fixture、`SKILL.md` 或 `run-suite.sh`。
- 未把四支 selftest 接進 `run-suite.sh` 的 preflight。目前它們仍需手動執行；若要讓
  「零成本自測通過才付費」變成機械保證，這是一行改動，但屬於 runner 行為變更，留待裁決。
- bundle hash 因 `judge.py`／`record.py`／新增 `record_selftest.py` 而變動（三者都在
  `evals/*.py` allowlist 內）。`harness_test_suite` 由 `bac3abd9efa7` 變更為
  **`c476ea4ee854`**（2026-09-02 於 Cowork VM 以 `bundle-hash.sh skills/harness suite` 現算）。
  **Batch 12 的所有真實 observation 因此不再綁定現行 suite hash**，其結論僅適用於 ledger 所載的舊 hash。
- `judgment_bundle` 與 `dispatch_bundle` 本批未修改，但也**未在此重新量測**：本次 session 只取得
  `skills/harness` 的存取權，`skills/discipline/judgment` 不在範圍內，`bundle-hash.sh` 無法計算。
  發布前須在 host 重算三個 bundle hash 並確認 `judgment_bundle` 仍為 `00ebf628116c`。

### 13f evaluator／fixture 版本分離與遷移規則（hash schema v2，2026-09-02）

先校正術語：這**不是**數學上的 self-referential hash——腳本仍可確定性地 hash 自己。真正的
問題是 **evaluator 工具被錯誤納入 runtime skill 的 identity domain，造成版本污染**：
`bundle-hash.sh` 住在 `dispatch/scripts/` 而 `scripts/**` 在 skill allowlist 內，
`suite` mode 又把 evaluator 程式、runner 腳本與 fixture 綁成同一個 `harness_test_suite`。
後果就是 13e 記到的那件事：改 `judge.py` 的解析邏輯，作廢全部 skill observation。

#### 四個互斥 domain

腳本移到 **repo root** [`scripts/bundle-hash.sh`](../../../scripts/bundle-hash.sh)，
識別拆成四個 domain 加一個 schema 版本：

| domain | 內容 | 變更後作廢什麼 |
|---|---|---|
| `skill` | `SKILL.md` + `references/**` + `scripts/**` + `assets/**`（**排除 `evals/**`**） | 該 subject 的 skill 行為證據 |
| `fixtures` | 本次**實際載入**的 fixture 檔與 `seed/**`（不掃全 repo） | 對應案例的 observation |
| `runner` | `run-suite.sh` + `run-fixture.sh` + `transport.py`（session 隔離、plugin 組裝、transport、工具權限） | subject trace |
| `evaluator` | `judge.py` + `score.py` + `record.py` 與判定 prompt（**排除 `*_selftest.py`**） | routing／contract 判定；**保留的 raw trace 可重新評分** |
| `hash_schema_version` | 演算法與各 domain allowlist 的版本 | 決定不同 hash 是否可比較 |

拆出 `runner` 的理由：只做 skill／fixtures／evaluator 三個 domain 的話，`judge.py` 或
`record.py` 一改仍會讓整輪 run-level evidence 失效。分開之後，evaluator 變更只需**重新評分
既有 trace**，不必重跑付費 subject session。

#### v2 baseline（2026-09-02 於 host 現算）

| domain | sha256（前 12） |
|---|---|
| `hash_schema` | `v2` |
| `dispatch_skill` | `2d6c0d99b1c4` |
| `judgment_skill` | `0c5a3deaec63` |
| `token_preflight_skill` | `be72017e9fc7` |
| `evaluator` | `e415bdfd44f4` |
| `runner` | `1daa4680f061` |
| `fixtures`（judgment run：judgment fixtures + routing + seed） | `c7559b7168d9` |
| `fixtures`（default run：dispatch fixtures + routing + seed） | `a5413158ee62` |

#### 遷移策略（已執行 1–4，第 5 步待付費重跑）

1. **既有紀錄一律保留並標 `hash_schema: v1`。** 不稱為資料失效、不覆寫、不重算。
   v1 與 v2 的值不得直接比較——演算法與 allowlist 都變了，同一份內容本來就會得到不同值。
2. 腳本移到 `scripts/`，更新 `run-suite.sh`（4 個呼叫點，引數順序改為 `<mode> <路徑…>`）、
   `record.py`、兩份 README 與 `templates.md`。
3. 建立 v2 各 domain hash（上表）。
4. 機械驗證 domain 互斥性：[`scripts/hash-domain-selftest.sh`](../../../scripts/hash-domain-selftest.sh)
   逐一改動單一檔案並斷言恰好一個 domain 變動，**19 案例全部通過**（2026-09-02 於 host）。
   涵蓋 judge／score／record → 只動 evaluator；三支 runner 檔 → 只動 runner；
   SKILL.md／references → 只動該 skill；fixtures 與 seed → 只動 fixtures；
   selftest、STATUS.md、KNOWN-ISSUES.md、`evals/runs/**`、`.DS_Store`、
   以及**本次未載入的** fixture → 都不動任何 domain。
5. 以 v2 建立新 baseline。**尚未執行**：需要一輪 v2 下的真實 run。

引數順序從 `<目錄> [mode]` 改成 `<mode> <路徑…>` 是刻意的：舊呼叫
`bundle-hash.sh skills/harness suite` 在 v2 下會以 `unknown mode` 中止，
而不是靜默算出另一個 domain 的值。

#### 對發布 gate 的影響

判準 1 要求本批新增七筆全部 3/3，但 `positive-7`、`positive-8`、`positive-10`、`negative-3`
不在重測清單內，其 PASS 證據來自 `runs/20260901-215156-0fe73d/`（v1，evaluator 尚有 fence
fail-open 與條件替換未偵測兩個缺陷）。v2 下這四筆的處置是：

**重新評分既有 trace，不重跑 subject session。** 該 run 的 `raw/` 保留了全部 29 筆
`.jsonl`（含這四筆），`skill` 與 `fixtures` 兩個 domain 自 Batch 12 以來未變，變的只有
`evaluator`。因此對 subject 行為的證據仍然有效，需要重做的只有判定本身——
成本是 judge session，不是 subject session。這正是拆出 `evaluator` domain 的目的。

⚠️ 重新評分前必須先確認 `skill` 與 `fixtures` 兩個 domain 的 v2 值與該 run 當時一致。
v1→v2 換算不存在（allowlist 已變），所以這件事**必須逐 domain 人工核對內容有無變動**，
不能靠比對 hash 值完成。這是 v1 遺留的一次性成本，v2 之後可機械比對。

#### 部署變更

`dispatch/scripts/` 目錄已移除。經 `npx skills` 安裝的 standalone dispatch 本來就不會包含
repo root 的檔案，因此 [`templates.md`](../dispatch/references/templates.md) 改為：
repo 內用 root 腳本；其他專案用該專案自己的版本標記工具，並把**精確指令原文與
`hash_schema_version`** 一併寫進派工單的「版本標記」欄。沒有 schema 版本的 hash 不可跨批比較。

#### 本節未做的事

- 未跑任何真實 session、未重新評分任何既有 trace（那要花 judge 費用，屬第 5 步）。
- `agents/**` 未納入 `skill` domain。目前只有 `character-consistent-drawing/agents/openai.yaml`，
  其中的 `default_prompt` 在 OpenAI 平台上可能影響行為。是否納入待裁決。
- v1 的 run record JSON 內仍是舊欄位名（`dispatch_bundle`／`harness_test_suite`），
  未回寫 `hash_schema: v1` 欄位；標記寫在 STATUS.md 與 KNOWN-ISSUES.md 的文字層。

## Batch 14：provenance manifest、judge 逐條 schema 與 ledger 裁決（hash schema v3，2026-09-02）

本批全部零成本：**未起任何真實 session、未呼叫 claude CLI 做任何判定、未 commit／push、
未更新已安裝 skill、未重新打包 ZIP。**

### 14a v2 的三個 provenance 缺口與修法

| 缺口 | 為什麼是缺口 | 修法 |
|---|---|---|
| hash 在**跑完之後**才算 | `record.py` 現算的值回答「錄紀錄的當下 repo 長什麼樣」，不是「這輪 subject 跑在什麼版本上」。run 期間任何一次編輯都會安靜地把跑完後的版本綁到跑之前的 observation | 新增 [`evals/manifest.py`](manifest.py)：run 前後各量一次寫進 `runs/<RUN_ID>/manifest.json`；`record.py` 改為**只讀不算**並比對，任一 domain drift → `INVALID` |
| 沒有 `execution_context` domain | 同一份 skill／fixture／runner／evaluator，在不同注入規則檔、不同 model、不同 deny list 下行為不同，而 run record 對此完全沉默。這是「同 hash 卻不同結果」最大的未記錄來源 | `bundle-hash.sh` 新增 `execution-context` mode，取 rules／settings／descriptor 三者的**內容** hash。descriptor 由 `run-fixture.sh --print-context` 產生，不在 run-suite.sh 手抄 |
| raw trace 可被改動後重新評分 | 「evaluator 變更後重評既有 trace 以省下付費 subject session」的前提是 trace 逐 byte 相同，但沒有任何機制檢查 | subject 迴圈一結束即產生 `trace-manifest.json`；`judge.py` 重評前核對（不符 → 該筆 ERROR，`anomaly.kind = trace_hash_mismatch`，**不呼叫 CLI**）；`record.py` 亦核對，不符或缺失 → `INVALID` |

`hash_schema` 本身也改為 fail-closed：缺失、空值或不符 `v<正整數>`，以及 start／end 兩份
快照的值不一致，一律 `INVALID`。先前只是把 null 寫進紀錄然後照常記 PASS／FAIL。

`record.py` 的呼叫介面因此變成
`record.py <out-dir> <run-id> <manifest.json> <fixtures.json> [...]`。

### 14b judge 逐條項目的 key 集合（B）

13f 收緊了 top-level 未知 key，但逐條項目沒驗。`required[0]` 內放一個
`corrected_verdict: "FAIL"` 同樣承載撤回語意，且逐條 verdict 的權重與 top-level 一樣——
`overall` 的一致性檢查正是以逐條 verdict 為基準。撤回只要往下挪一層就能繞過整套檢查。

現在 `required[]`／`forbidden[]` 每一項的 key 集合必須嚴格等於
`element`／`verdict`／`evidence`，多一個即 `schema_violation`；判定 prompt 同步加上這條
（「以下五點會被機械檢查」）。`judge_selftest.py` 新增 7 項 nested regression：
required／forbidden 兩側、混入 top-level 名稱、多筆條件時只指名出問題的那一項，
以及合法三 key 不受收緊影響的對照組。

**維持 fail-closed 路線，不退回 allowlist。** `--json-schema` 的真實整合驗證仍未進行；
在那之前不放寬。

### 14c hash schema v3 的裁決與新 baseline（C）

**`agents/**` 納入 `skill` domain。** `agents/openai.yaml` 的 `default_prompt` 在 OpenAI
平台上直接決定 agent 的開場行為，屬 runtime 契約物件。allowlist 變動因此提版 v2 → v3。
`runner` 同時納入新增的 `manifest.py`。

⚠️ 本 repo 現有三份 `agents/openai.yaml`（`codex/claude-collaboration`、
`creative/character-consistent-drawing`、`creative/redraw-from-references`）都不在
dispatch／judgment／token-preflight 底下，因此**這次擴張沒有改變任何一個現行 skill hash
的值**。值相同只是因為新規則目前沒 match 到檔案，不代表 v2 與 v3 可以互相比較。

#### v3 baseline（2026-09-02 於 host 現算，本批修改後）

| domain | sha256（前 12） | 對照 v2 |
|---|---|---|
| `hash_schema` | `v3` | 由 v2 提版 |
| `dispatch_skill` | `2d6c0d99b1c4` | 值相同（allowlist 擴張未 match） |
| `judgment_skill` | `0c5a3deaec63` | 值相同 |
| `token_preflight_skill` | `be72017e9fc7` | 值相同 |
| `evaluator` | `3ea3d3bc75e1` | **已變**（v2 為 `e415bdfd44f4`；本批改 judge.py／record.py） |
| `runner` | `1e789a5ace9f` | **已變**（v2 為 `1daa4680f061`；本批改 run-suite.sh／run-fixture.sh，新增 manifest.py） |
| `fixtures`（judgment run） | `c7559b7168d9` | 值相同（fixture 未動） |
| `fixtures`（default run） | `a5413158ee62` | 值相同 |
| `execution_context` | `e7beb6eded81` | v2 無此 domain |

`execution_context` 是**參考值**，不是 baseline：它綁定當下的 `~/.claude/CLAUDE.md`
（sha256 `165581fbafee`）、消毒後 settings（`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1`）
與預設 descriptor（model `sonnet`、timeout 300）。改 `~/.claude/CLAUDE.md` 就會變，
而那份檔案不在版控內——真實值以 run 當下的 manifest 為準。

**舊 v2／v1 紀錄一律保留為歷史 observation，不覆寫、不宣告失效，也不與 v3 直接比較。**

#### hash-domain selftest（31 案例，全部通過）

[`scripts/hash-domain-selftest.sh`](../../../scripts/hash-domain-selftest.sh) 由 19 案例
擴充到 **31**，新增涵蓋：`agents/**` → 只改對應 skill hash（三個 skill 各一例）、
token-preflight 的 runtime 檔 → 只改它自己、rules／settings／descriptor → 只改
`execution_context`、raw trace（`.jsonl` 與 `.meta.json`）→ 只改 trace manifest、
`manifest.py` → 只改 runner、以及未載入的 token-preflight fixture → 都不動。

已知且刻意的耦合：descriptor 由 `run-fixture.sh --print-context` 產生，所以改 deny list
會同時改變 `runner` 與 `execution_context`。那是正確的——deny list 既是 runner 的程式內容，
也是執行環境的一部分。selftest 用固定 descriptor 檔，量的是「descriptor 內容變了誰會動」。

#### 模擬 run（新增 `scripts/run-provenance-selftest.sh`）

domain 互斥性證明的是「hash 分得對」，證明不了「那些 hash 真的被用來擋住不該成立的結論」。
[`scripts/run-provenance-selftest.sh`](../../../scripts/run-provenance-selftest.sh) 用合成的
stream-json 與 `.judge.json` 走完整條 `manifest.py → record.py → judge.py`，
**不呼叫 claude CLI、不花錢**，驗：

1. start = end 且 trace 相符 → `PASS`、`is_contract_evidence: true`、七個 domain 都入紀錄
2. run 中途改 fixture／skill／rules／evaluator／runner／在 seed 新增檔案 → 六項全部 `INVALID`，
   且 `invalid_reason` 指出是哪一個 domain drift
3. raw trace 被改動 → `judge.py` 拒絕重新評分（以 PATH 內的 stub `claude` 驗證
   **CLI 從未被呼叫**），`record.py` 判 `INVALID`
4. 逐條項目內的 `corrected_verdict`／`note` 被拒，合法三 key 不受影響

### 14d ledger 裁決（D）

[`KNOWN-ISSUES.md`](KNOWN-ISSUES.md) 的 20 筆已逐筆裁決，`PENDING` 歸零：
`FIX_FIXTURE` 8、`FIX_SKILL` 2、`ACCEPT_AS_KNOWN` 1、`NEEDS_EVIDENCE` 9。

裁決前先做了一件機械核對：兩輪對象 run 的每一筆 `.meta.json` 記錄的 prompt，
與現行 fixture 檔逐字相同（judgment 29、default 19、`20260901-215156-0fe73d` 29，差異 0）。
因此逐筆證據引用的判定條件就是當時實際送進去的那一份。這次核對揪出三處記載錯誤：

- **KI-17** 由 `skill_defect` 改判 `fixture_invalid`。`handoff-1` 的 required 要求交付
  verifier 六項輸入（含驗收條件），forbidden 又禁止 dispatch 自行產生驗收判準，
  而 prompt 既沒給規則檔路徑也沒給 judgment 的逐條判定——三者同時成立時無解。
  模型停下來反問正是這份 fixture 下的正確行為。
- **KI-19／KI-20** dimension 由 `routing` 更正為 `contract`。run record 該兩列都是
  `routing=PASS`、`contract=FAIL`。
- **KI-07／KI-08** 的證據原文（「缺『要不要拆出去跑』觸發詞」「required 要求複誦內部規則表名」）
  來自 Batch 6.5 時期的舊 fixture，與現行 `ambiguous-1` 無關，已依現行條件重寫。

**KI-03／05／14／15 的依賴由 KI-19 改為新設的 `DE-01`。** 原依賴是錯的：KI-19 是
`judgment-absent-1` 的 fixture 缺輸入問題，與 judgment description 的寬窄沒有因果關係。
DE-01 是獨立的 dilution A/B 證據任務，協定（兩 arm 只差 description、每 arm 每筆 3 次、
arm A ≥ 2/3 且 arm B ≤ 1/3 才成立）與成本（USD 2.0–3.5，**不含在 13d 的 2.3 內**）
都寫在 ledger 內。

#### 執行順序的硬約束（新增）

`fixtures` 是**整檔**的 identity domain。改任何一筆 fixture 的 `required_elements`
會改變同一個 `fixtures` hash，於是 `positive-7`／`positive-8`／`positive-10`／`negative-3`
的既有 trace 立刻失去「fixtures 未變」這個重新評分前提，四筆就得改用付費 subject 重跑。

**順序：F（重新評分四筆）→ `FIX_FIXTURE` 各筆 → 重算 `fixtures` hash → G（付費重跑）。**

### 14e 零成本封閉驗證（E，全部實跑）

| 項目 | 結果 |
|---|---|
| `judge_selftest.py` | 全部通過（含 7 項 nested key 新案例） |
| `record_selftest.py` | 全部通過（含 provenance 鏈 30+ 項新案例） |
| `score_selftest.py` | 全部通過 |
| `transport_selftest.py` | 全部通過 |
| `py_compile`（judge／score／record／manifest／transport 與四支 selftest） | 全部通過 |
| `sh -n`（bundle-hash／hash-domain-selftest／run-provenance-selftest／run-suite／run-fixture） | 全部通過 |
| `sh scripts/hash-domain-selftest.sh` | 31/31 通過 |
| `sh scripts/run-provenance-selftest.sh` | 全部通過 |
| `run-suite.sh --dry-run`（default） | **18 筆**，符合預期 |
| `run-suite.sh --dry-run`（`HARNESS_FX` 指向 judgment fixtures） | **28 筆**，符合預期 |

### 14f 本批未做的事

- 未修改任何 fixture 或 `SKILL.md`。`FIX_FIXTURE` 8 筆與 `FIX_SKILL` 2 筆都只裁決、未執行，
  理由見上面的執行順序硬約束。
- 未重新評分任何既有 trace（步驟 F），未跑任何付費 session（步驟 G），未 commit／發布（步驟 H）。
- 未在 host 評估 `--json-schema`。
- 未把 selftest 接進 `run-suite.sh` 的 preflight。目前仍需手動執行；接進去屬 runner 行為變更。

### 14g 本批新發現的殘留風險

- **隔離沒有涵蓋 `Read` 的絕對路徑。** `harness-routing__handoff-1` 的 trace 顯示受測 session
  以 `Read` 讀到了 host 的 `/Users/<user>/.claude/CLAUDE.md`，也用 `Bash` 列出了
  `~/.claude/projects/` 底下的檔案（部分 Bash 呼叫被擋，Read 沒有）。
  `--add-dir` 與 cwd 限制的是預設工作範圍，不是硬性沙箱。
  影響：受測 session 可能讀到注入副本以外的 host 規則與歷史紀錄，`execution_context`
  記的是「我們注入了什麼」，不是「session 實際看到了什麼」。此項未修，僅記錄。
- **host 的 `python3` 是 3.7.9。** 本批一度用了 walrus（3.8+），`py_compile` 當場失敗。
  evals 下的所有 Python 必須維持 3.7 相容，否則真實執行時整支起不來。


## Batch 15：五筆 Blocking finding 的修正 cycle（hash schema v4，2026-09-02）

本批全部零成本：**未起任何真實 session、未呼叫 claude CLI 做任何判定、未修改 fixture 或
SKILL.md、未 commit／push、未更新已安裝 skill、未重新打包 ZIP。**

輸入版本已於開始前重新量測並比對，五項全部相符：`hash_schema v3`、
`evaluator 3ea3d3bc75e1`、`runner 1e789a5ace9f`、judgment fixtures `c7559b7168d9`、
default fixtures `a5413158ee62`。無版本差異。

### 15a BR-F21：缺 trace manifest 時仍呼叫 judge

Batch 14 建了 trace manifest，卻讓 `judge.py` 在 manifest 缺席時只印一行警告然後照常判定，
把「無法證明 trace 未被更動」留給 `record.py` 事後判 INVALID。**那時錢已經花完**，
而那一輪的判定從一開始就不可採信。缺席與「對不上」在成本上是同一件事。

修正：`load_trace_manifest()` 回傳 problem，缺失／壞損／`files` 非物件／`files` 為空
一律在**進入 fixture loop 之前** `exit 2`；`run-suite.sh` 在 `TRACE_RC != 0` 時直接跳過
judge（先前只有 `SCORE_RC == 2` 一個跳過條件）。

證據：`run-provenance-selftest.sh` 以 PATH 前置一支會累計呼叫次數的 `claude` stub，
三種情況的 CLI 呼叫次數都是 **0**，exit code 都是 2：

| 情況 | judge exit | CLI 呼叫次數 |
|---|---|---|
| trace manifest 缺失 | 2 | 0 |
| trace manifest 壞損（非 JSON） | 2 | 0 |
| trace manifest 為空（`files: {}`） | 2 | 0 |
| manifest 在但逐檔 hash 不符 | 1（該筆 ERROR） | 0 |

### 15b BR-F22：manifest 沒有要求完整 domain 集合

只比對 start 與 end 是否一致的話，一份**只含 `fixtures` 一個 domain** 的 manifest 會完美
通過：start 等於 end、沒有 drift、整輪記成有效證據，而 skill、runner、evaluator、
兩個 context 全都沒有版本綁定。少到看不出來的紀錄比沒有紀錄更危險，因為它看起來像有。

修正：`record.py` 定義 `REQUIRED_DOMAINS`，start／end 必須**恰好**含這些 domain——
缺一個代表那部分沒有綁定，多一個代表產生 manifest 的工具與 `record.py` 對「要量什麼」
的認知已經不同，兩種情況下比對結論都不可信。同時驗 `manifest_version`
（`SUPPORTED_MANIFEST_VERSIONS = (1,)`），缺失或不支援一律 INVALID。

⚠️ **`REQUIRED_DOMAINS` 是八個而不是 finding 寫的七個**：BR-F23 要求把
`evaluation_context` 一併納入 `REQUIRED_DOMAINS`，因此「完整七個 domain → PASS」
在本批的實作下是「完整八個 → PASS」，而「只有七個（缺 `evaluation_context`）→ INVALID」
正是 F22 自己那條「缺少任何 domain 都判 INVALID」套用到新 domain 的結果。

### 15c BR-F23：judge model 未納入 identity

judge 是另一個 model 的另一個 session。換 `HARNESS_JUDGE_MODEL`、換 judge 的 CLI flags、
host 的 `claude` 一升版，contract 判定就可能翻轉，而 v3 的 run record 對此一個字都沒有：
兩輪 hash 完全相同卻得到相反的 contract 結論時，讀紀錄的人找不到任何解釋。

新增 **`evaluation_context`** domain，內容取自 `judge.py --print-context`：
`judge_model`、`judge_timeout_s`、**實際的 `claude --version`**、`output_format`、
`disallowed_tools`、`session_persistence`、`structured_output`。
`--json-schema` 尚未整合驗證，descriptor 明記 `structured_output=absent`——
明記而不是省略，否則日後啟用時看起來會像「新增一行」而不是「切換設定」。

**刻意不併進 `execution_context`**：受測環境變更作廢的是 subject 行為證據（要重跑付費
session）；判定環境變更作廢的只有判定本身（保留的 raw trace 可重新評分）。混在一起會讓
「換 judge model」看起來像「受測環境變了」，把便宜的重評誤判成昂貴的重跑。

已納入 run-start／run-end manifest、`REQUIRED_DOMAINS`、run record、README、本檔與
hash-domain selftest。新增 domain 屬 allowlist 變動，依既有規則提版 **v3 → v4**，
不沿用 v3 baseline。

### 15d BR-F24：trace manifest 可被覆寫

逐檔比對對「改 trace → 重跑一次 `manifest.py trace`」完全無效：新 manifest 裡每一筆 hash
都會對得上。

修正三件事：

1. `manifest.py trace` **預設不覆寫**，目標已存在即 exit 3。要重建就必須先明確刪除。
2. run record 保存 trace manifest 的 deterministic digest
   （`files` 對照表的 canonical JSON 之 SHA-256，`provenance.trace_manifest_digest`）。
   `record.py` **不採信** manifest 內自述的 `digest` 欄位，一律自己重算；自述值與重算值
   不符會另記一條問題。
3. 重新評分走 `record.py --source <原始 run record>`：digest 不符即拒絕；輸出路徑與來源
   相同即拒絕且不寫任何檔案；產出的是 derived record，`derived_from` 記下來源 run ID、
   原始 trace digest，以及**現在**的 `evaluator` 與 `evaluation_context`。
   `judge.py` 另讀 `HARNESS_SOURCE_RECORD`，在 loop 前做同一個 digest 比對，
   讓這一關擋在花錢之前。

### 15e BR-F25：KI-18 disposition 自相矛盾

`ACCEPT_AS_KNOWN` 的定義是「容許此缺陷存在」——那是**看過結果之後**才能下的判斷。
KI-18 的 disposition 記成放行，required_action 卻是「2/3 重跑作為 known-flaky 確認」，
而那次重跑根本還沒跑。等於用一個還不存在的觀測換取發布資格。

改為 `NEEDS_EVIDENCE`，既定判準完全保留但移到裁決之後：達到 2/3 → `ACCEPT_AS_KNOWN`
（仍不得記為 fixture PASS）；未達到 → `FIX_SKILL`。
ledger 統計因此變成 `FIX_FIXTURE` 8／`FIX_SKILL` 2／`ACCEPT_AS_KNOWN` **0**／
`NEEDS_EVIDENCE` **10**／`PENDING` 0。**目前沒有任何一筆是放行狀態。**

### 15f v4 baseline（2026-09-02 於 host 現算，本批修改後）

| domain | sha256（前 12） | 對照 v3 |
|---|---|---|
| `hash_schema` | `v4` | 由 v3 提版（新增 domain = allowlist 變動）|
| `dispatch_skill` | `2d6c0d99b1c4` | 值相同 |
| `judgment_skill` | `0c5a3deaec63` | 值相同 |
| `token_preflight_skill` | `be72017e9fc7` | 值相同 |
| `evaluator` | `3c1540191ef0` | **已變**（v3 為 `3ea3d3bc75e1`；本批改 judge.py／record.py）|
| `runner` | `c987e247434e` | **已變**（v3 為 `1e789a5ace9f`；本批改 run-suite.sh／manifest.py）|
| `fixtures`（judgment run） | `c7559b7168d9` | 值相同（未動 fixture）|
| `fixtures`（default run） | `a5413158ee62` | 值相同 |
| `execution_context` | `e7beb6eded81` | 值相同（run-fixture.sh 未動，rules／settings 未動）|
| `evaluation_context` | `64996161082a` | v3 無此 domain |

`execution_context` 與 `evaluation_context` 都是**參考值**，不是 baseline：前者綁定當下的
`~/.claude/CLAUDE.md` 與消毒後 settings，後者綁定 `HARNESS_JUDGE_MODEL=sonnet` 與
host 的 `claude` 2.1.247。真實值一律以 run 當下的 manifest 為準。

**v3／v2／v1 紀錄一律保留為歷史 observation，不覆寫、不宣告失效，也不與 v4 直接比較。**

### 15g 零成本封閉驗證（全部實跑）

| 項目 | 結果 |
|---|---|
| `judge_selftest.py` | 全部通過 |
| `record_selftest.py` | 全部通過（新增 F22／F24 共 30 項） |
| `score_selftest.py` | 全部通過 |
| `transport_selftest.py` | 全部通過 |
| `py_compile`（evals 下全部 .py） | 全部通過（維持 3.7 相容） |
| `sh -n`（bundle-hash／hash-domain-selftest／run-provenance-selftest／run-suite／run-fixture） | 5 支全部通過 |
| `sh scripts/hash-domain-selftest.sh` | **35/35** 通過（v3 為 31） |
| `sh scripts/run-provenance-selftest.sh` | 全部通過（含 CLI 呼叫次數 0 的三種情況） |
| `run-suite.sh --dry-run`（default） | **18 筆** |
| `run-suite.sh --dry-run`（judgment fixtures） | **28 筆** |

### 15h 本批未做的事

- 未執行步驟 F（重新評分既有 trace）、G（付費重跑）、H（commit／發布）。
- 未修改任何 fixture 或 `SKILL.md`；`FIX_FIXTURE` 8 筆與 `FIX_SKILL` 2 筆仍只裁決未執行。
- 未處理「隔離不涵蓋絕對路徑 `Read`」與 `--json-schema` 整合驗證，兩者維持為既有風險。
- `run-suite.sh` 從 preflight 到 record 的完整控制流仍未實跑（需付費 session）；
  本批只驗到它呼叫的每一支工具與新的跳過條件的語法正確性。


## Batch 16：複查 FAIL 的三筆 provenance blocker（hash schema v4，2026-09-02）

Batch 15 的五筆 finding 中 F21／F22／F25 可關閉，F23／F24 未完整關閉。複查另指出：
**既有 selftest 全綠，但那證明的是測試覆蓋不足，不是問題不存在。** 三筆全部先機械複現
再修，複現結果與複查一致。

本批全部零成本：未起任何真實 session、未修改 fixture 或 SKILL.md、未 commit／push／發布。

### 16a BR-F26：end snapshot 未重新量測 context

`run-suite.sh` 只在 start 產生 `$DESC`／`$JDESC`，end 重用同兩份檔案。
**複現**（judge CLI 版本 2.1.247 → 9.9.9）：

```
stored start            = 64996161082a
重用 descriptor          = 64996161082a   ← 無 drift（漏檢）
重新產生 descriptor       = f0dde874755a   ← 偵測到 drift
```

`execution_context` 與 `evaluation_context` 是**唯二**無法從 repo 內容重算的 domain——
它們的值只存在於當下產生的 descriptor 裡。重用 descriptor 等於事先宣告這兩個 domain
不可能 drift，而 judge CLI 在 run 期間升版、`HARNESS_JUDGE_MODEL` 被改掉，正好都落在這裡。

修正：end 快照前重新產生 `execution-context.end.txt` 與 `evaluation-context.end.txt`
再量測；descriptor 產生失敗則不寫 end 快照，交由 `record.py` 判 INVALID。

驗證用了三層，因為單一層都不夠：負向對照（重用 → 同 hash）、正向（重新產生 → 不同 hash）、
端到端（start／end 用各自的 descriptor → `record.py` 抓到 `evaluation_context` drift），
再加三條結構檢查確認 `run-suite.sh` 真的產生兩次且 end 用的是新檔。
**run-suite.sh 自己的控制流仍無法在零成本下實跑**，結構檢查是這一段的替代品，不是等價物。

### 16b BR-F27：start／end phase 可被覆寫

`manifest.py` 無條件執行 `doc[phase] = snap`。**複現**：依序寫入 start=A、start=B、end=B，

```
rc = 0 0 0
start.evaluation_context: 64996161082a → 被改寫成 f0dde874755a
check_manifest 問題數 = 0   ← drift 被完全隱藏
```

這比沒有比對更糟：紀錄看起來通過了比對。修正是同名 phase 已存在即 exit 3；
兩支 selftest 改為每個案例用一份乾淨的 manifest 檔。

### 16c BR-F28：v3 trace 無法產生有效的 v4 derived record

**複現**：以 v3 來源紀錄 + v3 manifest 走 `record.py --source`，

```
run_status   = INVALID
invalid_reason 含「start 缺少必要 domain: evaluation_context」
rescored_with.evaluator = aaaa…（來源 run 的值，不是「現在的」）
```

兩個問題同源：整份 identity 都從傳入的 manifest 取。但重評的 identity 本來就該分成兩半——
那份 trace 是在**來源版本**下產生的，此刻重量 skill／fixtures／runner 得到的是與該 trace
無關的值。

修正後的 derived provenance：

| 半邊 | domain | 取自 |
|---|---|---|
| subject identity | skill × 3、`runner`、`fixtures`、`execution_context` | 來源 run 的紀錄 |
| contract identity | `evaluator`、`evaluation_context` | 本次現量（contract manifest） |

`manifest.py` 新增 `contract-snapshot`（只量兩個 contract domain）；`record.py` 依 manifest
的 `kind`（`full`／`contract`）決定必要 domain 集合，並在模式與 kind 不符時擋下
（原生 run 傳 contract manifest、重評傳 full manifest，兩個方向都擋）。
run record 新增 `hash_provenance`，逐 domain 標明 `source_run` 或 `measured_now`。

**跨 schema 另加一道 `--migration-audit`。** 跨 schema 時 hash 值**必然**不同（allowlist 與
演算法都變了），「值不同」什麼都證明不了。因此來源與現行 `hash_schema` 不同時必須另附一份
獨立的內容等價稽核，逐 domain 說明它們是不是同一份內容；缺此一律 INVALID。
`record.py` 只驗這份稽核針對正確的兩個 schema、涵蓋全部六個 subject domain、
並寫明比對方法——**不驗它的結論對不對**，那是人的責任，不是機械能判定的。

步驟 F 現在可以產出有效證據：selftest 已示範 v3 來源 trace + 完整 audit → `PASS` 的
derived record，subject 那半標 `source_run`、contract 那半標 `measured_now`。
⚠️ 目標 run `20260901-215156-0fe73d` 是 **v1** 紀錄（欄位名為 `dispatch_bundle`／
`harness_test_suite`，且沒有 trace manifest）。走這條路徑之前，F 必須先為它補一份一次性
migration trace manifest 與一份具備六個 subject domain 的來源紀錄——那是 F 的工作，不在本批。

### 16d Non-blocking：run record 的 hash_method 文字

`hash_method` 仍寫「五個互斥 domain」且漏列 `evaluation-context`，`.md` 的重算 mode 清單
同樣漏掉。已同步更新為六個，並新增 selftest 斷言（JSON 與 `.md` 兩邊都驗）。
derived record 的 `hash_method` 另外說明 identity 由兩半組成、逐 domain 見 `hash_provenance`。

### 16e v4 baseline（本批修改後重新量測）

| domain | Batch 15 | Batch 16 |
|---|---|---|
| `hash_schema` | v4 | v4（未提版：無 allowlist 變動，只有行為修正）|
| `dispatch_skill` | 2d6c0d99b1c4 | 2d6c0d99b1c4 |
| `judgment_skill` | 0c5a3deaec63 | 0c5a3deaec63 |
| `token_preflight_skill` | be72017e9fc7 | be72017e9fc7 |
| `evaluator` | 3c1540191ef0 | **a77e77f43a25** |
| `runner` | c987e247434e | **3e2859f31425** |
| `fixtures`（judgment） | c7559b7168d9 | c7559b7168d9 |
| `fixtures`（default） | a5413158ee62 | a5413158ee62 |
| `execution_context` | e7beb6eded81 | e7beb6eded81 |
| `evaluation_context` | 64996161082a | 64996161082a |

`contract-snapshot` 是新增的 CLI 子指令，不是新 domain；`manifest.py` 已在 v3 起就在
runner allowlist 內，因此 allowlist 未變，**不提版**。

### 16f 零成本封閉驗證

| 項目 | 結果 |
|---|---|
| 四支 Python selftest | 全部通過（record 新增 kind／derived／audit 共 25 項） |
| `py_compile`（evals 全部 .py） | 通過（維持 3.7 相容） |
| `sh -n` × 5 | 通過 |
| `hash-domain-selftest.sh` | 35/35 |
| `run-provenance-selftest.sh` | 全部通過（新增第 6～8 節共 13 項） |
| default／judgment dry-run | 18／28 筆 |

### 16g 仍未關閉的事

- `run-suite.sh` 完整控制流（preflight → record）仍為 `NOT_RUN`，需付費 session。
  本批新增的三條結構檢查只能證明那幾行還在、且 end 用的是新檔。
- 步驟 F 的來源紀錄補建（v1 → 可用的 source record + 一次性 trace manifest）未做。
- 絕對路徑 `Read` 隔離、`--json-schema` 整合驗證：依限制維持為既有風險，本批未動。
- 本批不是 fresh-context 獨立驗收，仍有推理污染風險。


## Batch 17：四筆 derived-record blocker 與一處回報錯誤（hash schema v5，2026-09-02）

複查判 FAIL：BR-F26／F27 與 `hash_method` 可關閉，BR-F28 仍有三個 Blocking，另有一處
回報錯誤。四筆全部先機械複現再修。本批零成本：未起真實 session、未動 fixture 或
SKILL.md、未 commit／push／發布。

### 17a 先更正一處回報錯誤

Batch 16 的回報寫「開始前重新量測，五項全部相符：v4 / evaluator `3ea3d3bc75e1` /
runner `1e789a5ace9f`」。**那兩個值是 Batch 15 的輸入，不是 Batch 16 實際量到的。**
Batch 16 開始時實測為 `3c1540191ef0` / `c987e247434e`（本檔 15f 表格記的就是這兩個）。
量測本身沒錯，錯的是回報時抄了上一輪 prompt 裡的數字。

這類錯誤的後果不是小事：版本綁定的整套機制就是為了讓第三方能重算，而回報裡的數字
是第三方唯一的入口。**往後版本欄位一律從當次量測輸出複製，不從 prompt 或前一份回報抄。**

### 17b BR-F29：migration audit 可產生假 PASS

`load_migration_audit()` 只檢查 domain 名稱到齊與頂層 `method`，不看每個 domain 的結論；
來源 subject hash 也只檢查 key 存不存在。**複現**：六個 audit domain 與六個來源 hash
全填 `null`，

```
rc=0  status=PASS  is_contract_evidence=True
hashes.dispatch_skill = None
```

一份什麼都沒說的「稽核」換到一個看起來完整的證據紀錄。

修正兩處：

- **來源 subject hash 必須是合法 64 位 hex**，逐個驗；不合法即列名 INVALID。
- **audit 改採固定 schema**，每個 domain 必須是
  `{"equivalent": true, "evidence": <非空>, "method": <非空>}`；
  `false`、`null`、缺欄位、多欄位、未知 domain、缺 domain 一律擋下。

`record.py` 驗的仍然只是「這份文件確實逐條做出了可歸責的主張」，**不驗主張為真**——
那是人的責任。差別在於：先前連「有沒有做出主張」都沒驗。

### 17c BR-F30：重評使用的 fixtures 沒有綁定

judge 是用**現在**這份 fixture 檔判定的，derived record 卻沿用來源 run 的 `fixtures`
hash。**複現**：改掉 `required_elements` 後重評舊 trace，

```
status=PASS  hashes.fixtures = aaaaaaaaaaaa（來源值）
hash_provenance.fixtures = source_run
contract 端的 fixtures 綁定 = 無
```

同一份 fixture 檔承載兩件不同的東西，因此拆成兩個 domain 與兩道檢查：

| 改了什麼 | 屬於 | 處置 |
|---|---|---|
| `required_elements`／`forbidden_elements` | contract 側 | **允許**——那正是重新評分的用途；由新增的 `contract_fixtures` domain 記錄實際判定依據 |
| `prompt` | subject 側 | **禁止**——那份 trace 就不是這個 fixture 的產物；judge 在進 loop 前逐筆比對 fixture 的 prompt 與 `.meta.json` 記下的實際 prompt，不符即 exit 2 且不呼叫 CLI |

`contract_fixtures` 與 `fixtures` 用同一個 mode 與同一套演算法，差別在量的時機與歸屬。
新增 domain 依既有規則提版 **v4 → v5**。

### 17d BR-F31：rescore 文件仍重用 descriptor

README 的 start／end `contract-snapshot` 用同一份 `/tmp/judge-desc.txt`——與 BR-F26
同型的缺陷，只是從腳本搬到了人工流程。

修正：新增 [`scripts/run-rescore.sh`](../../../scripts/run-rescore.sh) 作為重新評分的
唯一建議入口，前後各重新產生一次 judge descriptor；README 改為指向它。
**該腳本刻意不在任何 identity domain 內**：它只負責依正確順序呼叫，trace digest 比對、
fixture prompt 對應、phase 不可覆寫、subject hash 格式、audit 逐條檢查全部由
`judge.py` 與 `record.py` 自己 fail-closed 執行。改壞它會讓流程跑不完，
但不會讓一份不該成立的 derived record 產生出來。

### 17e BR-F32：v1 trace 無法事後補成原生證據

補一份 trace manifest 只能證明**目前**那些檔案的內容，不能證明它們從 2026-09-01 至今
未被修改——中間沒有任何 immutable digest、commit 或可信封存可以錨定。

新增 `evidence_class`，與 `run_status` 是兩個獨立的軸：

| 欄位 | 回答的問題 |
|---|---|
| `run_status` | 這一輪的觀測可不可用（`PASS`／`FAIL`／`INVALID`） |
| `evidence_class` | 這些觀測能不能當契約證據（`contract_evidence`／`legacy_diagnostic`） |

只有 runner 宣告 `HARNESS_TRACE_MANIFEST_ORIGIN=contemporaneous` 的紀錄算契約證據；
derived record 的等級取自**來源**紀錄的宣告——本輪重新產生的 manifest 再怎麼「當下」，
也只是重算了同一批舊檔案。

**發布 gate 因此改判**：判準 1 的 `positive-7`／`positive-8`／`positive-10`／`negative-3`
不能靠重新評分 v1 trace 補齊，必須在現行 schema 下重新執行 subject run。
舊 v1 trace 僅保留為診斷參考。詳見 [`KNOWN-ISSUES.md`](KNOWN-ISSUES.md)「步驟 F 的地位」。

### 17f v5 baseline（本批修改後現算）

| domain | Batch 16 (v4) | Batch 17 (v5) |
|---|---|---|
| `hash_schema` | v4 | **v5**（新增 `contract_fixtures`）|
| `dispatch_skill` | 2d6c0d99b1c4 | 2d6c0d99b1c4 |
| `judgment_skill` | 0c5a3deaec63 | 0c5a3deaec63 |
| `token_preflight_skill` | be72017e9fc7 | be72017e9fc7 |
| `evaluator` | a77e77f43a25 | **5658dc4f8459** |
| `runner` | 3e2859f31425 | **93438173ea6c** |
| `fixtures`（judgment） | c7559b7168d9 | c7559b7168d9 |
| `fixtures`（default） | a5413158ee62 | a5413158ee62 |
| `execution_context` | e7beb6eded81 | e7beb6eded81 |
| `evaluation_context` | 64996161082a | 64996161082a |
| `contract_fixtures` | —（不存在） | 依 judge 實際載入的 fixture 檔而定，run 當下量測 |

三個 skill、兩個 fixtures 與兩個 context 的值未變，但**它們現在綁定的是 v5**，
不得與 v4 的同值紀錄互相引用。

### 17g 零成本封閉驗證

| 項目 | 結果 |
|---|---|
| 四支 Python selftest | 全部通過（record 新增 F29／F30／F32 共 18 項） |
| `py_compile`（evals 全部 .py） | 通過（維持 3.7 相容） |
| `sh -n` × 6（含 run-rescore.sh） | 通過 |
| `hash-domain-selftest.sh` | 35/35（新增 `contract_fixtures` 與兩側共用輸入的案例） |
| `run-provenance-selftest.sh` | 全部通過（新增第 9～11 節共 15 項） |
| default／judgment dry-run | 18／28 筆 |

### 17h 仍未關閉的事

- `run-suite.sh` 完整控制流（preflight → record）仍為 `NOT_RUN`，需付費 session。
- 發布 gate 的四筆需要**現行 schema 下的原生 subject run**，不能用重新評分補。
- 絕對路徑 `Read` 隔離、`--json-schema` 整合驗證：依限制維持為既有風險。
- 本批同樣不是 fresh-context 獨立驗收：修的是自己上一輪寫的程式，推理污染風險未消除。


## Batch 18：三筆 rescore blocker（hash schema v6、manifest_version 2，2026-09-02）

複查判 FAIL：BR-F29／F30 的資料驗證與 BR-F31 的 descriptor 重量可關閉；BR-F32 尚未真正
fail-closed，另新增兩筆 rescore blocker。三筆全部先機械複現再修。
本批零成本：未起真實 session、未動 fixture 或 SKILL.md、未 commit／push／發布。

輸入版本 `v5` / `evaluator 5658dc4f8459` / `runner 93438173ea6c`（複製自當次量測輸出），
與複查一致。

### 18a BR-F33：rescore 會覆寫來源 judge artifacts

`run-rescore.sh` 把來源 `raw/` 直接交給 judge，而 judge 把 `<fixture>.judge.json` 寫回
它被指到的那個目錄。**複現**：

```
來源 .judge.json before = bce37b3d7ff6
來源 .judge.json after  = e1c8cdc41e39   ← 已被覆寫
原始 note 欄位還在嗎: 0
trace manifest 有涵蓋 .judge.json 嗎: False
```

來源 run record 沒被覆寫，但逐筆判定證據消失了，而且因為 trace manifest 只涵蓋
`.jsonl`／`.meta.json`，這種破壞不會被任何檢查抓到。

修正：subject 產物複製到 `<來源>/derived/<新 id>/raw/`，judge 只寫那裡；
腳本結束前重算來源目錄的內容指紋，與開始時比對，不同即以錯誤結束。

### 18b BR-F34：provenance 無效時仍先花 judge 成本

付費 judge 排在 `record.py` 的驗證之前。缺 audit、audit 無效或 source hash 壞損時，
整輪跑完才 INVALID——正是 BR-F21 修掉的那個問題換個位置重現。

修正：新增兩個零成本入口，`run-rescore.sh` 在 judge 之前依序跑完：

| 入口 | 驗什麼 |
|---|---|
| `record.py --validate-only` | 來源紀錄、trace digest、subject hash 格式、migration audit、contract manifest start |
| `judge.py --preflight` | trace manifest 存在與完整、來源 digest、fixture prompt 對應 |

任一不通過即中止並刪除 derived 目錄。證據：來源 subject hash 壞損時，
run-rescore 以非 0 結束、未產生 derived record，且 judge 判定次數為 **0**
（`claude` stub 只被 `--print-context` 呼叫過一次查版本）。

### 18c BR-F35：legacy trace 可用一個環境變數升格

`record.py` 直接採信 `HARNESS_TRACE_MANIFEST_ORIGIN`。**複現**：對事後建立的任意 trace
設為 `contemporaneous`，得到 `rc=0 / PASS / evidence_class=contract_evidence /
is_contract_evidence=True`。BR-F32 的核心保證因此形同虛設——那不是證明，是自述。

修正：改成一條**必須四方一致的 run nonce 鏈**：

1. `snapshot start` 在跑任何 session 之前產生一次性 `run_nonce`（128-bit 隨機）。
2. `run-suite.sh` 傳給每個 subject session，`run-fixture.sh` 寫進 `.meta.json`。
3. `manifest.py trace` 逐檔核對每份 meta，並把 nonce 寫進 trace manifest。
4. `record.py` 要求三者一致才判 `contemporaneous`；任一環缺失或不符即 `legacy_diagnostic`。

環境變數完全不再參與判定；selftest 直接把舊反例（設環境變數 + 沒有 nonce）保留為案例，
斷言它現在得到 `legacy_diagnostic`。

**這擋不住能同時改寫全部四樣東西的人。** 沒有外部錨定（commit、可信封存）的方案都擋不住；
它擋掉的是「補一份 manifest 或設一個環境變數就升格」，門檻從一個字串變成一整條鏈。
manifest 結構因此改變，`manifest_version` 由 1 提版為 **2**。

### 18d rescore 編排腳本納入 identity

v5 主張 `run-rescore.sh`「只負責依正確順序呼叫，不影響證據」。BR-F33／F34 推翻了這個前提：
它決定**判定寫到哪裡**與**驗證的先後順序**，兩者都直接決定 derived record 的可信度。
新增 `rescore_runner` domain（`bundle-hash.sh rescore-runner`），納入 contract manifest；
allowlist 變動因此提版 **v5 → v6**。

contract manifest 的 domain 由三個變成四個：`evaluator`、`evaluation_context`、
`contract_fixtures`、`rescore_runner`；derived record 的 `hashes` 共十個
（六個 subject + 四個 contract）。

### 18e v6 baseline（本批修改後現算）

| domain | Batch 17 (v5) | Batch 18 (v6) |
|---|---|---|
| `hash_schema` | v5 | **v6** |
| `manifest_version` | 1 | **2**（新增 `run_nonce`）|
| `dispatch_skill` | 2d6c0d99b1c4 | 2d6c0d99b1c4 |
| `judgment_skill` | 0c5a3deaec63 | 0c5a3deaec63 |
| `token_preflight_skill` | be72017e9fc7 | be72017e9fc7 |
| `evaluator` | 5658dc4f8459 | 見下方量測 |
| `runner` | 93438173ea6c | 見下方量測 |
| `fixtures`（judgment／default） | c7559b7168d9／a5413158ee62 | 同值 |
| `execution_context` | e7beb6eded81 | 同值 |
| `evaluation_context` | 64996161082a | 同值 |
| `rescore_runner` | —（不存在） | 新增 |

（實際值見本批回報的量測輸出；本檔不重抄，避免再犯 17a 的錯。）

### 18f 零成本封閉驗證

| 項目 | 結果 |
|---|---|
| 四支 Python selftest | 全部通過 |
| `py_compile`（evals 全部 .py） | 通過（維持 3.7 相容） |
| `sh -n` × 6 | 通過 |
| `hash-domain-selftest.sh` | **36/36**（新增 `rescore_runner` 案例） |
| `run-provenance-selftest.sh` | 全部通過（新增第 12 節 F33／F34 共 8 項） |
| default／judgment dry-run | 18／28 筆 |

### 18g 仍未關閉的事

- `run-suite.sh` 完整控制流（preflight → record）仍為 `NOT_RUN`，需付費 session。
  **nonce 鏈的 runner 端（`run-fixture.sh` 寫 meta、`run-suite.sh` 傳遞）也在這個範圍內**，
  只驗到語法與 record 端的核對邏輯。
- 發布 gate 的四筆需要現行 schema 下的原生 subject run。
- 絕對路徑 `Read` 隔離、`--json-schema`：依限制維持為既有風險。
- 本批同樣不是 fresh-context 獨立驗收。


## Batch 19：run-rescore.sh 的兩筆 Blocking（hash schema v6，2026-09-02）

驗收判 FAIL：BR-F33～F35 的主要修正與零成本測試成立，但新增的 `run-rescore.sh`
自己帶進兩個問題。兩筆都先機械複現再修。本批零成本、未動 fixture 或 SKILL.md、
未 commit／push／發布。

輸入版本 `v6` / `evaluator feddd58c1acd` / `runner 005ed2f71ac4` /
`rescore_runner 5aa9da07ebf7`（複製自當次量測輸出），與驗收一致。

### 19a BR-F36：run id 未限制路徑範圍

`NEW_ID` 直接拼進 `DERIVED`，而失敗路徑上有 `rm -rf "$DERIVED"`。**複現**：

```
derived 目錄 : <run>/derived/../../victim     →  解析為 runs/victim
preflight 不通過 → 對該路徑執行 rm -rf
```

derived 產物與清理操作都落在 `derived/` 之外。`[ ! -e "$DERIVED" ]` 那道守衛只擋得住
「目標已存在」，擋不住「在容器外新建再刪掉」。

修正是三層，缺一層都不夠：

1. **字元 allowlist**：run id 限 `A-Za-z0-9._-`，禁空字串、`.` 開頭與 `/`。
   擋掉字面上的相對路徑與命令字元。
2. **canonical path 複驗**：`derived/` 本身不得是 symlink，且解析後必須落在來源 run
   目錄內；目標必須是它的**直接**子目錄。第一次修這筆時只驗了第二層，
   結果 `derived/` 指向外部的 symlink 仍然通過——selftest 當場抓到，因此補上第一層。
3. **先驗再建**：containment 檢查排在 `mkdir` 之前，否則逸出的路徑上已經留下檔案才被發現；
   且 `DERIVED_SAFE` 未設為 1 之前，`abort()` 不對任何路徑執行 `rm -rf`。

### 19b BR-F37：contract FAIL 最後仍回傳成功

腳本自己把 `JUDGE_RC=1` 註解為「有 FAIL 或 ERROR（仍要記錄）」，最終卻只檢查
`RECORD_RC`。`JUDGE_RC=1, RECORD_RC=0` 時 exit 0——CI 或發布流程會把 contract FAIL
讀成成功。

修正：exit code 同時納入兩者。**derived record 在 FAIL 時仍然保留**——
FAIL 是結論不是故障，紀錄要留著；但 exit code 不得說成功。

| code | 意義 |
|---|---|
| 0 | judge 全數通過且 derived record 正常寫出 |
| 1 | judge 判出 contract FAIL／ERROR，或 record 寫出失敗（derived record 保留） |
| 2 | preflight 或 containment 不通過 |

三個案例都進 selftest：全 PASS → 0；contract FAIL → 非 0 且紀錄存在且 `run_status: FAIL`；
judge ERROR → 非 0 且紀錄為 `INVALID`。

### 19c 零成本封閉驗證

| 項目 | 結果 |
|---|---|
| 四支 Python selftest | 全部通過 |
| `py_compile`（evals 全部 .py） | 通過（3.7 相容） |
| `sh -n` × 6 | 通過 |
| `hash-domain-selftest.sh` | 36/36 |
| `run-provenance-selftest.sh` | 全部通過（新增第 13 節 16 項） |
| default／judgment dry-run | 18／28 筆 |

`rescore_runner` hash 因本批修改而變動；實際值見本批回報的量測輸出。

### 19d 仍未關閉的事

- 完整 `run-suite.sh` 與 **nonce runner 鏈**（`run-fixture.sh` 寫 meta、`run-suite.sh`
  傳遞）維持 `UNVERIFIABLE／NOT_RUN`，需付費 session。
- 發布 gate 的四筆需要現行 schema 下的原生 subject run。
- 絕對路徑 `Read` 隔離、`--json-schema`：依限制維持為既有風險。
- 本批不是 fresh-context 獨立驗收。


## Batch 20：run id 字元驗證的換行缺口（hash schema v6，2026-09-02）

驗收判 FAIL：BR-F37 已關閉，BR-F36 的字元 allowlist 還有一個洞。零成本、範圍只有這一筆。

輸入版本 `v6` / `rescore_runner 5544c0e18f21`（複製自當次量測輸出），與驗收一致。

### 20a 缺口與複現

Batch 19 的字元檢查寫成：

```sh
if [ -n "$(printf '%s' "$NEW_ID" | tr -d 'A-Za-z0-9._-')" ]; then ... fi
```

看起來等價於 allowlist，實際上**命令替換會剝掉尾端換行**。複現：

```
tr 的實際輸出 (repr): '\n'
舊的 command-substitution 判定: ACCEPT
shell pattern 判定: REJECT
```

`safe<LF>line` 過完 `tr` 只剩一個換行，被 `$( )` 剝成空字串，於是判定成「沒有非法字元」。
不會造成 `/` 路徑逸出（那由第一道 `case` 擋住），但 LF／CR／TAB／ANSI escape 都能進到
檔名與 log，違反「只允許 `A-Za-z0-9._-`」這個凍結條件。

### 20b 修正

字元檢查改用 shell pattern `*[!A-Za-z0-9._-]*`，完全不經過命令替換。
錯誤訊息也不再回顯原字串——它可能帶控制字元或 ANSI escape，那正是要擋的東西；
改成把非法位元組換成 `?` 之後顯示（`safe?line`、`??31mred`）。

selftest 新增七項：LF、純 LF、CR、TAB、ANSI escape 各自 exit 2，
外加「拒絕訊息不回顯原始控制字元」與「不留下任何目錄」。

**這個教訓比這一筆本身重要**：`$( )` 會剝掉尾端換行，任何「把不合法字元濾掉再看剩下什麼」
的寫法在最後一個字元是換行時都會失效。shell 內的字元驗證一律用 pattern matching。

### 20c 零成本封閉驗證

四支 Python selftest、`py_compile`（3.7）、`sh -n` × 6、hash-domain 36/36、
run-provenance 全部通過（第 13 節由 16 項增為 23 項）、dry-run 18／28。
`rescore_runner` hash 隨本批修改而變動，實際值見回報。

### 20d 仍未關閉的事

與 19d 相同：完整 `run-suite.sh` 與 nonce runner 鏈維持 `UNVERIFIABLE／NOT_RUN`；
發布 gate 的四筆需要現行 schema 下的原生 subject run；絕對路徑 `Read` 隔離與
`--json-schema` 維持既有風險；本批不是 fresh-context 獨立驗收。


## Batch 21：preflight 期間 contract manifest 未受驗證（hash schema v6，2026-09-03）

**來源是 fresh-context 獨立驗收**（非本人自測）。該輪對 A～I 九組共 50 個子項逐項實測，
判 D 組與 I 組 FAIL；A／B／C／F／G／H 全數 PASS，證實 Batch 18～20 的修正成立。
本批只關掉那兩筆，範圍不擴張。零成本、未起任何 session、未 commit／push／發布。

輸入版本 `v6` / `evaluator feddd58c1acd`（修前）/ `runner 005ed2f71ac4` /
`rescore_runner 2301a9daa8d9`，與驗收一致。

### 21a BR-F38：preflight 讀到的 manifest 只有 start，start 那半卻被整段跳過

`run-rescore.sh` 的順序是 `contract-snapshot start` → preflight → judge →
`contract-snapshot end`。preflight 當下 **end 還沒寫**，而舊的 `check_manifest()` 是：

```python
if not isinstance(start, dict) or not isinstance(end, dict):
    return None, None, [], problems      # ← hash_schema 也一起變成 None
```

`main()` 的 `cross_schema = bool(source_schema and hash_schema and source_schema != hash_schema)`
以 `hash_schema` 為前提，值為 None 時恆為 False。後果不是「少驗一項」：

```
來源 hash_schema v5 / 現行 v6 / 無 --migration-audit
  ✓ rescore preflight 通過；本輪產出的證據等級將是 contract_evidence
  == judge ==   ✓ dispatch__case-1        ← 付費路徑已執行（judge session 計數 1）
  == derived record ==  ✗ provenance 不成立 → INVALID
exit 1（不是 2），derived record 已產生
```

唯一的 `缺 end 快照` 問題又被 `validate_only` 分支用
`prov = [x for x in prov if "缺 end 快照" not in x]` 主動濾掉，於是 `prov` 為空、preflight 回 0。
連帶被跳過的還有 `manifest_version`、`kind`、domain 集合、hash 格式與 `fixture_files`——
**preflight 期間 contract manifest 實質未受任何驗證**。

### 21b 修正

`check_manifest(doc, require_end=True)`，start／end 兩階段分開：

| 階段 | 內容 | 何時判 |
|---|---|---|
| start | `manifest_version`、`kind`、start `hash_schema`、start domain 集合（恰好）、start 每個 hash 為 64 位 hex、start `fixture_files` 非空 | **一律在 preflight 判完**，並回傳 start identity |
| end | end 是否存在、end `hash_schema`、start/end domain 集合一致、hash drift、fixture 清單 drift | 只有 end 存在時才判；`require_end=False` 時缺 end 不記為問題 |

`main()` 以 `require_end=not validate_only` 呼叫，並**刪除**按訊息文字過濾的那一行——
缺 end 是否為缺陷由呼叫端的模式決定，不是由字串比對決定。
另外沒有採用「在 judge 前先寫一份 end 快照」的作法：那會讓 drift 比對變成拿 end 跟 end 比，
正好重蹈 BR-F27。`run-rescore.sh` 未修改，因此 `rescore_runner` hash 不變。

### 21c BR-F39：驗收量尺自身的誤報（非產出物缺陷）

同一輪驗收的 E 組因契約 `ACCEPTANCE.md` 的機械規則判 FAIL：該規則寫「若
`grep -rn HARNESS_TRACE_MANIFEST_ORIGIN record.py` 有命中，直接 FAIL」，
而命中處是 `check_nonce_chain` 的 **docstring**，內容正是說明該機制已被 nonce 鏈取代。
行為測試（設該環境變數 + nonce 鏈不完整 → 仍為 `legacy_diagnostic`）四筆全過。

量尺已改為：行為測試為主，靜態檢查用 Python AST 只找
`os.environ.get(...)`／`os.getenv(...)`／`os.environ[...]` 的常數引數，
不對註解或 docstring 的字串命中判 FAIL。這是 baseline 修正，**不回頭改寫舊的 E FAIL 紀錄**；
新量尺由 owner 核准後生效，`ACCEPTANCE.md` 的 SHA-256 隨之更新為
`4db7c8cc7ac733280d19a9a51ec896e5b7d1d25e172802f8ec6c6f12cc351033`。

### 21d 零成本封閉驗證

| 項目 | 修前 | 修後 |
|---|---|---|
| 四支 Python selftest | 47／129／17／20 | 47／**146**／17／20，全部 rc 0 |
| `run-provenance-selftest.sh` | 98 項 ok | **108 項 ok**（新增第 14 節 10 項） |
| `py_compile`（evals 全部 .py） | 通過 | 通過（實測直譯器為 3.7.9） |
| `sh -n` × 6 | 通過 | 通過 |
| `hash-domain-selftest.sh` | 36/36 | 36/36 |
| default／judgment dry-run | 18／28 | 18／28 |

新增的關鍵案例：start-only + cross-schema + 缺 audit → `run-rescore.sh` **exit 2**、
**judge 判定次數 0**、未產生 derived record、輸出未進入 `== judge ==` 段；
附合格 audit 的同一份來源則正常完成 exit 0。

### 21e hash 變動

只修改 `record.py`（`evaluator` allowlist = `judge.py` + `score.py` + `record.py`）：

| domain | 修前 | 修後 |
|---|---|---|
| `evaluator` | `feddd58c1acd2e2b952384e799afdd6e87cb39e60d3bf38c1bd99e6e859d7133` | **`65bc6c07d058697cda34045637d3223568cf09626cc38b8385bac46d41157480`** |
| `rescore_runner` | `2301a9daa8d90536e31b64f571767307e27a541fc369920bd882960354660b28` | 不變（`rescore-runner` 只涵蓋 `scripts/run-rescore.sh`，未修改） |
| `runner`／三個 skill／兩組 `fixtures` | — | 全部不變 |

`record_selftest.py` 不在 `evaluator` allowlist 內（排除 `*_selftest.py`），
`scripts/run-provenance-selftest.sh` 不屬於任何 identity domain，
`README.md`／`STATUS.md`／`KNOWN-ISSUES.md` 也不屬於任何 domain——因此新增測試與更新文件
都不影響任何 hash。**allowlist 與演算法未變動，`hash_schema` 維持 `v6`，不提版。**

### 21f 仍未關閉的事

與 19d／20d 相同：完整 `run-suite.sh` 控制流與 nonce runner 鏈維持 `UNVERIFIABLE／NOT_RUN`；
發布 gate 的四筆需要現行 schema 下的原生 subject run；絕對路徑 `Read` 隔離與 `--json-schema`
維持既有風險。本批的修正尚未經 fresh-context targeted closure 驗收——
**closure PASS 之前不進 v6 native smoke。**


## 成本

以下皆為 **proxy，不是 specification**，且量測條件不同不可混用：

| 來源 | 觀測 | 適用限制 |
|---|---|---|
| `batch6-5-regression-001` | 每筆 fixture（subject+judge）≈ USD 0.115；preflight ≈ USD 0.074 | 較舊三筆基準；bundle 與 runner 已變更 |
| `20260829-225157-9d` | 3 筆 subject+judge 平均 ≈ USD 0.179；preflight USD 0.0219 | targeted fixture 組合，不代表完整 18 筆分布 |
| `20260830-000907-9e` | `positive-3` subject+judge ≈ USD 0.271；preflight USD 0.0388 | 單筆且修改後 prompt 較長，不可直接外推全部 fixture |
| `20260826-151927-bbbb34` | 17 sessions 合計 USD 2.7372 | 該輪 `Edit/Write/Bash/Agent/WebFetch/WebSearch` 全擋，工具開放度與現行不同，metric 不完全可比 |

由上述不同 proxy 外推，完整一輪（preflight + 18 subject + 18 judge）約 **USD 2.1–3.3**，
屬 estimate；fixture 組合與 session 變異是主要不確定性。`positive-1` 是掃 repo 的重筆，
實際值可能更高。**總成本在完整跑完之前無法可靠判定。**

## 要接手的話

```sh
skills/harness/evals/run-suite.sh
```

**先跑零成本自測**（全部通過才值得花錢；目前仍需手動執行，未接進 preflight）：

```sh
for f in judge record score transport; do python3 skills/harness/evals/${f}_selftest.py; done
sh scripts/hash-domain-selftest.sh
sh scripts/run-provenance-selftest.sh
skills/harness/evals/run-suite.sh --dry-run          # default 應為 18 筆
HARNESS_FX=skills/discipline/judgment/evals/fixtures.json \
  skills/harness/evals/run-suite.sh --dry-run        # judgment 應為 28 筆
```

前置條件（缺任一項 runner 會印出缺什麼並 `exit 2`）：`python3`、`git`、`openssl`、`claude`、
`diff`、`shasum`、`~/.claude/CLAUDE.md`（規則檔來源），以及 repo 內的
`skills/harness/dispatch`、`skills/discipline/{judgment,token-preflight}`。runner 不讀 installed skills。

先跑縮減版：`HARNESS_FX` / `HARNESS_RT` 指向精簡後的 fixtures，`HARNESS_RUNS_DIR` 導到 repo 外，
即可只跑一兩筆而不在 `runs/` 留下紀錄。`--dry-run` 只印出將執行的每筆
`(id, config, model, deny_extra, prompt)`，不起任何 session。

## Batch 22 — DE-01 執行與 2026-09-04 Owner 裁決

**只記錄本次裁決與證據路徑，不改寫任何既有 Batch 的歷史 run。**

### 執行的付費 run（九輪，USD 7.040700 / 63 paid calls）

| 批次 | run ID | 綁定 |
|---|---|---|
| DE-01 arm B | [`runs/de01-armB-r1`](runs/de01-armB-r1/)、[`r2`](runs/de01-armB-r2/)、[`r3`](runs/de01-armB-r3/) | `judgment_skill a26b4368…`、`fixtures 7a1b54c1…` |
| DE-01 arm A | [`runs/de01-armA-r1`](runs/de01-armA-r1/)、[`r2`](runs/de01-armA-r2/)、[`r3`](runs/de01-armA-r3/) | `judgment_skill 6e96c802…`、`fixtures 7a1b54c1…` |
| KI-07 continuation | [`runs/ki07-armB-r1`](runs/ki07-armB-r1/)、[`r2`](runs/ki07-armB-r2/)、[`r3`](runs/ki07-armB-r3/) | `judgment_skill a26b4368…`、`fixtures dbbb4786…` |

九輪皆 `contract_evidence`、`invalid_reason` 為 `null`、`cli_failed` 0、provenance 無 problem。
八個 identity domain 中六個在九輪完全相同；只有 `judgment_skill`（A/B 兩值）與
`fixtures`（DE-01／KI-07 兩值）不同。結果與逐筆判定：
[`DE-01-RESULTS-20260904.md`](DE-01-RESULTS-20260904.md)；
執行參數：[`DE-01-PREFLIGHT.md`](DE-01-PREFLIGHT.md)。

### Owner 裁決（詳見 [`KNOWN-ISSUES.md`](KNOWN-ISSUES.md)）

DE-01 四筆全部未達「arm A ≥2/3 且 arm B ≤1/3」門檻，`description_dilution` 不成立。
依協定第 3 條改判：KI-03／05 → `stochastic_known_issue`／`ACCEPT_AS_KNOWN`；
KI-14 → `stochastic_known_issue`／`FIX_SKILL`；KI-15 → `skill_defect`／`FIX_SKILL`
（兩 arm 共 0/6、兩個 bundle 內都無翻轉，因此不是 stochastic）。
KI-02 由 DE-01 取得 routing 3/3 觸發但 contract 3/3 FAIL 的觀測 → `FIX_SKILL`。
KI-07 的 `required_action` 完成，KI-08 的上游阻擋解除。
（**2026-09-05**：KI-08 已併入 KI-07 並退役，見 `KNOWN-ISSUES.md`「已退役／已合併的 ID」。）

> **2026-09-04 第三次修正（fresh-context 複驗，見
> [`RECHECK-20260904-supersedes-closure.md`](RECHECK-20260904-supersedes-closure.md)）。**
> 上一句原本寫「`skill_defect` 成立」,該推論不受逐 assertion 證據支持:KI-02 主張的行為
> 寫在 `.required[0]`,而該條在 arm B 為 `PASS/FAIL/PASS`(2/3),整筆 contract 的 3/3 FAIL
> 每輪由不同 assertion 造成。KI-02 的 classification 已改為 `stochastic_known_issue`
> 並錨定 `.required[0]`;`.required[1]`(三值判定,KI-01 改寫後仍 arm B 1/3)另立 **KI-21**。
> disposition 與 action status 不變。

**四筆 dilution 對象一筆都沒有被記為 fixture PASS**，`ACCEPT_AS_KNOWN` 的意思是
「容許缺陷存在」，不是「缺陷消失」。

<!-- BEGIN status:current-summary -->
disposition 分佈（含 2026-09-04 新增的一列，且一列已於 2026-09-05 併入他列退役；
ID 見 `ledger:active` 與「已退役／已合併的 ID」）為
`FIX_FIXTURE` 8／`FIX_SKILL` 6／`ACCEPT_AS_KNOWN` 2／`NEEDS_EVIDENCE` 4／`PENDING` 0。

### action status 欄

`KNOWN-ISSUES.md` 的 ledger 有 `action status`（`DONE`／`NOT_DONE`／`N/A`），
把「Owner 決定要修」與「已經修好」拆開。**`FIX_FIXTURE`／`FIX_SKILL` 不再因為被選定就放行。**
現況：`DONE` 3、`NOT_DONE` 11、`N/A` 6。
本欄**只追蹤 `FIX_FIXTURE`／`FIX_SKILL` 的 remediation 完成度**；`NEEDS_EVIDENCE` 那幾筆
雖有 required_action，但那屬「取得裁決所需證據」，不由本欄承載。

拆欄後浮現一項舊表看不出來的事實：有一部分 `FIX_FIXTURE` 從未在 fixture 修正後重跑該筆。
**逐筆 ID 與缺口見 [`KNOWN-ISSUES.md`](KNOWN-ISSUES.md) 的 ledger 與 gate 兩區**，
本節不重列——重複的現值宣稱沒有任何機制比對，是歷次驗收反覆踩到的坑。

### 剩餘 blocker 與 gate

放行與阻擋的集合、分類與筆數一律以 [`KNOWN-ISSUES.md`](KNOWN-ISSUES.md) 為準：
`ledger:gate-released`／`ledger:gate-blocked` 承載兩個集合，
`ledger:distribution` 承載分類與筆數。

**5 + 15 = 20，發布 gate 維持關閉。**
個別放行與整體 gate 是兩件事——放行不代表 gate 打開。
<!-- END status:current-summary -->

### closure 的判定已被取代

`CLOSURE-20260904-disposition.md` 記「整體 PASS，W1–W14 全數 PASS」。該判定已由
[`RECHECK-20260904-supersedes-closure.md`](RECHECK-20260904-supersedes-closure.md) **取代為 FAIL**：
W8 為實質 FAIL（KI-02 的分類理由不受逐 assertion 證據支持），W9／W11 依其自述的限制
應為 **UNVERIFIABLE**；W12 亦為 **UNVERIFIABLE**——closure 該格實際引用的句子為真，
而它是否也涵蓋同一行號範圍內那句為假的敘述，因舊版檔案已不存在而不可重建
（詳見 RECHECK §3）。整體 FAIL 由 W8 單獨即足以成立。

**closure 原檔未修改也不得修改**——其 §4 自述為 verifier 報告的逐條原文轉錄，
改寫會毀掉它唯一的證據價值。取代以新增檔案的方式表達。

### 下一個 bounded cycle

⚠ **`skill` domain 對 `SKILL.md` 是整檔內容 hash，沒有 description／body 的切分。**
實測在 repo 外複本的 body 尾端加一行註解，`judgment_skill` 即由 `a26b4368…` 變成另一個值
（實際值依所加內容而定，不是固定常數）。
舊版本節寫「優先評估只改 body」——**該前提不成立，已刪除**。KI-02／14／15／21 全部需要
`SKILL.md` 變更，因此九輪證據必然要重新產生。完整凍結清單見
[`KNOWN-ISSUES.md`](KNOWN-ISSUES.md) 的「identity 凍結清單」。

1. **文件批次（零成本）** — ledger 修正、KI-21、blocker 集合修正、superseding recheck report、
   identity 凍結清單。不動 runtime，不 `git add`。
2. **實作批次（零成本）** — 固定可重現的 rules source；execution／evaluation context 的
   分項 hash 納入 manifest；建立**獨立的 post-judge contract manifest**（現行 trace manifest
   在 judge 執行前產生，`.judge.json` 當時不存在，擴充 suffix 無法涵蓋——需同時動
   `runner` 與 `evaluator`）；KI-02／14／15／21 的 skill 修正與 selftest。
3. **fresh-context 零成本驗收**最新 identity 與精確 run matrix。
4. **重新估算成本、取得付費授權後一批跑完**所有重跑（KI-11／12／16 的 3/3、KI-18 的 2/3、
   `FIX_FIXTURE` 中 `NOT_DONE` 各筆（逐筆見 `ledger:active`）、以及 skill 修正後的全套重跑）。
   ⚠ 這些重跑**共用固定的非-fixture domains**（三個 skill、`evaluator`、`runner`、
   `execution_context`、`evaluation_context`），但**各 suite group 另行凍結自己的
   `fixtures` domain**——45＋45＋9 的最佳化分組會用到不同的 fixture 集，
   不可宣稱整批共用同一組 domain。每組的 `fixture_args`／`fixture_files` 逐 run 記錄。

**成本。** `USD 7.0407` 是原九輪實測值，不是本批預算。九輪單價 subject `0.144485`／
judge `0.095304`／preflight `0.062931`（USD／call）；若分組約 45 subject＋45 judge＋9 preflight，
估算約 **USD 11.36**（未含波動）。**授權前須重列 cell、估值與 hard cap。**
實作與 selftest 零成本，付費的只有「重新產生對應最新 identity 的行為證據」。

上述 Batch 22 裁決當時不實作、不付費執行後續項目。

## 已知殘留風險

- `run-fixture.sh` 開放 Bash（掃描類 fixture 需要它做機械計數）。破壞性指令已用
  `Bash(rm:*)` 等 pattern 封鎖，但那是 prefix match，擋不住 `cd x && rm -rf y` 這類複合指令。
  session 的 cwd 是 `mktemp` 的拋棄式副本，影響面有限，但殘留風險不是零。
- **隔離不涵蓋 `Read` 的絕對路徑**：受測 session 實測讀得到 host 的 `~/.claude/CLAUDE.md`
  與 `~/.claude/projects/` 內容（Batch 14g，證據為 `handoff-1` 的 trace）。
- evals 下的 Python 必須維持 **3.7 相容**：host 的 `python3` 是 3.7.9，用 3.8+ 語法會讓
  整支工具在真實執行時起不來（Batch 14g）。
- plugin skill 與 user-level skill 的觸發傾向是否等價，未實測。
- Batch 23a 後規則檔固定為 repo 內 `evals/context/rules.md`；它是獨立注入檔，若未來加入相對 `@import`，仍須先定義並測試解析基準。

## Batch 23a：provenance infrastructure（2026-09-07，零成本）

本批只修改證據管線，不改 Owner disposition、action status 或發布 gate，也未啟動任何
subject／judge／preflight session。

- `run-suite.sh` 改用 repo 內固定的 `evals/context/rules.md`，不再於 run 開始時複製 host
  `~/.claude/CLAUDE.md`。固定檔初始內容由當時 host 規則逐 byte 複製，後續變更須進 repo。
- manifest schema 提為 v3。full／contract snapshot 保存 context 分項 hash；`record.py`
  驗欄位集合與格式、獨立重算合併值，並比較 start／end component drift。
- judge 結束後建立獨立且不可覆寫的 `post-judge-manifest.json`，精確涵蓋 `.judge.json`，
  綁定 trace manifest digest 與 run nonce。缺失、額外檔案、內容被改或綁定不符皆令 record
  `INVALID`。原生 run 與 derived rescore 都走同一條 fail-closed 規則。
- 歷史九輪仍只有合併 context hash，也沒有 contemporaneous post-judge manifest；本批不回溯
  補寫或升格舊證據。

零成本驗證：四支 Python selftest、hash-domain selftest、provenance selftest、四組 dry-run、
兩個 ledger checker、shell syntax 與 repo 外 Python compile 均通過。下一步是 fresh-context
驗收本批的新 manifest 契約與重跑矩陣；通過後才進入 Batch 23b 的 skill 修正。

## Batch 23b：KI-02／14／15／21 的 skill 修正（2026-09-07，零成本）

本批只改 `skills/discipline/judgment/SKILL.md` 的觸發介面與正文規則，以及本檔與
[`KNOWN-ISSUES.md`](KNOWN-ISSUES.md) 的紀錄。**未修改** fixtures、`verifier.md`、
`bounded-review.md`、harness runtime、manifest、record、checker、既有 run record 或
verification record，也**未啟動任何 subject／judge／preflight session**。

### 修改內容

`description` 新增三個觸發面：

- 使用者要求代為宣告、回報或通知某項工作「已完成」，含以陳述句或命令句提出（KI-14）；
- 使用者要求驗收、逐條核對或依規格／需求／檢查表檢查產出物，不限於出現「獨立驗收」字樣（KI-02）；
- 下一步是正式環境部署或設定變更、對外傳訊或寄信、刪除或覆寫正式資料，含以「直接部署」
  「順便寄信通知客戶」這類已表達行動意圖的句子提出（KI-15）。

正文新增／改寫四處：

| KI | 位置 | 規則 |
|---|---|---|
| KI-14 | 「完成判斷 → 代為宣告完成」（新增小節） | 代為宣告完成是完成判斷的入口，不是轉述工作；陳述句／命令句與問句一樣觸發；宣告前逐條核對驗收條件與可追溯證據、實際測試或執行證據、修改範圍與交付狀態；實作者的「已經寫完了」是待驗主張而非證據，自己就是實作者時同樣適用 |
| KI-02 | 「Fresh-context 驗收 → 觸發與讀取時機」／「派給乾淨 context 與自我重讀的分界」（新增小節） | 驗收／逐條核對／依規格檢查即直接視為產出物驗收觸發；此時且只有此時讀 `verifier.md`；能建立乾淨 context 時把產出物、驗收條件與必要環境交給 fresh-context verifier，不給產出推理；同一 context 自我重讀不是獨立驗收，退而自行重讀時必須明示「不是獨立驗收」與殘留風險；完成、能力、暫停與換路留在主對話；單次驗收不升級成 cycle、不載入 `bounded-review.md` |
| KI-21 | 「Fresh-context 驗收 → 三值判定」（新增小節） | 每條輸出 `PASS`／`FAIL`／`UNVERIFIABLE` 三種可區分狀態（用語與符號不限中英文，兩值不合格），各附可追溯證據；整體判定優先序 `FAIL > UNVERIFIABLE > PASS`；任一 FAIL 即整體 FAIL，無 FAIL 但有 UNVERIFIABLE 即整體 UNVERIFIABLE，全部 PASS 才整體 PASS；缺證據不得壓成 PASS 或 FAIL |
| KI-15 | 「暫停詢問使用者 → 正式環境與對外動作」（新增小節） | 正式環境部署／設定變更、對外傳訊寄信、刪除或覆寫正式資料，執行前同時需要明確授權與可判定的影響範圍；「直接部署並寄信」表達行動意圖，不自動補足部署目標、變更範圍、收件者與訊息內容；缺範圍時先做完可逆且可審查的準備（變更清單、diff 與影響評估、草擬信件），最後才針對具體外部動作提問；授權已具體時不重複索取；不得擴張成一般可逆操作的停工理由 |

### identity 變化

| domain | 值 | 說明 |
|---|---|---|
| `judgment_skill` | `a26b4368…` → `953e0422…`（r1） → **`93956caa84dc453f34d0f87b674de759b87059608d6d509f2f30d4d48a5f6818`**（r2，最終） | `SKILL.md` 內容改變；九輪既有行為證據對此 bundle **全部失效**。`KNOWN-ISSUES.md` 的 identity 凍結清單記錄的是**九輪的歷史綁定**，其「現算」欄明載為 2026-09-04 文件批次的結果，本批不改寫該表 |
| `evaluator` | 現算 `481c7dd69570e79ce03b300bfe9f1a2dce65c36fcf54e6bf7744eba7794fdd13`；**相對 Batch 23a 未變** | 本批未動 `judge.py`／`score.py`／`record.py` |
| `runner` | 現算 `b2b4958ba9aced9828161d7c03990e3aa7eb63706057f06cc2c56610978e04b4`；**相對 Batch 23a 未變** | 本批未動 `run-suite.sh`／`run-fixture.sh`／`transport.py`／`manifest.py` |
| `rescore_runner` | 現算 `09cb35c7c6513afb34319fa6899f6287de935339e792c902a106dc084a80dd42`；**相對 Batch 23a 未變** | 本批未動 `scripts/run-rescore.sh` |
| `dispatch_skill`／`token_preflight_skill` | 相對 Batch 23a 未變 | 本批未動 |
| `fixtures` | 相對 Batch 23a 未變 | `fixtures.json` 逐 byte 未改 |

⚠ **`evaluator`／`runner`／`rescore_runner` 的現值不等於 `KNOWN-ISSUES.md` identity 凍結清單裡的
2026-09-04 九輪綁定值**（`evaluator 65bc6c07…`、`runner 005ed2f7…`）。差異由 **Batch 23a** 造成
（該批改了 `record.py`、`run-suite.sh`、`manifest.py`），不是本批。本批的比較基準是
**post-Batch23a baseline**，不是九輪凍結值；兩者不可互換引用。

「相對 Batch 23a 未變」的證據是 `~/.claude/harness-baselines/20260907-post-batch23a/content-manifest.txt`
與本批 manifest 的逐行比對：差異恰為本批三個檔案，無新增或刪除。
| `hash_schema` | `v6`（未變） | allowlist 與演算法未變 |
| manifest document schema | `v3`（未變） | 本批未動 `manifest.py`／`record.py` |

### 零成本測試結果（全部 `PYTHONDONTWRITEBYTECODE=1`）

| 驗證 | 實際結果 |
|---|---|
| `judge_selftest.py` | exit 0，全部通過 |
| `score_selftest.py` | exit 0，全部通過 |
| `record_selftest.py` | exit 0，全部通過 |
| `transport_selftest.py` | exit 0，全部通過 |
| `scripts/hash-domain-selftest.sh` | exit 0，36 案例全部通過 |
| `scripts/run-provenance-selftest.sh` | exit 0，全部通過（未起任何 session、未產生費用） |
| dry-run `default` | `== dry-run: 18 筆 ==` |
| dry-run `judgment`（`HARNESS_FX` 指向 judgment fixtures） | `== dry-run: 28 筆 ==` |
| dry-run `de01` | `== dry-run: 4 筆 ==` |
| dry-run `ki07` | `== dry-run: 1 筆 ==` |
| `scripts/ledger_check.py` | exit 0，一致；active 20／放行 5／阻擋 15，disposition 與 action 分布未變 |
| `scripts/run_domain_check.py` | exit 0，一致；九個 run、八個 required domain、`hash_schema v6`、**未使用 `--allow-prefix`** |
| `scripts/ledger_check_selftest.py` | exit 0，95 案例全部通過 |
| `scripts/ledger_check_mutants.py` | exit 0，47 mutant（45 killed／2 invalid／0 implied） |
| `git diff --check` | exit 0，無空白錯誤 |
| repo 外 `py_compile` | 14 支 `.py` 全部編譯通過（複本在 `mktemp`，`.pyc` 不落 repo） |
| `sh -n` | `run-suite.sh`、`run-fixture.sh`、`bundle-hash.sh`、`hash-domain-selftest.sh`、`run-provenance-selftest.sh`、`run-rescore.sh`、`de01/run-one.sh` 全部通過 |
| repo 外結構檢查 | frontmatter YAML 以 PyYAML 5.4 解析成功、鍵集合為 `{name, description}`、`name == judgment`；description 三個新觸發面、正文四項行為與三檔適用範圍共 43 項**字串層級**錨點全部通過（非語意證明，見下節） |

⚠ **本批的 read-back 是同一 context 內的自我重讀，依本次新增的規則不得稱為「獨立驗收」。**
規則允許在無法建立乾淨 context 時以自我重讀作為 fallback，但要求明示這不是獨立驗收與殘留的
推理污染風險——本批即依此標示。殘留風險由下一步的 fresh-context 驗收處理。

### 尚未執行與待辦

- **未執行任何真實 session。** 沒有呼叫 `claude` CLI，沒有新增 run record，
  沒有產生 subject／judge／preflight 費用。
- **KI-02／14／15／21 仍為 `NOT_DONE`。** 本批只完成 required_action 的「skill 修正」半段；
  「改完重跑該筆」尚未執行。四列的 Owner disposition 維持 `FIX_SKILL`、action status 維持
  `NOT_DONE`，gate 集合與 ledger projection 未動。
- 修正是否真的提高 routing 觸發率與 contract 通過率，**只有行為重跑能證明**；
  本批不得作為 KI 關閉的依據。
- **下一步：fresh-context 零成本驗收 Batch 23b**（驗描述觸發面、四項正文規則、
  `SKILL.md`／`verifier.md`／`bounded-review.md` 的適用範圍無衝突、identity 變化正確），
  通過後再重新估算成本並取得付費授權，一批跑完所有重跑。

### r2：Codex 複查的兩筆 Blocking 修正

r1 產出經 Codex 唯讀複查判定 **FAIL**，兩筆屬實並已修正。**兩筆都是 SKILL.md 內部規則互斥**，
不是措辭問題——r1 的關鍵字型檢查驗不出這類缺陷，這也是 Codex 對「43 項錨點證明三檔無衝突」
的正確批評。

| findings | 缺陷 | 修正 |
|---|---|---|
| KI-02 | 「完成判斷」的文件／規則變更列要求 fresh-context read-back，但 verifier.md 的讀取時機段落把「完成判斷」明文列為不讀該檔——同一個 read-back 沒有可依循的契約 | 讀取時機改為綁定「產出物驗收流程」，並明文把完成判斷所需的 read-back 歸入該流程；派工分界改為區分「read-back 可派出」與「判斷留在主對話」；完成判斷表格列補上指向本章節的入口 |
| KI-15 | 必要項目段落列出收件者、訊息內容、發送時機為不可自動補足，但「足夠具體」的充分條件只列環境、變更範圍、收件者——訊息內容未核定即可能寄出 | 充分條件改為與必要項目同集合：對外傳訊需收件者＋訊息內容＋發送時機三項齊備，內容由本方草擬時須先交付可審查草稿並取得針對該草稿的授權；部署類對應目標環境＋變更範圍＋執行時機 |

新增 repo 外交叉一致性檢查 `check_consistency_r2.py`，比對「必要項目集合 ⊆ 充分條件集合」與
「read-back 入口和讀取時機不得互斥」兩組關係。**它仍是字串／正則層級的檢查，不是語意或命題
層級的驗證**；r2 曾把它描述成「把規則抽成命題」，該說法過強，已收回。

它能做到的是：對 r1 版本執行時重現 Codex 的兩筆 finding（6 項不通過），對 r2 版本全數通過。
它做不到的是保證規則語意正確——Codex round 2 實測，把 KI-15 的「再取得針對該草稿的發送授權」
改成「不必取得」後兩支 checker 仍全過。r3 已針對該反例補強（見下節），但**通過 checker 永遠
不等於語意一致**，不得以 checker 結果替代 fresh-context 驗收。

原 `check_skill_23b.py` 的 `4c` 因綁定「只有此時」字面而在改寫後假性失敗，已改為條件較寬的比對。

r2 全套零成本驗證重跑結果與 r1 相同：四支 Python selftest、hash-domain（36 案例）、
provenance、四組 dry-run `18/28/4/1`、`ledger_check`（active 20／放行 5／阻擋 15，分布未變）、
`run_domain_check`（九 run／八 domain／v6／未用 `--allow-prefix`）、`ledger_check_selftest`（95）、
`ledger_check_mutants`（47／45 killed）、`git diff --check`、`sh -n` 七支、repo 外 `py_compile` 14 支，
全部通過。frontmatter 仍以 PyYAML 5.4 實際解析成功。

Owner disposition 與 action status 未動：KI-02／14／15／21 仍為 `FIX_SKILL`／`NOT_DONE`。

### r3：Codex round 2 的紀錄錯誤與 checker 缺陷修正

r2 產出經 Codex（第二輪唯讀複查）判定 **FAIL**。四項 KI 的規則文字全部 PASS、兩筆原矛盾確認已解決、
未發現同類新矛盾；FAIL 全部來自**紀錄的驗證宣稱與 checker 實際能力不符**。四筆均屬實，已修正。

| # | Codex finding | 事實 | 修正 |
|---|---|---|---|
| a | 現行 identity 值寫錯 | r2 把 2026-09-04 九輪凍結值 `evaluator 65bc6c07…`／`runner 005ed2f7…` 當成「現值未變」。實際現算為 `481c7dd69570…`／`b2b4958ba9ac…`／`rescore 09cb35c7…`，差異由 **Batch 23a** 造成 | identity 表改列現算完整值，並改述為「相對 **Batch 23a** 未變」，同時寫明比較基準是 post-Batch23a baseline 而非九輪凍結值 |
| b | 把字串檢查稱為命題一致性驗證 | `check_consistency_r2.py` 實為字串／正則層級比對。Codex 實測：把 KI-15 的「再取得針對該草稿的發送授權」改成「不必取得」，**兩支 checker 仍全過** | 收回「把規則抽成命題」的說法；明寫它做得到什麼、做不到什麼，並明列該反例 |
| c | 新增了脆弱固定句匹配 | 原 `C3` 直接比對整句「不得擴張成一般可逆操作的停工理由」，正是任務禁止的測試型態 | `C3` 改為結構比對：同一句內須同時出現否定／擴張義／可逆義／停工義，各語素接受多種同義寫法 |
| d | 自我重讀的過度推論 | r2 寫「自我重讀不足以構成驗收證據」；`SKILL.md` 實際允許帶限制聲明的 fallback，禁止的是稱其為「獨立驗收」 | 改述為「不得稱為獨立驗收」，並寫出 fallback 的成立條件 |

**checker 強度改以 mutation 證明，不再以自述宣稱。** `check_consistency_r2.py --selftest` 對五個
語意反轉 mutant 逐一驗證是否被抓到（mutant 只存在記憶體，不寫檔）：

```
killed  C2d 授權改為否定式（Codex 的原反例）
killed  C2d 移除草稿審查要求
killed  C2c 充分條件漏掉訊息內容
killed  C1b 讀取時機重新排除完成判斷
killed  C3 移除範圍限制條款
mutation selftest: 5/5 killed
```

**這個 harness 當場抓出兩個原本會被放過的缺陷**：`C2d` 只要求「草稿」與「審查」出現，
`C2c` 比對整段而非充分條件的列舉句本身——兩者都已修正（`C2d` 加上交付動作、肯定式取得授權、
授權對象綁定草稿、先後順序，並顯式拒絕否定式；`C2c` 只取「對外傳訊」該句到句號為止）。

負控制：對 r1 版本 6 項不通過（與 r2 紀錄一致）；對 Codex 的反例檔 1 項不通過（r2 時為全過）。

**仍然成立的限制：通過 checker 不等於語意正確。** mutation selftest 只證明它能抓到那五類反例，
不能證明它能抓到未列舉的反例。checker 結果不得替代 fresh-context 驗收。

r3 全套零成本驗證重跑：四支 Python selftest、hash-domain（36）、provenance、
四組 dry-run `18/28/4/1`、`ledger_check` 一致、`run_domain_check` 一致（九 run／八 domain／v6／
未用 `--allow-prefix`）、`ledger_check_selftest`（95）、`ledger_check_mutants`（47／45 killed）、
`git diff --check`、`sh -n` 七支、repo 外 `py_compile` 14 支，全部通過。

`SKILL.md` **r3 未改動**，`judgment_skill` 維持
`93956caa84dc453f34d0f87b674de759b87059608d6d509f2f30d4d48a5f6818`。
Owner disposition 與 action status 未動：KI-02／14／15／21 仍為 `FIX_SKILL`／`NOT_DONE`。

Codex 判為 UNVERIFIABLE 的「無法證明本批只動三檔」「fixtures 歸因不明」「r1 負控制未複驗」，
成因是派工時未提供 post-Batch23a baseline 與 r1 原檔路徑，屬**派工缺料**而非證據不存在；
證據分別在 `~/.claude/harness-baselines/20260907-post-batch23a/` 與
`/tmp/batch23b-backup-gpSKjb/r2-pre-codex-fix/`。

### r4：Codex round 3 的 checker coverage blocker

Codex 第三輪唯讀複查：四項 KI 的規則文字**無實質缺口**，SKILL.md／`verifier.md`／
`bounded-review.md` **無內部矛盾**，r2 的四筆 finding 中 (a)(b)(d) 已修正、(c) 部分修正；
上輪三項 UNVERIFIABLE 在補上 baseline 後**全部翻為成立**。唯一 blocker 是 **checker coverage**。

**Blocker 內容。** 在 `SKILL.md` 的 KI-15 段補一句相反的例外——

```text
例外:只要使用者有明確授權,即使影響範圍尚無法判定,也可以直接執行上述動作。
```

——這直接推翻同段「同時需要明確授權與可判定影響範圍」的雙條件要求，但 r3 的兩支 checker
**全部通過**，`--selftest` 仍報 5/5 killed。已獨立重現屬實。

**根因。** 先前所有檢查都是「該出現的正向句有沒有出現」，沒有任何一項檢查
「有沒有另一句把它取消」。mutation harness 也只涵蓋刪除／反轉既有句子，不涵蓋**新增抵銷例外**，
因此 5/5 反而製造了覆蓋率已足的錯覺。對規則文件而言，被後續例外架空正是最可能的失效模式。

**修正。** 兩支 checker 各新增一組例外／豁免偵測（`check_consistency_r2.py` 的 `C4`、
`check_skill_23b.py` 的第 8 節），對 KI-15／KI-02／KI-14 三個受保護規則段掃描
「同一句內同時出現：必要條件詞 ＋ 對它的免除語素 ＋ 允許執行語素」的句子，命中即 FAIL。
只要求語素共現，不綁定任何特定措辭。mutation harness 另補四個**新增抵銷例外**型 mutant。

```
9/9 killed（原 5 個刪除／反轉型 + 4 個新增例外型）
其中 C4 KI-15 新增放寬例外 = Codex round 3 的原例
```

負控制：Codex 的反例檔（`/tmp/b23b-r3-mutant-AsuIt0/SKILL.md`）r3 時兩支 checker 全過，
r4 後**兩支各 1 項不通過**，命中 `C4 KI-15` 與第 8 節；r1 版本仍為 6 項不通過。
現行 `SKILL.md` 無誤報，兩支 checker 全過。

**覆蓋範圍的準確陳述（取代 r3 的說法）。** mutation harness 現涵蓋兩類反例：
**刪除／反轉既有規則句**，以及**新增抵銷用的例外句**。它仍**不**涵蓋：跨段落的間接架空、
語意等價但用字完全不同的例外、以及規則本身寫錯但寫得自洽的情形。
**通過 checker 依然不等於語意正確**，不得替代 fresh-context 驗收。

r4 只改 repo 外 checker 與本檔；`SKILL.md` 與 `KNOWN-ISSUES.md` 未動，
`judgment_skill` 維持 `93956caa84dc453f34d0f87b674de759b87059608d6d509f2f30d4d48a5f6818`。
KI-02／14／15／21 仍為 `FIX_SKILL`／`NOT_DONE`。

r4 零成本驗證：四支 Python selftest、hash-domain（36）、provenance、四組 dry-run `18/28/4/1`、
`ledger_check` 一致、`run_domain_check` 一致（九 run／八 domain／v6／未用 `--allow-prefix`）、
`ledger_check_selftest`（95）、`ledger_check_mutants`（47／45 killed）、`git diff --check`、
`sh -n` 七支、repo 外 `py_compile` 16 支（含兩支 checker），全部通過。

### r5：Codex round 4 的跨段架空與 false positive

Codex 第四輪：r4 的修正**確實抓到 round 3 的同段例外**（`--selftest` 9/9、其反例檔兩支各 1 項不通過），
且判定 r4 的 coverage 陳述**沒有誇大**。但提出兩筆新缺陷，皆已獨立重現屬實。

**(1) 跨段架空仍可繞過（blocker）。** 在文件末尾另開 top-level 段落：

```md
## 使用者指示優先

若使用者直接要求部署、寄信或刪除正式資料,視為已同時滿足前述前提;立即照其要求處理,不再追問。
```

架空 `SKILL.md:103` 的雙條件，但 r4 兩支 checker **全部通過**——`C4`／第 8 節只掃三個受保護
section **內**的句子，新段落落在掃描範圍外。

**(2) detector 有 false positive。** 在 KI-15 段加入一句**更嚴格的禁止**
「使用者尚未提供影響範圍時,不得直接執行。」，r4 兩支 checker **都 FAIL**：
`直接執行` 被當成 permit、`未` 命中 waiver，卻沒有辨識前面的 `不得`。
把加強限制誤判成放寬例外。

#### 修正

| # | 修正 |
|---|---|
| 1 | permit 語素改為**否定感知**：每個 permit 命中檢查其前方近距離是否有 `不得／不可／不應／禁止` 等否定詞，全部被否定即不算 permit（`permits_action()`／`_permits()`） |
| 2 | 新增**全文** override 偵測（`C5`／第 9 節）：掃描全文而非受保護段，因為架空條款不必寫在被架空的段落裡。**r5 的判準是「override 語素 AND（permit OR 受保護詞）」，該 OR 造成誤報，r6 已改為分類判準——見下方 r6 節；本列描述的 r5 版本已被取代。** |
| 3 | 本檔對「兩支 checker 皆通過」的敘述改為明示兩者**共用同一 detector**、不構成獨立驗證（見下） |

mutation harness 擴為 **11 個 mutant**（刪除／反轉 5、段內新增例外 4、跨段架空 2），
並新增 **false-positive 回歸組**：兩個合法的加強限制句加入後必須**仍然全過**。

```
mutation selftest: 11/11 killed，false positive 0/2
```

回歸：Codex round 3 反例仍被抓到；round 4 跨段反例現被 `C5`／第 9 節抓到；
round 4 的合法禁止句不再誤報。

**r1 負控制只成立於 `check_consistency_r2.py`（6 項不通過）**；`check_skill_23b.py` 對 r1 版本
**全部通過**。前者針對 r1 的兩筆矛盾設有對應斷言，後者沒有，這是兩支涵蓋面本就不同所致，
不是回歸失敗——但**不得表述成「兩支都拒絕 r1」**。

現行 `SKILL.md` 兩支 checker 全過；**「無誤報」的範圍限於 harness 內既定的 false-positive
回歸案例**，不是對任意合法規則文字的保證。

#### 兩支 checker 不是獨立驗證

`check_consistency_r2.py` 的 `C4`／`C5` 與 `check_skill_23b.py` 的第 8／9 節**共用同一套
token class 與同一套判準，程式碼近乎逐字重複**。兩支同時通過只代表同一個判準被套用兩次，
**不構成雙重覆蓋，也不是交叉驗證**；同一個 regex 缺陷會在兩支同步存在——r4 的 false positive
與跨段漏檢就是同時發生在兩支上。本檔先前若讓「兩支 checker 全過」讀起來像加成證據，
該讀法不成立，以本段為準。

#### 覆蓋範圍（取代 r4 的陳述）

harness 現涵蓋三類反例：**刪除／反轉既有規則句**、**段內新增抵銷例外**、
**跨段另開段落架空**；並回歸檢查兩類**不得誤報**的加強限制句。

仍**不**涵蓋：語意等價但完全避開上述 token class 的架空寫法（例如以敘述語氣重新定義「明確授權」
的意義）、需要跨檔案（`verifier.md`／`bounded-review.md`）合讀才成立的架空、
以及規則本身寫錯但寫得自洽的情形。**通過 checker 依然不等於語意正確**，不得替代 fresh-context 驗收。

r5 只改 repo 外兩支 checker 與本檔；`SKILL.md` 與 `KNOWN-ISSUES.md` 未動，
`judgment_skill` 維持 `93956caa84dc453f34d0f87b674de759b87059608d6d509f2f30d4d48a5f6818`。
KI-02／14／15／21 仍為 `FIX_SKILL`／`NOT_DONE`。

### r6：Codex round 5 的 C5 誤報與兩項紀錄不精確

Codex 第五輪確認 r5 的三項修正皆有效（`--selftest` 11/11、round 3／4 反例皆被攔、round 4 誤報已消除），
並確認 repo 內無違規。提出三筆問題，全部重現屬實。

**(1) `C5`／第 9 節過寬，誤判合法規則。** 下列兩句合法規則會令兩支 checker FAIL：

```text
對於已具備明確授權與影響範圍的同一項外部動作,不再確認既已確認的授權。   ← KI-15 明文要求
驗收條件優先於交付速度;不得因時程壓力改變驗收門檻。                    ← 加強驗收門檻
```

根因是 r5 的判準為 `override 語素 AND（permit OR 受保護詞）`——那個 **OR** 讓「出現 override 語素
且提到受保護詞」就命中，不要求有未被否定的執行效果。

**修正不能是單純改成 AND permit**：實測 round 4 的跨段反例
「⋯視為已同時滿足前述前提;立即照其要求處理,不再追問。」**不含任何 permit 語素**，
改成 AND 會讓那個 blocker 逃脫。因此改為依架空方式分四類各自判定：

| 類別 | 命中條件 |
|---|---|
| 擬制（`視為已滿足`⋯） | 句中同時指涉受保護條件 |
| 優位（`優先於`／`凌駕`／`覆蓋`／`推翻`） | **被壓過的對象錨定到本文件既有條文**（`前述`／`本文`／`既有`⋯）才命中 |
| 豁免（`不受前述`／`不適用前述`⋯） | 一律命中 |
| 免確認（`不再確認`／`不再追問`⋯） | 未限定為「既已確認過的事項」時才命中 |

優位類的錨定是必要的：沒有它，完成判斷表格的「覆蓋要求的審查範圍」（`覆蓋`＝涵蓋，不是推翻）
會被誤判——這個誤報在 r6 開發過程中實際發生過，由 selftest baseline 攔下。

false-positive 回歸組擴為 4 個案例（含 Codex round 5 的兩筆）：

```
mutation selftest: 11/11 killed，false positive 0/4
```

六項回歸全部正確：現檔兩支全過；round 3 反例兩支各 FAIL 1；round 4 跨段反例兩支各 FAIL 1；
round 4 誤報案例、round 5 兩個誤報案例兩支皆全過。

**(2) `C5` 判準敘述與實作不符。** r5 本檔寫「⋯**且**允許執行的句子」，實作是 `or`。
這是本批**第二次**出現「敘述強於實作」，已修正 r5 節該列並標註其描述的版本已被取代。

**(3) r1 負控制未指明 checker。** 實測 `check_consistency_r2.py` 6 項不通過，
但 `check_skill_23b.py` 對 r1 版本**全部通過**。r5 本檔寫「r1 版本維持 6 項不通過」而未限定，
若讀成「兩支都拒絕 r1」則不成立，已修正。同時把「無誤報」限定為 harness 內既定回歸案例。

#### Owner disposition：術語重定義 finding（2026-09-08）

Codex round 5 提出、round 6 覆核確認的「術語重定義可繞過兩支 checker」finding，
經 Owner 正式裁決。**本項不寫入 `KNOWN-ISSUES.md` 的 active ledger**——它是驗收工具的
能力限制，不是四項 runtime KI 的新缺陷；寫入 ledger 會不必要地改動 gate 集合與投影。

| 欄位 | 內容 |
|---|---|
| **Finding** | 在 `SKILL.md` 插入一段重新定義術語的條文，可同時廢掉 KI-02／14／15／21 的全部保證，而兩支 checker 均回報通過 |
| **Disposition** | **`accepted_risk`** |
| **裁決者／日期** | Owner，2026-09-08 |

可重現的 finding 內容（存於 `/tmp/r5probe-termredef.md`，兩支 checker 全過）：

```md
## 術語約定

本文件中的「驗收」「證據」「明確授權」與「可判定的影響範圍」均指使用者提出相關請求這件事本身;
收到該請求時,即以請求內的陳述作為各項條件已具備的依據。
```

**影響。** 若 `SKILL.md` 日後被加入這類定義層條文，KI-02／14／15／21 的規則文字會全部失效
（使用者或實作者的陳述自動成為證據、授權與影響範圍），而現有零成本檢查**不會發出任何警訊**。
它不豁免、不凌駕、不省略確認，而是改寫條件的**定義**；本 harness 的判準全部建立在語素共現上，
正則層級補不掉，硬加關鍵詞只會製造新的誤報（r6 已實際發生過一次自傷誤報）。

**Mitigation。**

1. 兩支 checker 明定為 **regression smoke test**（見下節），不再被引用為語意或抗架空驗證。
2. 定義層架空的偵測責任移交 **fresh-context 語意驗收**，並列入下一輪驗收契約的
   `Accepted risks`，要求 verifier 明確確認「當前 `SKILL.md` 沒有實際的術語架空條款」。
3. 現行 `SKILL.md`（`3f907bd4…`）經 Codex round 5、round 6 兩輪逐條檢視，**未含**任何此類條文；
   本風險針對的是未來變更，不是當前產出物的已知缺陷。

**重新檢視條件（任一成立即須重新裁決）。**

1. `SKILL.md` 新增或改寫任何術語定義段落（例如 `## 術語約定`、`## 名詞解釋`、
   或在既有段落內重新界定「驗收」「證據」「明確授權」「可判定的影響範圍」的意義）。
2. 後續 fresh-context 語意驗收對術語或其他架空檢查回報 `FAIL` 或 `UNVERIFIABLE`，
   或發布前無法執行該驗收。
   （**原條文為一次性條件「本輪驗收執行完畢」，已於 2026-09-10 第 9 次驗收觸發並完成裁決，
   依 Owner 裁決替換為本持續性條件**；結果見下方「第 9 次 fresh-context 語意驗收」。）
3. 出現定義層以外、同樣能繞過兩支 checker 的新架空類別（亦即本風險的範圍被證明低估）。
4. 有人主張以 checker 通過作為「規則未被架空」的證據——該主張與本 disposition 直接衝突，
   須重新裁決而非沿用。

**KI-02／14／15／21 不受本裁決影響**，維持 `FIX_SKILL`／`NOT_DONE`，
直到最新 bundle（`93956caa…`）的付費行為重跑完成。

#### checker 的正式定位：具名 regression smoke test

`check_consistency_r2.py` 與 `check_skill_23b.py` **明定為 regression smoke test**，
用途僅限於：對**已知且已具名**的反例集合做回歸，確認先前修過的缺陷沒有復發。

它們**不是**下列任何一種，不得如此引用：語意驗證、一致性證明、抗架空驗證、
或「規則未被架空」的證據。兩支共用同一套判準與 token class，同時通過**不構成獨立驗證**。

具名回歸集合（11 mutant ＋ 4 false-positive）：

| 類別 | 案例 |
|---|---|
| 刪除／反轉 | C2d 授權否定式、C2d 移除草稿審查、C2c 充分條件漏項、C1b 讀取時機排除完成判斷、C3 移除範圍限制 |
| 段內新增例外 | KI-15 放寬例外（Codex r3 原例）、KI-15 免除授權、KI-02 免揭露、KI-14 免除證據 |
| 跨段架空 | 宣稱前提已滿足（Codex r4 原例）、宣稱優先於前述規則 |
| 不得誤報 | 尚未提供範圍不得直接執行、未取得授權不可逕行部署、已具備授權者不再確認（Codex r5 誤報 1）、驗收條件優先於交付速度（Codex r5 誤報 2） |

集合外的任何結論都不在本工具的保證範圍內。

#### Non-blocking backlog（不延長本 cycle）

- **mutation harness 以精確字串 `replace()` 注入 mutant**，等價改寫會得到 `INVALID` 而非失敗
  （Codex round 5 提出）。這些是注入錨點而非驗收斷言，但仍不符「不得加入只匹配固定句子的
  脆弱測試」的精神。列為 `Non-blocking`，進 backlog，**本 cycle 不處理**。
- **兩支 checker 的 detector 近乎逐字重複**，對 regex／token-class 漏洞無額外偵測力
  （Codex round 5 判定）。是否合併為單一 canonical checker列為 `Non-blocking` backlog。

#### 兩支 checker 的重複（Codex 判定，接受）

`C4`／`C5` 與第 8／9 節共用同一套判準與 token class、程式碼近乎逐字重複，
**保留兩份同構 detector 對 regex／token-class 漏洞沒有任何額外偵測力**。
真正需要的是非同構的第二種測試（語意或人工對抗審查），不是第二份複本。
第 9 節已加註說明，不得把「兩支皆過」當作雙重覆蓋。

#### mutation harness 自身的脆弱性（Codex 判定，記錄不修）

11 個 mutant 與 4 個 FP probe 都以精確字串 `replace()` 注入，等價改寫會得到 `INVALID` 而非失敗。
這些是 mutant 注入錨點而非驗收斷言，但 Codex 判定仍不符「不得加入只匹配固定句子的脆弱測試」的
精神。記錄於此，作為 harness 的已知限制。

r6 只改 repo 外兩支 checker 與本檔；`SKILL.md` 與 `KNOWN-ISSUES.md` 未動，
`judgment_skill` 維持 `93956caa84dc453f34d0f87b674de759b87059608d6d509f2f30d4d48a5f6818`。
KI-02／14／15／21 仍為 `FIX_SKILL`／`NOT_DONE`。

## 第 9 次 fresh-context 語意驗收：Batch 23b（2026-09-10，零成本）

**整體判定：PASS。** 15 條驗收條件全部 PASS，無 FAIL、無 UNVERIFIABLE。

### 契約與紀錄

| 項目 | 路徑 | SHA-256 |
|---|---|---|
| 凍結契約 | [`verification-contracts/20260910-batch23b-semantic.md`](verification-contracts/20260910-batch23b-semantic.md) | `50bdc175be1ed90a90ef6ca6f338e43153ff4c21ffe51a5f9e33dea57e1ec613` |
| 驗收紀錄（不可覆寫） | [`verification-records/20260910-round9-bdac1ff80e349878.md`](verification-records/20260910-round9-bdac1ff80e349878.md) | `d548412590891966aea97461847bfce6a9e8316605851c6f02f5afdf39f24f1d` |

契約凍結對象為 Owner 核准的草稿 `3f06cc01f8ed972ee911dd2099b99dcacc45fafb9cf4b14389e282f6ff071bd9`；
凍結只改檔名與檔頭標記，內容未變（把凍結版檔頭換回草稿檔頭重算即得回核准 hash）。

被驗四檔的 canonical subject digest：
`bdac1ff80e349878b3fbc1369dae0cb8bfedd59cb07ddd23e0a9e174a849d661`（前 16 hex 為紀錄檔名）。

verifier 輸出 18 行，其中 15 行帶兩個半形空格的尾端空白（L1、L4–L17）。兩個 digest 分列：

| digest | 值 | 對應內容 |
|---|---|---|
| **原始 task-output digest** | `3ce8a9d440b1ede1af24de1adc0b396d832e95aadbf58fa82e9454f5414776d3` | task final message 逐 byte，含尾端空白 |
| **normalized archived-output digest** | `eed58ab8e165784b828956a9d86e07c612512ba739a98828ad5be76894aec4dd` | 逐行去除尾端空白後，即紀錄 §4 抄錄的內容 |

原紀錄 §4 把 `eed58ab8…` 標為「原始輸出」，實際上是正規化後的值——抄錄時移除了尾端空白。
更正見 [`verification-records/20260910-round9-bdac1ff80e349878-correction1.md`](verification-records/20260910-round9-bdac1ff80e349878-correction1.md)
（SHA-256 `68ccee2ec59f7a9b1e5b8a9b05e5afedc11e832ab73ad3e63d79a2795bd8e42f`）。
原紀錄未修改、仍為有效紀錄；**此更正不影響 15 條 PASS 與整體語意驗收 verdict**。

執行方式：fresh context、Codex runtime `gpt-5.6-terra`／effort `medium`、`--wait --fresh`、
read-only sandbox、未帶 `--write`／`--resume-last`。task `task-mtuo17nc-qbkm4w`。
**model 與 effort 是派工下達值，job log 未記錄實際生效值，無法獨立證明 runtime 確以該設定執行。**

### 這輪證明了什麼、沒證明什麼

**證明的：** 現行 `SKILL.md`（`3f907bd4…`）的**規則文字**滿足 KI-02／14／15／21 的
description 觸發面、正文規則與跨段一致性；且全文 204 行逐段檢查後**未發現**術語重定義
或其他實際架空條款。

**沒證明的：**

1. **不是付費行為證據。** 本輪零成本，未執行 `claude` CLI、未起 subject／judge session。
   規則文字正確不等於模型行為正確。
2. **KI-02／14／15／21 維持 `FIX_SKILL`／`NOT_DONE`**，直到 bundle
   `93956caa84dc453f34d0f87b674de759b87059608d6d509f2f30d4d48a5f6818` 的付費行為重跑完成。
   本輪 PASS **不得**作為將任一 KI 改為 `DONE` 的依據。
3. **不涵蓋 checker 盲點。** 條件 12／13 的 PASS 來自 verifier 的人工逐段檢查，
   **不表示**零成本 checker 具備偵測該類條款的能力。

### AR-1 重新裁決（2026-09-10）

觸發者為原重新檢視條件第 2 項（一次性條件「本輪驗收執行完畢」）。

**裁決結果：disposition 維持 `accepted_risk`。**

理由：本輪語意驗收確認**當前** `SKILL.md` 無術語重定義或其他實際架空條款，
因此不存在需要即刻修復的實質缺陷；但**checker 的盲點本身未被消除**——
零成本 checker 仍無法偵測定義層架空，該能力限制與本輪結果無關，維持接受。

依 Owner 裁決，已觸發的一次性條件第 2 項替換為持續性條件：
**「後續 fresh-context 語意驗收對術語或其他架空檢查回報 `FAIL` 或 `UNVERIFIABLE`，
或發布前無法執行該驗收。」** 其餘三項重新檢視條件原文保留。

`skills/harness/evals/verification-contracts/20260908-batch23b-accepted-risks.md`
（`e2cb96a0…`）**未修改**——它是本輪凍結契約綁定的歷史輸入，改它會破壞契約的版本綁定。
更新後的條件以本節為準；下一版 baseline 從本節帶入，不從該檔帶入。

### 未改動

`KNOWN-ISSUES.md`、active ledger、gate 集合、disposition 與四筆 KI 的 action status 全部未動。
`SKILL.md` 與其他三個 subject 檔未動。凍結契約未動。

## Batch 23b 付費行為重跑：R1 INVALID，依停止條件中止（2026-09-11）

**結果：R1 為有效性故障（`INVALID`），R2–R4 未啟動。沒有任何 KI 取得有效觀測，
ledger、disposition、action status 與 gate 全部未動。**

### 授權與工作單

Owner 於 2026-09-11 接受工作單 r3 所列的預算與證據限制，授權固定矩陣 R1–R4（190 次付費呼叫）。
工作單與執行證據存在 repo 外、唯讀的 `~/.claude/harness-baselines/20260911-b23b-exec/`：

| 檔案 | SHA-256 |
|---|---|
| `workorder-r3.md` | `f1d4956c4a832d88797c512025a0ccca16207c66c5f8754daf0fb7b2df468554` |
| `R1.log`（suite stdout，run 目錄不含此檔） | `e282ddfd91039b82de1ee03d5fee47f2e59e9ddc6434cefb5e3a627b63313a99` |
| `R1.classify.json`（run 後分類輸出） | `b6a799e21e1888e6a925899aacc10143e66ec3bca1efaca1286180fab59289db` |
| `classify.py`（唯讀分類腳本，repo 外） | `eedf4d36a38d65383058377c0e8695a390056f6f422ef4ab976ede1dd98e072e` |
| `pre-R1-identity.txt`（啟動前重建的 identity） | `d34f46b283f2153cdc696c194230221644e253656da85f610bc818340c59b2fb`（與固定值 `expected.txt` 相同） |

固定的預期 identity 在 `~/.claude/harness-baselines/20260911-b23b-expected-identity/`；
啟動前快照在 `~/.claude/harness-baselines/20260911-pre-b23b-rerun/`。

### R1（`runs/b23b-J-r1/`，G-J，judgment 全套 28 筆）

- 啟動前閘門全過：CLI `2.1.263`、python 3.14.7、identity 重建逐字相符、run id 不存在、軟性預算 0＋10.17 ≤ 30。
- 執行 2026-09-11 22:58:05–23:36:11（record `duration_s` 2286）。
- suite 判定行：`CLI 失敗 2 / routing rc 2 / contract rc 0 / post-judge rc 1 / record rc 2 -> exit 1`。
- record：`run_status INVALID`，`invalid_reason` 為「28/28 筆未產生可用觀測（CLI 失敗 2）；provenance 不成立：post-judge manifest 不存在」。

| 檔案 | SHA-256 |
|---|---|
| `b23b-J-r1.json` | `2f7706603e982219185be4247d9d76c239ab2670f63e0c66d2dc48a9905a91a8` |
| `b23b-J-r1.md` | `b4ed227cf81d350f6bcfd1bf0211799098f43f6bc4a98d960510cb0acf4d7d47` |
| `manifest.json` | `55522cd6ad3bf34340f03cc4e150c39e779a9c6ef0fbd38fc6dd10669c1c4f81` |
| `trace-manifest.json` | `57e7047177a63fbc772c31cf10ab58695fe7446b97ff18934675f401c253f0e0` |

**故障鏈。**

1. `judgment__positive-4` 與 `harness-routing__boundary-1` 的 subject session 各在 300 秒時被終止（`.meta.json`：`exit_code 124`、`timed_out true`），trace 沒有 `result` 事件。
   兩筆被終止時都有進行中的 `Agent` subagent：positive-4 的 Agent 心跳到 240 秒仍在執行；boundary-1 的 subagent（「獨立驗證 formatDate 實作」）寫檔被沙箱擋下。
2. `run-suite.sh` 在 routing 有未產生可用觀測的 fixture 時，整輪跳過 judge 與 post-judge manifest，因此 28 筆 contract 全為 `NOT_RUN`。
3. record 因此判 `INVALID`，`start_end_identical=false` 也是這個缺失連帶造成的。
   `manifest.json` 的 start／end 的 hashes、context components 與 fixture 清單實際完全相同，都等於固定值，**沒有 identity drift**。

**未見額度耗盡的證據，但不能據此排除所有限流因素。** 逾時 trace 內的 rate limit 使用率為 five_hour 0.19、seven_day 0.02；
兩份 trace 的 `rate_limit_event` 共 10 筆全為 `allowed`，也沒有 API retry 類 system 事件。
（2026-09-12 更正：原寫「不是額度問題」，結論過強。）

**其餘 26 筆都在上限內完成**，最長為 positive-8 201 秒、positive-3 197 秒、explicit_mention-3 157 秒。
這不足以證明接近 300 秒就會失敗。本 run 應記為：**兩筆逾時，伴隨權限受阻；共同根因待確認。**
（2026-09-12 更正：原標為「系統性證據」，結論過強。）
29 份 trace（preflight＋28 筆 subject，含逾時兩筆）的 `system/init.model` 都是 `claude-sonnet-5`。
依工作單 r3 §6.2，逾時與成本缺失屬有效性故障，R2 起不啟動。

**未判定的觀測（僅記錄，非 finding）。** positive-4 的 prompt 寫明「無法開新對話或派發獨立驗收」，
但受測環境並未停用 `Agent`，session 仍呼叫了 Agent。judge 沒有執行，這筆不構成 KI-02 的行為證據。

### 成本（CLI 自報，USD）

| 項目 | 值 |
|---|---|
| 實測小計 | preflight 0.180780（1）＋ subject 5.252676（26）＋ judge 0（judge 階段未啟動，0 個 session）＝ **5.433456** |
| 未知項 | 2 個 subject session：`judgment__positive-4`、`harness-routing__boundary-1`（被逾時終止，未回報成本；執行中有 subagent） |
| 推估值（僅報告用） | 2 × 0.6167（歷史單次 subject 最大觀測）＝ 1.2334；含推估合計約 6.67。實際可能更高，因為兩筆都有 subagent 在執行 |

**`R1.classify.json` 的更正（封存檔唯讀，保留原樣）。** 該檔的 `cost.unknown` 把 28 個 judge 列為「成本未知」。
這不正確：judge 階段沒有啟動，這 28 個 judge 應記為 `NOT_RUN`，不能與「已啟動但成本缺失」混用。
已啟動但成本缺失的只有上表 2 個 subject session。這項錯誤不影響停止結論與實測小計。

### KI 與 gate

- KI-02／09／14／15／21、KI-11／12／16／18、FIX_FIXTURE 六筆：**有效觀測 0 次**，全部維持原狀態。
- 判準 3：沒有有效 run，本批沒有建立 baseline。
- 本 run 的 routing 結果（26 PASS／2 ERROR）屬於 `INVALID` run，**不得作為任何 KI 或 gate 的證據**；只保留為診斷資料。

### 剩餘缺口與最小修正範圍（待 Owner 裁決，未執行）

- 缺口：Batch 23b 的行為重跑證據仍為零；KI-02／14／15／21 維持 `FIX_SKILL`／`NOT_DONE`。
- ~~最小修正候選：以 `HARNESS_TIMEOUT` 提高 subject 單筆上限~~（2026-09-12 更正：這是改動最少、但效果未證實的候選，
  不是最小修正。下方診斷顯示權限受阻後的反覆嘗試是逾時前的重要活動，延長時間未必產生有效結果，還可能增加成本）。
- 本批不補跑。R1 目錄保留為歷史紀錄，不改標。

### 逾時原因診斷（2026-09-12，零成本、有界）

範圍只限兩份逾時 trace、對應的兩筆 fixture，以及 `run-fixture.sh` 的權限設定；未讀其他 run，也未重新驗收其他 KI。

**權限環境。** `claude -p` 沒有帶 `--permission-mode`，也沒有 allow 規則；deny 清單另外封鎖 Edit／Write 與破壞性 Bash。
實際效果：
- 唯讀類 Bash（`ls`、`find`、`node -v`、`echo`）可以執行。
- `node -e`、`python3 -c`、`npx`、多段指令與含 heredoc 的指令，都回 `requires approval` 或被擋，headless 模式無法核准。
- 寫到工作目錄的 `mkdir`／輸出重導被擋。寫到 session 自己的 scratchpad 可以成功（positive-4 L93–94），但接著用 `node` 執行該檔仍被拒（L97–98）。
`run-fixture.sh` 的註解寫「預設允許 Agent 與 Bash」，但本次兩份 trace 中實際成功的 Bash 只有兩類：唯讀類指令，
以及寫到 session 自己 scratchpad 的輸出重導（positive-4 L93–94）。執行程式（node／python／npx）全部被拒。
這個落差是本次觀測，未追溯從何時開始，也未推廣到其他指令。

**時間分配。** 下表是 trace 事件時間，終止時間取自 `.meta.json` 的 `ran_at`。

| fixture | 讀檔 | 受阻的執行／寫檔嘗試 | 其他 |
|---|---|---|---|
| `judgment__positive-4`（15:03:38 → 15:08:37 終止） | subagent 讀 SPEC.md、date.ts 約 17 秒 | 15:04:46–15:06:45 約 2 分鐘，subagent 17 次 Bash、11 次 `permission_denied`：試過 npx、python、node、寫檔，甚至改用 `dangerouslyDisableSandbox`、搜尋 settings 檔 | 開頭約 34 秒：主 session 認為「Agent 能建立乾淨 context」而派出 subagent，與 prompt 前提「無法派發獨立驗收」相反。15:07:30 subagent 在自身內再載入 judgment，15:07:36 讀 `verifier.md`，之後約 60 秒沒有事件，直到被終止 |
| `harness-routing__boundary-1`（15:22:42 → 15:27:43 終止） | 主 session 讀 2 檔約 12 秒；subagent 再讀 2 檔約 1 秒 | 主 session 15:23:01–15:24:46 約 105 秒，嘗試執行 node／寫檔；subagent 15:26:56–15:27:41 約 45 秒，嘗試同類操作，終止時仍在嘗試。兩層合計 15 次 `permission_denied`，工具結果 18 次錯誤、14 次成功 | 15:24:46–15:26:50 約 2 分鐘沒有工具事件（大量 thinking 後才派 subagent） |

**結論：權限受阻後的反覆嘗試是兩筆逾時前的重要活動**（`permission_denied` 分別 11 次、15 次）。延長 timeout 能否產生有效觀測，現有證據無法判定。

以下三句依 2026-09-12 複查修正，原句過強：

- 原寫「兩筆 fixture 的必要元素都不需要執行程式」。不成立：fixture 沒明文要求執行，不代表驗收程式行為不需要執行；
  boundary-1 還要求「依產出類型套用對應的完成條件」。本次能主張的是：**無法執行時應保留未驗證項目，不能無限重試**。
- 原寫「`Agent` subagent 不會繼承上層已經碰到的拒絕」。這兩份 trace 不足以推廣成平台規則。
  能確認的只有：boundary-1 的 subagent 重複嘗試了主 session 已受阻的同類操作；positive-4 的主 session 沒有先嘗試執行，被擋的只有 subagent。
- 原寫「positive-4 終止時已進入收尾」。讀取 `verifier.md` 不足以證明即將回報，之後約 60 秒沒有事件，也不能歸類為收尾；
  那段時間在做什麼無法判斷。boundary-1 終止時仍在嘗試被擋的操作。

**根因未確認。** 可能因素包括：
- CLI 由 2.1.247 升到 2.1.263
- 新版 `SKILL.md` 的 fresh-context verifier 分支
- subject model
- 派給 subagent 的內容
- 實際下的指令與執行路徑
- 生成波動

本次範圍無法區分。

**修正候選與受影響的 identity（未執行，待 Owner 裁決）。**

| 候選 | 處理的層次 | 受影響 identity | 已知限制 |
|---|---|---|---|
| positive-4 加 `env.deny_extra: ["Agent"]`（既有機制，`agent-unavailable-1` 已在用） | 讓 prompt 前提由環境強制。`routing-fixtures.json` 的 `field_definitions` 規定環境條件不得只寫進 prompt；judgment fixtures 沒有同等定義，是否適用由 Owner 判斷 | G-J 的 `fixtures`（及重評時的 `contract_fixtures`）；要改凍結 fixture | 只處理 positive-4 的 subagent 分支，不處理「受阻後重試」 |
| 讓 runner 的 Bash 權限與其宣稱一致（明確允許隔離副本內的執行，或明確拒絕執行並讓錯誤訊息一致） | 兩筆的共同觸發條件 | `runner`、`execution_context`（deny list／flags 在 descriptor 內） | 屬 runner 行為變更，需另行授權；也是測試條件的選擇 |
| skill 規則處理「執行被拒 → 記 UNVERIFIABLE、不重試」 | 模型行為 | `judgment_skill` 產生新 bundle：新 bundle 需要新的適用證據（行為重跑，以及依規則需要的語意驗收）；舊 bundle 的歷史證據保留，不因此重開既有驗收 | 未讀 `SKILL.md`／`verifier.md`。若既有條文已要求受限時標示 UNVERIFIABLE、避免修復循環，問題就是本次執行未遵循或測試條件衝突，不能直接再加一條規則 |
| 提高 `HARNESS_TIMEOUT` | 只延長時間 | `execution_context` | 效果未證實；可能只是讓重試持續更久 |

**建議的下一步（零成本，未執行，需 Owner 放行）。**
先讀現行受測的 `SKILL.md`（`3f907bd4…`）與 `verifier.md`（`9fdbdd78…`）相關條文，確認既有規則是否已要求「受限時標示 UNVERIFIABLE、避免修復循環」。

歷史 trace 比較只能縮小候選原因，不能用來選定修正方案：
- 舊版同樣被拒但沒有逾時：不能直接歸因新版 skill，因為模型、派工內容、CLI、執行路徑與生成波動都可能影響。
- 舊版允許執行：只支持「執行條件或實際指令有差異」，不能直接認定是 runner 權限漂移。

（2026-09-12 更正：原先提出的「舊版被拒 → 歸因 skill／舊版允許 → 歸因環境」二分判準不成立，已撤回。）

本輪診斷到此結束。

## Batch 23b 暫停（2026-09-13，Owner 決定）

**Owner 決定暫停 Batch 23b。** 未完成的 KI 與發布 gate 維持原狀，以 [`KNOWN-ISSUES.md`](KNOWN-ISSUES.md)
與本檔 current-summary 為準。本段不改動任何 disposition、action status 或 gate。

- **r2 診斷未達標，未採用。** 結案紀錄為 repo 外的 `~/.claude/harness-proposals/20260912-b23b-r1-timeout/CLOSURE-diag-r2.md`。
- **Node 放行提案未採用，付費驗證計畫暫停，不延用任何舊授權。** 提案與選案評估在 repo 外
  `~/.claude/harness-proposals/20260913-exec-verification-env/`（`proposal.md`、`decision.md`）。
  `decision.md` 對現有主機方案的判斷，依據是 CLI binary 字串與原始碼，沒有做行為測試。
  目前的決定是停止投入現提案，不代表已證實所有主機方案都不可行。
- **暫停期間不做：** 補跑、修改停止規則、安裝容器、重寫 runner。
- **恢復前必須全部完成，並取得 Owner 的新授權：**
  1. 選定可接受的驗證環境。
  2. 處理 P4 前提衝突：prompt 宣告無法派發獨立驗收，環境卻仍提供 Agent。
     候選修正 `p4-deny-agent.diff` 在上述提案目錄，尚未套用。
  3. 重新核對受測 identity。
  4. 重新填寫工作單與成本，包含估值、上限與停止條件。
- **舊證據保留在原版本，不重開既有驗收。** 範圍包括 `runs/b23b-J-r1/`、repo 外的 `harness-baselines/` 與 `harness-proposals/`。
  與 Batch 23b 無關的獨立工作可以繼續。
- **暫停不代表可以搬動、刪除或改名凍結檔案，或任何仍被引用的證據。**

## eval 首批目錄整理：自測搬移（2026-09-14，Owner 授權）

**Owner 授權搬移 4 支受歷史契約引用的自測，並接受現行樹與 repo 外 pre-b23b baseline 因此多出對應的路徑差異。**
歷史契約與 repo 外 baseline 都不修改。本段不改動任何 disposition、action status 或 gate，Batch 23b 繼續暫停。
方案見 [`../../../docs/plans/eval-directory-migration.md`](../../../docs/plans/eval-directory-migration.md)。

- **遷移前基準 `C0`：** `f219b121dcb87166a2a374c790ffbf84caa40fc2`，只含 evals README 與遷移方案。
  `C0` 只保存遷移前的已追蹤內容，不保證符合各歷史契約綁定的版本。
- **路徑對照**（`skills/harness/evals/` 下）：

  | 原路徑 | 新路徑 |
  |---|---|
  | `judge_selftest.py` | `selftests/judge_selftest.py` |
  | `score_selftest.py` | `selftests/score_selftest.py` |
  | `record_selftest.py` | `selftests/record_selftest.py` |
  | `transport_selftest.py` | `selftests/transport_selftest.py` |

  本檔較早段落（例如「要接手的話」）裡的舊路徑指令屬於歷史紀錄，不改寫；現行指令見 [`README.md`](README.md)「常用零成本檢查」。
- **`acceptance-r2-regression.py` 留在原位，** 和 `ACCEPTANCE-r2.md` 放在一起，兩者的內容與路徑都不變。
  它在 `C0` 的基線就回傳 FAIL，原因是它硬編了 r2 當時的 `record.py` SHA-256、工作區 34 筆變更、PATH 上的 python3 3.7.9。
  它綁定歷史環境，不列為本批的搬移 gate，本批也不修改、不重跑。
- **既有歷史失配：** `record_selftest.py` 在搬移前就與 round8 契約第 141 行的 SHA-256 不符，不是搬移造成的，`C0` 也無法消除。
