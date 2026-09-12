# Known-issue ledger — Batch 12 最終兩輪

對象 run（唯一有效來源，未重跑不得更新）：

綁定值為 **`hash_schema: v1`**，與現行 v6 的值不可直接比較（見 STATUS.md「Batch 13f」「Batch 14」「Batch 15」「Batch 17」「Batch 18」）。

| run | 狀態 | 綁定（hash_schema v1） |
|---|---|---|
| [`runs/20260901-batch12-judgment-final/`](runs/20260901-batch12-judgment-final/) | 有效 FAIL；routing 21/28、contract 16/28 | `judgment_bundle 00ebf628116c`、`dispatch_bundle 2cf168c664e9`、`harness_test_suite bac3abd9efa7` |
| [`runs/20260902-batch12-default-final/`](runs/20260902-batch12-default-final/) | INVALID（judge parser）；routing 16/18 | 同上 |

**2026-09-02 已機械核對：** 這兩輪 raw trace 內每一筆 `.meta.json` 記錄的 prompt，與現行
fixture 檔逐字相同（judgment 29 筆、default 19 筆、`20260901-215156-0fe73d` 29 筆，
差異 0 筆）。因此下方逐筆證據引用的 `required_elements`／`forbidden_elements`
就是當時實際送進判定的那一份，**不是**事後改過的版本。

<!-- BEGIN ledger:summary -->
**Owner disposition 已於 2026-09-02 逐筆裁決完畢，`PENDING` 0。**
**2026-09-04 第二次裁決**（依 DE-01 與 continuation 證據）後仍有 `NEEDS_EVIDENCE` 4，
另有 `NOT_DONE` 11 已裁決要修但尚未完成。ID 清單見下方 ledger 與 gate 兩區，
此處不重列。發布 gate 維持關閉（見文末「發布 gate 現況」）。
<!-- END ledger:summary -->

## 詞彙

**dimension** — 該問題落在哪個判定面：`routing`（score.py 機械判定）、`contract`
（judge.py 語意判定）、`routing→contract`（contract 只是 routing 未觸發的下游結果，
不是獨立缺陷，修好 routing 才知道 contract 真實狀態）。

**classification（proposed，五種）**

| 值 | 意義 | 成立所需證據 |
|---|---|---|
| `fixture_invalid` | fixture 本身測不到它宣稱的行為 | 指出 prompt／assertion 與宣稱受測行為的具體落差 |
| `skill_defect` | skill 規則或 description 的缺口 | trace 顯示行為缺席，且該行為是 skill 應輸出的 |
| `stochastic_known_issue` | 同 bundle 已觀測到翻轉 | 至少兩輪同 bundle 的相反結果，附 run 路徑 |
| `description_dilution` | description 擴張導致其他案例 routing 退化 | 舊／新 description 的 A/B；**單次 observation 不成立** |
| `harness_error` | 工具鏈缺陷 | 可在無真實 session 下重現 |

**Owner disposition（五種）** — disposition 是**決策**，不是完成度。

| 值 | 意義 | 發布效果 |
|---|---|---|
| `ACCEPT_AS_KNOWN` | 容許此缺陷存在，條目保留在本檔 | 放行 |
| `FIX_FIXTURE` | 改 fixture；改完重算 `fixtures` domain hash 並重跑該筆 | **僅在 action status = `DONE` 時放行** |
| `FIX_SKILL` | 改 SKILL.md／description；改完重跑該筆 | **僅在 action status = `DONE` 時放行** |
| `NEEDS_EVIDENCE` | 證據不足以裁決，需指定 A/B 或重跑才能定案 | **擋住** |
| `PENDING` | 尚未裁決 | **擋住** |

**action status（2026-09-04 新增，三種）** — **只追蹤 `FIX_FIXTURE`／`FIX_SKILL` 的
remediation 完成度**，不追蹤其他 disposition 的 required_action。

| 值 | 意義 |
|---|---|
| `DONE` | `required_action` 全部完成，且有 run record 或產出物 hash 可追溯 |
| `NOT_DONE` | 已裁決要修，但修正或重跑尚未完成 |
| `N/A` | 本欄不適用於此 disposition（`ACCEPT_AS_KNOWN`／`NEEDS_EVIDENCE`／`PENDING`） |

**`N/A` 不等於「沒有待辦」。** `NEEDS_EVIDENCE` 各筆都有具體 required_action
（3/3 或 2/3 重跑；逐筆內容見 `ledger:active`，ID 與筆數見 `ledger:distribution`），
只是那些重跑屬於「取得裁決所需證據」，不是
「已裁決後的 remediation」，因此不由本欄承載——它們的擋住效果來自 disposition 本身。
（2026-09-04 修正：舊定義寫成「該 disposition 不要求行動」，與這四列的 required_action 直接衝突。）

**為什麼要拆這一欄。** 舊表把「Owner 決定要修」與「已經修好」混在同一格：
`FIX_SKILL` 一旦被選定，「放行（改動完成後）」那句括號沒有任何欄位承載，
讀表的人無從分辨哪幾筆真的做完了。2026-09-04 的 closure 複驗就踩到這個坑——
KI-07 的 description 寫入完成即被當成整筆 closed，而 `required_action` 的另一半
（與 DE-01 A/B 同批進行）當時根本沒跑。
**`FIX_FIXTURE`／`FIX_SKILL` 不因為被選定就放行，必須 action status = `DONE`。**

**原子性契約** — 一列只承載一個問題：一個 fixture、一個 dimension、一個 classification、
一個 required_action。同一 fixture 的兩個獨立缺陷拆成兩列；上下游關係用「阻擋於」欄表達，
不重複列同一件事。新增列時沿用下一個未用的 `KI-nn`，不重編既有 ID。

**錨定 assertion（2026-09-04 新增）** — 當一個 fixture 的 contract 由多條 assertion 組成，
而各條的結果不一致時，`dimension` 欄的粒度不足以承載問題：整筆 contract 可能輪輪 FAIL，
但每輪 FAIL 的成因是不同的 assertion。這種情況下該列**必須在 required_action 內寫明
錨定的 assertion 索引**（如 `.required[0]`），classification 依「該條 assertion 的
逐輪結果」判定，不得以整筆 contract 的彙總結果代替。
2026-09-04 的 KI-02 就是踩到這一點：它以「contract 3/3 FAIL」推導 `skill_defect`，
而它真正主張的行為寫在 `.required[0]`，該條在同 bundle 內是 PASS/FAIL/PASS。

## Ledger（每列一個原子問題）

