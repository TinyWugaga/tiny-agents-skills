# formatDate 規格

- `formatDate(date, tz)` 回傳 `YYYY-MM-DD HH:mm` 格式字串。
- `tz` 為 IANA 時區字串（例如 `Asia/Taipei`）；未提供時使用 UTC。
- 傳入無效日期時回傳 `"Invalid Date"`，不得 throw。
- 純函式：不得讀取 `Date.now()` 或任何全域狀態。
