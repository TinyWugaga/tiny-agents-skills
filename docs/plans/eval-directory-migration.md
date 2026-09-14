# eval 實體目錄遷移方案

- 日期：2026-09-14
- 盤點基準：branch `chore/organize-eval-docs`，HEAD `8004bbe07e2d21866486554ac77d155b37342ab7`，唯一的未提交修改是 `skills/harness/evals/README.md`。
- 範圍：`skills/harness/evals/`。各 skill 專屬的 `evals/fixtures.json` 維持在原 skill 內。
- 性質：本檔只是方案，不是授權。本檔撰寫時沒有搬移任何檔案。
- Owner 決定（2026-09-14）：`C0` = `f219b121dcb87166a2a374c790ffbf84caa40fc2`。首批由 5 支縮為 4 支：`acceptance-r2-regression.py` 在 `C0` 的基線就已回傳 FAIL，屬於綁定歷史環境的工具，留在原位（見 §3.1）。

## 1. 結論

- **首批只做一件事：把 4 支零成本自測移進 `evals/selftests/`。** 這批不改變任何 identity 值，也不必做行為重跑。但這 4 個檔案被凍結契約以「路徑＋SHA-256」綁定，所以需要 Owner 明確授權（見 §5）。
- **歷史證據留在原位（§4 的選項 A）。** 遷移前 commit `C0` 只保存遷移前的已追蹤內容，用來還原被搬走的檔案。它不保證與各歷史契約綁定的版本相符（見 §4「C0 的保證範圍」）。
- **現行工具、整合案例、`runs/`、`de01/` 都不搬。** 這些檔案的路徑會進入 identity 或執行入口，搬移收益小於重建 identity 的成本（見 §3.3）。

## 2. 依賴類型

| 類型 | 定義 | 搬移後的效果 |
|---|---|---|
| 內容 hash | 只綁定內容的 SHA-256，例如契約中的「hash＋路徑」清單、`evidence.sha256`、`trace-manifest.json` | 凍結契約寫的是舊路徑。舊路徑的遷移前內容可從 `C0` 還原，但還原的內容是否符合契約的綁定值，要逐檔比對 |
| 含路徑的 identity | 路徑字串本身進入 hash 輸入 | 搬移會改變 identity 值，舊 run 的值無法在新樹上重算 |
| 執行入口 | 程式實際開啟的路徑，例如 `$BASE/...`、`__file__/../../..` | 不改就壞，改了就動到該程式的內容（若程式在 identity domain 內，identity 也跟著變） |
| 純文字引用 | 文件中的路徑或指令敘述 | 現行文件可以更新。歷史段落不改寫，只在帳本追加對照 |

含路徑 identity 的來源：`scripts/bundle-hash.sh:174-184` 以 `evals/<檔名>` 固定清單列出 evaluator 與 runner，並在 `:279-281` 輸出「路徑＋hash」作為摘要輸入；fixtures mode 在 `:193-211` 以 repo 相對路徑計入；`evals/manifest.py:189` 把 `fixture_args` 寫成 repo 相對路徑。`bundle-hash.sh:115` 規定 allowlist 一變就要升 `HASH_SCHEMA_VERSION`。

## 3. 目標目錄與路徑清單

### 3.1 首批：自測（推薦）

| 原路徑（`skills/harness/evals/` 下） | 新路徑 |
|---|---|
| `judge_selftest.py` | `selftests/judge_selftest.py` |
| `score_selftest.py` | `selftests/score_selftest.py` |
| `record_selftest.py` | `selftests/record_selftest.py` |
| `transport_selftest.py` | `selftests/transport_selftest.py` |

**`acceptance-r2-regression.py` 留在原位**，和它讀取的 `ACCEPTANCE-r2.md` 放在一起，內容和路徑都不變。

- 它在 `C0` 的基線就回傳 FAIL，repo 根目錄與其他 cwd 兩種執行方式的 FAIL 清單相同。
- 失敗原因是它硬編了 r2 當時的狀態：`record.py` 的 SHA-256（`:21`）、工作區有 34 筆變更（`:23`）、PATH 上的 python3 為 3.7.9（`:419`）。
- 因此它綁定歷史環境，不列為本批必須通過的搬移 gate。本批不修改它，不重跑它，也不改用「FAIL 清單相同」來驗收。