<!-- BEGIN ledger:active -->
| ID | fixture | dimension | proposed classification | 阻擋於 | required_action | Owner disposition | action status |
|---|---|---|---|---|---|---|---|
| KI-01 | `judgment__positive-2` | contract | `fixture_invalid` | — | 移除逐字措辭要求，改判「是否逐條給出三值判定與證據」；同一 fixture 的「整體判定使用 FAIL > UNVERIFIABLE > PASS 優先順序」一併改為不綁定字面。**2026-09-04 已於 DE-01 縮減集重跑**（`fixtures 7a1b54c1…`，非全套 `3d225afc…`） | FIX_FIXTURE | DONE |
| KI-02 | `judgment__positive-2` | contract（**錨定 `.required[0]`**；2026-09-04 由 `routing→contract` 更正——arm B routing 已 3/3 觸發，不再是下游） | `stochastic_known_issue`（2026-09-04 由 `skill_defect` 改判） | — | SKILL.md 補上「何時必須開 fresh context 驗收」的具體規則（觸發條件＋與自我重讀的分界），改完重跑 `judgment__positive-2`。**證據錨定 `.required[0]`**（「啟動 fresh-context 驗收並只在此時讀取 verifier 規則」）：arm B（`judgment_skill a26b4368…`）逐輪 `PASS/FAIL/PASS` = 2/3、arm A 逐輪 `FAIL/FAIL/PASS` = 1/3；**同 bundle 內有翻轉，因此是 stochastic**。（證據：`runs/de01-armB-r{1,2,3}/raw/judgment__positive-2.judge.json` 的 `.required[0].verdict`） **2026-09-07 Batch 23b：已完成 skill 文字修正,行為重跑尚未執行**(`judgment_skill` 由 `a26b4368…` 變為 `953e0422…`;本列仍為 `NOT_DONE`,action 完成需後續付費重跑證據)。 | FIX_SKILL | NOT_DONE |
| KI-03 | `judgment__positive-2` | routing | `stochastic_known_issue`（2026-09-04 由 `description_dilution` 改判） | — | DE-01 已執行：arm A 1/3、arm B 3/3，未達「A≥2/3 且 B≤1/3」門檻，dilution 不成立；同 bundle（arm A `6e96c802…`）內出現 FAIL/FAIL/PASS 翻轉。**不得記為 fixture PASS。**（證據：2026-09-04 DE-01／KI-07，`runs/de01-*`、`runs/ki07-*`，見 [`DE-01-RESULTS-20260904.md`](DE-01-RESULTS-20260904.md)） | ACCEPT_AS_KNOWN | N/A |
| KI-04 | `judgment__positive-4` | contract | `fixture_invalid` | — | prompt 補上待驗收產出物（或在 seed 放一份可驗的變更），否則測到的是「索取輸入」。**2026-09-04 已於 DE-01 縮減集重跑**（`fixtures 7a1b54c1…`，非全套 `3d225afc…`） | FIX_FIXTURE | DONE |
| KI-05 | `judgment__positive-4` | routing | `stochastic_known_issue`（2026-09-04 由 `description_dilution` 改判） | — | DE-01 已執行：arm A 2/3、arm B 3/3，arm B 超過 1/3 門檻，dilution 不成立；同 bundle（arm A `6e96c802…`）內出現 PASS/FAIL/PASS 翻轉。**不得記為 fixture PASS。**（證據：2026-09-04 DE-01／KI-07，`runs/de01-*`、`runs/ki07-*`，見 [`DE-01-RESULTS-20260904.md`](DE-01-RESULTS-20260904.md)） | ACCEPT_AS_KNOWN | N/A |
| KI-06 | `judgment__negative-1` | contract | `fixture_invalid` | — | 拆開「缺必要輸入而暫停」與「無判斷點卻暫停」，只禁後者；prompt 同時補上 function 所在路徑，否則 required「直接執行命名調整」無法達成。**fixture 已改，但修正後尚未重跑該筆** | FIX_FIXTURE | NOT_DONE |
| KI-07 | `judgment__ambiguous-1` | routing | `skill_defect` | DE-01（順序） | description 補上「互斥方案 + 選錯成本高 + 徵詢語氣」這個觸發面（如「你覺得呢」「兩個方案不相容」），**改完連 routing 與 contract 一併重跑 `ambiguous-1`**。**必須與 DE-01 的 A/B 同批進行**，A/B 量測對象是最終要發布的那份 description。**2026-09-04：已完成**——description 定稿（`judgment_skill a26b4368…`），DE-01 A/B 六輪已跑，`ambiguous-1` continuation **routing 3/3、contract 3/3**（含原 KI-08 併入的 contract 觀測；routing 觸發後未觀測到下游缺陷，**這是「未觀測到」，不是「證明不存在」**）。（證據：`runs/ki07-armB-r{1,2,3}`、`runs/de01-*`，見 [`DE-01-RESULTS-20260904.md`](DE-01-RESULTS-20260904.md)） | FIX_SKILL | DONE |
| KI-09 | `judgment__ambiguous-2` | contract | `skill_defect` | — | SKILL.md 強制該情境輸出能力升降或推理耦合度的判斷（routing 已 PASS，skill 已在 context 內仍未輸出） | FIX_SKILL | NOT_DONE |
| KI-10 | `judgment__explicit_mention-2` | contract | `fixture_invalid` | — | prompt 指定目標規則檔與 diff。**fixture 已改，但修正後尚未重跑該筆** | FIX_FIXTURE | NOT_DONE |
| KI-11 | `judgment__positive-9` | contract | `stochastic_known_issue` | — | 3/3 重跑（本批新增案例，不適用 2/3） | NEEDS_EVIDENCE | N/A |
| KI-12 | `judgment__explicit_mention-3` | contract | `stochastic_known_issue` | KI-13 | 3/3 重跑，且必須跑在 KI-13 修正後的 fixture 上 | NEEDS_EVIDENCE | N/A |
| KI-13 | `judgment__explicit_mention-3` | contract | `fixture_invalid` | — | prompt 補上遷移計畫本文，否則測到的是索取輸入。**fixture 已改，但修正後尚未重跑該筆** | FIX_FIXTURE | NOT_DONE |
| KI-14 | `judgment__positive-1` | routing | `stochastic_known_issue`（2026-09-04 由 `description_dilution` 改判） | — | DE-01 已執行：arm A 0/3、arm B 1/3，dilution 不成立；同 bundle（arm B `a26b4368…`）內出現 FAIL/FAIL/PASS 翻轉。arm B 僅 1/3 觸發，需 skill 修正提高觸發率，改完重跑該筆。（證據：2026-09-04 DE-01／KI-07，`runs/de01-*`、`runs/ki07-*`，見 [`DE-01-RESULTS-20260904.md`](DE-01-RESULTS-20260904.md)） **2026-09-07 Batch 23b：已完成 skill 文字修正,行為重跑尚未執行**(`judgment_skill` 由 `a26b4368…` 變為 `953e0422…`;本列仍為 `NOT_DONE`,action 完成需後續付費重跑證據)。 | FIX_SKILL | NOT_DONE |
| KI-15 | `judgment__positive-5` | routing | `skill_defect`（2026-09-04 由 `description_dilution` 改判） | — | DE-01 已執行：兩個 arm 合計 0/6，**兩個 bundle 內都沒有翻轉**，因此不是 stochastic。需 skill 修正讓該情境能觸發，改完重跑該筆。（證據：2026-09-04 DE-01／KI-07，`runs/de01-*`、`runs/ki07-*`，見 [`DE-01-RESULTS-20260904.md`](DE-01-RESULTS-20260904.md)） **2026-09-07 Batch 23b：已完成 skill 文字修正,行為重跑尚未執行**(`judgment_skill` 由 `a26b4368…` 變為 `953e0422…`;本列仍為 `NOT_DONE`,action 完成需後續付費重跑證據)。 | FIX_SKILL | NOT_DONE |
| KI-16 | `judgment__ambiguous-3` | routing | `stochastic_known_issue` | — | 3/3 重跑（本批新增案例，不適用 2/3） | NEEDS_EVIDENCE | N/A |
| KI-17 | `harness-routing__handoff-1` | contract | `fixture_invalid`（2026-09-02 由 `skill_defect` 改判） | — | prompt 補上規則檔路徑與 judgment 的逐條判定；現行 fixture 自相矛盾（要求交付驗收條件，卻既不提供也 forbidden 自行產生）。**fixture 已改，但修正後尚未重跑該筆** | FIX_FIXTURE | NOT_DONE |
| KI-18 | `harness-routing__boundary-2` | routing→contract | `stochastic_known_issue` | — | **2/3 重跑尚未執行**。跑完依結果改判：達到 2/3 → `ACCEPT_AS_KNOWN`（記為 gate 容許的 known flaky，**不得記為 fixture PASS**）；未達到 → `FIX_SKILL` | NEEDS_EVIDENCE | N/A |
| KI-19 | `harness-routing__judgment-absent-1` | contract（2026-09-02 由 `routing` 更正） | `fixture_invalid` | — | prompt 補上待核對的路徑，否則永遠測到索取輸入。**fixture 已改，但修正後尚未重跑該筆** | FIX_FIXTURE | NOT_DONE |
| KI-20 | `harness-routing__agent-unavailable-1` | contract（2026-09-02 由 `routing` 更正） | `fixture_invalid` | — | prompt 補上**掃描目標／判準**（範圍「全 repo」已給，缺的是掃什麼）。**fixture 已改，但修正後尚未重跑該筆** | FIX_FIXTURE | NOT_DONE |
| KI-21 | `judgment__positive-2` | contract（**錨定 `.required[1]`**） | `stochastic_known_issue` | — | **2026-09-04 新增。** KI-01 依 required_action 改寫了 `.required[1]`（三值判定改為不綁定字面：「用語與符號不限，只要三種結果在報告中彼此可區分」），改寫後在 DE-01 仍大量 FAIL，而此事原本沒有任何列承載——KI-01 只負責「改 fixture 並重跑」，KI-02 錨定的是 `.required[0]`。逐輪：arm B `FAIL/PASS/FAIL` = 1/3、arm A `FAIL/FAIL/FAIL` = 0/3；**翻轉只由 arm B（`a26b4368…`）承載，arm A bundle 內無翻轉**。required_action：SKILL.md 強制驗收輸出可區分的三值判定（含「無法驗證」），改完重跑 `judgment__positive-2`。（證據：`runs/de01-armB-r{1,2,3}/raw/judgment__positive-2.judge.json` 的 `.required[1].verdict`） **2026-09-07 Batch 23b：已完成 skill 文字修正,行為重跑尚未執行**(`judgment_skill` 由 `a26b4368…` 變為 `953e0422…`;本列仍為 `NOT_DONE`,action 完成需後續付費重跑證據)。 | FIX_SKILL | NOT_DONE |
<!-- END ledger:active -->

