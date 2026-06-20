# 每日定時問 Claude 並寄信

每天台灣時間 06:00，GitHub Actions 在雲端用 `claude -p` 問 `questions.txt` 裡的問題，
把答案寄到你的 Gmail，並把問答記錄存進 `log/`。電腦不開機也會跑。

## 一次性設定

### 1. 產生 Claude 訂閱授權 token（本機）
```bash
claude setup-token
```
複製輸出的 token。

> 注意：本機若設了失效的 `ANTHROPIC_API_KEY` 環境變數會蓋掉 OAuth，請先移除。

### 2. 產生 Gmail 應用程式密碼
Google 帳號 → 安全性 → 兩步驟驗證（需先開啟）→ 應用程式密碼 → 產生一組 16 碼密碼。
（用的是「應用程式密碼」，不是你的登入密碼。）

### 3. 在 GitHub repo 設定 Secrets
repo → Settings → Secrets and variables → Actions → New repository secret，加入：

| Secret | 值 |
|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | 步驟 1 的 token |
| `GMAIL_ADDRESS` | 你的寄件 Gmail，例如 `you@gmail.com` |
| `GMAIL_APP_PASSWORD` | 步驟 2 的 16 碼密碼 |
| `MAIL_TO` | 收件信箱，例如 `<your-email>@gmail.com` |

### 4. 推上 GitHub
```bash
git remote add origin <你的 repo URL>
git push -u origin main
```

## 測試（不必等隔天）
repo → Actions → `daily-ask` → Run workflow（手動觸發）。
跑完檢查：有沒有收到信、`log/` 是否多了當天日期的 `.md`。

## 改問題
編輯 `questions.txt`，一行一題，commit 後即生效。

## 運作小知識
- 排兩個觸發時間（06:00 / 06:10）；當天 `log/<日期>.md` 存在就跳過，避免重複寄信。
- 每天 commit log 也讓 repo 保持活躍，避免 60 天無活動被停用排程。
- 「天氣」這類即時問題靠 Claude 的 WebSearch/WebFetch 工具作答。