目錄名用 `selftests/`，因為 repo 根目錄已經有 `tests/`（目前含 `tests/agent-instructions.md`），避免兩者混淆。

**必要修改**（只有執行入口與文字，不動任何 identity）：

- **執行入口**：
  - `judge_selftest.py:17-18`、`score_selftest.py:15-16`、`transport_selftest.py:10-11`：模組路徑改為上一層的 `judge.py`／`score.py`／`transport.py`。
  - `judge_selftest.py` 另外在 `:80` 用 `from judge import`。它原本靠 Python 自動把腳本所在目錄放進 `sys.path[0]`，所以要補一行 `sys.path.insert(0, _HERE)`，讓 import 的解析順序和搬移前相同。這一處在首批實作時才發現。
  - `record_selftest.py:21-23`：`sys.path` 改為插入上一層目錄。
  - `scripts/hash-domain-selftest.sh:239-240`：兩個 case 的目標路徑改為 `selftests/`。這兩個 case 斷言「改 selftest 不動任何 domain」，搬移後仍應回 `none`。
- **含路徑 identity**：無。evaluator 以明列清單計算（`bundle-hash.sh:174-176`），不含 `*_selftest.py`；`skills/harness/README.md:132` 也寫明排除。
- **內容 hash**：round5–8 契約以「路徑＋SHA-256」綁定這 4 支，以及留在原位的 `acceptance-r2-regression.py`（例如 `verification-contracts/20260907-round8.md:139-143` 共五筆）。實測時 `judge`、`score`、`transport` 三支 selftest 與 `acceptance-r2-regression` 仍與 round8 的值相符，`record_selftest.py` 已經不同。4 支搬移並修改入口後，遷移前內容只能從 `C0` 取回，契約不修改。
  - `record_selftest.py` 的失配在搬移前就存在，不是搬移造成的，`C0` 也無法消除。
  - 本方案沒有搜尋與 round8:141 相符的歷史版本，這項標示為未驗證。repo 外的 `~/.claude/harness-baselines/20260911-pre-b23b-rerun/repo-files.sha256` 會多出 4 條路徑差異。
- **純文字引用**：
  - `evals/README.md`（行號以 SHA-256 `e6e5b5a0…00a2` 的版本為準）要更新三處：
    - `:45` 目錄樹。
    - `:73-74` 分類表。
    - `:150-160`「常用零成本檢查」：`:152` 目前指向 STATUS「要接手的話」，改成在 README 直接列出新路徑的自測指令。
  - `STATUS.md` 有 25 處引用（`git grep -c -E '[a-z_]+_selftest\.py|acceptance-r2-regression\.py'`），另外還有 `:1528` 的 `${f}_selftest.py` 迴圈，這個樣式數不到。這些都在追加式帳本內，歷史段落不改寫；只在 marker 區外追加一段遷移對照，內容包含 `C0` 與上表。
  - round5–8 契約不改。

### 3.2 條件式批次：歷史證據（只在 Owner 選 §4 選項 B 時執行）

| 原路徑 | 新路徑 |
|---|---|
| `ACCEPTANCE-r2.md`、`CLOSURE-20260904.md`、`CLOSURE-20260904-followup.md` | `records/contracts/` |
| `verification-contracts/*`（6 份） | `records/contracts/` |
| `CLOSURE-20260904-disposition.md`、`RECHECK-20260904-supersedes-closure.md` | `records/verifications/` |
| `verification-records/*`（5 份） | `records/verifications/` |
| `DE-01-arms.md`、`DE-01-PREFLIGHT.md`、`DE-01-RESULTS-20260904.md` | `records/investigations/de01/` |

