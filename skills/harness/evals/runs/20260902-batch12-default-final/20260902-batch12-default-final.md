# harness run 20260902-batch12-default-final

> **本輪不構成契約證據（run_status: INVALID）。** 1/18 筆未產生可用觀測（CLI 失敗 0）；樣本：dispatch__negative-2 — routing=PASS  / contract=ERROR judge 判定非合法 JSON: Extra data: line 3 column 1 (char 417)

- 狀態：**INVALID**
- Claude Code 版本：2.1.247 (Claude Code)
- 受測 model：sonnet　judge model：sonnet
- 耗時：1281 秒　CLI 失敗：0 筆
- session 數：preflight 1／受測 18／judge 18
- 成本 USD：preflight 0.0467665／受測 1.3632／judge —／合計 —　（null 表示該來源未回報，未以推估補完）

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
| `dispatch__positive-1` | positive | PASS | PASS | dispatch |  |
| `dispatch__positive-2` | positive | PASS | PASS | dispatch |  |
| `dispatch__positive-3` | positive | PASS | PASS | dispatch |  |
| `dispatch__positive-4` | positive | PASS | PASS | dispatch |  |
| `dispatch__negative-1` | negative | PASS | PASS | （無） |  |
| `dispatch__negative-2` | negative | PASS | ERROR | judgment | judge 判定非合法 JSON: Extra data: line 3 column 1 (char 417) |
| `dispatch__negative-3` | negative | PASS | PASS | （無） |  |
| `dispatch__ambiguous-1` | ambiguous | FAIL | FAIL | （無） | dispatch: 預期觸發，實際未觸發 |
| `dispatch__explicit-mention-1` | explicit_mention | PASS | FAIL | dispatch |  |
| `harness-routing__handoff-1` | positive | PASS | FAIL | dispatch |  |
| `harness-routing__boundary-1` | negative | PASS | PASS | judgment |  |
| `harness-routing__boundary-2` | negative | PASS | PASS | judgment |  |
| `harness-routing__boundary-3` | negative | FAIL | PASS | （無） | judgment: 預期觸發，實際未觸發 |
| `harness-routing__dispatch-absent-1` | positive | PASS | PASS | （無） | （另有失敗的 Skill 呼叫，不計入觸發: dispatch） |
| `harness-routing__dispatch-absent-2` | negative | PASS | PASS | （無） |  |
| `harness-routing__judgment-absent-1` | positive | PASS | PASS | （無） |  |
| `harness-routing__agent-unavailable-1` | positive | PASS | FAIL | dispatch |  |
| `harness-routing__ambiguous-1` | ambiguous | PASS | PASS | judgment |  |
