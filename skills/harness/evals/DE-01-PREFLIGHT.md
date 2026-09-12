# DE-01 exact-run preflight — description dilution A/B ＋ KI-07 重跑

**狀態：已全部執行完畢（2026-09-04）**——DE-01 A/B 6 輪 USD 6.2590，
KI-07 `ambiguous-1` continuation 3 輪 USD 0.7817，合計 USD 7.0407 / 63 paid calls。
結果與逐筆判定見
[`DE-01-RESULTS-20260904.md`](DE-01-RESULTS-20260904.md)。
本檔仍只保存執行參數，不含任何觸發率或判定——那些一律落在 results 檔與 run record。
日期：2026-09-04｜HEAD：`b9cb8150a30be2b69b07a615e02f5ed8b9f21d2b`（未 commit）｜hash_schema：v6

**修訂 r3** — r1 有四個會讓這份 preflight 不可執行的錯誤，全部已修：
只設 `HARNESS_FX` 而未覆寫 `HARNESS_RT`，實際每輪會跑 13 筆、6 輪 78 筆；
宣稱可 routing-only，但 `run-suite.sh` 沒有 skip-judge 開關；
判定門檻被改寫成比 governing 協定寬鬆的版本；
縮減集沒有 `ambiguous-1`，卻宣稱能處理 KI-08。

**r3 再修四項**：外層 `for` 迴圈會吞掉中途的閘門失敗，已改為 9 次獨立呼叫
[`de01/run-one.sh`](de01/run-one.sh)；停止條件誤用 `run-suite.sh` 的 exit code，
而 arm B 不觸發（`score.py` rc 1）正是要量的資料，已改依來源 rc 分流；
「同一 cell 補跑 1 次」不可執行，已改為 cell 失敗即該 arm `INVALID`；
固定路徑 `/tmp/de01-armB-backup.SKILL.md` 已移除，arm A 改在 repo 外完整副本執行。

## 1. 這輪回答什麼

| 批次 | 對象 KI | required_action 出處 |
|---|---|---|
| DE-01 A/B | KI-03（`positive-2`）、KI-05（`positive-4`）、KI-14（`positive-1`）、KI-15（`positive-5`） | `KNOWN-ISSUES.md` §DE-01 協定 |
| KI-07 重跑 | KI-07（`ambiguous-1`，`FIX_SKILL`：改完重跑該筆） | `KNOWN-ISSUES.md:42`、`:60` |

**KI-08 不在本輪範圍。** 它是 KI-07 的下游，需要 `ambiguous-1` 在 routing 觸發後的
contract observation。本輪的 KI-07 重跑會**產生**那筆資料，但是否足以裁決 KI-08 要看
routing 是否真的觸發，不能事先承諾。r1 宣稱 12 個 arm-B judge 可處理 KI-08，是錯的——
縮減集裡根本沒有 `ambiguous-1`。

## 2. Arms（已凍結）

| | arm A（pre-bounded） | arm B（現行，DE-01 定稿） |
|---|---|---|
| description 區塊全文 | `f85de9b22643770b3455b83c0d380d8280285d93e2397a853e154b931146a13a` | `f18afdd0c145c5551f77797cff085f238c886654f537659c21d1ffb7ee5eed36` |
| description 純值 | `25120b42861022dc6d65dbbebfec5c1733f278e2a0dfd5088da4466785f7ba8d` | `78acf3135a458cb6c22051d644d94f67be2622197c11ddc97978c1476a3fde2f` |
| SKILL.md 全檔 | `45c7a7c3af9a323661da826c8e503c47bf52ccca71b540cc7a8a89377142576c` | `10a88e48388811d5bc957055ee960ae81b92fecc5bd3faaaeabdadd1ac36439e` |
| `judgment_skill` domain | `6e96c802be26d299a827bd93ed62ca576159444332c1ae641ac547e0ed9208d1` | `a26b436888d81e7181199932590ca29f21e58ff9b8066eb792458e68ed5b3d47` |
| 檔案 | [`de01/armA.SKILL.md`](de01/armA.SKILL.md) | `skills/discipline/judgment/SKILL.md`（原地） |

