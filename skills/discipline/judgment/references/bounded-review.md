# 有界複查

同一產出物需要第二意見、跨模型複查，或已進入 finding → 修正 → closure 流程時適用。本檔是主對話
（Owner）的 orchestration 契約：規定 cycle 怎麼開始、怎麼裁決、怎麼結束。

驗收者收到材料後的逐條判定規則在 [`verifier.md`](verifier.md)，本檔不重複。單次 fresh-context
驗收只需要 `verifier.md`；本檔只在需要多方複查或跨輪 closure 時載入。

## 適用與不適用

適用：兩個以上 reviewer（不同模型、不同 session 或不同人）對同一產出物提意見；複查已來回兩輪
以上仍未收斂；修正後需要確認原 findings 是否關閉。

不適用：一次性的 code review 或文件審閱；沒有待驗產出物的「再找個模型看看」；單一 reviewer
的單次驗收。

## 為什麼需要邊界

reviewer 在開放式指令下永遠交得出新意見，因此「雙方都想不到更多問題」不是可達成的停止條件。
唯一可達成的停止條件是「凍結基準下沒有未關閉的 accepted_blocking finding」。

擴張的第二個來源是審查對象漂移：第 N 輪複查的是第 N−1 輪的評論而非產出物，討論標的逐輪變大。

## Baseline 凍結

未凍結 baseline 不得開始 review。baseline 至少包含：

- `原始需求`：這次要交付什麼。
- `驗收條件`：可逐條判定 PASS / FAIL 的條目。
- `Non-goals`：本次明確不處理的範圍。中性、可驗證的需求語言，不帶原 reviewer 的論證。
- `Accepted risks`：已知並接受的風險，每條附影響與重新檢視條件。沒有重新檢視條件的不得寫入。
- `被審對象識別`：對象在版本控制內、已納入追蹤且與 HEAD 無差異時用 commit hash；dirty、untracked
  或未納入版本控制時用「版本＋內容 sha256 前 12 碼」。取不到穩定識別時才退而記錄量測時間。
- `Owner`：裁決者。

baseline 由 Owner 核准後凍結。不得由產出方單方面認定——產出方自訂基準會寫成自己做得到的樣子，
複查即形同虛設。

同一個 cycle 內不得修改 baseline。closure verification 沿用凍結時的同一版本。在 cycle 中途新增
non-goal 等於用改需求讓 finding 消失，而不是裁決 finding。

## Reviewer 的輸入邊界

full review 的 reviewer 只收到「產出物 + 凍結 baseline」。closure verification 的輸入不同，見
「輪次與停止條件」——那是本節的唯一例外，其餘階段一律適用本節。

不得提供：另一個 reviewer 的評論或 findings、review log、產出過程的推理與失敗軌跡。把 reviewer A
的意見交給 reviewer B 評論會把驗證變成辯論，並使審查對象逐輪膨脹。

把 findings 交給作者修正是允許的；要求另一個 reviewer 評論這些 findings「想得夠不夠完整」不允許。

## Finding schema

本節只規定 full review 的 finding。`Scope proposal`、`New blocker` 與`基準爭議`是互斥的獨立
輸出類型,各自使用後文 schema,不得套用 finding schema。

每個 finding 必填：

- `Violated criterion`：違反 baseline 的哪一條需求或驗收條件。
- `Evidence`：可重現案例、具體段落或推導。
- `Impact`：不修正實際會發生什麼。
- `Severity`：`Blocking` / `Non-blocking`。
- `Minimal fix`：滿足原需求所需的最小修改。

`Violated criterion` 是 finding 的必要條件;指不出的不得列為 `Blocking` 或 `Non-blocking`
finding。若意見主張 baseline 缺少需求,改輸出 `Scope proposal`;若證據或推論不成立,
不得以 `Scope proposal` 保留。`Minimal fix` 是抑制修正階段擴張的欄位，缺這欄會讓
「這裡應該重新設計」變成新任務。

`Blocking` finding 限於同時指名違反的既定需求或驗收條件,且不修正會造成實質
correctness / security 問題或不可接受風險。

`Severity` 只有這兩個值，不得自創第三種。

## Scope proposal