### 已退役／已合併的 ID

退役的 ID **不重複使用、不重編**，也**不計入 active ledger 的任何統計**。
保留在此是為了讓引用過該 ID 的歷史文件仍可追溯。

<!-- BEGIN ledger:retired -->
| ID | 去向 | 說明 |
|---|---|---|
| KI-08 | **併入 KI-07**（2026-09-05） | 原記 `judgment__ambiguous-1`／`routing→contract`。原始觀測是 routing 未觸發造成的 contract 不可觀測，本身即非獨立缺陷；KI-07 修正後 routing 觸發、contract 3/3 PASS，未觀測到獨立缺陷。**這是「未觀測到」，不是「證明不存在」。** 退役理由：它在五個 classification 值裡沒有成立的填法——填 `skill_defect` 需「trace 顯示行為缺席」，而其自身證據是行為存在（3/3 PASS）；且 `required_action` 欄只是一句觀測結論、不含可完成的動作，無法支撐 `DONE`。作為 KI-07 的非獨立下游而長期佔一列，也違反原子性契約的「不重複列同一件事」。相關重跑要求與證據已併入 KI-07 的 `required_action`。 |
<!-- END ledger:retired -->

`harness-routing__boundary-3` 不在本表：它未在對象 run 中 FAIL，只因已觀測翻轉而列入重測清單。

### disposition 分佈

<!-- BEGIN ledger:distribution -->
| disposition | 筆數 | ID | action status |
|---|---|---|---|
| `FIX_FIXTURE` | 8 | KI-01、04、06、10、13、17、19、20 | `DONE` 2（01、04）／`NOT_DONE` 6 |
| `FIX_SKILL` | 6 | KI-02、07、09、14、15、**21** | `DONE` 1（07）／`NOT_DONE` 5 |
| `ACCEPT_AS_KNOWN` | 2 | KI-03、05 | `N/A` 2 |
| `NEEDS_EVIDENCE` | 4 | KI-11、12、16、**18** | `N/A` 4 |
| `PENDING` | 0 | — | — |

合計 20 筆：action status `DONE` 3、`NOT_DONE` 11、`N/A` 6。
<!-- END ledger:distribution -->
（**KI-08 已於 2026-09-05 併入 KI-07 並退役**，不計入上表，見「已退役／已合併的 ID」。）

**2026-09-04 Owner 裁決（依 DE-01 六輪與 KI-07 continuation 三輪）：**
KI-03／05 由 `NEEDS_EVIDENCE` 改 `ACCEPT_AS_KNOWN`（`stochastic_known_issue`）；
KI-02／14／15 由 `NEEDS_EVIDENCE` 改 `FIX_SKILL`（皆 `NOT_DONE`）；
KI-08 由 `NEEDS_EVIDENCE` 改 `FIX_SKILL`／`DONE`；KI-07 維持 `FIX_SKILL`，action status 改 `DONE`。
`NEEDS_EVIDENCE` 因此由 10 降為 4。**四筆 dilution 對象一筆都沒有被記為 fixture PASS。**

**2026-09-04 第三次修正（fresh-context 複驗後，見
[`RECHECK-20260904-supersedes-closure.md`](RECHECK-20260904-supersedes-closure.md)）：**
KI-02 的 classification 由 `skill_defect` 改 `stochastic_known_issue` 並錨定 `.required[0]`
（原理由「skill 已在 context 內仍未輸出該行為」不受逐 assertion 證據支持，disposition 不變）；
新增 KI-21（`.required[1]`）；action status 的 `N/A` 定義修正；
blocker 由誤記的 16 更正為 **15**。

**2026-09-05（第二次 fresh-context 驗收後）：KI-08 併入 KI-07 並退役。**
兩次嘗試把它填進五值詞彙表都失敗——`skill_defect` 要求「trace 顯示行為缺席」，
而它自身的證據是 contract 3/3 PASS（行為存在）。根因是它本來就不是獨立問題，
不該長期佔一列。**未新增第六個 classification 值**：`resolved` 之類是 lifecycle state，
屬 disposition／action status 的職責，放進 classification taxonomy 會讓兩者混同。
該次退役後，active ledger 由 21 降為 20，個別放行由 6 降為 5；當時阻擋仍為 15，發布 gate 狀態未變。

**KI-18 於 2026-09-02 由 `ACCEPT_AS_KNOWN` 改為 `NEEDS_EVIDENCE`。** 原本的寫法自相矛盾：
disposition 記成放行，required_action 卻是「2/3 重跑作為 known-flaky 確認」，
而那次重跑根本還沒跑。`ACCEPT_AS_KNOWN` 的定義是「容許此缺陷存在」——那是**看過結果之後**
才能下的判斷。把尚未執行的重跑先記成已放行，等於用一個還不存在的觀測換取發布資格。
既定的重跑判準完全保留，只是移到裁決之後：達到 2/3 改 `ACCEPT_AS_KNOWN`，未達到改 `FIX_SKILL`。

