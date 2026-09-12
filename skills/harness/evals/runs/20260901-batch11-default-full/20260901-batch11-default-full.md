# harness run 20260901-batch11-default-full

- 狀態：**FAIL**
- Claude Code 版本：2.1.247 (Claude Code)
- 受測 model：sonnet　judge model：sonnet
- 耗時：1223 秒　CLI 失敗：0 筆
- session 數：preflight 1／受測 18／judge 18
- 成本 USD：preflight 0.0465458／受測 1.5619／judge 1.1642／合計 2.7726　（null 表示該來源未回報，未以推估補完）

## bundle hashes

| bundle | sha256 |
|---|---|
| `dispatch_bundle` | `fd139f25b7e5745df7c5ab6aa1d20629e40edcb8a807f5277c11acf433eddcae` |
| `judgment_bundle` | `3f4e14ce80719396f1d5e21aeb8e95276db06694a428fc4225b98c7fc0cb871e` |
| `token_preflight_bundle` | `a705ca101d56f27a6ff7addc66eb6fa80375a4e6b85286422fca8463e4982de1` |
| `harness_test_suite` | `bac3abd9efa7a1bb3dbcd233e608aedd3b4a185f096064589966c4fa0f46de2c` |

重算方式：`skills/harness/dispatch/scripts/bundle-hash.sh <目錄> [skill|suite]`

## 逐筆判定

| fixture | 類別 | routing | contract | 觸發 | 說明 |
|---|---|---|---|---|---|
| `dispatch__positive-1` | positive | PASS | PASS | dispatch |  |
| `dispatch__positive-2` | positive | PASS | PASS | dispatch |  |
| `dispatch__positive-3` | positive | PASS | PASS | dispatch |  |
| `dispatch__positive-4` | positive | PASS | PASS | dispatch |  |
| `dispatch__negative-1` | negative | PASS | PASS | （無） |  |
| `dispatch__negative-2` | negative | PASS | PASS | judgment |  |
| `dispatch__negative-3` | negative | PASS | PASS | （無） |  |
| `dispatch__ambiguous-1` | ambiguous | FAIL | FAIL | （無） | dispatch: 預期觸發，實際未觸發 |
| `dispatch__explicit-mention-1` | explicit_mention | PASS | FAIL | dispatch |  |
| `harness-routing__handoff-1` | positive | PASS | FAIL | dispatch |  |
| `harness-routing__boundary-1` | negative | PASS | PASS | judgment |  |
| `harness-routing__boundary-2` | negative | PASS | PASS | judgment |  |
| `harness-routing__boundary-3` | negative | FAIL | FAIL | （無） | judgment: 預期觸發，實際未觸發 |
| `harness-routing__dispatch-absent-1` | positive | PASS | PASS | （無） | （另有失敗的 Skill 呼叫，不計入觸發: dispatch） |
| `harness-routing__dispatch-absent-2` | negative | PASS | PASS | （無） |  |
| `harness-routing__judgment-absent-1` | positive | PASS | PASS | （無） | （另有失敗的 Skill 呼叫，不計入觸發: judgment） |
| `harness-routing__agent-unavailable-1` | positive | PASS | FAIL | dispatch |  |
| `harness-routing__ambiguous-1` | ambiguous | PASS | PASS | judgment |  |
