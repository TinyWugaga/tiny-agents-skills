# harness run 20260901-batch12-judgment-final

- 狀態：**FAIL**
- Claude Code 版本：2.1.247 (Claude Code)
- 受測 model：sonnet　judge model：sonnet
- 耗時：2292 秒　CLI 失敗：0 筆
- session 數：preflight 1／受測 28／judge 28
- 成本 USD：preflight 0.04349479999999999／受測 3.6412／judge 1.9665／合計 5.6512　（null 表示該來源未回報，未以推估補完）

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
| `judgment__positive-1` | positive | FAIL | PASS | （無） | judgment: 預期觸發，實際未觸發 |
| `judgment__positive-2` | positive | FAIL | FAIL | （無） | judgment: 預期觸發，實際未觸發 |
| `judgment__positive-3` | positive | PASS | PASS | judgment |  |
| `judgment__positive-4` | positive | FAIL | FAIL | （無） | judgment: 預期觸發，實際未觸發 |
| `judgment__positive-5` | positive | FAIL | PASS | （無） | judgment: 預期觸發，實際未觸發 |
| `judgment__positive-6` | positive | PASS | PASS | judgment |  |
| `judgment__negative-1` | negative | PASS | FAIL | （無） |  |
| `judgment__negative-2` | negative | PASS | PASS | （無） |  |
| `judgment__ambiguous-1` | ambiguous | FAIL | FAIL | （無） | judgment: 預期觸發，實際未觸發 |
| `judgment__ambiguous-2` | ambiguous | PASS | FAIL | judgment |  |
| `judgment__explicit_mention-1` | explicit_mention | PASS | PASS | judgment |  |
| `judgment__explicit_mention-2` | explicit_mention | PASS | FAIL | judgment |  |
| `judgment__positive-7` | positive | PASS | PASS | judgment |  |
| `judgment__positive-8` | positive | PASS | PASS | judgment |  |
| `judgment__positive-9` | positive | PASS | FAIL | judgment |  |
| `judgment__negative-3` | negative | PASS | PASS | （無） |  |
| `judgment__ambiguous-3` | ambiguous | FAIL | PASS | （無） | judgment: 預期觸發，實際未觸發 |
| `judgment__explicit_mention-3` | explicit_mention | PASS | FAIL | judgment |  |
| `judgment__positive-10` | positive | PASS | PASS | judgment |  |
| `harness-routing__handoff-1` | positive | PASS | FAIL | dispatch |  |
| `harness-routing__boundary-1` | negative | PASS | PASS | judgment |  |
| `harness-routing__boundary-2` | negative | FAIL | FAIL | dispatch | judgment: 預期觸發，實際未觸發; dispatch: 預期不觸發，實際觸發 |
| `harness-routing__boundary-3` | negative | PASS | PASS | judgment |  |
| `harness-routing__dispatch-absent-1` | positive | PASS | PASS | （無） | （另有失敗的 Skill 呼叫，不計入觸發: dispatch） |
| `harness-routing__dispatch-absent-2` | negative | PASS | PASS | （無） |  |
| `harness-routing__judgment-absent-1` | positive | PASS | FAIL | （無） | （另有失敗的 Skill 呼叫，不計入觸發: judgment） |
| `harness-routing__agent-unavailable-1` | positive | PASS | FAIL | dispatch |  |
| `harness-routing__ambiguous-1` | ambiguous | PASS | PASS | judgment |  |