## DE-01：description dilution 的獨立 A/B 證據任務

KI-03／05／14／15 先前都寫「阻擋於 KI-19」。那是錯的：KI-19 是
`harness-routing__judgment-absent-1` 的 fixture 缺輸入問題，與 judgment 的 description
寬窄毫無因果關係，四筆 routing 退化不會因為修好它而得到任何解釋。**依賴已改為 DE-01。**

DE-01 不是缺陷，是一件證據任務，因此不佔 `KI-nn` 編號。

**待證命題**：judgment 的 description 自 Batch 11 起擴張後，`positive-1`／`positive-2`／
`positive-4`／`positive-5` 的 routing 觸發率下降，且下降由 description 變更造成。

**協定**（四筆共用，任一筆的證據不得外推到另一筆）：

1. 兩個 arm 只差 description：arm A = 11g 基準的舊 description，arm B = 現行（或 KI-07
   修改後、實際要發布的那份）。其餘所有 domain 必須逐 hash 相同——
   `fixtures`、`runner`、`evaluator`、`execution_context` 都不得在兩個 arm 之間變動。
2. 每個 arm 對每筆 fixture 跑 **3 次**，記錄 routing 觸發次數（0–3）。
3. 判定門檻：同一筆 fixture 在 arm A 至少 2/3 觸發、arm B 至多 1/3 觸發，才支持
   `description_dilution`；否則該筆改判 `stochastic_known_issue` 或 `skill_defect`。
4. **單次 observation 不成立。** 12b 的單次 A/B（舊 description 觸發、現行未觸發）
   是本命題的來源，不是它的證據。

**成本**：2 arm × 4 fixture × 3 次 = 24 筆 subject + 24 筆 judge，另加各 arm 的 preflight。
依 13d 的邊際單價（每筆 0.08–0.14、preflight 約 0.04）估 **USD 2.0–3.5**。
這是 G 之外的額外預算，不含在 13d 的 USD 2.3 內。

**先決條件**：DE-01 必須在 KI-07 的 description 修改**定稿後**才跑，否則 arm B 量的是
一份不會發布的 description。

## 證據

逐筆證據取自對象 run 的 `.judge.json` 與 trace。2026-09-02 複查時逐筆重讀原始
`.judge.json`，更正三處與 run record 不符的記載（KI-17／19／20），下方各自標示。

- **KI-01** — required 要求回應逐字出現 `PASS`／`FAIL`／`UNVERIFIABLE`；judge 的原文證據是
  「表格判定欄用的是 ✅/⚠️ 部分/❌ 缺，通篇沒有出現 PASS、FAIL 或 UNVERIFIABLE 字樣，
  不符合指定用語格式」。第三條 required（優先順序）之所以 FAIL，judge 寫的理由是
  「由於逐條判定沒有用 PASS/FAIL/UNVERIFIABLE 標記，無法確認……」——同一個根因，
  因此併入本列而不另開一列。綁定措辭違反 `tool-checklist`「不綁定措辭／內部名稱」。
- **KI-02** — required 的「啟動 fresh-context 驗收」確實缺席（trace 只有 Bash／Read）。
  但**同一輪 `positive-2` 的 routing 也 FAIL**，judgment 從未觸發，SKILL.md 的內容根本
  沒進到 context。因此無法區分「規則缺席」與「規則沒送到」，dimension 由 `contract`
  改為 `routing→contract`，classification 標為待證。
- **KI-03 / KI-05 / KI-14 / KI-15** — 11g 列為 dilution A/B 對象的既有 6 筆之一；
  12b 為單次 A/B（舊 description 觸發、現行未觸發）。**單次 observation 不支撐因果**，
  分類要成立需補 A/B，協定見 DE-01。四筆的 routing 失敗訊息都是
  「judgment: 預期觸發，實際未觸發」。
- **KI-04** — prompt 未提供待驗收產出物；`git status/log/diff` 無變更，模型回報找不到可驗收
  對象並索取輸入。與 12d 的 `dispatch__positive-4` 同型。
- **KI-06** — prompt 未給檔案路徑，required 卻要求「直接執行命名調整」；judge 自己寫下
  「因為條件本身是缺資訊而非決策分歧，仍構成不當暫停」——判定人自己指出了條件的缺陷，
  仍依 forbidden 判 FAIL。
- **KI-07** — routing 未觸發 judgment。**required_action 已更正**：先前寫「description 缺
  『要不要拆出去跑』這類字面觸發詞」，那句話來自 Batch 6.5 時期的舊 fixture；現行
  `ambiguous-1` 的 prompt 是「這個公開 API 可以照 A 方案做，也可以照不相容的 B 方案做，
  選錯會讓已有用戶必須重寫整合，你覺得呢？」，與派工無關。缺的觸發面是
  **互斥方案 + 高改錯成本 + 徵詢語氣**。
- **KI-08** — **證據已更正**：先前寫「required 要求複誦內部規則表名」，那同樣是舊 fixture
  的內容。現行 `ambiguous-1` 的 required 是行為層的（「當環境支援時建議調高模型能力或
  effort，並附上取捨依據」），judge 的 FAIL 理由是「回應全文未提及調高模型能力、
  reasoning effort、切換模型」。由於 routing 未觸發，這是 KI-07 的下游，不是獨立的
  fixture 缺陷。
- **KI-09** — routing PASS、judgment 已觸發，回應全文仍未出現任何能力升降或推理耦合度的判斷。
  觸發後未產出該判斷，指向 SKILL.md 未強制該情境輸出。這是本表唯一一筆
  「skill 確實在 context 內卻沒做到」的證據。
- **KI-10** — 目標規則檔未指定，模型連要驗收哪一份都無法確認，回頭索取路徑與 diff。
  三條 required 都因此無對象可判。
- **KI-11** — 12a 同組 observation 為 PASS，12e 轉 FAIL。judge 記「有做到近似但覆蓋不完整」，
  屬邊界判定而非明確缺席。
- **KI-12 / KI-13** — 12a PASS → 12e FAIL（KI-12）；本輪 FAIL 的直接原因是使用者未提供遷移計畫
  本文，回應以未來式描述將執行的步驟（KI-13）。翻轉觀測與 fixture 缺輸入是兩件事，因此拆列。
- **KI-16** — 12a PASS → 12e FAIL；本批新增觸發面。
- **KI-17** — **classification 已由 `skill_defect` 改判為 `fixture_invalid`。**
  直接證據來自 trace 與 fixture 本身的互斥：fixture 的 required 要求
  「驗收 prompt 顯式交付 verifier 六項輸入」，其中一項是驗收條件；同一 fixture 的 forbidden
  又禁止「由 dispatch 重新產生一套完成條件或驗收判準」；而 prompt
  （「judgment 已經判定這份規則檔需要 fresh-context 驗收了，幫我把驗收派出去」）
  **既沒給規則檔路徑，也沒給 judgment 的逐條判定**。三者同時成立時無解。
  模型的實際回應正是指出這一點：「派工單的『驗收條件』欄位需要逐條可判定的清單——
  我不能憑猜測填，填錯會整輪驗收結果失真」，並反問 judgment 具體判定要驗哪幾點。
  judge 也把兩條 forbidden 判成 PASS（沒有自行產生判準、沒有把可寫 agent 當唯讀驗收者）。
  停在計畫階段是這份 fixture 下的正確行為，不是 skill 缺口。
