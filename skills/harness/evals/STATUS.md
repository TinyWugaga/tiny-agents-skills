# harness evals — 現況

## 已驗證

- `dispatch` skill 本身：fresh-context 驗收 C1–C10 **PASS**
  （見 `runs/20260826-151927-bbbb34/` 的 source-verification 紀錄）
- routing assertion 在真實 `claude -p` session 中可觀測且會通過。
  但那一輪的 harness 有 fail-open 缺陷，結果標為 **SUPERSEDED**，不作為憑據。

## 未驗證

- **response contract**（`required_elements` / `forbidden_elements`）從未完整跑過。
  `judge.py` 已寫好並單筆煙霧測試通過，但完整 17 筆的 judge pass 沒有執行。
- 修正後的 harness（fail-closed + `--add-dir` + Agent/Bash 開放 + 真實 seed repo）
  **只跑過單筆煙霧測試**，沒有完整 suite 紀錄。

## 要接手的話

```sh
skills/harness/evals/run-suite.sh
```

會自動建立 seed git repo 與隔離 config，跑完 17 筆後依序輸出 routing 與 contract 判定。
raw trace 落在 `runs/<run-id>/raw/`，但只留在本機或 CI artifact，不進版本控制。
預估成本 $8–10、耗時約 20–30 分鐘。

## 已知殘留風險

`run-fixture.sh` 用 `--add-dir ~/.claude/skills` 讓 session 讀得到 skill 的 references，
同時開放 Bash（掃描類 fixture 需要它做機械計數）。破壞性指令已用
`Bash(rm:*)` 等 pattern 封鎖，但理論上 session 仍有能力寫入該目錄。沒有理由這麼做，
但殘留風險不是零。要完全消除的話，改成把 references 複製進 work dir 再跑。

## 為什麼停在這裡

核心交付物（skill、CLAUDE.md 整合、舊檔退役）已完成並通過驗收。
eval harness 從驗證手段變成了獨立專案，投入產出比已經不合理。
harness 修好了、缺陷都記錄了，完整重跑留給需要時再做。
