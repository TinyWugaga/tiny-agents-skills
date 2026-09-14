# harness evals 導覽

本目錄存放 harness collection（`dispatch`、`judgment`、`token-preflight`）的行為評測，內容分四類：

- **工具**：runner、evaluator、零成本自測。
- **案例**：fixture、seed、注入規則與 DE-01 凍結輸入。
- **狀態與索引**：現況與 KI 以 `STATUS.md`、`KNOWN-ISSUES.md` 為準；驗收判定以對應的原始驗收紀錄為準；
  `VERIFICATION-LOG.md` 只作導覽索引，不作判定來源。
- **歷史證據**：驗收契約、驗收結果、診斷材料與 run 證據；內容凍結，不改寫。

本檔只是導覽，**不是**狀態或 gate 的依據。執行機制見 [`../README.md`](../README.md) 的「執行機制」章節。

## 目前狀態

- **Batch 23b 已暫停**（2026-09-13，Owner 決定）。恢復前必須完成的條件，寫在 [`STATUS.md`](STATUS.md) 最末段「Batch 23b 暫停」。
- KI、disposition 與發布 gate 以兩處為準，本檔不複製：
  - [`KNOWN-ISSUES.md`](KNOWN-ISSUES.md)
  - [`STATUS.md`](STATUS.md) 內的 `<!-- BEGIN status:current-summary -->` 區塊
- 現行 hash schema v6 的完整鏈路仍未完成原生 subject run，見 [`STATUS.md`](STATUS.md) 開頭「基礎設施狀態」。

## 接手先讀

1. [`STATUS.md`](STATUS.md)：開頭「基礎設施狀態」、current-summary 區塊、最末「Batch 23b 暫停」。這份檔是追加式帳本，歷史段落不改寫。
2. [`KNOWN-ISSUES.md`](KNOWN-ISSUES.md)：known-issue ledger（active ledger）。
3. [`../../../AGENTS.md`](../../../AGENTS.md)：本 repo 的開發、驗證與停止規範。
4. [`VERIFICATION-LOG.md`](VERIFICATION-LOG.md)：驗收導覽索引。判定以對應的原始驗收紀錄為準，見下方「歷史證據索引」的驗收結果表。
5. repo 外的 `~/.claude/harness-proposals/`：暫停前最後兩個工作包，即 r2 診斷結案與測試環境選案評估。

## 目錄樹

2026-09-14 的文件整理階段不搬移頂層歷史文件，也不另建 `records/` 子目錄。原因是這些路徑目前被凍結契約與
repo 外 baseline 引用，而 [`STATUS.md`](STATUS.md) 的「Batch 23b 暫停」段落規定暫停期間不得搬動凍結檔案或仍被引用的證據。
邏輯分組見下方「歷史證據索引」。

```text
evals/
├── README.md                    本導覽
│   ── 狀態與索引 ──
├── STATUS.md                    狀態帳本（追加式）
├── KNOWN-ISSUES.md              KI ledger
├── VERIFICATION-LOG.md          驗收導覽索引（非判定來源）
│   ── 工具 ──
├── run-suite.sh  run-fixture.sh  transport.py  manifest.py     runner
├── score.py  judge.py  record.py                              evaluator
├── *_selftest.py  acceptance-r2-regression.py                 零成本自測
│   ── 案例 ──
├── routing-fixtures.json        harness-routing fixture（其他 suite 的 fixture 在各 skill 的 evals/）
├── seed/                        fixture 的前置產出物
├── context/rules.md             注入受測 session 的規則檔
├── de01/                        DE-01 的凍結輸入與單筆 runner
│   ── 歷史證據 ──
├── ACCEPTANCE-r2.md             驗收契約（r2 provenance）
├── CLOSURE-20260904*.md         closure 契約與 verifier 報告封存
├── RECHECK-20260904-supersedes-closure.md   取代 closure 判定的 recheck 報告
├── DE-01-*.md                   DE-01 A/B 診斷：preflight、arms、結果
├── verification-contracts/      fresh-context 驗收契約
├── verification-records/        不可覆寫的驗收紀錄（檔名含 subject digest）
├── runs/<run-id>/               run 證據（raw/ 被 gitignore）
└── __pycache__/                 Python 快取（gitignore）
```

