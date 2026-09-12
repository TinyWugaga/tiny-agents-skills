# 驗收索引

**本檔只是索引，不是 gate 的依據。** authoritative 的是 `verification-records/` 下
不可覆寫的逐輪紀錄；本檔可被編輯，因此**不得單獨作為某輪已通過的證據**。

## 紀錄檔名與 canonical digest 規則

檔名格式：`<YYYYMMDD>-round<N>-<subject-digest 前 16 hex>.md`。

`subject-digest` ＝ 下列字串的 SHA-256，內容與身分綁定——subject 一變就是新的一份紀錄，
不是修改舊的：

* 每列為 `<sha256>` ＋ **兩個空格** ＋ **完整 repo-relative path**
* 依該紀錄第 1 節的表列順序
* 以 `\n` 連接
* **無尾換行**

⚠ **這條規則於 2026-09-06 才被固定。** 在此之前規則只以一句話帶過，
第 4 次的紀錄因此宣稱用「相對路徑」、實際卻用**裸檔名**計算，檔名與自述不符。
三種變體的實測值列在
[`20260905-round4-460e5a01bfd601ee.md`](verification-records/20260905-round4-460e5a01bfd601ee.md) §0。

## 為什麼驗收狀態不放在被驗文件裡

`RECHECK-20260904-supersedes-closure.md` 原本在自己內部記錄自己的驗收歷程
（歷程表與「尚缺第 N 次」）。那造成無解的回歸：**寫入第 N 次的結果就會改動剛被
第 N 次驗證的檔案，於是又需要第 N+1 次。** 2026-09-06 起狀態移出，
RECHECK 只保留判定與證據（那些是穩定的）。

驗收契約應把本檔與 `verification-records/` **排除在被驗 subject 之外**，
否則同一個回歸會以另一種形式回來。

## 文件批次

| 輪次 | 日期 | 結果 | 紀錄 |
|---|---|---|---|
| 同 context 機械檢查 | 2026-09-04 | 通過 | 無紀錄；不構成獨立見證，僅防低階錯誤 |
| fresh-context 第 1 次 | 2026-09-04 | FAIL：`judgment_skill` 兩值只列一個 | **無不可覆寫紀錄**（當時未建立本機制） |
| fresh-context 第 2 次 | 2026-09-05 | FAIL：KI-08 的 `skill_defect` 與其 3/3 PASS 證據矛盾；`required_action` 無可完成動作 | **無不可覆寫紀錄** |
| fresh-context 第 3 次 | 2026-09-05 | FAIL：`STATUS.md` 的 W12 敘述與 §4 現值未隨改判同步 | **無不可覆寫紀錄** |
| fresh-context 第 4 次 | 2026-09-05 | **達到門檻**；正式 verdict `UNVERIFIABLE` | [`20260905-round4-460e5a01bfd601ee.md`](verification-records/20260905-round4-460e5a01bfd601ee.md) |

**第 4 次的 gate 依據是 `460e5a01bfd601ee` 那一份。**
舊的 [`20260905-round4-f79e0b389b2455b0.md`](verification-records/20260905-round4-f79e0b389b2455b0.md)
**已 superseded、不得作為 gate 依據**：它記載的是同一次驗收、結論無誤，
但 digest 以裸檔名計算而自述為相對路徑，身分綁定失效。
舊檔**保留、不修改、不刪除**——它自己宣告不可覆寫，改它會破壞紀錄機制的契約。

前三輪只有本索引的一行摘要，**沒有可獨立重算的紀錄**——它們發生在本機制建立之前。
那三行是實作者轉錄，證據力低於第 4 次的紀錄，更低於一次真正的獨立驗收。

## 2a：ledger-consistency checker

| 輪次 | 日期 | 結果 | 紀錄 |
|---|---|---|---|
| fresh-context 第 1 次 | 2026-09-06 | FAIL：73 個 error code 中 19 個無任何案例覆蓋 | **無不可覆寫紀錄** |

## 2b：文件整合與正式 checker 接線