- 即使選 B，`de01/` 與 `runs/` 仍然不搬，理由見 §3.3。
- 選 B 要改的東西：
  - `acceptance-r2-regression.py`（首批後仍在原位）的 `ACCEPTANCE` 路徑。
  - `scripts/LEDGER-CHECK-SPEC.md:30` 規定的紀錄路徑慣例。這是規則變更，需要 Owner。
  - 現行帳本中的連結：STATUS 10 處、KNOWN-ISSUES 6 處、VERIFICATION-LOG 11 處。改完要重跑 `ledger_check`。
  - `evals/README.md` 的歷史證據索引。
- STATUS 歷史段落中的連結會在現行樹上失效，而且依規則不改寫；讀者要回到 `C0` 才能打開。

### 3.3 保留原位的項目與理由

| 項目 | 主要依賴（來源） | 判斷 |
|---|---|---|
| runner：`run-suite.sh`、`run-fixture.sh`、`transport.py`、`manifest.py` | 含路徑 identity（`bundle-hash.sh:181-184`）；執行入口 `manifest.py:81-83`、`run-suite.sh:15-26`、`scripts/run-rescore.sh:38`；repo 外 `harness-baselines/20260911-b23b-expected-identity/rebuild.sh:6,18-19` 以絕對路徑呼叫 `manifest.py` | 搬移需要 hash schema v7 並重建 runner identity，也會影響 Batch 23b 的預期 identity。不搬 |
| evaluator：`judge.py`、`score.py`、`record.py` | 含路徑 identity（`bundle-hash.sh:174-176`）；執行入口 `record.py:78-80`、`run-rescore.sh`、`scripts/run-provenance-selftest.sh` 的 `$E/record.py` | 同上。不搬 |
| 整合案例：`routing-fixtures.json`、`seed/` | fixtures identity 含 repo 相對路徑（`manifest.py:189`）；`run-suite.sh:18,133` 的路徑一改，runner identity 就變；fixture 內文 `(見 evals/seed/)` 出現在 `routing-fixtures.json` 6 處與 `dispatch/evals/fixtures.json:136`，改內文會變動 fixtures 內容 hash | 搬移會同時改變 runner 與 fixtures 兩個 identity。不搬 |
| `context/rules.md` | execution-context 只計內容，但路徑寫死在 `run-suite.sh:21`，改路徑就改了 runner identity | 不搬 |
| `runs/` | `.gitignore:10`、`run-suite.sh:19`、`de01/run-one.sh:43,69`；raw 為 ignored，共 1,099 檔、約 13 MB。以 `git mv` 或檔案系統搬移整個目錄時，raw 可能一起被搬走，但 Git commit 不保存這些未追蹤內容，搬移前必須另行備份並驗證完整性；pre-b23b baseline 以舊路徑列出 1,012 個 raw 檔 | 不搬 |
| `de01/` | 執行入口 `run-one.sh:23-24`；round8 契約綁定 `run-one.sh` 內容且目前仍相符；`de01-*` run 的 `fixture_args` 含此路徑 | 不搬 |
| `STATUS.md`、`KNOWN-ISSUES.md`、`VERIFICATION-LOG.md`、`README.md` | 現行入口；`ledger_check` 由文件中的指令以路徑呼叫 | 不搬 |

`main` 不含 `skills/harness/evals/`（`git ls-tree -r main` 沒有任何命中），所以這次遷移不影響 `main` 的同步。

## 4. 歷史證據如何維持可查驗

| | A：歷史留原位，只整理現行檔（推薦） | B：先保存可重現舊路徑的快照，再搬歷史證據 |
|---|---|---|
| 已追蹤內容 | 仍在原路徑；首批移走的 4 支 selftest 從 `C0` 還原遷移前內容 | 全部從 `C0` 還原遷移前內容 |
| ignored raw | 不移動，沿用 `trace-manifest.json` 與 `evidence.sha256` 驗證（兩者都用 run 內相對路徑） | 同 A，前提是 `runs/` 不搬。若將來要搬 `runs/`：整個目錄搬移時 raw 可能一起移動，但 Git commit 不保存 raw，必須另行備份（例如 tar）並用 SHA-256 清單驗證完整性 |
| repo 外 baseline、proposal 複本 | 路徑與現行樹大致一致 | 路徑只與 `C0` 的樹一致；內容是否相符要逐檔核對 |
| 凍結契約的重驗 | 大多數舊路徑仍能在現行樹上找到；綁定值是否相符要逐檔比對 | 舊路徑只能在 `C0` 的 worktree 上找到；同樣要逐檔比對，`C0` 不保證相符 |
| 現行文件連結 | 不受影響 | STATUS 歷史段落的連結失效，且依規則不修 |
| 需要的變更 | 無規則變更 | 需修改 `LEDGER-CHECK-SPEC.md:30`，並需 Owner 解除 STATUS:2331 的限制 |
| 可讀性收益 | 頂層仍留 8 份歷史 md 與 3 個歷史目錄，靠 README 索引導覽 | 頂層只剩現行檔案 |