**arm A 為何重新合成。**
[`runs/20260901-batch11-ab-old-desc/inputs/old-description.SKILL.md`](runs/20260901-batch11-ab-old-desc/inputs/old-description.SKILL.md)
（`4f465d66…`）的 body 停在 batch-11，之後現行版多了「有界複查」整節與 KI-09 規則。
協定第 1 條要求兩 arm 只差 description，直接沿用會同時改動 body。
`de01/armA.SKILL.md` ＝ 現行 body ＋ 該檔 description 區塊，已機械核對。

## 3. 凍結輸入檔

| 檔案 | SHA-256 | 內容 |
|---|---|---|
| [`de01/fixtures.json`](de01/fixtures.json) | `cc323cfdbd3279ad2f46fcf6ff1588707dc8208f025f1c59f1b5ac2c13c26f1c` | DE-01 四筆 |
| [`de01/ki07-fixtures.json`](de01/ki07-fixtures.json) | `c3f7cba76cd66d38af9deb18490660613e0b0b3ee54c6eb45f046ba51e0612d2` | `ambiguous-1` 一筆 |
| [`de01/routing-empty.json`](de01/routing-empty.json) | `e0208630a0a3105046e8c2dbc59e3fedac3d8759d3bd3adf0e0c7d05cc5fb642` | routing suite 停用（`fixtures: []`） |
| [`de01/armA.SKILL.md`](de01/armA.SKILL.md) | `45c7a7c3af9a323661da826c8e503c47bf52ccca71b540cc7a8a89377142576c` | arm A 變體 |

**`routing-empty.json` 存在的唯一理由：** `run-suite.sh:18` 的 `HARNESS_RT` 預設是
`routing-fixtures.json`（9 筆）。r1 只覆寫 `HARNESS_FX`，於是每輪實跑 4＋9 ＝ **13 筆**，
6 輪 78 筆——是預算的三倍多。覆寫 `HARNESS_RT` 後 dry-run 實測每輪 **4 筆**。

四筆／一筆的內容逐字取自現行 `skills/discipline/judgment/evals/fixtures.json`，
`schema_version` 均為 `2.1`。**這是縮減集：絕對觸發率不得與 batch-12 全套（28 筆）比較**，
唯一有效比較是同一輪內 arm A vs arm B。

## 4. 跨 arm 必須逐 hash 相同的 domain

| domain | DE-01 綁定值 |
|---|---|
| `evaluator` | `65bc6c07d058697cda34045637d3223568cf09626cc38b8385bac46d41157480` |
| `runner` | `005ed2f71ac49a8b6747dd1c43f42c8ee67315a9fb3ec8ce395f921ccf6cee3c` |
| `rescore_runner` | `2301a9daa8d90536e31b64f571767307e27a541fc369920bd882960354660b28` |
| `dispatch_skill` | `2d6c0d99b1c4ca927e2c06c82e065c389fa6a6b8ddbc325b0e9bde9bc071c4fc` |
| `token_preflight_skill` | `be72017e9fc7952e9a403cf90e951669496b08f4339938bc73a2829d44ef592a` |
| `fixtures`（DE-01 批次） | `7a1b54c1eddf710e030323ab6124e525d983ef5b32a1316d1780dd12d08d4738` |
| `fixtures`（KI-07 批次） | `dbbb4786db55bf8f568a5071f013072edb68d78273474ee49744a1654639656a` |
| `execution-context` | 兩 arm 同 model（`sonnet`）、同 deny list、同 rules；以 `run-fixture.sh --print-context` 為單一來源 |

**唯一允許不同的是 `judgment_skill`。** 出現第二個 drift，該輪作廢。
DE-01 與 KI-07 是兩個不同的 `fixtures` domain，**不得跨批次比較觸發率**。

## 5. 執行控制（F18 r3）

**不使用外層 `for` 迴圈。** 迴圈會讓中間某輪的閘門失敗被後續輪次蓋掉，錢繼續花。
每一次 paid run 由 [`de01/run-one.sh`](de01/run-one.sh) 單獨啟動，事前事後各一組閘門，
任一不過即 `exit 9`，呼叫端停止後續 paid run。

