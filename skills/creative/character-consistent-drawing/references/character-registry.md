# 角色設計圖對照表

此 registry 是 project 未提供自身「角色設計圖對照表」時的預設資料來源。檔名用於搜尋 project sources，不代表圖片已內嵌於 skill。

| 角色名稱 | 角色設計名稱 | 正式角色設計圖檔名 | 角色獨立設定 |
| --- | --- | --- | --- |
| Tifu | Tifu 角色設計 | `tifu_config_q.png` | [characters/tifu.md](characters/tifu.md) |
| Claudi | Claudi 角色設計 | `claudi_config_q.png` | [characters/claudi.md](characters/claudi.md) |
| Codxi | Codxi 角色設計 | `codxi_config_q.png` | [characters/codxi.md](characters/codxi.md) |

## 維護契約

新增角色時：

1. 新增一列，角色名稱須與使用者會點名的正式名稱一致。
2. 指定唯一的正式角色設計圖檔名或 project-relative path。
3. 在 `characters/` 新增同名 kebab-case 設定檔，記錄設計圖不易可靠判讀的髮型、五官、服裝、特殊部件、配色、比例與禁止事項。

不得只新增角色名稱而省略正式角色設計圖。角色別名如有需要，應明列於角色獨立設定；不得靠模糊比對猜測。