## 分類

2026-09-14 起，本目錄除 `runs/*/raw/`、`__pycache__/` 外全部已納入版控
（`runs/20260901-batch12-default-fixture-correction/` 只有 `raw/`，因此整個目錄為 ignored）。
**ignored 不代表可以刪除**：`raw/` 仍被 trace manifest、`evidence.sha256` 或 run record 綁定。

| 類別 | 路徑 | 用途 |
|---|---|---|
| 工具：runner | `run-suite.sh`、`run-fixture.sh` | 建立隔離環境、依 fixture 起受測 session |
| 工具：runner | `transport.py`、`manifest.py` | prompt 單行傳輸；run 前後的 identity 快照與 trace manifest |
| 工具：evaluator | `score.py`、`judge.py`、`record.py` | routing 判定、LLM judge 契約判定、run record |
| 工具：自測 | `judge_selftest.py`、`score_selftest.py`、`record_selftest.py`、`transport_selftest.py` | 零成本自測 |
| 工具：自測 | `acceptance-r2-regression.py` | r2 驗收量尺的 regression，讀 `ACCEPTANCE-r2.md` |
| 案例 | `routing-fixtures.json` | harness-routing suite（dispatch 與 judgment 的邊界、交棒） |
| 案例 | `seed/` | subject cwd 的前置檔案（SPEC.md、date.ts 等） |
| 案例 | `context/rules.md` | runner 注入的規則檔（`run-suite.sh` 的 `RULES_SOURCE`） |
| 案例 | `de01/` | DE-01 的 arm description、縮減 fixture、`run-one.sh` |
| 狀態 | `STATUS.md` | 各 batch 的紀錄、成本、current-summary |
| 狀態 | `KNOWN-ISSUES.md` | KI、disposition、action status |
| 索引 | `VERIFICATION-LOG.md` | 驗收導覽索引；不是判定或 gate 依據 |
| 歷史證據 | 頂層 `ACCEPTANCE-r2.md`、`CLOSURE-*`、`RECHECK-*`、`DE-01-*`，以及 `verification-contracts/`、`verification-records/` | 驗收契約、驗收結果、診斷材料；逐檔見下節 |
| 歷史證據 | `runs/<run-id>/` | run record（`<id>.json`／`.md`）、manifest、findings；`raw/` 為受測與 judge 的原始 trace |
| 快取 | `__pycache__/` | Python bytecode |

各 run 的判定（PASS、FAIL、INVALID、SUPERSEDED）記在 [`STATUS.md`](STATUS.md) 的「執行紀錄」與各 Batch 段落，
以及 [`KNOWN-ISSUES.md`](KNOWN-ISSUES.md) 的對象 run 表。本檔不重複列出。

## 歷史證據索引

依性質分組；位置不變。各輪驗收判定以下方「驗收結果」表中對應的原始紀錄為準，本表不複製；
[`VERIFICATION-LOG.md`](VERIFICATION-LOG.md) 只作導覽索引。沒有原始紀錄的輪次，本檔不代為認定判定。

**驗收契約**（交給 fresh-context verifier 的輸入）

