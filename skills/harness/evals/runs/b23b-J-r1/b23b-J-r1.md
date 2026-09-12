# harness run b23b-J-r1

> **本輪不構成契約證據（run_status: INVALID，evidence_class: contract_evidence）。** 28/28 筆未產生可用觀測（CLI 失敗 2）；樣本：judgment__positive-1 — routing=PASS  / contract=NOT_RUN 無 .judge.json；provenance 不成立：post-judge manifest 不存在: post-judge-manifest.json

- 狀態：**INVALID**　證據等級：**contract_evidence**
- Claude Code 版本：2.1.263 (Claude Code)
- 受測 model：sonnet　judge model：sonnet
- 耗時：2286 秒　CLI 失敗：2 筆
- session 數：preflight 1／受測 28／judge 0
- 成本 USD：preflight 0.18078／受測 —／judge 0.0／合計 —　（null 表示該來源未回報，未以推估補完）

## identity hashes（hash_schema v6）

值取自 **run-start 快照**；run-end 已重新量測並比對，任一 domain 不同即整輪 INVALID。

| domain | sha256 | 量測來源 | 變更後作廢 |
|---|---|---|---|
| `dispatch_skill` | `2d6c0d99b1c4ca927e2c06c82e065c389fa6a6b8ddbc325b0e9bde9bc071c4fc` | run-start 快照 | 該 skill 的行為證據 |
| `evaluation_context` | `44abd795f668ee5ff4cb44cbbbf711c1b25e0b699ecd325a672bf80265abe96a` | run-start 快照 | contract 判定（judge model／CLI 版本／flags）；保留的 raw trace 可重新評分 |
| `evaluator` | `481c7dd69570e79ce03b300bfe9f1a2dce65c36fcf54e6bf7744eba7794fdd13` | run-start 快照 | routing／contract 判定；保留的 raw trace 可重新評分 |
| `execution_context` | `e7beb6eded81b04fae8bee2076dec7ceeefc5f55f60980aebd3b7fc4cfb9d4e0` | run-start 快照 | subject 行為證據（規則檔／settings／model／flags／deny list） |
| `fixtures` | `3d225afc58e479eef05efc156d599c94b57684bcd729e754411831889bad3d4f` | run-start 快照 | 對應案例的 observation |
| `judgment_skill` | `93956caa84dc453f34d0f87b674de759b87059608d6d509f2f30d4d48a5f6818` | run-start 快照 | 該 skill 的行為證據 |
| `runner` | `b2b4958ba9aced9828161d7c03990e3aa7eb63706057f06cc2c56610978e04b4` | run-start 快照 | subject trace |
| `token_preflight_skill` | `be72017e9fc7952e9a403cf90e951669496b08f4339938bc73a2829d44ef592a` | run-start 快照 | 該 skill 的行為證據 |

本次 fixtures domain 實際涵蓋的檔案：`skills/discipline/judgment/evals/fixtures.json`、`skills/harness/evals/routing-fixtures.json`、`skills/harness/evals/seed/.gitignore`、`skills/harness/evals/seed/SPEC.md`、`skills/harness/evals/seed/docs/api.md`、`skills/harness/evals/seed/src/api/client.ts`、`skills/harness/evals/seed/src/api/orders.ts`、`skills/harness/evals/seed/src/api/products.ts`、`skills/harness/evals/seed/src/api/users.ts`、`skills/harness/evals/seed/src/hooks/useCart.ts`、`skills/harness/evals/seed/src/utils/date.ts`

### context component hashes

| domain | component | sha256／狀態 |
|---|---|---|
| `evaluation_context` | `descriptor` | `ed90f46556bf2d6e38b89ca27e30b12ddd47dc6100158bc77c547e32ad2e32ba` |
| `execution_context` | `descriptor` | `e378beb1c7982c112a64517c56c3ac5c95a8741068bcb3a44300317a230d5ac5` |
| `execution_context` | `rules` | `165581fbafee0b999c27e5d290a7377c54a36330c337a0ac2acce39ec466836f` |
| `execution_context` | `settings` | `a89ad3df7500f358f5a4f009dd1165bcc0f12316922a2ced6a79f721fb16db04` |