### 5.1 為什麼不能用 `run-suite.sh` 的 exit code 當停止條件

`score.py:171-172` 的離開碼有三種語意：

| rc | 意義 | 對 DE-01 |
|---|---|---|
| 0 | 全部 fixture routing PASS | 可用觀測 |
| 1 | 觀測全部可用，但有 fixture 未觸發 | **這是資料，不是失敗** |
| 2 | 有 `ERROR`／`NOT_RUN`，未產生可用觀測 | 失敗，停止 |

`run-suite.sh` 把 rc 1 併進 `SUITE_RC=1`。**DE-01 量的就是「arm B 是否不觸發」**，
若以 `SUITE_RC != 0` 當停止條件，第一輪 arm B 就會中止整個 A/B——錢花了卻拿不到對照組。
`run-one.sh` 因此改依來源 rc 分流，並另外檢查 `run_status`。

### 5.2 閘門

事前：launch deadline 未到、累計成本低於 launch cutoff、fixtures 檔存在、
**run id 未被使用過**（拒絕覆寫）、`judgment_skill` domain 等於本輪預期的 arm。
事後：CLI 失敗數 ＝ 0、routing rc ≠ 2、record rc ＝ 0、`run_status` ∈ {`PASS`,`FAIL`}
（`INVALID` 即停）、record 內 `evaluator`／`runner`／`dispatch_skill`／
`token_preflight_skill`／`judgment_skill` 與預期逐一相同、成本寫入 repo 外帳本。

### 5.3 cell 失敗即整個 arm INVALID，本輪不補跑

r2 寫「同一 cell 最多補跑 1 次」是不可執行的：`run-suite.sh` 以 run id 建目錄且拒絕覆寫，
補跑必然產生新 run id 與新 run record，`score.py` 沒有 per-fixture 重試入口。
**最小安全修法：任一 cell 失敗即該 arm 記 `INVALID`，本輪不補跑、不下 DE-01 結論。**

### 5.4 arm 切換：不原地 swap

arm A **在 repo 外的完整副本執行**，真實 working tree 全程不動：

```
SRC=/Users/tinywu/Desktop/Apps/tiny-agents-skills
COPY=$(mktemp -d "${TMPDIR:-/tmp}/de01-armA.XXXXXX")
cp -R "$SRC"/. "$COPY"/
cp "$SRC/skills/harness/evals/de01/armA.SKILL.md" "$COPY/skills/discipline/judgment/SKILL.md"
sh "$COPY/scripts/bundle-hash.sh" skill "$COPY/skills/discipline/judgment"   # 必須 6e96c802…
shasum -a 256 "$SRC/skills/discipline/judgment/SKILL.md"                     # 仍須 10a88e48…
```

跑完把 arm A 的 run 目錄複製回 `$SRC` 的 `runs/`，再刪除 `$COPY`。
**沒有原地 swap，就沒有還原失敗的風險**；固定路徑 `/tmp/de01-armB-backup.SKILL.md`
（r2 的做法，會被並行執行或殘留檔互相覆蓋）已移除。

若因故必須原地 swap，備份檔一律 `mktemp` 產生唯一路徑，並在 swap 前安裝
`trap 'cp "$BAK" "$SRC/skills/discipline/judgment/SKILL.md"' EXIT INT TERM`，
還原後強制核對 `10a88e48…`／`a26b4368…`，不符即中止全部後續動作。

### 5.5 執行序列（逐次下指令，共 9 次 paid run）

```
export DE01_LEDGER=<repo 外帳本路徑>
export DE01_LAUNCH_DEADLINE=<epoch 秒：開始後 80 分鐘>
export DE01_LAUNCH_CUTOFF_USD=6.00
R=skills/harness/evals/de01/run-one.sh
B=a26b436888d81e7181199932590ca29f21e58ff9b8066eb792458e68ed5b3d47
A=6e96c802be26d299a827bd93ed62ca576159444332c1ae641ac547e0ed9208d1
```

