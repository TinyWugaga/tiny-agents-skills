# 方案與額度事實（dispatch 的成本判斷依據）

只在 `dispatch` 需要判斷「這樣派工划不划算、額度夠不夠」時讀本檔。
Claude Code 的**能力**事實(model、effort、fast mode、subagent 機制)在
[`claude-code-capabilities.md`](claude-code-capabilities.md);本檔只談**額度與消耗**。

沿用同一套規則:**官方支援**與**本機觀測**兩欄回答不同問題,不互相覆蓋;
會影響當次決策的事實,執行前重查,查不到就標「未驗證」。

---

## 官方支援（來源:support.claude.com / claude.com，查閱日期 2026-08-26）

### 額度是跨 surface 的共用池

適用 surface:Claude 網頁／桌面／行動版、Claude Code。

- 每個方案的用量在**五小時滾動 session 視窗**重置;付費方案在其上**另有週上限**,
  週上限在帳號被指派的固定時間重置。
- **Pro 與 Max 的用量上限由 Claude 與 Claude Code 共用**——兩邊的活動都記進同一個池。
- 查看方式:`Settings > Usage`,有五小時 session 與週用量兩條進度條。

來源:
<https://support.claude.com/en/articles/11647753-how-do-usage-and-length-limits-work>、
<https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan>

> **對派工的意義**:省不省額度要看**整個池**,不是只看當前 session。
> 在 Claude Code 大量派工,會直接壓縮同一天在 chat 那邊的可用量。

### 並行會倍增消耗；Cowork 的預設方向與本 skill 相反

- **同時跑多個 session 或 subagent 會倍增 token 消耗。**
- **Cowork 支援 sub-agent 協調**,官方描述為把複雜工作拆成小任務、協調**平行**工作流,
  多個 sub-agent 同時進行。
  → 這個方向與本 skill 的「預設自己做、預設依序派工」**相反**。
    在 Cowork 跑大任務時,額度要另外盯,不要把這裡的並行紀律想成到處都成立。
- **Claude Code 與 Cowork 的 token 消耗速率明顯高於一般 chat。**

來源:
<https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork>、
<https://support.claude.com/en/articles/9797557-usage-limit-best-practices>、
<https://support.claude.com/en/articles/14782391-claude-enterprise-consumption-guide>

### 本規則的適用範圍

本 skill 只在 Claude Code 生效。`~/.claude/CLAUDE.md` 是 Claude Code 的載入機制,
Cowork 與 chat 不讀它,因此本 skill 的派工紀律不會自動套用到那兩個 surface。

⚠️ **未驗證**:舊版規則檔曾記載「chat 無 subagent 機制」。2026-08-26 複查時,
官方文件只正面記載 Cowork 與 Claude Code 的 subagent 能力,**沒有找到明確說明 chat
有或沒有**。屬於查不到而非已證實,不得當成已知事實引用。

---

## 本機觀測

| 項目 | 值 | 觀測日期 | 方法 |
|---|---|---|---|
| 方案 | **未驗證** | — | `/usage`,或 claude.ai `Settings > Usage` |
| 當前五小時視窗用量 | **未驗證** | — | 同上 |
| 當前週用量 | **未驗證** | — | 同上 |
| usage credits 是否開啟 | **未驗證** | — | `/status` 或 `/usage-credits` |

**未驗證項目不得當成已知事實引用。** 額度吃緊與否會直接改變派工決策,
需要據此決策時先在互動式 session 跑 `/usage` 確認,再回填本表並註明觀測日期。
