# Judgment description A/B observation

- 目的：比較 pre-bounded description 與 current description 對六筆既有 judgment fixture 的 routing。
- 證據性質：每個 cell 單次 observation，不宣稱因果。
- current 側：`20260901-215156-0fe73d`，`judgment_bundle e2a9d915cb9d`。
- old 側：只把 current `SKILL.md` frontmatter description 還原為 pre-bounded 文字，body、references、
  其他 skills、model（sonnet）、rules 與 settings 不變；變體 bundle `610dbea83a82`。
- old 側 6 個 subject sessions 全部成功，cost observation USD 0.496889。

| fixture | old | current |
|---|---|---|
| `positive-1` | trigger | no trigger |
| `positive-2` | trigger | trigger |
| `positive-4` | no trigger | no trigger |
| `positive-5` | no trigger | no trigger |
| `ambiguous-1` | no trigger | no trigger |
| `ambiguous-2` | trigger | trigger |

五筆一致，只有 `positive-1` 出現差異。這是需重複量測的 cell，本輪不足以把差異歸因於
description 擴張。raw trace、meta、兩份 `SKILL.md` snapshot 與縮減 fixtures 保留在本目錄。
