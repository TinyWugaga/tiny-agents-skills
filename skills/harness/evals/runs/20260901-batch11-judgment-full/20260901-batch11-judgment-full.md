# harness run 20260901-batch11-judgment-full

> **本輪不構成契約證據（run_status: INVALID）。** 1/27 筆未產生可用觀測（CLI 失敗 0）；樣本：harness-routing__boundary-1 — routing=PASS  / contract=ERROR judge 判定非合法 JSON: Extra data: line 3 column 1 (char 639)

- 狀態：**INVALID**
- Claude Code 版本：2.1.247 (Claude Code)
- 受測 model：sonnet　judge model：sonnet
- 耗時：2116 秒　CLI 失敗：0 筆
- session 數：preflight 1／受測 27／judge 27
- 成本 USD：preflight 0.07184／受測 2.5253／judge —／合計 —　（null 表示該來源未回報，未以推估補完）

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
| `judgment__positive-1` | positive | FAIL | PASS | （無） | judgment: 預期觸發，實際未觸發 |
| `judgment__positive-2` | positive | FAIL | FAIL | （無） | judgment: 預期觸發，實際未觸發 |
| `judgment__positive-3` | positive | PASS | FAIL | judgment |  |
| `judgment__positive-4` | positive | FAIL | FAIL | （無） | judgment: 預期觸發，實際未觸發 |
| `judgment__positive-5` | positive | FAIL | PASS | （無） | judgment: 預期觸發，實際未觸發 |
| `judgment__positive-6` | positive | PASS | PASS | judgment |  |
| `judgment__negative-1` | negative | PASS | FAIL | （無） |  |
| `judgment__negative-2` | negative | PASS | PASS | （無） |  |
| `judgment__ambiguous-1` | ambiguous | FAIL | FAIL | （無） | judgment: 預期觸發，實際未觸發 |
| `judgment__ambiguous-2` | ambiguous | FAIL | FAIL | （無） | judgment: 預期觸發，實際未觸發 |
| `judgment__explicit_mention-1` | explicit_mention | PASS | PASS | judgment |  |
| `judgment__explicit_mention-2` | explicit_mention | PASS | FAIL | judgment |  |
| `judgment__positive-7` | positive | PASS | PASS | judgment |  |
| `judgment__positive-8` | positive | PASS | PASS | judgment |  |
| `judgment__positive-9` | positive | PASS | PASS | judgment |  |
| `judgment__negative-3` | negative | PASS | PASS | （無） |  |
| `judgment__ambiguous-3` | ambiguous | FAIL | PASS | （無） | judgment: 預期觸發，實際未觸發 |
| `judgment__explicit_mention-3` | explicit_mention | PASS | FAIL | judgment |  |
| `harness-routing__handoff-1` | positive | PASS | FAIL | dispatch |  |
| `harness-routing__boundary-1` | negative | PASS | ERROR | judgment | judge 判定非合法 JSON: Extra data: line 3 column 1 (char 639) |
| `harness-routing__boundary-2` | negative | PASS | PASS | judgment |  |
| `harness-routing__boundary-3` | negative | FAIL | FAIL | （無） | judgment: 預期觸發，實際未觸發 |
| `harness-routing__dispatch-absent-1` | positive | PASS | PASS | （無） | （另有失敗的 Skill 呼叫，不計入觸發: dispatch） |
| `harness-routing__dispatch-absent-2` | negative | PASS | PASS | （無） |  |
| `harness-routing__judgment-absent-1` | positive | PASS | PASS | （無） |  |
| `harness-routing__agent-unavailable-1` | positive | PASS | FAIL | dispatch |  |
| `harness-routing__ambiguous-1` | ambiguous | PASS | PASS | judgment |  |