| 輪次 | 日期 | 結果 | 紀錄 |
|---|---|---|---|
| fresh-context 第 5 次 | 2026-09-06 | FAIL：第 7 條——round-4 record 的 canonicalization 自述與實際 digest 不符 | **無不可覆寫紀錄**（FAIL 輪次不產生 record） |
| fresh-context 第 5 次（重跑） | 2026-09-06 | FAIL：第 2 條——`ledger_check.py` 對 narrative 區大量漏檢，gate 區內翻掉一筆 disposition 也不會被抓到 | **無不可覆寫紀錄** |
| fresh-context 第 6 次 | 2026-09-06 | **UNVERIFIABLE、未達門檻**：第 16 條缺 pre-2b snapshot 不可判；第 18 條為預期內。其餘 16 條 PASS | **無不可覆寫紀錄**（未達門檻不產生 record） |
| fresh-context 第 7 次 | 2026-09-06 | **FAIL、未達門檻**：第 16 條——marker 外仍有未受檢的 ledger 現值；第 17 條經複核由 PASS 改判 `UNVERIFIABLE` | **無不可覆寫紀錄**（FAIL 輪次不產生 record） |
| fresh-context 第 8 次 | 2026-09-07 | **達到門檻；正式 verdict `UNVERIFIABLE`**（1–16 `PASS`，17、18 `UNVERIFIABLE`） | [`20260907-round8-b377b27fb1cc2281.md`](verification-records/20260907-round8-b377b27fb1cc2281.md) |

**2b 已於第 8 次達到門檻**（2026-09-07）：無 FAIL，`UNVERIFIABLE` 僅限第 17、18 條，
整體正式 verdict 記為 `UNVERIFIABLE`，**不得寫成 `PASS`**。
契約 `verification-contracts/20260907-round8.md`（`c3f8842a…`），
subject digest `b377b27fb1cc2281aa4c4f15556e21aa3c977e9b0cf573d45c4139bd377330eb`。

**第 5–7 次的失敗與更正歷史保留在下方各節，不因達到門檻而改寫或刪除。**
那四輪的修正都動到被驗物本身，**不得沿用任何一輪的逐條 PASS**：
第 5 次的修正動到 `VERIFICATION-LOG.md`、`verification-records/` 與契約；
重跑的修正動到 `ledger_check.py`、selftest、mutants、`LEDGER-CHECK-SPEC.md`、
`KNOWN-ISSUES.md`、`STATUS.md`；第 6 次的修正動到 `KNOWN-ISSUES.md` 與本檔；
第 7 次的修正動到 `KNOWN-ISSUES.md`、`STATUS.md` 與本檔。
第 8 次據此以新契約重跑了全部 18 條，未沿用任何一輪的逐條結果。

**達到門檻不等於 2b 沒有 provenance 缺口。** 契約第 18 條的六類缺口全部仍然開放，
逐項列在 round-8 record §8；第 17 條的「相對 pre-2b 新增恰為三項」結構上不可重建。
第 9 次起第 17 條必須明文把比較起點換成本輪 baseline。

### 第 5 次重跑的 FAIL 與處置（2026-09-06）

漏檢的根因不是少寫一條 regex，是 narrative 區**根本沒有被解析**：
`gate_ids()` 只讀唯一一行 `IDs:`，`declared()` 的 pattern 讀不到表格欄位，
`equation()` 用 `re.search` 只取第一條。實測在 `gate-released` 補一張表把一筆
disposition 翻掉、塞入不存在的 `KI-99`、再補一條 `9 + 99 = 108`，全部回 `rc=0`。

處置採**收斂文件表示**而非繼續加 regex——後者每換一種措辭就多一個漏洞，
是「每輪修正都增加特例、沒有消除原因」的換路訊號。五個 narrative 區改為正面表列
（規則見 `scripts/LEDGER-CHECK-SPEC.md` 硬性設計約束第 4 點），重複的現值宣稱
從文件刪除、改為指向 authoritative ledger。

⚠ **殘留風險：把現值宣稱搬到 marker 之外，依構造偵測不到。** 這是 review 紀律，
不是機械保證，已寫進 spec 並在契約列為獨立條件。

### 第 6 次的判定更正與處置（2026-09-06）

**verifier 初判第 16 條 FAIL，經複核更正為 `UNVERIFIABLE`。** 契約第 16 條的判準是
「本批次刪掉的重複現值有沒有被**搬到** marker 外」，而 repo 內無 2b 的 pre-cycle
snapshot，搬移與否不可重建；依契約硬限制「含無法驗證的子項時該條整條判
`UNVERIFIABLE`」，該條就是 `UNVERIFIABLE`。初判改用較廣的「marker 外是否存在未受檢
現值」結案，**屬於替換驗收條件**——驗收端只能依契約字面判定，認為判準有問題應照字面
判完再另段說明。

**實質發現仍然成立**（與 verdict 無關）：`KNOWN-ISSUES.md` 當時第 373 行
「仍有 15 筆阻擋」是 marker 外未受檢的現在式現值。實測在 repo 外複本把 ledger 改成
放行 6／阻擋 14 並同步 marker 內全部宣稱後，`ledger_check` 仍回 `rc=0`「一致」，
而該行仍宣稱 15。

