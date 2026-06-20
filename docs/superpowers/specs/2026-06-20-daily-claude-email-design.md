# 每日定時問 Claude 並寄信 — 設計文件

- 日期：2026-06-20
- 作者：David Pan（與 Claude 協作）
- 專案目錄：D:\Workspace\99_Claude\05_每日定時問Claude v1\
- 狀態：待使用者審閱

## 目標

每天固定時間（台灣時間早上 6:00）自動向 Claude 提出一個預設問題，取得回答後寄到指定 Gmail。需滿足：

- **準時**：大概那個時間即可，不要求精確到分鐘。
- **電腦不一定開著**：執行環境必須在雲端，與使用者本機無關。
- **用訂閱額度**：透過 `claude -p`（Claude Code headless 模式）使用既有訂閱，不另外按 token 付費。

## 選定方案

**GitHub Actions + `claude -p`（headless）+ Gmail SMTP 寄信。**

理由：免費、用訂閱額度、寄 Email 是成熟做法、設定一次後幾乎免維護；使用者不要求精確準時，故 GitHub Actions 尖峰延遲幾分鐘可接受，省去自架 VPS 的維護成本。

備案（本設計不實作）：
- B：Claude Code 內建排程雲端代理（`/schedule`）——最省事，但寄 Email 需另接 Gmail 連接器。
- C：便宜 VPS + cron——最準、最可控，但要付費並自行維護機器。

## 需求參數

| 項目 | 值 |
|---|---|
| 寄送時間 | 台灣時間（UTC+8）每天 06:00 |
| 對應 UTC cron | `0 22 * * *`（主）、`10 22 * * *`（補觸發） |
| 預設問題 | 「今天新北市永和區天氣如何」 |
| 收件 Email | <your-email>@gmail.com |
| LLM 存取 | `claude -p`，使用訂閱授權 `CLAUDE_CODE_OAUTH_TOKEN` |

## 整體架構

一個 GitHub repo（建議設為 private），內含一支主程式與一個 GitHub Actions 排程設定。每天到時間，GitHub 在雲端執行：讀出預設問題 → 用 `claude -p` 問 Claude（允許網路查詢工具以取得即時天氣）→ 將答案以 Gmail SMTP 寄出 → 把答案 commit 進 `log/` 作為記錄。

## 元件

各元件職責單一、可獨立理解與測試。

### 1. `questions.txt`
- 放預設問題，一行一題。初始內容：`今天新北市永和區天氣如何`。
- 要改問題只需編輯此檔，無需動程式。

### 2. `ask.py`
主程式，職責：
1. 讀取 `questions.txt`。
2. **防重複判斷**：檢查 `log/` 是否已有「今天（台灣日期）」的記錄，若有則直接結束（避免補觸發造成重複寄信）。
3. 對每題呼叫 `claude -p`（透過 subprocess），允許網路查詢工具，取得回答。
4. 將所有問答組成 Email 內容，透過 Gmail SMTP 寄到收件信箱。
5. 將本次問答寫入 `log/YYYY-MM-DD.md` 並由 workflow commit 回 repo。
- 暫時性錯誤（claude 呼叫或 SMTP 失敗）自動重試數次後才放棄。

### 3. `.github/workflows/daily.yml`
- 觸發：
  - `schedule`：`0 22 * * *` 與 `10 22 * * *`（UTC）。
  - `workflow_dispatch`：手動觸發按鈕，供測試用。
- **concurrency**：設定 concurrency group（例如 `daily-ask`）並 `cancel-in-progress: false`，確保同一時間只有一個此 workflow 在跑、後來者排隊，避免主觸發與補觸發重疊造成重複寄信。
- 步驟：checkout → 安裝 Node 與 `@anthropic-ai/claude-code` → 注入 Secrets 為環境變數 → 執行 `python ask.py` → commit `log/` 變更。
- 具備寫入 repo 內容的權限（`permissions: contents: write`）以便 commit 記錄。

### 4. GitHub Secrets
- `CLAUDE_CODE_OAUTH_TOKEN`：由本機 `claude setup-token` 產生，讓雲端用訂閱額度。
- `GMAIL_ADDRESS`：寄件 Gmail。
- `GMAIL_APP_PASSWORD`：Gmail 應用程式密碼（非登入密碼）。
- `MAIL_TO`：收件信箱（預設同上 Gmail）。

## 資料流

```
cron / 手動觸發
  → 安裝 claude code
  → ask.py：讀問題 → 檢查今日是否已寄
      （已寄）→ 結束
      （未寄）→ claude -p 取得答案 → Gmail SMTP 寄信 → 寫 log/
  → workflow commit log/ 回 repo
```

## 關鍵設計決策

### 「漏觸發就補跑」與「如何確認已寄過」
GitHub Actions 無法偵測自己漏觸發，改以兩段式達成等效：
- 排兩個 cron：06:00 與 06:10（台灣時間）。
- **確認已寄過的依據**：每天寄完信後會把問答寫成 `log/YYYY-MM-DD.md` 並 commit + push 回 repo。這個當天日期的記錄檔「存不存在」即代表「今天寄過了沒」——不靠記憶、不靠猜。
- 流程：`ask.py` 以 UTC+8 算出今天日期 → 檢查 repo 內是否有 `log/<今天>.md` → 有則結束、沒有則寄並寫檔。
- 正常 6:00 寄出並留下記錄檔；6:10 checkout 後看到檔已存在 → 跳過。若 6:00 被漏掉或延遲掉，6:10 看不到檔 → 補寄。
- **前提**：6:00 那次需在 6:10 前完成 commit + push；問答加寄信通常僅數秒，10 分鐘間隔充足。
- **競態補強**：以 workflow 的 concurrency 設定確保兩次觸發不會同時執行，徹底排除重疊重寄的縫隙（雙重保險）。

### 即時資訊問題需開網路工具
「今天天氣如何」屬於需要即時資料的問題，Claude 本身不知道，必須在 `claude -p` 啟用網路查詢工具才能作答。設計中會允許對應工具。

### repo 60 天無活動會被停用排程
每日將答案 commit 進 `log/`，使 repo 保持活躍，同時累積問答歷史，一舉兩得。

### 時區
GitHub cron 走 UTC；台灣 06:00 = 前一日 UTC 22:00。台灣日期判斷（防重複）在 `ask.py` 內以 UTC+8 計算。

## 錯誤處理

- `ask.py` 對暫時性錯誤（claude 呼叫、SMTP）自動重試數次。
- 任一步驟最終失敗 → workflow 失敗 → GitHub 內建寄信通知該次 Action 失敗，不會無聲無息。

## 測試方式

- `workflow_dispatch` 手動觸發按鈕：不必等隔天，按一下即可驗證問答與寄信流程。
- 先以手動觸發確認整條流程正常，再交付每日排程。

## 後續（本設計範圍外）

- 多題問題、輪替問題、依當天情境動態產生問題。
- 改寄 LINE/Telegram。
- 若日後要求精確準時，再考慮備案 C（VPS）。
