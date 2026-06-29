# 05_每日定時問Claude — 專案索引（關鍵字檢索用）

> ## 📌 現況總覽（2026-06-22 合併｜本專案＝單一專案、兩個機制）
> 原 05、06 已合併進**同一資料夾**（本資料夾），保留兩個機制並存：
>
> | 機制 | 角色 | 狀態 |
> |---|---|---|
> | **A — GitHub Actions + `claude -p`**（本檔下方詳述） | 每天清晨寄永和區天氣信 → 紀錄／備援 | ✅ 上線 |
> | **B — claude.ai 雲端 routine（`/schedule` Remote）** | 每天台灣 **05:50** 跑最小 prompt「用一句話給我今天的鼓勵」，**專責準時啟動 5 小時互動視窗**，讓 reset 約落 10:50/15:50/20:50 | ✅ **已驗證成功** |
>
> - **B 才是真正達成「視窗對齊工作時段」目的的那個；A 留作天氣信／備援。**
> - **✅ 驗證完成（2026-06-22）**：B 的 routine 確認會準時啟動 Claude 互動 5 小時用量視窗（usage 頁重置時間約 10:30，與 05:30 啟動相符）。專案目的達成。
> - B 的詳細設定與限制見下方〈🌅 機制 B（claude.ai 雲端 routine）設定與限制〉。
> - 為何另立 B：A 走 GitHub 免費 cron 延遲可達 1～5 小時、且約 2026/6/15 起 `claude -p` 疑似改扣非互動額度、可能不啟動互動視窗；routine 算互動用量且偏移只有幾分鐘，故由 B 負責「準時啟動視窗」。
>
> ---

> 一句話：**GitHub Actions 雲端每天台灣時間 05:30 用 `claude -p` 問固定問題 → 取得答案（可查即時資訊）→ 寄到 Gmail + commit 記錄**，電腦關機也照跑。

> 🎯 **真正目的（最重要）**：用清晨的自動提問「**啟動 Claude Code 的 5 小時用量視窗**」。視窗自首次使用起算 +5 小時 reset；目前設 **05:30 啟動 → 約 10:30 reset → 15:30 reset → 20:30**，讓三段用量配額涵蓋工作時段。天氣問題只是「按下計時器」的載體；寄信只是順便留個證明。
> - 之所以行得通：本專案用的 `CLAUDE_CODE_OAUTH_TOKEN` 就是訂閱本人授權，這通會算進**同一個 5 小時配額池**。
> - 注意：視窗以「訊息實際送達」起算；GitHub 免費 cron 尖峰可能延遲數分鐘，reset 點會跟著順移。想讓 reset 落在不同時間就調整 cron 起算點（起算點 +5 小時 = reset）。

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
GitHub Actions（schedule: cron 30 21 / 40 21 UTC = 台灣 05:30 / 05:40；另有 workflow_dispatch 手動鈕）
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
- **時間換算**：GitHub cron 走 UTC；台灣時間要 −8 換成 UTC（05:30 → `30 21`）。**reset 時間 = 啟動時間 + 5 小時**，要移 reset 就移 cron 起算點。
- **實測 GitHub 排程延遲 ≈ 80～95 分鐘（穩定）**：cron 設台灣 05:23 觸發，實際到信時間觀察：

  | 日期 | 到信 | 延遲 |  | 日期 | 到信 | 延遲 |
  |---|---|---|---|---|---|---|
  | 6/22 | 06:58 | ~95m |  | 6/25 | 06:43 | ~80m |
  | 6/23 | 06:58 | ~95m |  | 6/26 | 06:54 | ~91m |
  | 6/24 | 06:43 | ~80m |  |  |  |  |

  5 天全落在 **06:43–06:58** 窄帶內，延遲固定 80～95 分鐘 —— 沒出現傳說的 1～5 小時暴衝，這個清晨時段 GitHub 算穩定，A 大約 **06:50±8 分**到，可預測。⚠️ **別為此把 cron 提早去「校正」** —— GitHub 延遲仍可能變動，越調越亂；要準時靠機制 B（雲端 routine），A 這封信幾點到無所謂（只是天氣信／備援）。（持續每日觀察中）

