# harness evals — 現況

**Batch 6（run record）狀態：STOPPED / NOT COMPLETE。不是 PASS。**
不補跑 Batch 6 的完整 suite；後續縮減重跑另立 batch 與 run record，不覆寫既有紀錄。

## 基礎設施：已驗證可用

host OAuth + plugin 隔離 + preflight + runner + score + judge + record 全鏈路在 host 端實跑通過。
機制說明見 [`../README.md`](../README.md) 的「執行機制」章節。

`run-suite.sh` 現在會依 fixtures JSON 依序執行 **18 筆**（`dispatch` 9 + `harness-routing` 9），
prompt 的唯一來源是那兩個 JSON，腳本內不含任何 prompt 字面。

## 執行紀錄

| run | 位置 | 結論 |
|---|---|---|
| `20260826-151927-bbbb34` | repo 內 | **SUPERSEDED**。harness 有 fail-open 缺陷，不作為憑據。其記錄的 bundle hash 於 Batch 2 改用 allowlist 後全部失效 |
| `20260827-191514-fdb1fd` | repo 內 | **INVALID**。host 登入過期，18 筆全部在推論前 `authentication_failed`，routing/contract ERROR 18/18 |
| `20260827-193053-a2b802` | repo 內 | **INVALID**。登入正常，但當時的 `CLAUDE_CONFIG_DIR` 隔離連帶隱藏 host OAuth；subject ERROR 18/18、judge 在 3 筆後人工中止（白花 USD 0.144） |
| `20260829-152748-9c` | repo 內 | **FAIL（有效證據）**。2 筆 CLI 全成功；routing PASS 1 / FAIL 1、contract PASS 2 / FAIL 0、cost USD 0.4074 |
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
本輪依決策接受 FAIL，不修改 fixture、scorer 或 runner。

真實 trace 首次覆蓋 9a 的非 null 分支：12 個 child assistant 事件共用 Agent tool-use id 作為
`parent_tool_use_id`，包含 Bash 與 Read；post-9a judge 排除這些 child 事件，同時保留主執行緒的
Agent 派工證據，`dispatch-absent-1` contract 因而 PASS。repo 內只保存 `.json`／`.md` run record，
raw trace 留在 repo 外暫存目錄。

成本（observation，metric=Claude Code session 自報 cost，unit=USD）：preflight 0.063963、
subject 0.2408、judge 0.1026、合計 0.4074，低於本輪 target USD 0.55。
hash：`dispatch_bundle 6c9d922dcdac30fa500201504de58d030dc35d7522db802be06756409e7e2149`；
`harness_test_suite 0233336ec3091d99fd6206ee9f1579e92cedb087bfa19716aeb292bfbbf13219`。

## 成本

以下皆為 **proxy，不是 specification**，且量測條件不同不可混用：

| 來源 | 觀測 | 適用限制 |
|---|---|---|
| `batch6-5-regression-001` | 每筆 fixture（subject+judge）≈ USD 0.115；preflight ≈ USD 0.074 | 目前最接近現行 harness 的基準 |
| `20260826-151927-bbbb34` | 17 sessions 合計 USD 2.7372 | 該輪 `Edit/Write/Bash/Agent/WebFetch/WebSearch` 全擋，工具開放度與現行不同，metric 不完全可比 |

由此外推完整一輪（preflight + 18 subject + 18 judge）≈ **USD 2.1**，屬 estimate。
`positive-1` 是掃 repo 的重筆，實際值可能高於此。**總成本在完整跑完之前無法可靠判定。**

## 要接手的話

```sh
skills/harness/evals/run-suite.sh
```

前置條件（缺任一項 runner 會印出缺什麼並 `exit 2`）：`python3`、`git`、`openssl`、`claude`、
`~/.claude/CLAUDE.md`（規則檔來源）、`~/.claude/skills/{dispatch,judgment,token-preflight}`。

先跑縮減版：`HARNESS_FX` / `HARNESS_RT` 指向精簡後的 fixtures，`HARNESS_RUNS_DIR` 導到 repo 外，
即可只跑一兩筆而不在 `runs/` 留下紀錄。`--dry-run` 只印出將執行的每筆
`(id, config, model, deny_extra, prompt)`，不起任何 session。

## 已知殘留風險

- `run-fixture.sh` 開放 Bash（掃描類 fixture 需要它做機械計數）。破壞性指令已用
  `Bash(rm:*)` 等 pattern 封鎖，但那是 prefix match，擋不住 `cd x && rm -rf y` 這類複合指令。
  session 的 cwd 是 `mktemp` 的拋棄式副本，影響面有限，但殘留風險不是零。
- plugin skill 與 user-level skill 的觸發傾向是否等價，未實測。
- 規則檔以單檔複製注入，若 `~/.claude/CLAUDE.md` 內有 `@import`，那些相對匯入可能失效。