- **KI-18** — 同 bundle 下 judgment run FAIL、default run PASS。本輪唯一工具呼叫是
  `Skill(dispatch)`，完全略過 judgment。routing 與 contract 同源同因，故為單一問題。
- **KI-19** — **dimension 已由 `routing` 更正為 `contract`。** run record 該列是
  `routing=PASS ... （另有失敗的 Skill 呼叫，不計入觸發: judgment）`、`contract=FAIL`：
  `no-judgment` 變體下 judgment 呼叫失敗、正確地不計入觸發，routing 因此符合預期。
  失敗的是 contract：回應只承諾「等你給我路徑後我才能照替代流程逐條核對」——與 KI-04、
  KI-10 同屬「缺必要輸入」的結構。分類取 `fixture_invalid` 而非 `stochastic_known_issue`：
  翻轉是缺輸入下的隨機表現，不是獨立缺陷。
- **KI-20** — **dimension 已由 `routing` 更正為 `contract`。** run record 該列是
  `routing=PASS`、`contract=FAIL`。`env.deny_extra: ["Agent"]` 設定正確，**不是**
  harness_error。prompt「幫我派個 agent 去做全 repo 掃描」的**範圍已給**（全 repo），
  缺的是掃描目標與判準；judge 的證據是「只呼叫了 Skill(dispatch) 並向使用者詢問掃描目標
  與範圍」，模型從未嘗試呼叫 Agent，因此永遠到不了「被拒」這個受測分支。
  （2026-09-02 複查修正：先前記為「缺掃描範圍」，措辭不準。）

## 已修正的 harness_error

