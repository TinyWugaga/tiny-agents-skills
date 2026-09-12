# Recheck report — supersedes the verdict of `CLOSURE-20260904-disposition.md`

本檔**取代** [`CLOSURE-20260904-disposition.md`](CLOSURE-20260904-disposition.md) 的**判定**
（該檔 §3 記「整體 PASS，W1–W14 全數 PASS，無 FAIL、無 UNVERIFIABLE」）。

**closure 原檔不得修改。** 它的 §4 自述為 verifier 報告的逐條原文轉錄，改寫會毀掉它唯一的
證據價值。因此本檔以新增方式覆蓋其判定，closure 保留為歷史紀錄。

## 1. 修正後的判定：**FAIL**

| 條 | closure 原判 | 修正後 | 理由 |
|---|---|---|---|
| W8 | PASS | **FAIL** | 它核對了 KI-02 的措辭與 routing 數字，但未核對 KI-02 理由所指的那一條 assertion（見 §2） |
| W9 | PASS | **UNVERIFIABLE** | 該格自述「比對基準取自本任務給定值」；`KNOWN-ISSUES.md` untracked、`git log --all` 無紀錄，09-02 版本無法 diff |
| W11 | PASS | **UNVERIFIABLE** | 該格自述「無 round-start 快照，歸屬判斷依刪除內容主題推定」 |
| W12 | PASS | **UNVERIFIABLE** | closure 該格實際引用的句子為真；RECHECK 原本指為假的是同一行號範圍內的**另一句**，而該句是否落在其刪節號涵蓋範圍內已無法重建（見 §3） |
| 其餘 | PASS | PASS | 可獨立重算，見 §5 |

依 `FAIL > UNVERIFIABLE > PASS`，整體為 **FAIL**。
closure §3 的「無 FAIL、無 UNVERIFIABLE」與它自己 §5 列出的兩項限制不相容。

## 2. W8 的實質缺陷：KI-02 的分類理由不受證據支持

KI-02 原記 `skill_defect`（DE-01 已證），理由是「arm B routing 3/3 觸發、contract 3/3 FAIL
——skill 已在 context 內仍未輸出該行為」。逐 assertion 重讀
`runs/de01-arm*/raw/judgment__positive-2.judge.json`：

| | `.required[0]` fresh-context | `.required[1]` 三值判定 | contract |
|---|---|---|---|
| arm B r1／r2／r3 | `PASS/FAIL/PASS` = 2/3 | `FAIL/PASS/FAIL` = 1/3 | FAIL ×3 |
| arm A r1／r2／r3 | `FAIL/FAIL/PASS` = 1/3 | `FAIL/FAIL/FAIL` = 0/3 | FAIL ×3 |

**沒有任何一條 assertion 在 arm B 是 3/3 FAIL**，每輪 contract FAIL 的成因不同
（r1、r3 是 `.required[1]`，r2 是 `.required[0]`）。KI-02 主張的行為寫在 `.required[0]`，
該條在 arm B 多數輪次是 PASS——原理由的事實前提不成立。
`DE-01-RESULTS-20260904.md:79` 亦自述「本檔不對 KI-02 下判定」。

**已處置**：KI-02 改判 `stochastic_known_issue` 並錨定 `.required[0]`（同 bundle 有翻轉），
disposition 維持 `FIX_SKILL`／`NOT_DONE`；`.required[1]` 另立 **KI-21**；
ledger 新增「錨定 assertion」契約條款。

## 3. W12：一句為真、一句為假，歸屬無法重建

舊版本節裡有兩句相鄰但獨立的敘述，必須分開看：

| 敘述 | 真假 |
|---|---|
| 「任何 description 變更都會讓現行 DE-01 arm B 身分失效」 | **為真** |
| 「優先評估能否只改 body 不改 description」（即：只改 body 可保留 identity） | **為假** |

第二句為假：`scripts/bundle-hash.sh` 的 `skill` mode 對 `SKILL.md` 取整檔內容 hash，
**沒有 description／body 的切分**。實測（repo 外複本，repo 未動）：僅在 body 尾端加一行註解，
`judgment_skill` 即由 `a26b4368…` 變成另一個值（實際值依所加內容而定，不是固定常數）。