| 檔案 | 對象 |
|---|---|
| [`ACCEPTANCE-r2.md`](ACCEPTANCE-r2.md) | harness provenance（hash schema v6）獨立驗收 r2 |
| [`CLOSURE-20260904.md`](CLOSURE-20260904.md) | 2026-09-04 targeted closure（FIX_FIXTURE ×8 ＋ FIX_SKILL ×2）；已驗收封存 |
| [`CLOSURE-20260904-followup.md`](CLOSURE-20260904-followup.md) | followup closure（KI-01 量詞修正 ＋ DE-01 preflight r2）；不取代上一份 |
| [`verification-contracts/20260906-round5.md`](verification-contracts/20260906-round5.md)、[`round6`](verification-contracts/20260906-round6.md)、[`round7`](verification-contracts/20260906-round7.md)、[`20260907-round8.md`](verification-contracts/20260907-round8.md) | ledger checker 2b 的第 5–8 次驗收；每份取代前一份，舊版保留為歷史 |
| [`verification-contracts/20260908-batch23b-accepted-risks.md`](verification-contracts/20260908-batch23b-accepted-risks.md) | Batch 23b Owner 裁決的 accepted risk 帶入項；不是完整契約 |
| [`verification-contracts/20260910-batch23b-semantic.md`](verification-contracts/20260910-batch23b-semantic.md) | Batch 23b 語意驗收（第 9 次）凍結契約 |

**驗收結果**（verifier 報告封存與不可覆寫紀錄）

| 檔案 | 內容 |
|---|---|
| [`CLOSURE-20260904-disposition.md`](CLOSURE-20260904-disposition.md) | 2026-09-04 Owner disposition／發布 gate 重算的 verifier 逐條報告原文；判定已被 RECHECK 取代 |
| [`RECHECK-20260904-supersedes-closure.md`](RECHECK-20260904-supersedes-closure.md) | 取代上一份的判定；同時是 ledger checker fresh-context 驗收的 subject 之一 |
| [`verification-records/20260905-round4-460e5a01bfd601ee.md`](verification-records/20260905-round4-460e5a01bfd601ee.md)、[`20260905-round4-f79e0b389b2455b0.md`](verification-records/20260905-round4-f79e0b389b2455b0.md) | 文件批次第 4 次驗收紀錄（該輪無 repo 內契約） |
| [`verification-records/20260907-round8-b377b27fb1cc2281.md`](verification-records/20260907-round8-b377b27fb1cc2281.md) | 第 8 次驗收紀錄；`verification-records/` 內沒有第 5–7 次的紀錄 |
| [`verification-records/20260910-round9-bdac1ff80e349878.md`](verification-records/20260910-round9-bdac1ff80e349878.md) | 第 9 次（Batch 23b 語意）驗收紀錄 |
| [`verification-records/20260910-round9-bdac1ff80e349878-correction1.md`](verification-records/20260910-round9-bdac1ff80e349878-correction1.md) | 第 9 次紀錄 output digest 的更正附錄；原紀錄不改 |

**診斷材料**（DE-01 description dilution A/B 與 KI-07 重跑）

| 檔案 | 內容 |
|---|---|
| [`DE-01-arms.md`](DE-01-arms.md) | 兩個 arm 的 description 原文與 SHA-256 凍結記錄 |
| [`DE-01-PREFLIGHT.md`](DE-01-PREFLIGHT.md) | exact-run 執行參數；不含判定 |
| [`DE-01-RESULTS-20260904.md`](DE-01-RESULTS-20260904.md) | 結果與逐筆判定 |
| [`de01/`](de01/)、`runs/de01-*`、`runs/ki07-*` | 凍結輸入與對應 run 證據 |

## 不可任意搬動、改名或刪除的路徑

identity 由 [`../../../scripts/bundle-hash.sh`](../../../scripts/bundle-hash.sh)（hash schema v6）計算。
搬動或改名下列路徑，會讓 identity 算不出來或值改變，也會讓既有紀錄的引用失效。