| 項目 | 觀測 | 處置 |
|---|---|---|
| judge 輸出解析（尾端殘餘） | `runs/20260901-batch11-judgment-full` 的 `boundary-1`、`runs/20260902-batch12-default-final` 的 `dispatch__negative-2`，judge 在合法 JSON 後附加內容，整輪記 INVALID | Batch 13b 修：fail-closed、補 schema 與條目數驗證、異常型態進 run record；判定失敗仍保留 `_cost_usd` |
| judge fence 解析 fail-open | 13b 的 `_strip_fence` 用 `rsplit` 丟棄 closing fence 後的文字，fenced JSON 後接「I retract this verdict」仍被判可用且不記異常 | Batch 13f 修：完整 fence 比對，closing fence 後非空白一律 `fence_trailing_content` |
| judge parser 中斷整輪 | 13b 的 `_strip_fence` 對 ```` ``` ````／```` ```json ```` 拋 IndexError，呼叫端無 try，一筆截斷會讓後面每一筆失去 `.judge.json` | Batch 13f 修：`parse_verdict` 與 `main()` 單筆各加例外攔截，轉成 ERROR 記錄 |
| judge 條件替換未被偵測 | 13b 只把條目數傳進 parser，element 內容不驗；條件替換、重複充數、漏判補位三種都放行 | Batch 13f 修：改傳原始條件陣列，逐條正規化比對；未知 top-level key 一律 ERROR |
| judge 逐條項目未驗 key 集合 | top-level 收緊後，撤回語意只要往下挪一層（`required[0].corrected_verdict`）即可繞過整套檢查 | Batch 14 修：逐條項目的 key 集合必須嚴格等於 `element`／`verdict`／`evidence`，多一個即 `schema_violation`；判定 prompt 同步加上這條 |
| 缺 trace manifest 仍照常呼叫 judge | Batch 14 只在缺 manifest 時印一行警告，判定照跑，把「無法證明 trace 未被更動」留給 record 事後判 INVALID——那時 judge 的錢已經花完，而那一輪判定從一開始就不可採信 | Batch 15 修（BR-F21）：manifest 缺失／壞損／為空一律在進 fixture loop 前 `exit 2`，一次 CLI 都不呼叫；`run-suite.sh` 在 `TRACE_RC != 0` 時直接跳過 judge |
| manifest 未要求完整 domain 集合 | 只比對 start／end 是否一致的話，一份只含 `fixtures` 一個 domain 的 manifest 會完美通過——沒有 drift、記成有效證據，而 skill／runner／evaluator／context 全無綁定。少到看不出來的紀錄比沒有紀錄更危險 | Batch 15 修（BR-F22）：`record.py` 定義 `REQUIRED_DOMAINS`，start／end 必須**恰好**含這些 domain；`manifest_version` 也必須是支援值 |
| judge model 未納入 identity | 換 `HARNESS_JUDGE_MODEL`、換 judge CLI flags、host `claude` 升版都會讓 contract 判定翻轉，而 run record 一個字都沒記；兩輪 hash 相同卻得到相反結論時無法解釋 | Batch 15 修（BR-F23）：新增 `evaluation_context` domain（judge model／實際 CLI 版本／flags／structured-output），與 subject 的 `execution_context` **分開**——前者變更只作廢判定，後者變更作廢行為證據 |
| trace manifest 可被覆寫 | 改 trace、重跑一次 `manifest.py trace`，新 manifest 逐檔比對全部通過。逐檔核對對這條路徑完全無效 | Batch 15 修（BR-F24）：`trace` 目標已存在即 exit 3；run record 保存 deterministic digest；重評時比對 digest，並產生不覆寫來源的 derived record |
| end 快照重用 start 的 descriptor | `run-suite.sh` 只在 start 產生 execution／evaluation descriptor，end 重用同兩份檔案。實測：judge CLI 版本改變後重用得到同一個 `evaluation_context` hash（`da74452145de`），重新產生才不同（`1e682b0cce98`）。「run 結束後重新量測」對這兩個 domain 是空話 | Batch 16 修（BR-F26）：end 快照前重新產生兩份 descriptor（`*.end.txt`）再量測；產生失敗則不寫 end 快照，record 判 INVALID |
| 同名 phase 可被覆寫 | `manifest.py` 無條件 `doc[phase] = snap`。實測依序寫入 start=A、start=B、end=B 三次都回傳 0，`check_manifest()` 得到**零問題**——原始 start 已被蓋掉，比對變成拿 end 跟 end 比，drift 完全隱形而紀錄看起來通過了比對 | Batch 16 修（BR-F27）：同名 phase 已存在即 exit 3；測試改用獨立 manifest 檔 |
| migration audit 可產生假 PASS | audit 只驗 domain 名稱、來源 subject hash 只驗 key 存在。實測：六個 audit domain 與六個來源 hash 全填 `null`，仍得到 `rc=0 / PASS / is_contract_evidence=true`——一份什麼都沒說的「稽核」換到一個看起來完整的證據紀錄 | Batch 17 修（BR-F29）：subject hash 必須是合法 64 位 hex；audit 改採固定 schema，逐 domain 要求 `equivalent: true`、非空 `evidence` 與 `method`，拒絕 `false`／`null`／缺欄位／多欄位／未知或缺 domain |
| 重評使用的 fixtures 沒有綁定 | judge 用**現在**的 fixtures 判定，derived record 卻沿用來源 run 的 `fixtures` hash。改掉 `required_elements` 再重評舊 trace，紀錄仍宣稱使用來源 fixtures | Batch 17 修（BR-F30）：新增 `contract_fixtures` domain（judge 實際載入的 assertion 來源，現量）；另在 judge 進 loop 前逐筆比對 fixture 的 `prompt` 與 `.meta.json`，不符即中止且不呼叫 CLI |
| rescore 文件重用 descriptor | README 的 start／end `contract-snapshot` 用同一份 judge descriptor，重評期間的 CLI drift 仍會漏檢——與 BR-F26 同型，只是搬到了人工流程 | Batch 17 修（BR-F31）：新增 [`scripts/run-rescore.sh`](../../../scripts/run-rescore.sh) 作為唯一建議入口，前後各重新產生一次 descriptor；README 改為指向該腳本 |
| rescore 覆寫來源 judge artifacts | `run-rescore.sh` 把來源 `raw/` 直接交給 judge，judge 把新的 `<fixture>.judge.json` 寫回同一目錄。實測來源逐筆判定證據被覆蓋且 marker 消失；trace manifest 不涵蓋 `.judge.json`，偵測不到 | Batch 18 修（BR-F33）：subject 產物複製到 `<來源>/derived/<新 id>/raw/`，judge 只寫那裡；結束前核對來源目錄逐 byte 未變 |
| provenance 無效時仍先花 judge 成本 | 付費 judge 排在 `record.py` 的 provenance 驗證之前，缺 audit／audit 無效／source hash 壞損時整輪最後才 INVALID——「判不了仍先花錢」換個位置重現 | Batch 18 修（BR-F34）：新增 `record.py --validate-only` 與 `judge.py --preflight`，兩者都零成本；`run-rescore.sh` 在 judge 之前跑完，不通過即中止並刪掉 derived 目錄 |
| legacy trace 可用一個環境變數升格 | `record.py` 直接採信 `HARNESS_TRACE_MANIFEST_ORIGIN`。實測對事後建立的任意 trace 設為 `contemporaneous` 即得到 `PASS / contract_evidence / is_contract_evidence=true`，BR-F32 的核心保證形同虛設 | Batch 18 修（BR-F35）：改為 run nonce 鏈——`snapshot start` 產生一次性 nonce，subject meta、trace manifest、run record 三方必須一致才判 `contemporaneous`；環境變數完全不參與判定。manifest 結構改變，`manifest_version` 提版為 2 |
| rescore run id 未限制路徑範圍 | `NEW_ID` 直接拼進 `DERIVED`，而失敗路徑上有 `rm -rf "$DERIVED"`。實測 `../../victim` 解析到 `<run>/derived/../../victim` = `runs/victim`——derived 產物與 `rm -rf` 的目標都在 `derived/` 之外 | Batch 19 修（BR-F36）：run id 限 `A-Za-z0-9._-`，禁空／`.` 開頭／`/`；建立目錄前後各以 canonical path 複驗（`derived/` 不得是 symlink、目標須為其直接子目錄）；containment 未確認前不執行任何 `rm -rf`。Batch 20 補：字元檢查改用 shell pattern——原本的 `$(… \| tr -d …)` 會被命令替換剝掉尾端換行，`safe<LF>line` 因此被判成「沒有非法字元」而放行 |
| preflight 期間 contract manifest 實質未受驗證 | `run-rescore.sh` 的順序是 `contract-snapshot start` → preflight → judge → `contract-snapshot end`，所以 preflight 讀到的 manifest **只有 start**。`check_manifest()` 在 end 缺席時整段早退並回傳 `hash_schema=None`，而 `main()` 的 `cross_schema` 以它為前提，因此恆為 False——跨 hash_schema 缺 `--migration-audit` 這道閘在 preflight 完全不觸發。fresh-context 驗收實測：來源 `v5`、現行 `v6`、無 audit 時 preflight 印「✓ 通過」，judge 照跑（judge session 計數 1），`INVALID` 等付費之後才出現，exit 1 而非 2。同時被跳過的還有 `manifest_version`、domain 集合、hash 格式與 fixture 清單 | Batch 21 修（BR-F38）：`check_manifest(doc, require_end=)` 把 start／end 兩半分開——start 的 schema、domain 集合、hash 格式與 `fixture_files` 一律在 preflight 就驗完並回傳 start identity；只有 end 是否存在、start/end domain 集合一致、hash drift 與 fixture 清單 drift 延後。另刪除 `main()` 內 `prov = [x for x in prov if "缺 end 快照" not in x]` 這種「先製造錯誤再按訊息文字過濾」的寫法。**closed**：`record_selftest` 新增 17 項、`run-provenance-selftest` 新增第 14 節 10 項，含「跨 schema 缺 audit → exit 2 且 judge 計數 0」 |
| contract FAIL 最後仍回傳成功 | `run-rescore.sh` 定義 `JUDGE_RC=1` 為 contract FAIL／ERROR，最終卻只檢查 `RECORD_RC`。`JUDGE_RC=1, RECORD_RC=0` 時 exit 0，CI 會把 contract FAIL 讀成成功 | Batch 19 修（BR-F37）：exit code 同時納入兩者（0 全過／1 judge 或 record 有問題／2 preflight 或 containment 不過）；derived record 在 FAIL 時仍保留 |
| rescore 編排腳本不在 identity 內 | v5 主張「它只影響流程不影響證據」，被 BR-F33／F34 推翻：它決定判定寫到哪裡與驗證順序 | Batch 18 修：新增 `rescore_runner` identity domain（`bundle-hash.sh rescore-runner`），納入 contract manifest；hash schema 提版 v6 |
| 事後補的 trace manifest 被當成契約證據 | 補 manifest 只能證明「目前檔案」的內容，不能證明它從產生到現在沒被改過。照舊制，補一份 manifest 就能把任何舊檔案升格成證據 | Batch 17 修（BR-F32）：新增 `evidence_class`（`contract_evidence`／`legacy_diagnostic`），只有 runner 宣告 `HARNESS_TRACE_MANIFEST_ORIGIN=contemporaneous` 的紀錄算契約證據；derived record 的等級取自**來源**紀錄的宣告 |
| v3 trace 無法產生有效的 v4 derived record | 重評把整份 identity 都從傳入的 manifest 取：v3 來源的 manifest 少一個 `evaluation_context`，必被 `REQUIRED_DOMAINS` 擋掉；而 `rescored_with.evaluator` 拿到的是**來源 run 的** evaluator，與它宣稱的「現在的」正好相反。步驟 F 因此產不出有效證據 | Batch 16 修（BR-F28）：derived identity 拆成兩半——subject（skill×3／runner／fixtures／execution_context）取自來源紀錄，contract（evaluator／evaluation_context）由 `manifest.py contract-snapshot` 現量；跨 schema 另附 `--migration-audit` 記錄內容等價，缺此一律 INVALID |
| run record 的版本綁定是「錄製當下」 | `record.py` 在整輪跑完後才現算 hash，run 期間任何一次編輯都會安靜地把跑完後的版本綁到跑之前的 observation | Batch 14 修：`manifest.py` 在 run 前後各量一次，`record.py` 只讀不算並比對，任一 domain drift 判 `INVALID` |
| raw trace 可被更動後重新評分 | 「evaluator 變更後重新評分既有 trace」省下付費 session 的前提是 trace 未變，但沒有任何機制檢查 | Batch 14 修：subject 迴圈結束即產生 trace manifest；`judge.py` 重評前核對，不符即該筆 ERROR 且不呼叫 CLI；`record.py` 亦核對並判 `INVALID` |