**處置：修文件，不擴大 checker 掃描範圍。** 擴大掃描會讓歷史段的正確數字重新變成掩護，
正是 checker 刻意只解析 marker 內的原因。`KNOWN-ISSUES.md` marker 外六處敘述改為
明確限定時間（「該次／當時／舊版」），重複的現值筆數改為指向受檢摘要；
`STATUS.md` 未動——其命中都在有編號的歷史批次段落內且數值為舊值，
改寫等於改寫歷史紀錄。判準看完整上下文，不只看動詞或數字是否等於現值。

**第 16 條於下一輪改為可直接驗證的現況判準**，不再依賴缺失的 snapshot，
且新判準不追溯套用到第 6 次。

**證據歸屬。** 本輪複核只支持三件事：22 個鎖定檔案的 hash 比對、第 373 行漏檢的實測、
以及第 16 條的契約解讀。**其餘 16 條仍僅由第 6 次 verifier 該輪的證據支持，未取得第二來源。**
該 verifier 的 session／task ID 為 `unavailable`。

**第 6 次另發現一類 provenance 缺口**（記入契約的 UNVERIFIABLE 條）：有效 record
`20260905-round4-460e5a01bfd601ee.md` §1 的三個 subject hash 所指的檔案內容已被 2b 覆寫，
repo 內無倖存副本——只能驗證「檔名確由該三值依 §0 規則導出」的內部一致性，
無法驗證該三值曾對應真實檔案內容。該 record 的 subject 綁定本身也是轉錄值。

### 第 7 次的 FAIL 與處置（2026-09-07）

**第 16 條 FAIL。** marker 外仍有未受檢的 ledger 現值，經該輪 verifier 與一次定向複查
合計指認 10 處：`KNOWN-ISSUES.md` 的 `NEEDS_EVIDENCE` 筆數與 ID 集合、`## Ledger` 標題的
active 筆數、執行順序段兩處 `FIX_FIXTURE` 筆數、發布 gate 表的 `PENDING` 現值、
判準 2 的 `PENDING` 現值、下一 cycle 段的 blocker 筆數；`STATUS.md` 的 blocker 筆數、
`FIX_FIXTURE` NOT_DONE 筆數、執行順序段的 `FIX_FIXTURE` 筆數。
其中發布 gate 表那一處經實測：在 repo 外複本把 `PENDING` 由 0 改成 1，`ledger_check`
仍回 `rc=0`「一致」。**處置：十處全部改為指向受檢摘要或去除數值，不補日期規避。**

**第 16 條的漏判形狀值得記錄。** 該輪初次掃描以逐行 pattern 進行，發布 gate 表那一列
確實出現在命中清單內，卻在分節判斷時整張表被略過。逐行掃描與「表格作為獨立一類」
是兩種方法，前者命中不等於後者已做。第 8 次契約因此把表格掃描列為強制的第二種方法。

**第 17 條由 PASS 改判 `UNVERIFIABLE`。** 「相對 pre-2b 新增恰為三項」需要 pre-2b 的
條目清單才能排除「一項被替換、另一項新增」，該清單不存在。初判只驗到 55−52 的算術
與三個條目存在即記 PASS，並把缺口寫進第 18 條——那是同一份報告內的自我不一致。

**由此暴露的判準缺陷（第 8 次契約已改）。** 舊 §4 的「含無法驗證的子項時該條整條判
`UNVERIFIABLE`」會讓 HEAD 改變、暫存區非空這類**可驗**的退化被同條的歷史缺口掩蓋。
改為**條內同樣採 `FAIL > UNVERIFIABLE > PASS`**，並適用於全部條件，不只第 17 條。
門檻相應改為「無 FAIL，且 `UNVERIFIABLE` 僅限第 17、18 條」。

**新增 baseline，但不改變歷史缺口的歸屬。** 第 7 次修正定稿後保存兩份 repo 外 baseline
（`status-entries` 與 `content-manifest`），由第 8 次契約鎖定其 hash。它們只建立
**第 8 次之後**的比較起點：第 9 次起第 17 條必須明文更換比較起點，
「相對 pre-2b」的缺口仍留在第 18 條，不因 baseline 存在而關閉。
兩份用途不可互換——`status-entries` 只證明條目差異，untracked 檔案改內容不改條目，
byte 級副作用由 `content-manifest` 承載。baseline 放 repo 外，避免保存動作本身改變被測的
`git status`；代價是它不受版本控管，hash 不符或檔案不存在時驗收者應停止並回報，不得自行重建。