重算方式：`scripts/bundle-hash.sh <mode> <路徑…>`（mode: skill｜evaluator｜runner｜fixtures｜execution-context｜evaluation-context｜schema-version）。
**不同 `hash_schema` 的值不得直接比較。**

## provenance

- run-start 量測：2026-09-11T22:58:06.544430+08:00
- run-end 量測：2026-09-11T23:36:11.356493+08:00
- raw trace manifest：58 個檔案，digest c8536737a2cb，核對通過

- post-judge manifest：0 個檔案，digest —，未通過或缺失

違反項：
- post-judge manifest 不存在: post-judge-manifest.json

## 逐筆判定

| fixture | 類別 | routing | contract | 觸發 | 說明 |
|---|---|---|---|---|---|
| `judgment__positive-1` | positive | PASS | NOT_RUN | judgment | 無 .judge.json |
| `judgment__positive-2` | positive | PASS | NOT_RUN | judgment | 無 .judge.json |
| `judgment__positive-3` | positive | PASS | NOT_RUN | judgment | 無 .judge.json |
| `judgment__positive-4` | positive | ERROR | NOT_RUN | （無） | CLI exit_code=124 |
| `judgment__positive-5` | positive | PASS | NOT_RUN | judgment | 無 .judge.json |
| `judgment__positive-6` | positive | PASS | NOT_RUN | judgment | 無 .judge.json |
| `judgment__negative-1` | negative | PASS | NOT_RUN | （無） | 無 .judge.json |
| `judgment__negative-2` | negative | PASS | NOT_RUN | （無） | 無 .judge.json |
| `judgment__ambiguous-1` | ambiguous | PASS | NOT_RUN | judgment | 無 .judge.json |
| `judgment__ambiguous-2` | ambiguous | PASS | NOT_RUN | judgment | 無 .judge.json |
| `judgment__explicit_mention-1` | explicit_mention | PASS | NOT_RUN | judgment | 無 .judge.json |
| `judgment__explicit_mention-2` | explicit_mention | PASS | NOT_RUN | judgment | 無 .judge.json |
| `judgment__positive-7` | positive | PASS | NOT_RUN | judgment | 無 .judge.json |
| `judgment__positive-8` | positive | PASS | NOT_RUN | judgment | 無 .judge.json |
| `judgment__positive-9` | positive | PASS | NOT_RUN | judgment | 無 .judge.json |
| `judgment__negative-3` | negative | PASS | NOT_RUN | （無） | 無 .judge.json |
| `judgment__ambiguous-3` | ambiguous | PASS | NOT_RUN | judgment | 無 .judge.json |
| `judgment__explicit_mention-3` | explicit_mention | PASS | NOT_RUN | judgment | 無 .judge.json |
| `judgment__positive-10` | positive | PASS | NOT_RUN | judgment | 無 .judge.json |
| `harness-routing__handoff-1` | positive | PASS | NOT_RUN | dispatch | 無 .judge.json |
| `harness-routing__boundary-1` | negative | ERROR | NOT_RUN | （無） | CLI exit_code=124 |
| `harness-routing__boundary-2` | negative | PASS | NOT_RUN | judgment | 無 .judge.json |
| `harness-routing__boundary-3` | negative | PASS | NOT_RUN | judgment | 無 .judge.json |
| `harness-routing__dispatch-absent-1` | positive | PASS | NOT_RUN | （無） | 無 .judge.json |
| `harness-routing__dispatch-absent-2` | negative | PASS | NOT_RUN | （無） | 無 .judge.json |
| `harness-routing__judgment-absent-1` | positive | PASS | NOT_RUN | （無） | 無 .judge.json |
| `harness-routing__agent-unavailable-1` | positive | PASS | NOT_RUN | dispatch | 無 .judge.json |
| `harness-routing__ambiguous-1` | ambiguous | PASS | NOT_RUN | judgment | 無 .judge.json |