## 待重測清單（每筆 3 次、預先指定）

`judgment__positive-9`（KI-11）、`judgment__ambiguous-3`（KI-16）、
`judgment__explicit_mention-3`（KI-12）、`harness-routing__boundary-2`（KI-18，2/3）、
`harness-routing__boundary-3`。判準見 STATUS.md「Batch 13a」。

**此清單不足以滿足 gate 判準 1**，但缺口不必用付費重跑補。本批新增七筆中的
`positive-7`、`positive-8`、`positive-10`、`negative-3` 不在清單內，其 PASS 證據綁定
v1 的 `harness_test_suite bac3abd9efa7`。

**2026-09-02 改判：這四筆不能靠重新評分舊 trace 補齊。** 先前的規劃是重新評分
`runs/20260901-215156-0fe73d/raw/` 內保留的 trace（成本是 judge session 而非 subject
session），但那個 run 沒有當時產生的 trace manifest，現在補一份證明不了它從那時到現在
未被修改。依 BR-F32，那種產出只能是 `legacy_diagnostic`。四筆必須在現行 schema 下
重新執行 subject run；舊 trace 保留為診斷參考。

## 步驟 F 的地位（2026-09-02 改判）

**步驟 F 的產出一律是 `legacy_diagnostic`，不得計入發布 gate。**

目標 run `20260901-215156-0fe73d` 是 v1 紀錄，當時沒有產生 trace manifest。現在補一份
只能證明**目前**那些 `.jsonl` 的內容，不能證明它們從 2026-09-01 至今未被修改——
中間沒有任何 immutable digest、commit 或可信封存可以錨定。這不是工具能補的缺口：
`record.py` 會據 `trace_manifest_origin` 把這種紀錄降為 `legacy_diagnostic`，
`is_contract_evidence` 為 false。

因此 gate 判準 1 的四筆（`positive-7`／`positive-8`／`positive-10`／`negative-3`）
**不能靠重新評分舊 trace 補齊**，必須在現行 schema 下重新執行 subject run。
舊 v1 trace 只保留為診斷參考。

## 執行順序的硬約束

**`FIX_FIXTURE` 各筆必須排在既有 trace 重新評分（STATUS.md 步驟 F）之後**
（筆數見 `ledger:distribution`）。
`fixtures` 是**整檔**的 identity domain：動 `judgment__positive-2` 的 required_elements
會改變同一個 `fixtures` hash，於是 `positive-7`／`positive-8`／`positive-10`／`negative-3`
的既有 trace 立刻失去「fixtures 未變」這個重新評分的前提，四筆就得改用付費 subject 重跑。

順序：F（重新評分四筆）→ FIX_FIXTURE 各筆 → 重算 `fixtures` hash → G（付費重跑）。

## 發布 gate 現況

| 判準（STATUS.md 13a） | 狀態 |
|---|---|
| 1. 本批新增七筆 routing 與 contract 全部 PASS | 未達成——`positive-9`／`ambiguous-3`／`explicit_mention-3` 待 3/3；另四筆**須在現行 schema 下重跑 subject**（2026-09-02 改判：重新評分 v1 trace 只能產生 legacy diagnostic，見上節）|
| 2. 每一筆 disposition 都不是 `PENDING` | **已達成**（現值見 `ledger:distribution` 的 `PENDING` 列） |
| 3. 相對前一輪同 skill hash 且同 fixture hash 的 observation 無新的 PASS→FAIL 退化 | 不可判定——尚無 v5 下的原生 baseline |

### 2026-09-04 裁決後的阻擋清單

<!-- BEGIN ledger:gate-released -->
IDs: KI-01、03、04、05、07

**個別放行（5 筆）** — 依本檔 disposition 表的放行定義（`ACCEPT_AS_KNOWN` 放行；
`FIX_FIXTURE`／`FIX_SKILL` 僅在 action status = `DONE` 時放行）。

逐筆的放行依據**不在此重列**：它就是 ledger 對應列的 `required_action` 與
`action status`，那裡才是 authoritative。本區只承載集合本身。
<!-- END ledger:gate-released -->

<!-- BEGIN ledger:gate-blocked -->
IDs: KI-02、06、09、10、11、12、13、14、15、16、17、18、19、20、21

**仍擋住（15 筆）** — 依同一組放行定義取補集之外的部分；本區的集合獨立列出，
不由放行集合推導。

各筆「缺什麼」**不在此重列**：`NEEDS_EVIDENCE` 缺的是取得裁決所需的重跑，
`FIX_FIXTURE`／`FIX_SKILL`／`NOT_DONE` 缺的是修正後的重跑，逐筆內容見 ledger
對應列的 `required_action`。分類與筆數見 ledger:distribution 區。
<!-- END ledger:gate-blocked -->

<!-- BEGIN ledger:gate-totals -->
5 + 15 = 20，與 active ledger 列數相符（退役 ID 不計入，見「已退役／已合併的 ID」）。
<!-- END ledger:gate-totals -->
（**2026-09-04 更正**：舊版寫「仍擋住 16 筆」，其下三列卻只加總為 14，並把
`DONE` 的 KI-01／04 以「已計入上列」塞進阻擋側——那與本檔自己的放行定義衝突。
KI-01／04 依定義屬個別放行；該次新增 KI-21 後，當時阻擋數為 15。
**2026-09-05 更正**：KI-08 併入 KI-07 退役；該次更正後，個別放行由 6 降為 5，當時阻擋仍為 15。）

**2026-09-04 檢查時觀察到：當時的 `FIX_FIXTURE` 有 6 筆從未在修正後重跑。**
舊表沒有 action status 欄，那 6 筆看起來像是「已裁決要修 → 放行」，實際上
`required_action` 的「重跑該筆」從沒發生。這正是本次新增 action status 欄要防的誤讀。

**個別放行與阻擋的集合與筆數見上方受檢摘要（`ledger:gate-released`／
`ledger:gate-blocked`／`ledger:gate-totals`），此處不重列。整體發布 gate 維持關閉。**
判準 2（disposition 皆非 `PENDING`）依然只保證「都裁決過了」，不保證「都做完了」——
做完與否現在由 action status 承載。
（**2026-09-04 更正**：舊版寫「沒有任何一筆進入可發布狀態」，與同節「已解除」「放行」
直接衝突。**個別放行與整體 gate 是兩件事——個別放行不代表 gate 開啟。**
2026-09-05 KI-08 退役後個別放行數下修，逐筆現值見上方受檢摘要。）

### identity 凍結清單（2026-09-04 新增）

九輪證據綁定的每個 domain 由下列來源決定。**動到其中任何一項，對應證據即不再對應
要發布的版本**，`DONE` 必須退回重跑。清單依 `scripts/bundle-hash.sh` 的 allowlist 逐條核對。

**八個 domain 全列**（`hash_schema v6`；三個 skill domain 各自獨立，不可泛稱為 `skill`）。
末欄為 2026-09-04 文件批次的現算結果。
**其中兩個 domain 在九輪內是兩值**——`judgment_skill`（DE-01 的 A/B 受控變因）
與 `fixtures`（DE-01／KI-07 兩組）。**兩者都不可只列一個值。**