推薦 A。B 的主要收益是頂層外觀，代價卻包括永久失效的歷史連結、一次規則變更，以及所有舊契約的路徑查找都得改在 `C0` 上進行。

**查驗舊路徑的程序**（A 與 B 共用）：

1. 以 `git worktree add --detach <暫存目錄> C0` 還原遷移前的已追蹤樹。
2. 需要 raw 時，從現行樹的 `runs/<id>/raw/` 複製到暫存樹的相同相對路徑，再用該 run 的 `trace-manifest.json` 或 `evidence.sha256` 核對。
3. 結束後用 `git worktree remove` 移除暫存樹。

**C0 的保證範圍**

- **遷移前內容可還原：** `C0` 保證這一點。遷移前的已追蹤檔案都能從 `C0` 逐 byte 取回。
- **歷史契約版本可重現：** `C0` 不保證這一點。某份契約綁定的版本必須逐檔用契約列出的 SHA-256 比對。
- **已知失配：** `record_selftest.py` 在遷移前就與 round8:141 不符，不是搬移造成的，`C0` 也無法消除。
- **未驗證：** 其他沒有逐檔比對過的綁定。本方案不為此搜尋或重建歷史版本。
- ignored raw 與 repo 外 baseline 都不在 `C0` 內。

所有凍結契約、歷史紀錄與 repo 外 baseline 都不修改，也不為了讓新路徑通過舊驗收而改動它們。

## 5. 暫停規則下的授權分級

依據：`STATUS.md:2331` 寫明「暫停不代表可以搬動、刪除或改名凍結檔案，或任何仍被引用的證據」；`:2329` 寫明舊證據保留在原版本。

| 範圍 | 可否在目前規則內進行 |
|---|---|
| 本方案、README 導覽等純文件工作 | 可以。仍需依 AGENTS.md 填寫工作單 |
| 首批 selftest 搬移 | 需要 Owner 明確授權。這 4 支被 round5–8 凍結契約以「路徑＋SHA-256」綁定，並列在 pre-b23b baseline 中。已於 2026-09-14 授權 |
| 選項 B、修改 `LEDGER-CHECK-SPEC.md` 的路徑慣例 | 需要 Owner 授權，並需對 STATUS:2331 做出裁決 |
| 搬移 runner、evaluator、案例或 `runs/` | 需要 Owner 授權，並涉及 hash schema v7、重建 identity 與 Batch 23b 預期 identity 的處置。本方案不推薦 |

Batch 23b 結案或恢復，都不會自動解除任何 baseline 或凍結契約的約束，屆時仍由 Owner 裁決。

## 6. 首批實作單

```text
交付：4 支自測移到 evals/selftests/；停在實作與零成本驗證，不發布。
範圍（本批 diff 允許清單）：上列 4 支的 rename 與載入路徑修改；scripts/hash-domain-selftest.sh:239-240；skills/harness/evals/README.md；skills/harness/evals/STATUS.md（僅在 marker 外追加）；docs/plans/eval-directory-migration.md（本方案）。develop 系 branch；Claude Code。
驗收：下列零成本檢查全部通過；identity 值與 C0 相同；acceptance-r2-regression.py 與 ACCEPTANCE-r2.md 的路徑和內容都不變；round8:139-143 五筆歷史比對（涵蓋 4 支搬移檔與原位的 regression）在搬移前後一致（預期 4 符、record_selftest.py 不符——既有限制，非搬移造成，C0 不消除）。
不做：acceptance-r2-regression.py 的搬移、修改或重跑；其他工具、案例、runs、de01、歷史證據的搬移；hash schema 變更；付費測試。
驗證成本：只做零成本檢查，無付費呼叫。
停止：見下方停止條件。
裁決者：Owner。
```

