# 05_每日定時問Claude — 專案索引（關鍵字檢索用）

> 一句話：**GitHub Actions 雲端每天台灣時間 06:00 用 `claude -p` 問固定問題 → 取得答案（可查即時資訊）→ 寄到 Gmail + commit 記錄**，電腦關機也照跑。

---

## 🔑 關鍵字（檢索用）

`每日定時問Claude` `daily claude email` `daily-claude-email` `定時問問題` `自動寄信`
`GitHub Actions` `cron` `workflow_dispatch` `雲端排程` `無人值守` `電腦關機也能跑`
`claude -p` `headless` `claude setup-token` `CLAUDE_CODE_OAUTH_TOKEN` `訂閱 OAuth` `0 API 費用`
`WebSearch` `WebFetch` `即時天氣` `永和區天氣`
`Gmail SMTP` `SMTP_SSL` `app password` `應用程式密碼` `兩步驟驗證`
`防重複` `concurrency` `log 記錄` `pytest` `TDD` `Python 標準函式庫`
`davidpaul9` `MAIL_TO BOM 坑` `Actions 被停用換帳號`
`微信報表`（姊妹專案，見下）`claude-headless-automation`（Skill）

---

## 📁 路徑與資源

| 項目 | 內容 |
|------|------|
| 本機路徑 | `D:\Workspace\99_Claude\05_每日定時問Claude v1\` |
| GitHub | https://github.com/davidpaul9/daily-claude-email （Private，帳號 **davidpaul9**） |
| 本機分支 / 遠端分支 | `main` → `main` |
| 核心程式 | `ask.py`（純 Python 標準函式庫） |
| 排程設定 | `.github/workflows/daily.yml` |
| 問題清單 | `questions.txt`（一行一題；目前：今天新北市永和區天氣如何） |
| 答案記錄 | `log\YYYY-MM-DD.md`（由 workflow 自動 commit 回 repo） |
| 測試 | `tests\test_ask.py`（13 個 pytest） |
| 機密設定 | GitHub repo Secrets（不在程式碼裡，見下） |
| 設計/計畫文件 | `docs\superpowers\specs\`、`docs\superpowers\plans\` |

---

## 🏗️ 架構（資料流）

```
GitHub Actions（schedule: cron 0 22 / 10 22 UTC = 台灣 06:00 / 06:10；另有 workflow_dispatch 手動鈕）
  └─ ubuntu-latest：checkout → 裝 Node → 裝 @anthropic-ai/claude-code → 裝 Python
       └─ python ask.py
            ├─ 1. today_tw()         台灣(UTC+8)今天日期
            ├─ 2. already_sent()     log\<今天>.md 存在 → 直接結束（防重複/補觸發跳過）
            ├─ 3. read_questions()   讀 questions.txt
            ├─ 4. ask_claude()       claude -p --model sonnet --allowedTools "WebSearch WebFetch"
            │                        （訂閱 OAuth，0 API 費用；開網路工具才能查即時天氣）
            ├─ 5. compose_email() + send_email()  → Gmail smtplib.SMTP_SSL(465)
            └─ 6. write_log()        → log\<今天>.md
       └─ workflow「Commit log」步驟：git add log/ → commit → push（保 repo 活躍 + 累積歷史）
  concurrency: group=daily-ask（同時只跑一個，防主/補觸發重疊重寄）
