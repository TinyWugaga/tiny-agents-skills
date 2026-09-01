---
name: character-consistent-drawing
description: Draw or edit images containing established project characters by resolving character names to official design sheets and per-character settings, preserving identity while applying requested scenes, poses, compositions, or focused changes. Use for image requests that name registered characters; do not invent unregistered character designs.
---

# Character Consistent Drawing

以正式角色設計為 baseline，再套用使用者本次明確要求的場景、動作或變更。場景可改變，未被指定修改的角色設計不可漂移。

## 解析角色資料

1. 讀取目前 workspace 適用的 Project Instructions。若其中含「角色設計圖對照表」或連結到 project registry，以 project registry 為準；否則讀取 [references/character-registry.md](references/character-registry.md)。
2. 對每個被點名的既有角色，解析正式角色設計圖檔名與獨立設定。依檔名搜尋 project sources；不得用另一名角色或一般美術判斷代替缺少的正式資料。
3. 讀取 [references/character-drawing-rules.md](references/character-drawing-rules.md)，以及 registry 指向的每份角色獨立設定。多人構圖必須逐一解析，不能共用單一角色的設定。
4. 若角色未登錄，停止該角色的生成並請使用者提供設計資料或確認建立新角色。若角色已登錄但正式設計圖缺失，指出缺少的檔名；不要詢問角色長相，也不要自行補畫設計。
5. 若同一檔名有多個候選，優先採用 project registry 同目錄或其明確指定路徑的檔案；仍無法唯一判定時，列出候選並請使用者指定。

## 組合繪圖要求

- 正式角色設計圖定義角色外觀、比例、服裝、配件、辨識特徵與角色本身的畫風。
- 角色獨立設定補充設計圖無法可靠表達的細節與禁止事項。
- 使用者本次要求定義姿勢、表情、視線、場景、背景、鏡位、構圖、站位、互動、道具、光線與氣氛。
- 使用者明確要求變更角色元素時，只把該元素視為本次 delta；其他元素仍沿用 baseline。「其他維持不變」是強限制。
- 額外參考圖先分類為角色設計、場景、姿勢、構圖或畫風參考。只有正式角色設計圖可以主導既有角色本人外觀。

使用宿主可用的圖片生成或編輯能力，將每名角色的正式設計圖、必要的角色設定、使用者提供的目標圖片與本次要求一併帶入。不得假設特定平台工具一定存在；能力不足時，明確列出缺少的輸入或人工步驟。

## 生成前與修改後檢查

生成前確認角色名稱、設計圖、獨立設定及本次 delta 均已解析。多人構圖另確認共同畫風與合理遮擋。

修改既有圖片時採最小變更：比對修改前後，確認未指定的髮型、五官比例、頭身比例、身材、服裝、配色、畫風、鏡位、其他角色與背景均未變動。檢查四肢、頭髮、配件、手持物與延伸部位是否穿模、錯位或消失。

設計圖細節無法辨認時採保守處理：沿用可確認的既有資訊，不新增設定。無法可靠維持角色一致性時，說明不確定細節，不宣稱已符合正式設計。
