# harness evals 導覽

本目錄存放 harness collection（`dispatch`、`judgment`、`token-preflight`）的行為評測：
runner、評分工具、fixture、狀態帳本、驗收紀錄與 run 證據。
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
4. [`VERIFICATION-LOG.md`](VERIFICATION-LOG.md)：驗收索引。具權威性的是 [`verification-records/`](verification-records/)。
5. repo 外的 `~/.claude/harness-proposals/`：暫停前最後兩個工作包，即 r2 診斷結案與測試環境選案評估。

## 目錄樹

```text
evals/
├── README.md                    本導覽
├── STATUS.md                    狀態帳本（追加式）
├── KNOWN-ISSUES.md              KI ledger
├── VERIFICATION-LOG.md          驗收索引
├── ACCEPTANCE-r2.md             驗收契約（r2 provenance）
├── CLOSURE-20260904*.md         closure 契約與報告
├── RECHECK-20260904-supersedes-closure.md
├── DE-01-*.md                   DE-01 A/B 的 preflight、arms、結果
├── verification-contracts/      fresh-context 驗收契約
├── verification-records/        不可覆寫的驗收紀錄（檔名含 subject digest）
├── run-suite.sh  run-fixture.sh  transport.py  manifest.py     runner
├── score.py  judge.py  record.py                              evaluator
├── *_selftest.py  acceptance-r2-regression.py                 零成本自測
├── routing-fixtures.json        harness-routing fixture（其他 suite 的 fixture 在各 skill 的 evals/）
├── seed/                        fixture 的前置產出物
├── context/rules.md             注入受測 session 的規則檔
├── de01/                        DE-01 的凍結輸入與單筆 runner
├── runs/<run-id>/               run 證據（raw/ 被 gitignore）
└── __pycache__/                 Python 快取（gitignore）
```

## 分類

「git」欄是 2026-09-13 的狀態：`tracked`、`tracked*`（已追蹤但有未提交的修改）、`untracked`、`ignored`。
**untracked 或 ignored 不代表可以刪除。** 下表多數證據檔尚未納入版控，但仍被 hash 或文件引用。

| 類別 | 路徑 | 用途 | git |
|---|---|---|---|
| 工具：runner | `run-suite.sh`、`run-fixture.sh` | 建立隔離環境、依 fixture 起受測 session | tracked* |
| 工具：runner | `transport.py`、`manifest.py` | prompt 單行傳輸；run 前後的 identity 快照與 trace manifest | untracked |
| 工具：evaluator | `score.py`、`judge.py`、`record.py` | routing 判定、LLM judge 契約判定、run record | tracked* |
| 工具：自測 | `judge_selftest.py`、`score_selftest.py` | 零成本自測 | tracked* |
| 工具：自測 | `record_selftest.py`、`transport_selftest.py` | 零成本自測 | untracked |
| 工具：自測 | `acceptance-r2-regression.py` | r2 驗收量尺的 regression，讀 `ACCEPTANCE-r2.md` | tracked |
| fixture／seed | `routing-fixtures.json` | harness-routing suite（dispatch 與 judgment 的邊界、交棒） | tracked* |
| fixture／seed | `seed/` | subject cwd 的前置檔案（SPEC.md、date.ts 等） | tracked |
| fixture／seed | `context/rules.md` | runner 注入的規則檔（`run-suite.sh` 的 `RULES_SOURCE`） | untracked |
| fixture／seed | `de01/` | DE-01 的 arm description、縮減 fixture、`run-one.sh` | untracked |
| 狀態帳本 | `STATUS.md` | 各 batch 的紀錄、成本、current-summary | tracked* |
| 狀態帳本 | `KNOWN-ISSUES.md` | KI、disposition、action status | untracked |
| 狀態帳本 | `VERIFICATION-LOG.md` | 驗收索引（非 gate 依據） | untracked |
| 契約與驗收紀錄 | `verification-contracts/`、`verification-records/` | 驗收契約；以 digest 命名、不可覆寫的紀錄 | untracked |
| 契約與驗收紀錄 | `CLOSURE-20260904*.md`、`RECHECK-*.md`、`DE-01-*.md` | 2026-09-04 的 closure、recheck、DE-01 契約與結果 | untracked |
| 契約與驗收紀錄 | `ACCEPTANCE-r2.md` | r2 provenance 驗收契約 | tracked |
| run 證據 | `runs/<run-id>/` | run record（`<id>.json`／`.md`）、manifest、findings；`raw/` 為受測與 judge 的原始 trace | 最早 6 個 run 的 record、findings、`evidence.sha256`、`inputs/` 為 tracked，其餘 run untracked；`raw/` 一律 ignored |
| 快取 | `__pycache__/` | Python bytecode | ignored |

各 run 的判定（PASS、FAIL、INVALID、SUPERSEDED）記在 [`STATUS.md`](STATUS.md) 的「執行紀錄」與各 Batch 段落，
以及 [`KNOWN-ISSUES.md`](KNOWN-ISSUES.md) 的對象 run 表。本檔不重複列出。

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
| `verification-records/*.md` | 檔名含 canonical subject digest，規定不可覆寫；被 VERIFICATION-LOG 索引 | 驗收紀錄鏈斷裂 |
| `verification-contracts/*.md` | 被驗收紀錄引用與綁定 | 驗收紀錄無法對照契約 |
| `STATUS.md`、`KNOWN-ISSUES.md` | [`../../../scripts/ledger_check.py`](../../../scripts/ledger_check.py) 以 marker 解析；round4、round8 紀錄綁定當時的 digest | 帳本檢查失敗；歷史 digest 對照失據 |
| `de01/` | `DE-01-arms.md` 記錄 arm 的 SHA-256；DE-01 文件引用 | DE-01 證據無法重現 |
| `ACCEPTANCE-r2.md` | `acceptance-r2-regression.py` 讀取 | regression 失敗 |
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