**closure 的 W12 格引用的是第一句**（`CLOSURE-20260904-disposition.md:59`：
「`KNOWN-ISSUES.md:321-329`「**任何 description 變更…**」……」）。該句為真，
所以不能說 W12 驗證了一個假敘述。第二句雖落在它引用的同一行號範圍內，
但**是否落在那個刪節號的涵蓋範圍已無法重建**——被引用的前一版檔案已不存在，
`KNOWN-ISSUES.md` 為 untracked 且 `git log --all` 無紀錄。
因此 W12 判 **UNVERIFIABLE**，不是 FAIL 也不是 PASS。

兩句中為假的那一句已從兩份文件刪除，改為 identity 凍結清單。
**整體判定不受影響**：W8 單獨即足以使整體為 FAIL。

這一格仍留下一個教訓：closure 的 W12 只驗證了「兩份文件說法一致」，
**一致不等於為真**——兩份文件同時寫錯同一件事時，一致性檢查不會有任何反應。

## 4. 2026-09-04 那次 16 條複驗的結果

FAIL 6 條、UNVERIFIABLE 1 條、其餘 PASS。

> **本節記錄 2026-09-04 當時的判定與當時的處置。** 其中三格的處置或數字已被
> 2026-09-05 的 KI-08 退役取代，逐格標註於下。**現值一律以 `KNOWN-ISSUES.md` 為準：
> active ledger 20 筆、個別放行 5、阻擋 15。**

| 條 | 判定 | 摘要 |
|---|---|---|
| 7 | FAIL | KI-02 分類理由不受 `.required[0]` 證據支持（§2）。**已處置** |
| 9 | FAIL | KI-08 的 classification「下游，非獨立缺陷」不屬詞彙表五值。當時處置為改填 `skill_defect` 並註明共用 root cause。**該處置已於 2026-09-05 被推翻**——`skill_defect` 要求「trace 顯示行為缺席」，與其自身的 contract 3/3 PASS 矛盾；KI-08 改為併入 KI-07 退役（§7） |
| 11 | FAIL | 計數正確，但 `N/A` 定義「該 disposition 不要求行動」與 `NEEDS_EVIDENCE` 四筆的 required_action 衝突。**已處置**（改為只追蹤 `FIX_FIXTURE`／`FIX_SKILL` 的 remediation） |
| 12 | FAIL | 「仍擋住 16 筆」與其下三列加總 14 矛盾；`DONE` 的 KI-01／04 被塞進阻擋側。**已處置**（當時：放行 6、阻擋 15、合計 21；**2026-09-05 KI-08 退役後為放行 5、阻擋 15、合計 20**） |
| 13 | FAIL | 「沒有任何一筆進入可發布狀態」與同節「已解除 2＋放行 2」衝突。**已處置**（當時改為「6 筆個別放行，gate 仍因 15 筆阻擋而關閉」；**2026-09-05 後為 5 筆個別放行**，gate 仍關閉） |
| 15 | FAIL | closure 的 W8／W9／W11 判定（§1）。W12 於 2026-09-05 另判 UNVERIFIABLE（§3） |
| 16 | UNVERIFIABLE | repo 內僅有實作者建立的轉錄，agentId／模型／時間皆為自述，無第二來源可證舊 verifier 為 fresh context |
| 1–6、8、10、14 | PASS | 見 §5 |

## 5. 可獨立重算的部分（全部通過）

- 九輪皆 `contract_evidence`、`invalid_reason=null`、`cli_failed=0`、`provenance.problems=[]`。
- routing matrix 重算與宣稱逐格相符；`ambiguous-1` continuation contract 3/3 PASS。
- 成本 Decimal 加總 `7.040678` → `7.0407`；subject 27／judge 27／preflight 9 = 63 paid calls。
- 八個 identity domain 去重：只有 `judgment_skill`（A/B）與 `fixtures`（DE-01／KI-07）為兩值。
- trace-manifest 所列 **72 個檔案** sha256 逐一相符，0 mismatch；九份 canonical `files` digest
  重算後與 manifest 自述、record `provenance.trace_manifest_digest`、內嵌副本三處一致。
- `judge`／`score`／`record`／`transport` 四支 selftest 全部通過；
  `hash-domain-selftest.sh` 36 案例通過；四組 `--dry-run` 為 18／28／4／1 筆。