**步驟**

0. 前置：
   - 工作區乾淨（`git status --porcelain --untracked-files=all` 為空）。
   - 取得 `C0`（遷移前 commit，需包含本 branch 目前的 README 修改，因此需要 commit 授權）。
   - 在 `C0` 上跑一次全部零成本檢查作為基線，自測目錄用舊路徑 `"$REPO/skills/harness/evals"`。任一必要項已經失敗就停止，那不是遷移造成的問題。`acceptance-r2-regression.py` 在 `C0` 已知失敗，不列為必要項（見 §3.1）。
   - 記錄 `acceptance-r2-regression.py` 與 `ACCEPTANCE-r2.md` 的 SHA-256。
   - 執行 `hist_check live > "$OUT/hist-before.txt"`，記錄搬移前的歷史比對結果（函式定義見下方）。
   - 記錄三項 identity 值：`bundle-hash.sh evaluator skills/harness`、`bundle-hash.sh runner skills/harness`，以及 `bundle-hash.sh fixtures` 對 `skills/harness/dispatch/evals/fixtures.json`、`skills/harness/evals/routing-fixtures.json`、`skills/harness/evals/seed` 的值。
1. 用 `git mv` 移動 4 支檔案。只做 §3.1 列出的入口修改。
2. 更新 `evals/README.md`；在 `STATUS.md` 的 marker 區外追加遷移對照（含 `C0`、原路徑 → 新路徑）。

**零成本驗證**（必做）

以下指令在 sh 或 zsh 都可執行。步驟 0 的基線用同一組函式，只把自測目錄換成舊路徑。