| 路徑 | 約束來源 | 搬動或刪除的後果 |
|---|---|---|
| `run-suite.sh`、`run-fixture.sh`、`transport.py`、`manifest.py` | `runner` domain 以固定相對路徑收錄 | runner identity 改變或計算失敗 |
| `judge.py`、`score.py`、`record.py` | `evaluator` domain | evaluator identity 改變 |
| `routing-fixtures.json`、`seed/`，以及各 skill 的 `evals/fixtures.json` | `fixtures` domain；manifest 記錄實際載入檔案的 repo 相對路徑 | fixtures identity 改變，manifest 無法重算 |
| `context/rules.md` | `run-suite.sh` 的規則來源；內容進入 `execution_context` | runner 啟動失敗或 execution_context 改變 |
| `runs/<run-id>/raw/` | `b23b-J-r1`、`de01-*`、`ki07-*` 由 `trace-manifest.json` 以檔名與 digest 綁定；`9d`、`9e` 由已追蹤的 `evidence.sha256` 綁定；其餘 run 的 raw 是 run record 與 KI 判定的原始依據 | 綁定驗證失敗或判定失去原始依據（ignored 不等於可刪） |
| `runs/<run-id>/` 目錄名 | STATUS、KNOWN-ISSUES、DE-01 文件以路徑引用；repo 外 `harness-baselines/` 的 R1 證據指向 `runs/b23b-J-r1/` | 引用斷裂 |
| `verification-records/*.md` | 檔名含 canonical subject digest，規定不可覆寫；路徑慣例由 [`../../../scripts/LEDGER-CHECK-SPEC.md`](../../../scripts/LEDGER-CHECK-SPEC.md) 規定；凍結契約與後續紀錄以完整路徑綁定；被 VERIFICATION-LOG 索引 | 驗收紀錄鏈斷裂 |
| `verification-contracts/*.md` | 驗收紀錄以完整路徑＋SHA-256 綁定；round5、round6、round8 契約內文自述所在目錄；後一版以同目錄檔名引用前一版 | 驗收紀錄無法對照契約；凍結內容與實際位置矛盾 |
| `CLOSURE-20260904*.md`、`RECHECK-*.md`、`DE-01-*.md` | round5–8 契約以完整路徑＋SHA-256 綁定 disposition、RECHECK、DE-01 preflight 與 results；`CLOSURE-20260904.md` 綁定 `DE-01-arms.md`；followup 契約以檔名引用 | 凍結契約無法重算版本綁定 |
| 頂層 `ACCEPTANCE-r2.md`、`CLOSURE-*`、`RECHECK-*`、`DE-01-*`、`VERIFICATION-LOG.md`、`KNOWN-ISSUES.md`、`STATUS.md`，以及 `verification-*/` 全部檔案 | repo 外 `~/.claude/harness-baselines/20260911-pre-b23b-rerun/repo-files.sha256` 以路徑逐檔記錄（Batch 23b 剩餘重跑的前置 baseline） | baseline 比對失敗 |
| `STATUS.md`、`KNOWN-ISSUES.md` | [`../../../scripts/ledger_check.py`](../../../scripts/ledger_check.py) 以 marker 解析；round4、round8 紀錄綁定當時的 digest | 帳本檢查失敗；歷史 digest 對照失據 |
| `de01/` | `DE-01-arms.md` 記錄 arm 的 SHA-256；DE-01 文件引用 | DE-01 證據無法重現 |
| `ACCEPTANCE-r2.md` | `acceptance-r2-regression.py` 以固定路徑讀取；同列於上述 repo 外 baseline | regression 失敗 |
| `../../../scripts/run-rescore.sh` | `rescore-runner` domain（repo 根目錄） | 重評 identity 改變 |

`skill` domain 只收錄各 skill 的 `SKILL.md`、`references/`、`scripts/`、`assets/`、`agents/`，**排除 `evals/`**。
所以本目錄的文件修改不影響受測 skill 的 identity。

## 常用零成本檢查

自測指令見 [`STATUS.md`](STATUS.md)「要接手的話」。
該段把 `~/.claude/CLAUDE.md` 列為規則檔來源，但現行 `run-suite.sh` 讀的是 `context/rules.md`，以程式為準。

帳本一致性檢查：

```sh
python3 scripts/ledger_check.py \
  --known-issues skills/harness/evals/KNOWN-ISSUES.md \
  --status skills/harness/evals/STATUS.md
```

## 清理

本目錄內的任何清理都要先取得 Owner 授權。
清理候選清單放在 repo 外：`~/.claude/harness-proposals/20260913-evals-guide/cleanup-candidates.md`。