---

## 🌅 機制 B（claude.ai 雲端 routine）設定與限制

> 原 `06_每日定時問Claude part2.md` 內容已併入此處，該檔已移除。

- **設定內容**：每日**台灣 05:50** 觸發（routine 用帳號本地時區、數分鐘固定偏移；2026-06-26 由 05:30 改 05:50）；prompt 用最小提問如「用一句話給我今天的鼓勵」（只為消耗一次互動用量以啟動視窗）；執行在 **Anthropic 雲端**；預期 reset 約 10:50 / 15:50 / 20:50。管理：`/schedule list`、`/schedule update`，或 claude.ai 的 Routines 頁。
- **一定要建 Remote（雲端）routine，不要 Local/桌面排程**：本機/桌面排程只在 Claude 應用程式開著時才跑，不符「電腦關機照跑」；雲端 routine 才跑在 Anthropic 雲端、關機照跑。
- **帳號時區要設 Taipei**：routine 依 claude.ai 帳號的本地時區，時區設對才會是台灣 05:30。
- **前置需求**：需 **Pro/Max ＋ 啟用 Claude Code on the web**；`/schedule` 需**訂閱登入** —— 若環境設了 `ANTHROPIC_API_KEY`/`ANTHROPIC_AUTH_TOKEN`，`/schedule` 會消失。
- **執行限制**：routine 每日執行次數有上限（一天一次無虞）；最小間隔 1 小時。
- **可能要綁一個 GitHub repo**：建立 routine 時可能要求綁 repo（primer 用不到，可掛現有 `daily-claude-email` 或一個空 repo）。
- **用量**：routine 用量算進訂閱配額（會吃配額）；本專案目的本就是要它吃一次以啟動互動視窗。
- **research preview**：此功能仍在預覽，行為、限制、API 可能變動。
- 原理（為何用 routine 而非 `claude -p`/GitHub）：官方文件載明「routines draw down subscription usage the same way interactive sessions do」→ routine 會啟動**互動**視窗；而 `claude -p`/GitHub Actions 約 2026/6/15 起疑似改扣**非互動獨立額度**、可能不啟動互動視窗；且 routine 偏移只有數分鐘，遠優於 GitHub 免費 cron 的 1～5 小時亂飄。

---

## 📖 名詞釐清：routine vs schedule、Local vs Remote

- **routine ＝ 名詞**（會定時自動跑的任務本身）；**`/schedule` ＝ 動作/指令**（用來建立、管理 routine）。不是二選一 —— 是「用 `/schedule` 去建一個 routine」。`/schedule list`、`/schedule update` 都是在管 routines。
- routine 分兩種，差在跑在哪、關機跑不跑：
  - **Local（本機）routine**：跑在自己電腦，**Claude 程式開著才跑**，關機不跑 → 不適用本專案。
  - **Remote（雲端）routine**：跑在 Anthropic 雲端，**關機照跑** → 機制 B 用的就是這個。
- **兩個入口、同一件事**：claude.ai 網頁的 **Routines** 頁，或終端機 `claude` 的 `/schedule`（要選 **Remote**）。
- ⚠️ **桌面 agent 環境的排程工具建的是「本機型」**，不是雲端的；要管機制 B 的雲端 routine，得回 claude.ai 的 Routines 頁或終端機 `/schedule`，不在桌面 agent 這邊。

---

## 🔗 相關

- **Skill**：`claude-headless-automation`（用 `claude -p` 做排程/無人值守 AI 自動化的通用做法，本專案即實例）
- **姊妹專案**：`01_Wechat-report`（`D:\Workspace\99_Claude\01_Wechat-report\`）——同樣用 `claude -p` 訂閱分析，差別在它走 Windows 本機排程、本專案走 GitHub Actions 雲端排程。

---

_最後更新：2026-06-22（合併 05+06 為單一專案兩機制；機制 B routine 已驗證成功啟動 5 小時視窗，專案目的達成）_
_2026-06-21（建立並驗證上線；含換帳號 davidpaul9、token/Gmail/BOM 三類踩坑修法）_