reviewer 認為需要新增需求、擴充測試矩陣或改變決策前提時，輸出 `Scope proposal`，不是 finding。
scope proposal 沒有 `Violated criterion`（它主張的正是目前 baseline 缺了什麼），必填 `Rationale`、
`Impact`、`建議的 baseline 變更`。

scope proposal 不進 findings 清單，不參與 closure，不在本 cycle 處理，一律進 backlog 等待
Owner 在下一版 baseline 裁決。

## Disposition

Owner 對每個 finding 給一個 disposition，並記錄理由：

| Disposition | 投影進下一版 baseline | 形式 |
|---|---|---|
| `accepted_blocking` | 否 | 本 cycle 修正 |
| `rejected_out_of_scope` | 是 | Owner 轉寫成 `Non-goal` |
| `accepted_risk` | 是 | 寫成 `Accepted risk`，保留影響與重新檢視條件，不得寫成 non-goal |
| `deferred` | 視情況 | 留 backlog；本版本明確排除時另寫 non-goal |
| `rejected_invalid` | 否 | finding 的證據或推論錯誤 |
| `already_satisfied` | 否 | baseline 不變 |
| `duplicate` | 否 | baseline 不變 |

`rejected_invalid` 絕不轉成 non-goal。reviewer 誤報「缺少某項防護」被駁回，不代表該領域不需要
驗證；寫成 non-goal 會讓下一個 reviewer 被禁止檢查一個從未被驗證過的真實風險。

`accepted_blocking` 只適用於 `Blocking` finding。`Non-blocking` finding 預設 `deferred`，本 cycle
不修——Owner 認同一個 Non-blocking 建議時，建立新任務或寫進下一版 baseline，不得升格成本輪必要
工作。作者只修 `accepted_blocking`。

## 輸出格式的優先序

兩個階段用不同格式，不得混用：

- Full review：輸出 finding 清單（`Violated criterion` / `Evidence` / `Impact` / `Severity` /
  `Minimal fix`）與 scope proposals。不使用 PASS / FAIL / UNVERIFIABLE。
- Closure verification：使用 `verifier.md` 的判定格式——逐條 finding 給 PASS / FAIL /
  UNVERIFIABLE 與證據，再依 `FAIL > UNVERIFIABLE > PASS` 給整體判定。不重新產出 finding schema。

## 輪次與停止條件

上限為一次 full review 加一次 closure verification。

```text
Baseline 凍結
  → Full review
  → Owner disposition
  → 修正 accepted_blocking findings
  → Closure verification（同一 baseline）
  → cycle 結束
```

closure 是**重新派工的一次新驗收**，不是同一個驗收者接續執行——驗收者回報後即結束，不得進入
重新驗收循環。closure 的驗收者只收到「修正後產出物 + 同一 baseline + accepted_blocking finding IDs + 修改範圍」。

closure 的通過條件：沒有未關閉的 `accepted_blocking` finding。判定沿用 `verifier.md` 的三值與優先序
`FAIL > UNVERIFIABLE > PASS`；缺少判定所需資訊或能力時回報 `UNVERIFIABLE`，不得壓成 PASS 或 FAIL。

closure 階段不得重新做完整 review，也不得擴張測試範圍。只允許回報兩類新問題：

- 修正本身引入，且發生在被修改範圍內的 regression。
- 原始範圍內、有直接證據、達 `Blocking` 的問題。

其餘新發現一律進 backlog，不延長目前 cycle。

這兩類新問題以 `New blocker` 輸出。`New blocker` 不是 full review finding,不要求
`Violated criterion`,也不混進既有 finding 的逐條判定;必填：

- `類型`：`regression`（由本次修正引入，須附修正前後同一案例的對照）或 `in-scope blocking`
  （須指名它落在原始需求的哪個交付範圍）。
- `Evidence` / `Impact` / `Minimal fix`。

任一 `New blocker` 使 closure 整體判定為 `FAIL`。closure 不自動進第三輪——由 Owner 決定建立新
cycle 或新任務。缺少修正前對照時只能證明缺陷存在，不能證明由修正引入，該問題不得標為
`regression`。

意見分歧時先依凍結 baseline 裁決；baseline 不足以裁決才交給人。不要求 reviewer 之間互相說服。

超出範圍的問題建立新任務，不延長目前任務。

## 基準爭議