<!-- BEGIN ledger:freeze -->
| domain | 綁定值 | 綁定輪次 | 現算 | 來源 |
|---|---|---|---|---|
| `dispatch_skill` | `2d6c0d99b1c4ca927e2c06c82e065c389fa6a6b8ddbc325b0e9bde9bc071c4fc` | `de01-armA-r1`、`de01-armA-r2`、`de01-armA-r3`、`de01-armB-r1`、`de01-armB-r2`、`de01-armB-r3`、`ki07-armB-r1`、`ki07-armB-r2`、`ki07-armB-r3` | 相符 | `skills/harness/dispatch/` 的 `SKILL.md`、`references/**`、`scripts/**`、`assets/**`、`agents/**` |
| `judgment_skill` | `a26b436888d81e7181199932590ca29f21e58ff9b8066eb792458e68ed5b3d47` | `de01-armB-r1`、`de01-armB-r2`、`de01-armB-r3`、`ki07-armB-r1`、`ki07-armB-r2`、`ki07-armB-r3` | arm B 相符 | `skills/discipline/judgment/`（同上五類） |
| `judgment_skill` | `6e96c802be26d299a827bd93ed62ca576159444332c1ae641ac547e0ed9208d1` | `de01-armA-r1`、`de01-armA-r2`、`de01-armA-r3` | arm A 為歷史綁定，現行 tree 不再對應 | `skills/discipline/judgment/`（同上五類） |
| `token_preflight_skill` | `be72017e9fc7952e9a403cf90e951669496b08f4339938bc73a2829d44ef592a` | `de01-armA-r1`、`de01-armA-r2`、`de01-armA-r3`、`de01-armB-r1`、`de01-armB-r2`、`de01-armB-r3`、`ki07-armB-r1`、`ki07-armB-r2`、`ki07-armB-r3` | 相符 | `skills/discipline/token-preflight/`（同上五類） |
| `evaluator` | `65bc6c07d058697cda34045637d3223568cf09626cc38b8385bac46d41157480` | `de01-armA-r1`、`de01-armA-r2`、`de01-armA-r3`、`de01-armB-r1`、`de01-armB-r2`、`de01-armB-r3`、`ki07-armB-r1`、`ki07-armB-r2`、`ki07-armB-r3` | 相符 | `evals/judge.py`、`score.py`、`record.py` |
| `runner` | `005ed2f71ac49a8b6747dd1c43f42c8ee67315a9fb3ec8ce395f921ccf6cee3c` | `de01-armA-r1`、`de01-armA-r2`、`de01-armA-r3`、`de01-armB-r1`、`de01-armB-r2`、`de01-armB-r3`、`ki07-armB-r1`、`ki07-armB-r2`、`ki07-armB-r3` | 相符 | `evals/run-suite.sh`、`run-fixture.sh`、`transport.py`、`manifest.py` |
| `fixtures` | `7a1b54c1eddf710e030323ab6124e525d983ef5b32a1316d1780dd12d08d4738` | `de01-armA-r1`、`de01-armA-r2`、`de01-armA-r3`、`de01-armB-r1`、`de01-armB-r2`、`de01-armB-r3` | 相符（DE-01 組） | 該輪 `manifest.json` 的 `fixture_args`／`fixture_files` |
| `fixtures` | `dbbb4786db55bf8f568a5071f013072edb68d78273474ee49744a1654639656a` | `ki07-armB-r1`、`ki07-armB-r2`、`ki07-armB-r3` | 相符（KI-07 組） | 該輪 `manifest.json` 的 `fixture_args`／`fixture_files` |
| `execution_context` | `e7beb6eded81b04fae8bee2076dec7ceeefc5f55f60980aebd3b7fc4cfb9d4e0` | `de01-armA-r1`、`de01-armA-r2`、`de01-armA-r3`、`de01-armB-r1`、`de01-armB-r2`、`de01-armB-r3`、`ki07-armB-r1`、`ki07-armB-r2`、`ki07-armB-r3` | 相符 | 注入規則檔（`~/.claude/CLAUDE.md` 每輪副本）＋消毒後 settings＋`run-fixture.sh --print-context` descriptor |
| `evaluation_context` | `64996161082a8b43374e911c1b5e1d2c4ba36333cd324c53cfc37caecdc2b33c` | `de01-armA-r1`、`de01-armA-r2`、`de01-armA-r3`、`de01-armB-r1`、`de01-armB-r2`、`de01-armB-r3`、`ki07-armB-r1`、`ki07-armB-r2`、`ki07-armB-r3` | 相符 | `judge.py --print-context`：judge model／timeout／`claude_version`／flags／structured output |
<!-- END ledger:freeze -->

**三件容易誤判的事。**

1. **`skill` domain 對 `SKILL.md` 是整檔內容 hash，沒有 description／body 的切分。**
   實測：在 repo 外複本的 body 尾端加一行註解，`judgment_skill` 即由 `a26b4368…` 變成
   另一個值（**實際值依所加內容而定，不是固定常數**，重現時不必比對特定 hash）。
   舊版本節寫「優先評估能否只改 body 不改 description」——**該前提不成立，已刪除**。
   KI-02／14／15／21 全部需要 `SKILL.md` 變更，因此下一個 cycle 必然要重新產生行為證據。
2. **`evaluation_context` 含 `claude_version`**，host 的 CLI 一升版該 domain 就自行漂移，
   不需任何人動 repo 內的檔案。判定證據的有效期因此不完全由本 repo 控制。
3. **歷史九輪的 `execution_context` 只能驗合併值，不能拆解 component。**
   Batch 23a 已讓新 manifest 保存 rules／settings／descriptor 分項 hash，並由 `record.py`
   重算合併值；新 run 可歸因 drift。既有九輪使用舊 manifest，沒有分項資料，不能回溯補成
   contemporaneous evidence。固定 rules source 也只約束 Batch 23a 之後的新 run。

### 下一個 bounded cycle 的排序

1. **文件批次（零成本）** — 本次即為此批：ledger 修正、KI-21、blocker 集合修正、
   superseding recheck report、本凍結清單。不動 runtime，不 `git add`。
2. **Batch 23a（零成本，已完成）** — 固定 repo 內 rules source；execution／evaluation
   context 分項 hash 納入 manifest；建立獨立、不可覆寫且綁定 trace digest／run nonce 的
   post-judge manifest。歷史 run 不回溯升格。
3. **fresh-context 零成本驗收 23a** — 驗最新 runner／evaluator identity、manifest v3、
   context 分項重算、post-judge fail-closed 路徑與精確 run matrix。
4. **Batch 23b（零成本）** — 完成 KI-02／14／15／21 的 skill 修正與 selftest。
5. **fresh-context 零成本驗收 23b**，再重新估算成本；取得付費授權後一批跑完所有重跑。

**成本。** `USD 7.0407` 只是原九輪的實測值，不是本批預算。九輪實測單價為
subject `0.144485`／judge `0.095304`／preflight `0.062931`（USD／call）。
若最佳化分組約為 45 subject＋45 judge＋9 preflight，估算約 **USD 11.36**，尚未含波動。
**正式授權前必須重列 cell、估值與 hard cap**，不得沿用 `USD 7.0`。

實作與 selftest 本身零成本；**要付費的只有「重新產生對應最新 identity 的行為證據」**。
因此先把第 2、3 項全部做完並零成本驗收，再一次付清重跑，不要分批重跑。

上述文件批次當時不實作、不付費執行後續項目。