```

### 🎯 設計重點 / 決策理由

每個選擇背後都有原因，避免日後「不知道當初為什麼這樣做」而誤改：

1. **雲端排程走 GitHub Actions，不走本機排程器**
   - 需求是「準時 + 電腦不一定開著」→ 本機 cron/工作排程器關機就不跑
   - GitHub Actions 在雲端、與本機無關、免費；不要求精確到分鐘，尖峰延遲幾分鐘可接受
   - → 備案（更省事但要接 Gmail 連接器的內建 `/schedule`、最準的 VPS+cron）暫不採用

2. **分析用 `claude -p`（訂閱 OAuth），不在程式裡串 API 金鑰**
   - 走 Claude 訂閱額度，**0 額外費用**、無需申請/保管/輪替 API key
   - 雲端認證用 Secret `CLAUDE_CODE_OAUTH_TOKEN`（本機 `claude setup-token` 產生）
   - → 刻意用 OAuth 訂閱，**絕不設 `ANTHROPIC_API_KEY`**（會蓋掉 OAuth 並另計費）

3. **開啟 `WebSearch WebFetch` 工具**
   - 「今天天氣」這類需即時資料的問題，Claude 本身不知道，必須允許網路工具才答得出（實測會引用來源）
   - → 若問題其實不需上網，可拿掉更單純

4. **防重複：log 檔存在判斷 + 兩段 cron + concurrency**
   - 排 06:00 與 06:10 兩次；`log\<台灣日期>.md` 存在就跳過 → 達成「漏觸發就補跑」又不重寄
   - concurrency 再保證兩次不會同時執行
   - → 「是否已寄」靠 repo 裡的當日記錄檔，不靠記憶

5. **每日 commit log 回 repo**
   - 一兼二顧：累積問答歷史 + 讓 repo 保持活躍（GitHub 對 60 天無活動的 repo 會停用排程）

6. **prompt 走 stdin + `encoding="utf-8"`**
   - 避免命令列長度/跳脫問題；utf-8 不可省（否則中文/emoji 亂碼）

7. **固定時區 `timezone(timedelta(hours=8))`**
   - 不依賴系統時區或 tzdata，Windows/Linux 行為一致

8. **防呆清理輸入（`_clean()`）**
   - 去除 token / app password / 信箱的前後空白與**隱形字元（BOM/零寬）**
   - 來由：用 PowerShell 管道 `| gh secret set` 設 `MAIL_TO` 時被塞了 BOM，導致收件地址無效退信
   - → 一律改用 `gh secret set NAME --body "值"`（傳參數、不走管道）

9. **TDD + 純標準函式庫**
   - `ask.py` 只用標準函式庫（subprocess/smtplib/email/datetime/pathlib），執行端零第三方相依
   - 13 個 pytest 覆蓋日期、防重複、讀題、重試、claude 呼叫、組信、寫 log、寄信、main 流程

---

## 📨 問題與輸出

- **問題**：`questions.txt`，一行一題（可多題）。目前一題：「今天新北市永和區天氣如何」。
- **答案**：每天寄一封 Email，主旨「每日 Claude 問答 YYYY-MM-DD」，內文為各題問答。
- **記錄**：`log\YYYY-MM-DD.md`，含問題與完整答案（天氣類會附來源連結）。

---

## 🧩 關鍵檔案速查

| 檔案 | 用途 |
|------|------|
| `ask.py` | **核心**：防重複 → 問 claude → 寄信 → 寫 log（含 `_clean` 防呆） |
| `.github/workflows/daily.yml` | 排程（雙 cron + 手動）、裝環境、跑 ask.py、commit log |
| `questions.txt` | 預設問題（改這裡即可換題） |
| `tests/test_ask.py` | 13 個單元測試 |
| `log/` | 每日問答記錄（自動 commit） |
| `README.md` | 一次性設定與部署指南 |
| `docs/superpowers/specs/`、`plans/` | 設計文件與實作計畫 |

---

## ⚙️ 環境設定（GitHub repo Secrets）

| Secret | 內容 |
|--------|------|
| `CLAUDE_CODE_OAUTH_TOKEN` | 本機 `claude setup-token` 產生（訂閱授權，雲端用你的訂閱問 Claude） |
| `GMAIL_ADDRESS` | 寄件 Gmail 地址 |
| `GMAIL_APP_PASSWORD` | Gmail 應用程式密碼（16 碼，**非**登入密碼；需先開兩步驟驗證） |
| `MAIL_TO` | 收件信箱（目前 `<your-email>@gmail.com`） |

可選環境變數（有預設值）：`CLAUDE_BIN`（預設 `claude`）、`CLAUDE_MODEL`（預設 `sonnet`）、`QUESTIONS_FILE`（預設 `questions.txt`）、`LOG_DIR`（預設 `log`）。

**前置需求**：本機 claude CLI 須先以訂閱帳號 `/login`（非 API 金鑰），`claude setup-token` 才會產出有效 token。

---

## ⚠️ 已知坑 / 注意事項（皆為本次部署實際踩過）

- **GitHub 帳號 Actions 被停用**：原帳號 `737540903` 在帳號層被停用 Actions（repo 按 Enable 報「Unable to enable」），改用 **davidpaul9** 才正常。`gh` 用 PAT 登入需 `repo`、`workflow`、`read:org` scope。
- **401 Invalid bearer token**：根因是本機 `claude` CLI 登入失效 → `setup-token` 產的 token 無效。先 `claude` `/login`、確認 `claude -p "hi"` 本機能答，再 `setup-token`。Windows 貼驗證碼用 Git Bash + Shift+Insert；**驗證碼只貼進終端機，不要貼到別處**。
- **Gmail 535 BadCredentials**：要先開兩步驟驗證、用 app password、`GMAIL_ADDRESS` 與產密碼的帳號一致。可用本機一行驗證：`python -c "import smtplib;s=smtplib.SMTP_SSL('smtp.gmail.com',465);s.login('地址','16碼');print('OK')"`。
- **550 NoSuchUser（退信）**：`MAIL_TO` 被 PowerShell 管道塞了 BOM 隱形字元。修法：`gh secret set MAIL_TO --body "..."`，程式 `_clean()` 另做雙保險。
- **防重複的副作用**：手動觸發測試會產生「當天」的 log，於是當天 06:00 排程會判定「已寄」而跳過。想連當天也收，刪掉 `log\<當天>.md` 再 push。
- **claude -p 失敗常見**：未登入、PATH 上有失效的 `ANTHROPIC_API_KEY`（蓋掉 OAuth）、訂閱限流、斷網。
- **時間換算**：GitHub cron 走 UTC；台灣時間要 −8 換成 UTC（06:00 → `0 22`）。

---

## 🔗 相關

- **Skill**：`claude-headless-automation`（用 `claude -p` 做排程/無人值守 AI 自動化的通用做法，本專案即實例）
- **姊妹專案**：`01_Wechat-report`（`D:\Workspace\99_Claude\01_Wechat-report\`）——同樣用 `claude -p` 訂閱分析，差別在它走 Windows 本機排程、本專案走 GitHub Actions 雲端排程。

---

_最後更新：2026-06-21（建立並驗證上線；含換帳號 davidpaul9、token/Gmail/BOM 三類踩坑修法）_