finding 主張的若是「baseline 本身錯誤，且會導致交付物無用」，標記為`基準爭議`而非 finding。
基準爭議中止本 cycle，回到 baseline 設定，只能由 Owner 裁決，模型不得自行升級。

提出限制：

- 只能在 full review 階段提出。closure 階段不接受基準爭議。
- 必須附 `Evidence`、`Impact` 與 `最小 baseline 變更`；缺任一項不受理。
- Owner 駁回後，同一 artifact 與同一 baseline 版本內不得以相同理由重提。baseline 換版後才可
  重新提出。

這個閥門是有界驗證的必要配套：沒有它，錯誤的 baseline 會讓兩輪都 PASS，用靜默失敗換掉範圍擴張。

## Review log 與下一版 baseline

review log 保存完整 finding、證據、disposition 與理由，供稽核。review log 不作為 reviewer 的輸入。

Owner 在下一個 cycle 開始前，把仍有效的 `rejected_out_of_scope`（與明確排除的 `deferred`）提煉成
baseline vNext 的 non-goals，經核准後凍結。不自動轉寫。每次新增 non-goal 都是需求範圍變更。

baseline vNext 的 audit 必須逐條重新確認既有 non-goals 與 accepted risks 仍成立，不預設繼承。
non-goals 單向累積會讓 baseline 逐版變成「凡是曾被裁決過的都不再檢查」。

## 依產出物類型鎖定

- 測試任務：先鎖定測試矩陣與風險等級。複查不得新增平台、使用情境或案例類別。
- 決策文件：鎖定決策問題、評估準則與證據截止日期，並把`候選方案搜尋契約`列為驗收條件——寫明
  搜尋了哪些來源與哪些軸線。不要寫「候選方案已窮盡」，那不可驗證，寫進驗收條件只會產生無法
  判定項。搜尋契約使「漏了某軸線的方案」成為違反既定條件的 `Blocking`，而不是被壓成 scope change。

## Full review 指令模板

```text
你正在執行有界驗證，不是重新設計或全面改善。

驗證基準：
- 原始需求：[…]
- 驗收條件：[…]
- 明確排除：[…]
- 已接受風險：[…]
- 被審版本：[…]

只回報同時符合以下條件的 Blocking finding：
1. 位於原始範圍內；
2. 明確違反既定需求或驗收條件；
3. 有具體證據或可重現案例；
4. 不修正會造成實質錯誤或不可接受風險。

位於原始範圍、能指名 `Violated criterion`、但未達 Blocking 門檻的有價值意見標為
Non-blocking。若你認為 baseline 缺了某項需求，輸出 Scope proposal（Rationale、Impact、
建議的 baseline 變更），不要寫成 finding。兩者都不得要求在本任務處理。

每個 finding 必須包含 Violated criterion、Evidence、Impact、Severity、Minimal fix。

若你認為基準本身錯誤且會導致交付物無用，不要列為 finding，改標記為「基準爭議」並停止，
並附 Evidence、Impact 與最小 baseline 變更。

這是完整 review 的唯一一輪。
```

## Closure 指令模板

```text
這是 closure verification，不是新的完整 review。

驗證基準（與 full review 同一份，未變更）：
- 原始需求：[…]
- 驗收條件：[…]
- 明確排除：[…]
- 已接受風險：[…]
- 被審版本（修正後）：[…]
- 修改範圍：[…]

只驗證以下 accepted_blocking findings 是否已關閉：[…]

不得提出新的改善建議或擴張範圍。只有同時滿足「原始範圍內、有直接證據、Blocking 嚴重度」，
或屬於本次修改範圍內由修正引入的 regression，才能回報；否則記入 backlog。

逐條 finding 回報 PASS / FAIL / UNVERIFIABLE 與證據。
符合上述兩類例外的新問題另以 New blocker 區塊回報（類型 / Evidence / Impact / Minimal fix），
不併入既有 finding 的判定。類型為 regression 時,`Evidence` 必須附修正前後同一案例對照;
缺對照時不得標為 regression。類型為 in-scope blocking 時,必須指名它落在原始需求的哪個
交付範圍。任一 New blocker 使整體判定為 FAIL。
再給整體判定。
整體判定的優先序為 FAIL > UNVERIFIABLE > PASS。不重新產出 finding schema，
不接受基準爭議。
```
