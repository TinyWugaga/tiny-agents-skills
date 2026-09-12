# harness run 20260901-batch12-positive4-contract-correction

- 狀態：**PASS**
- Claude Code 版本：2.1.247 (Claude Code)
- 受測 model：sonnet　judge model：sonnet
- 耗時：64 秒　CLI 失敗：0 筆
- session 數：preflight 1／受測 1／judge 1
- 成本 USD：preflight 0.0435218／受測 0.0827／judge 0.0721／合計 0.1983　（null 表示該來源未回報，未以推估補完）

## bundle hashes

| bundle | sha256 |
|---|---|
| `dispatch_bundle` | `2cf168c664e9fb3569c0b184f885a7c7fe6025d8836f7e4c46c6cf4fd0e0edd6` |
| `judgment_bundle` | `00ebf628116c7d8339d0d540e094d0754f97c45a36c68213c3f0b69161fa2652` |
| `token_preflight_bundle` | `a705ca101d56f27a6ff7addc66eb6fa80375a4e6b85286422fca8463e4982de1` |
| `harness_test_suite` | `bac3abd9efa7a1bb3dbcd233e608aedd3b4a185f096064589966c4fa0f46de2c` |

重算方式：`skills/harness/dispatch/scripts/bundle-hash.sh <目錄> [skill|suite]`

## 逐筆判定

| fixture | 類別 | routing | contract | 觸發 | 說明 |
|---|---|---|---|---|---|
| `dispatch__positive-4` | positive | PASS | PASS | dispatch |  |