```sh
REPO=/Users/tinywu/Desktop/Apps/tiny-agents-skills   # repo 絕對路徑
C0=<步驟 0 記錄的 commit hash>
OUT=<repo 外的暫存目錄，存放搬移前後的歷史比對結果>
cd "$REPO"

# 4 支搬移的自測逐支執行並記錄各自的 exit code；任一支失敗，函式回傳 1，不會被後面的成功蓋掉
# acceptance-r2-regression.py 在 C0 已知失敗，不在這個 gate 內，也不重跑（見 §3.1）
run_selftests() {   # $1 = 自測所在目錄的絕對路徑，$2 = 執行時的 cwd
  rc=0
  for f in judge_selftest.py score_selftest.py record_selftest.py transport_selftest.py; do
    if (cd "$2" && python3 -B "$1/$f"); then echo "ok   $f"; else echo "FAIL $f (rc=$?, cwd=$2)"; rc=1; fi
  done
  return "$rc"
}
SELF="$REPO/skills/harness/evals/selftests"  # 步驟 0 基線改用 "$REPO/skills/harness/evals"
CWD2=$(mktemp -d)
run_selftests "$SELF" "$REPO"; rc_root=$?    # cwd = repo 根目錄，4 支都跑
run_selftests "$SELF" "$CWD2"; rc_other=$?   # cwd = 其他目錄，4 支都跑
rmdir "$CWD2"                                # 失敗代表自測在 cwd 留下檔案，需要調查
[ "$rc_root" -eq 0 ] && [ "$rc_other" -eq 0 ] # 任一非零即驗收失敗
git diff --quiet "$C0" -- skills/harness/evals/acceptance-r2-regression.py skills/harness/evals/ACCEPTANCE-r2.md   # 原位檔：路徑與內容都未變

git diff -M --stat "$C0"                     # 只出現工作單「範圍」允許清單內的變更：4 筆 rename，以及 hash-domain-selftest.sh、evals README、STATUS、本方案
git diff -M "$C0" -- skills/harness/evals    # rename 檔的差異只含入口路徑行
sh scripts/hash-domain-selftest.sh           # 維持 36 個案例通過
sh scripts/run-provenance-selftest.sh        # 檔頭自述零成本；結果與基線一致
python3 -B scripts/ledger_check.py --known-issues skills/harness/evals/KNOWN-ISSUES.md --status skills/harness/evals/STATUS.md   # 「一致」
sh scripts/bundle-hash.sh evaluator skills/harness; sh scripts/bundle-hash.sh runner skills/harness
sh scripts/bundle-hash.sh fixtures skills/harness/dispatch/evals/fixtures.json skills/harness/evals/routing-fixtures.json skills/harness/evals/seed
                                             # 三個值與步驟 0 的記錄相同
# 歷史比對：把 round8:139-143 列出的舊路徑內容逐一與契約值比對
hist_check() {   # $1 = live（搬移前的工作樹）或 c0（搬移後從 C0 取回）
  sed -n 139,143p "$REPO/skills/harness/evals/verification-contracts/20260907-round8.md" |
  while read -r want rel; do                 # 不用 path 當變數名：zsh 的 path 與 PATH 綁定
    if [ "$1" = live ]; then got=$(shasum -a 256 "$REPO/$rel" | cut -d' ' -f1)
    else got=$(git -C "$REPO" show "${C0}:${rel}" | shasum -a 256 | cut -d' ' -f1); fi
    if [ "$got" = "$want" ]; then echo "match    $rel"; else echo "mismatch $rel"; fi
  done
}
hist_check c0 > "$OUT/hist-after.txt"
diff "$OUT/hist-before.txt" "$OUT/hist-after.txt"   # 必須無差異；預期 4 筆 match、record_selftest.py mismatch（既有限制）
(cd "$REPO/skills/harness/evals" && python3 -c "import re,os;t=open('README.md',encoding='utf-8').read();m=[x for x in re.findall(r'\]\(([^)\s]+)\)',t) if '://' not in x and not os.path.exists(x.split('#')[0])];print('missing',m);raise SystemExit(bool(m))")   # README 相對連結全部可達
```

**行為驗證**（需要模型呼叫）：本批不改動任何 identity 或 runtime 內容，所以不需要，也不執行。之後不得寫成「行為驗證已通過」。

**回復方式**

- commit 前：先以 `git status` 確認沒有本批以外的變更。接著只撤回本批路徑：`git mv` 把 4 支移回原位，再執行 `git restore --source="$C0" --staged --worktree --` 4 個原路徑、`scripts/hash-domain-selftest.sh`、`skills/harness/evals/README.md`、`skills/harness/evals/STATUS.md`，最後刪除空的 `selftests/`。不要對整個目錄 restore。
- commit 後：`git revert <遷移 commit>`。
- 兩種都不動 ignored 資料。

**停止條件**

- 任一 identity 值改變：立即回復並停止。
- `hist-before.txt` 與 `hist-after.txt` 不一致：立即回復並停止。
- 基線通過的檢查在搬移後失敗：同一問題只修入口路徑，最多 2 輪（AGENTS.md），仍失敗就回復並回報。
- diff 出現工作單「範圍」允許清單以外的檔案，或需要修改任何凍結契約、紀錄、baseline：停止。
- 全部通過即結束本批，不順勢開始第二批。

## 7. 需要 Owner 決定的事項

1. 已決定（2026-09-14）：授權首批搬移 4 支受 round5–8「路徑＋SHA-256」綁定的 selftest，並接受 pre-b23b baseline 因此多出 4 條路徑差異；`acceptance-r2-regression.py` 留在原位。
2. 已決定：`C0` = `f219b121dcb87166a2a374c790ffbf84caa40fc2`，只含 README 與本方案，作為遷移前已追蹤內容的還原基準。`C0` 不保證符合各歷史契約綁定的版本。
3. 已決定：遷移對照追加在 `STATUS.md` 的 marker 區外。
4. 已決定：歷史證據採 A。
5. 已決定：runner、evaluator、整合案例、`runs/`、`de01/` 本批不搬，但不作永久留在原位的決定。
