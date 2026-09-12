# harness run 20260901-batch11-default-regression

- 狀態：**FAIL**
- Claude Code 版本：2.1.247 (Claude Code)
- 受測 model：sonnet　judge model：sonnet
- 耗時：103 秒　CLI 失敗：0 筆
- session 數：preflight 1／受測 2／judge 2
- 成本 USD：preflight 0.0435128／受測 0.1003／judge 0.1377／合計 0.2815　（null 表示該來源未回報，未以推估補完）

## bundle hashes

| bundle | sha256 |
|---|---|
| `dispatch_bundle` | `fd139f25b7e5745df7c5ab6aa1d20629e40edcb8a807f5277c11acf433eddcae` |
| `judgment_bundle` | `00ebf628116c7d8339d0d540e094d0754f97c45a36c68213c3f0b69161fa2652` |
| `token_preflight_bundle` | `a705ca101d56f27a6ff7addc66eb6fa80375a4e6b85286422fca8463e4982de1` |
| `harness_test_suite` | `bac3abd9efa7a1bb3dbcd233e608aedd3b4a185f096064589966c4fa0f46de2c` |

重算方式：`skills/harness/dispatch/scripts/bundle-hash.sh <目錄> [skill|suite]`

## 逐筆判定

| fixture | 類別 | routing | contract | 觸發 | 說明 |
|---|---|---|---|---|---|
| `dispatch__positive-4` | positive | FAIL | FAIL | （無） | dispatch: 預期觸發，實際未觸發 |
| `dispatch__negative-3` | negative | PASS | FAIL | （無） |  |