| # | 指令 | 批次 |
|---|---|---|
| 1–3 | `sh $R de01-armB-r{1,2,3} de01/fixtures.json $B` | DE-01 arm B |
| 4–6 | `sh $R ki07-armB-r{1,2,3} de01/ki07-fixtures.json $B` | KI-07 arm B |
| — | 5.4 的 repo 外副本切換 | — |
| 7–9 | `sh $R de01-armA-r{1,2,3} de01/fixtures.json $A`（在副本內） | DE-01 arm A |

`{1,2,3}` 是**三次獨立指令**的簡寫，不是迴圈。每次跑完必須先看閘門輸出再下一次。

## 6. 判定門檻（照抄 governing 協定，不得改寫）

`KNOWN-ISSUES.md:104–113`，逐字適用：

1. 兩個 arm 只差 description，其餘 domain 逐 hash 相同。
2. 每個 arm 對每筆 fixture 跑 **3 次**，記錄 routing 觸發次數（0–3）。
3. **判定門檻：同一筆 fixture 在 arm A 至少 2/3 觸發、arm B 至多 1/3 觸發**，
   才支持 `description_dilution`；否則該筆改判 `stochastic_known_issue` 或 `skill_defect`。
4. **單次 observation 不成立。**
5. **任一筆的證據不得外推到另一筆**——逐筆獨立判定、逐筆改判。

KI-07 只回報 `ambiguous-1` 在 arm B 的三次 routing／contract observation，
**不與 DE-01 四筆比較**（不同 `fixtures` domain）。

## 7. 成本

**63 paid sessions ＝ 27 subject ＋ 9 preflight ＋ 27 judge。**

| 項目 | 筆數 | 期望值 | 以歷史最大值計 |
|---|---|---|---|
| DE-01 subject | 24 | $1.85 | $2.75 |
| KI-07 subject | 3 | $0.12 | $0.15 |
| preflight（每次 `run-suite.sh` 呼叫 1 筆，`run-suite.sh:316`） | 9 | $0.41 | $0.70 |
| DE-01 judge | 24 | $1.77 | $2.15 |
| KI-07 judge | 3 | $0.24 | $0.38 |
| **合計** | **63** | **$4.39** | **$6.13** |

單價樣本：subject 148 筆、judge 140 筆取自 `runs/2026090*`；
**preflight 13 筆取自 `runs/*`，其中 3 筆來自 2026-08**
（`20260829-225157-9d`、`20260830-000907-9e`、`20260830-032007-full`），
不能寫成全部來自 `runs/2026090*`。

### 預算 enforcement

執行環境**沒有可機械 enforce 的 provider／CLI budget cap**（`claude` CLI 無 per-call
預算旗標）。因此 USD 7.50 是 **stop threshold，不是 hard cap**：

- **launch cutoff USD 6.00** — 累計達此值後 `run-one.sh` 的事前閘門拒絕啟動新的 paid call。
- **保留 USD 1.50** 給啟動當下正在執行的那一次呼叫（單次歷史最大約 $0.45）。
- 帳本置於 repo 外，每次 run 後由 `run-one.sh` 寫入實際 `cost.total_usd`。

## 8. 停止條件

1. 累計成本達 **USD 6.00** → 不再啟動 paid call（事前閘門機械執行）。
2. 任一閘門失敗（`run-one.sh` exit 9）→ 停止後續 paid run；該 arm 記 `INVALID`，不補跑。
3. `run_status` `INVALID`、trace／manifest 缺失、record rc ≠ 0 → 停。
4. 第 4 節以外的 domain drift → 該輪作廢，停。
5. **開始後第 80 分鐘起不得啟動新的 paid session**（`DE01_LAUNCH_DEADLINE`）。
6. 剩餘時間不足完成下一個 suite → 不啟動。
7. 資料不完整時保留已完成的有效 run，**不得下 DE-01 結論**。
8. 本輪不得更新 `KNOWN-ISSUES.md` 的 disposition 或發布 gate；結果只落成 run record。
