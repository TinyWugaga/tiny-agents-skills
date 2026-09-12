# harness run de01-armA-r3

- 狀態：**FAIL**　證據等級：**contract_evidence**
- Claude Code 版本：2.1.247 (Claude Code)
- 受測 model：sonnet　judge model：sonnet
- 耗時：390 秒　CLI 失敗：0 筆
- session 數：preflight 1／受測 4／judge 4
- 成本 USD：preflight 0.045885999999999996／受測 0.4988／judge 0.3564／合計 0.9011　（null 表示該來源未回報，未以推估補完）

## identity hashes（hash_schema v6）

值取自 **run-start 快照**；run-end 已重新量測並比對，任一 domain 不同即整輪 INVALID。

| domain | sha256 | 量測來源 | 變更後作廢 |
|---|---|---|---|
| `dispatch_skill` | `2d6c0d99b1c4ca927e2c06c82e065c389fa6a6b8ddbc325b0e9bde9bc071c4fc` | run-start 快照 | 該 skill 的行為證據 |
| `evaluation_context` | `64996161082a8b43374e911c1b5e1d2c4ba36333cd324c53cfc37caecdc2b33c` | run-start 快照 | contract 判定（judge model／CLI 版本／flags）；保留的 raw trace 可重新評分 |
| `evaluator` | `65bc6c07d058697cda34045637d3223568cf09626cc38b8385bac46d41157480` | run-start 快照 | routing／contract 判定；保留的 raw trace 可重新評分 |
| `execution_context` | `e7beb6eded81b04fae8bee2076dec7ceeefc5f55f60980aebd3b7fc4cfb9d4e0` | run-start 快照 | subject 行為證據（規則檔／settings／model／flags／deny list） |
| `fixtures` | `7a1b54c1eddf710e030323ab6124e525d983ef5b32a1316d1780dd12d08d4738` | run-start 快照 | 對應案例的 observation |
| `judgment_skill` | `6e96c802be26d299a827bd93ed62ca576159444332c1ae641ac547e0ed9208d1` | run-start 快照 | 該 skill 的行為證據 |
| `runner` | `005ed2f71ac49a8b6747dd1c43f42c8ee67315a9fb3ec8ce395f921ccf6cee3c` | run-start 快照 | subject trace |
| `token_preflight_skill` | `be72017e9fc7952e9a403cf90e951669496b08f4339938bc73a2829d44ef592a` | run-start 快照 | 該 skill 的行為證據 |

本次 fixtures domain 實際涵蓋的檔案：`skills/harness/evals/de01/fixtures.json`、`skills/harness/evals/de01/routing-empty.json`、`skills/harness/evals/seed/.gitignore`、`skills/harness/evals/seed/SPEC.md`、`skills/harness/evals/seed/docs/api.md`、`skills/harness/evals/seed/src/api/client.ts`、`skills/harness/evals/seed/src/api/orders.ts`、`skills/harness/evals/seed/src/api/products.ts`、`skills/harness/evals/seed/src/api/users.ts`、`skills/harness/evals/seed/src/hooks/useCart.ts`、`skills/harness/evals/seed/src/utils/date.ts`

重算方式：`scripts/bundle-hash.sh <mode> <路徑…>`（mode: skill｜evaluator｜runner｜fixtures｜execution-context｜evaluation-context｜schema-version）。
**不同 `hash_schema` 的值不得直接比較。**

## provenance

- run-start 量測：2026-09-04T13:22:57.187368+08:00
- run-end 量測：2026-09-04T13:29:25.258350+08:00
- raw trace manifest：10 個檔案，digest e2511e23fa3e，核對通過

## 逐筆判定

| fixture | 類別 | routing | contract | 觸發 | 說明 |
|---|---|---|---|---|---|
| `judgment__positive-1` | positive | FAIL | PASS | （無） | judgment: 預期觸發，實際未觸發 |
| `judgment__positive-2` | positive | PASS | FAIL | judgment |  |
| `judgment__positive-4` | positive | PASS | FAIL | judgment |  |
| `judgment__positive-5` | positive | FAIL | PASS | （無） | judgment: 預期觸發，實際未觸發 |