- 現算 `skill`＝`a26b4368…`、`runner`＝`005ed2f7…`、`evaluator`＝`65bc6c07…`、
  `fixtures`＝`7a1b54c1…`／`dbbb4786…`，皆與九輪綁定相同。

## 6. Provenance 限制（不可事後補強）

**`.judge.json` 不在任何 contemporaneous manifest 內。** `run-suite.sh` 在 subject 迴圈一結束
就產生 trace manifest，judge 尚未執行，`.judge.json` 當時不存在——這不是 suffix 清單的疏漏，
是順序決定的。因此 §2 的 assertion-level 證據**只能證明檔案現在的內容，不能證明它產出後
未被改動**。

現況指紋（2026-09-04 唯讀重算，**present-state fingerprint，不是 contemporaneous provenance**）：

| 集合 | 檔數 | 彙總 sha256 |
|---|---|---|
| `runs/{de01,ki07}-arm*/raw/*.judge.json` | 27 | `281f739d1b6d27ffaf32a83f9e82dd0b16acc63c91a6803ad92f3e83b355adcd` |
| `runs/{de01,ki07}-arm*/raw/*.err` | 36 | `9b003f7eb27be0d8f49836d1e92febffe70fc2de34baf3e73a2c7b8463ab78f5` |

（彙總方式：`find … | sort | xargs shasum -a 256 | shasum -a 256`。）

**`execution_context` 的合併值已重算相符，但無法拆解各 component。**
依 `run-suite.sh` 的真實順序重建三個 component 後現算為 `e7beb6ed…`，與九輪綁定相同。
⚠ **重建時漏設 `HARNESS_SETTINGS_FILE`，descriptor 會變成 `settings=absent`，
算出假的 drift**——本輪一度據此誤報該 domain 已 drift，後以完整重建推翻。
`manifest.json` 只保存合併後的單一值，沒有分項 hash，因此該 domain 一旦與綁定值不符，
**仍無法歸因到哪一個 component**。修法（分項 hash 進 manifest）屬 `manifest.py`，
列入實作批次。

八個 domain 於本次文件批次後全部現算並與九輪綁定相符：
`dispatch_skill 2d6c0d99…`、`judgment_skill a26b4368…`、`token_preflight_skill be72017e…`、
`evaluator 65bc6c07…`、`runner 005ed2f7…`、`fixtures 7a1b54c1…`／`dbbb4786…`、
`execution_context e7beb6ed…`、`evaluation_context 64996161…`（含 `claude_version=2.1.247`）。

## 7. 本檔的證據力邊界

本次 16 條複驗以唯讀方式執行，未修改 repo；其後的文件修正（本檔與 ledger／STATUS）
才動檔案。**複驗的後半段與 Codex 複測共用對話 context，因此本檔不是獨立的 fresh-context
見證**，與 closure §6 的自述同屬同一類限制。第 5 節每一項都機械可重算，
不依賴對驗收者的信任；第 2 節依賴 §6 所述的 present-state 限制。

**驗收歷程與狀態不在本檔。** 見 [`VERIFICATION-LOG.md`](VERIFICATION-LOG.md) 與
`verification-records/` 下不可覆寫的逐輪紀錄。

**為什麼移出去。** 本檔原本在自己內部記錄自己的驗收狀態（歷程表與「尚缺第 N 次」），
那造成無解的回歸：**寫入第 N 次的結果就會改動剛被第 N 次驗證的檔案，於是又需要第 N+1 次。**
本檔現在只保留判定與證據——那些是穩定的，不會因為又跑了一輪驗收而改變。

值得記錄的一點：KI-08 兩度嘗試填進五值詞彙表都失敗，
第二次還是照 minimal fix 建議填了 `skill_defect`。真正的原因是它本來就不是獨立問題——
**在 taxonomy 裡找不到位置，往往代表那一列不該存在，而不是 taxonomy 少一個值。**
新增 `downstream_resolved` 之類的第六值曾被提出並否決：`resolved` 是 lifecycle state，
屬 disposition／action status 的職責，混進 classification 會讓兩者失去分工。

**下一輪的最小改善**：把 `KNOWN-ISSUES.md` 納入 git 追蹤（需 commit，非 `git add`），
讓 W9 那類比對在下一輪可獨立重做。本輪未 commit，pre/post SHA 與可反向重建的副本
保存在 session scratchpad，未寫入 repo。