**`scripts/bundle-hash.sh` 於第 8 次契約落鎖，但第 18 條的該類缺口只移除一半。**
新鎖定值證明的是「本輪重算所用的量測工具版本」，**不能**回溯證明九輪 run 產生當時
或 pre-2b 的該檔內容相同。歷史量測工具版本仍屬不可驗。

**第 7 次的 subject digest 不作廢。** 它仍識別第 7 次當時的那一版產出物，
只是不適用於第 8 次的 subject——作廢與不適用是兩件事。

**交付格式衝突已修正。** 第 7 次契約訂「報告不超過 40 個 Markdown source lines」，
而第 14、16 條要求逐支具名對照與逐處掃描理由，兩者無法同時滿足；該輪報告實際
遠超過 40 行且未指出衝突，等於默默改了交付條件。第 8 次契約改為分層交付：
摘要不超過 40 行，逐條證據與掃描明細另節、不設行數上限。

### 第 8 次的更正與補驗（2026-09-07）

第 8 次整體**達到門檻**，但報告有四處證據表述須更正、一條須補驗。
**這些更正不改變任何逐條 verdict，也不改變整體結果。**
完整內容寫在 [`20260907-round8-b377b27fb1cc2281.md`](verification-records/20260907-round8-b377b27fb1cc2281.md)
§4、§5、§7；本節只是索引。

1. **第 4 條補做（來源錯誤，資料無缺陷）。** 契約要求自九份 run record 重算 freeze 表，
   報告當時實際用的是 `manifest.json`。其後才以 `runs/<id>/<id>.json` 補算：
   record identity 9/9 正確、record hashes 與 manifest start／end hashes **0 mismatch**、
   10 組 domain/值的綁定輪次集合與 freeze 表逐組相等。
   **不得改寫成「原報告當時已從 record 重算」**——支持該條的是補做的重算，不是當時的操作。
2. **撤回「第 7 次 (g) 漏檢已不復現」。** 第 7 次漏的是 marker **外** gate 表的 `PENDING`，
   第 8 次的 (g) 改的是 marker **內** 的 `ledger:distribution`，不是同一個注入。
   marker 外的重複現值是**由文件收斂移除、並由第 16 條人工掃描確認**才不再成立，
   **不是 checker 增加了 marker 外的偵測能力**——那一層仍然只是 review 紀律。
3. **context hash 與 session UUID 的證據力收斂。** context 重建 hash 相等只支持
   「本輪重建輸入在既定 canonicalization 下吻合歷史綁定」，不證明原始檔案一直未變，
   也不涵蓋消毒時被排除的 settings 鍵。session 識別值由環境路徑取得，
   **不構成身分認證或 freshness 證明**；task ID 為 `unavailable`。
4. **撤回第 16 條的「6 非現值」。** `FIX_FIXTURE` 的 `NOT_DONE` 現值正是 6；
   該處的歷史分類只依段內自述「**當時的**」成立，不依數字是否等於現值。

**更正／補驗紀錄原檔在 repo 外**（session scratchpad，`ce3efd08…`），
**不受版本控管、不得作為長期 authoritative evidence**；
所有影響判讀的內容已完整寫入 round-8 record，該 record 自足。

**該輪之後的複核不構成第二次完整獨立驗收**：複核方只核對了契約 hash、鎖定檔案與 baseline、
subject digest、正式 checker 與 marker 外表格清單，其餘條件未全部重跑。

## 待改善

1. ~~**驗收契約未落檔。**~~ 已處置：自第 5 次起契約落檔於 `verification-contracts/`，
   並由外部 prompt 鎖定其 SHA-256。第 4 次的 16 條契約仍只存在於 session scratchpad，
   該輪的契約 hash 無法從 repo 重算。
2. **verifier 身分無法證明。** 第 4 次的 session／task ID、模型、執行時間全部未取得，
   因此**無法證明 freshness**。自第 5 次起契約要求 verifier 回報 session／task ID
   並在取不到時明白寫出；原始輸出 digest 改由呼叫端事後計算（verifier 自算是自我指涉）。
3. **這些檔案本身未納入 git 追蹤**（需 commit，非 `git add`），
   因此「某輪之後有沒有被改過」仍只能靠 hash 比對，不能靠版本歷史。
4. **canonical 規則曾只以一句話帶過，導致第 4 次的 digest 與自述不符。**
   規則現已固定於本檔上方與 correction record §0。下一輪應確認新舊兩份 record 的
   角色在契約內被明確鎖定，避免 gate 指向失效紀錄。
