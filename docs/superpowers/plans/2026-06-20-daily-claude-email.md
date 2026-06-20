# 每日定時問 Claude 並寄信 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 GitHub Actions 雲端每天台灣時間 06:00 用 `claude -p` 問一個預設問題，把答案寄到 Gmail，並把問答記錄 commit 回 repo。

**Architecture:** 一支純 Python 標準函式庫的 `ask.py`（拆成多個單一職責、可獨立測試的函式）+ 一個 `.github/workflows/daily.yml` 排程。排程兩段觸發（06:00 / 06:10）配合「當天記錄檔是否存在」做防重複，concurrency 防重疊。`claude -p` 走訂閱授權並允許 WebSearch/WebFetch 取得即時天氣。

**Tech Stack:** Python 3.11+（僅標準函式庫：`subprocess`/`smtplib`/`email`/`datetime`/`pathlib`）、pytest（測試）、GitHub Actions、Claude Code CLI（`@anthropic-ai/claude-code`）、Gmail SMTP。

## Global Constraints

- 執行環境為 GitHub Actions `ubuntu-latest`（Linux）；`claude` CLI 經 npm 全域安裝後在 PATH 上，`CLAUDE_BIN` 預設 `"claude"`。
- 與 Claude 互動一律用 `claude -p`，prompt 走 **stdin**，subprocess 設 `encoding="utf-8"`。
- 雲端認證用 Secret `CLAUDE_CODE_OAUTH_TOKEN`（由本機 `claude setup-token` 產生）；**絕不可**設定 `ANTHROPIC_API_KEY`（會蓋掉 OAuth）。
- 台灣日期/時間一律用固定時區 `timezone(timedelta(hours=8))`，不依賴系統時區或 tzdata。
- 寄送時間：台灣 06:00 = UTC 22:00 → cron `0 22 * * *` 與 `10 22 * * *`。
- 預設問題（`questions.txt` 初始內容）：`今天新北市永和區天氣如何`。
- 收件信箱預設 `<your-email>@gmail.com`（由 Secret `MAIL_TO` 提供）。
- 測試一律用 `python -m pytest`（確保 repo 根目錄在 import path 上）。
- Commit 訊息結尾加上：`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

---

### Task 1: 專案骨架與設定檔

**Files:**
- Create: `questions.txt`
- Create: `.gitignore`
- Create: `requirements-dev.txt`
- Create: `log/.gitkeep`
- Create: `tests/__init__.py`（空檔）

- [ ] **Step 1: 初始化 git 與目錄**

```bash
cd "D:/Workspace/99_Claude/05_每日定時問Claude v1"
git init
mkdir -p log tests .github/workflows
```

- [ ] **Step 2: 建立 `questions.txt`**

```text
今天新北市永和區天氣如何
```

- [ ] **Step 3: 建立 `.gitignore`**

```gitignore
__pycache__/
*.pyc
.pytest_cache/
.venv/
.env
```

- [ ] **Step 4: 建立 `requirements-dev.txt`**

```text
pytest>=8.0
```

- [ ] **Step 5: 建立佔位檔**

`log/.gitkeep`（空檔，讓空的 log 目錄能進版控）與 `tests/__init__.py`（空檔）。

- [ ] **Step 6: 安裝測試相依並驗證 pytest 可跑**

Run: `python -m pip install -r requirements-dev.txt && python -m pytest -q`
Expected: pytest 啟動，顯示 `no tests ran`（尚無測試），exit 0。

- [ ] **Step 7: Commit**

```bash
git add questions.txt .gitignore requirements-dev.txt log/.gitkeep tests/__init__.py
git commit -m "chore: 專案骨架與設定檔

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: 台灣日期與防重複判斷

**Files:**
- Create: `ask.py`
- Test: `tests/test_ask.py`

**Interfaces:**
- Produces:
  - `today_tw() -> str`：回傳台灣（UTC+8）今天日期字串 `"YYYY-MM-DD"`。
  - `already_sent(log_dir: pathlib.Path, date_str: str) -> bool`：`log_dir/f"{date_str}.md"` 存在則 True。

- [ ] **Step 1: 寫失敗測試**

```python
# tests/test_ask.py
from datetime import datetime, timezone, timedelta
from pathlib import Path

import ask


def test_today_tw_matches_utc_plus_8():
    expected = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    assert ask.today_tw() == expected


def test_already_sent_false_when_missing(tmp_path):
    assert ask.already_sent(tmp_path, "2026-06-20") is False


def test_already_sent_true_when_present(tmp_path):
    (tmp_path / "2026-06-20.md").write_text("x", encoding="utf-8")
    assert ask.already_sent(tmp_path, "2026-06-20") is True
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest tests/test_ask.py -q`
Expected: FAIL（`ModuleNotFoundError: No module named 'ask'` 或 `AttributeError`）。

- [ ] **Step 3: 寫最小實作**

```python
# ask.py
from datetime import datetime, timezone, timedelta
from pathlib import Path

TW_TZ = timezone(timedelta(hours=8))


def today_tw() -> str:
    return datetime.now(TW_TZ).strftime("%Y-%m-%d")


def already_sent(log_dir: Path, date_str: str) -> bool:
    return (Path(log_dir) / f"{date_str}.md").exists()
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest tests/test_ask.py -q`
Expected: 3 passed。

- [ ] **Step 5: Commit**

```bash
git add ask.py tests/test_ask.py
git commit -m "feat: 台灣日期與防重複判斷

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: 讀取問題清單

**Files:**
- Modify: `ask.py`
- Test: `tests/test_ask.py`

**Interfaces:**
- Produces:
  - `read_questions(path: pathlib.Path) -> list[str]`：回傳去除空白後的非空行清單。

- [ ] **Step 1: 寫失敗測試**

```python
# tests/test_ask.py 追加
def test_read_questions_skips_blank_and_strips(tmp_path):
    f = tmp_path / "questions.txt"
    f.write_text("今天新北市永和區天氣如何\n\n  另一題  \n", encoding="utf-8")
    assert ask.read_questions(f) == ["今天新北市永和區天氣如何", "另一題"]
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest tests/test_ask.py::test_read_questions_skips_blank_and_strips -q`
Expected: FAIL（`AttributeError: module 'ask' has no attribute 'read_questions'`）。

- [ ] **Step 3: 寫最小實作**

```python
# ask.py 追加
def read_questions(path: Path) -> list[str]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [s.strip() for s in lines if s.strip()]
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest tests/test_ask.py -q`
Expected: 4 passed。

- [ ] **Step 5: Commit**

```bash
git add ask.py tests/test_ask.py
git commit -m "feat: 讀取問題清單

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: 重試工具與 claude -p 呼叫

**Files:**
- Modify: `ask.py`
- Test: `tests/test_ask.py`

**Interfaces:**
- Produces:
  - `with_retries(fn, attempts: int = 3, delay: float = 5.0)`：呼叫 `fn()`，例外時最多重試 `attempts` 次，最終仍失敗則 raise 最後一個例外；成功回傳 `fn()` 結果。
  - `ask_claude(question: str, claude_bin: str = "claude", model: str = "sonnet", timeout: int = 180) -> str`：以 stdin 餵 prompt 呼叫 `claude -p`，允許 `WebSearch WebFetch`，成功回傳非空字串，失敗 raise `RuntimeError`。

- [ ] **Step 1: 寫失敗測試**

```python
# tests/test_ask.py 追加
import subprocess
import pytest


def test_with_retries_succeeds_after_failures():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("boom")
        return "ok"

    assert ask.with_retries(flaky, attempts=3, delay=0) == "ok"
    assert calls["n"] == 3


def test_with_retries_raises_after_exhausting():
    def always_fail():
        raise ValueError("nope")

    with pytest.raises(ValueError):
        ask.with_retries(always_fail, attempts=2, delay=0)


def test_ask_claude_uses_stdin_and_returns_output(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["input"] = kwargs.get("input")
        captured["encoding"] = kwargs.get("encoding")
        return subprocess.CompletedProcess(cmd, 0, stdout="多雲偶陣雨\n", stderr="")

    monkeypatch.setattr(ask.subprocess, "run", fake_run)
    out = ask.ask_claude("今天天氣", claude_bin="claude", model="sonnet")
    assert out == "多雲偶陣雨"
    assert captured["input"] == "今天天氣"
    assert captured["encoding"] == "utf-8"
    assert "-p" in captured["cmd"]
    assert "WebSearch WebFetch" in captured["cmd"]


def test_ask_claude_raises_on_nonzero(monkeypatch):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="err")

    monkeypatch.setattr(ask.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError):
        ask.ask_claude("x")
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest tests/test_ask.py -q -k "with_retries or ask_claude"`
Expected: FAIL（`AttributeError`：`with_retries` / `ask_claude` 不存在）。

- [ ] **Step 3: 寫最小實作**

```python
# ask.py 追加（在檔案上方 import 區加入 subprocess、time）
import subprocess
import time


def with_retries(fn, attempts: int = 3, delay: float = 5.0):
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 — 重試所有暫時性錯誤
            last = e
            if i < attempts - 1 and delay:
                time.sleep(delay)
    raise last


def ask_claude(question: str, claude_bin: str = "claude",
               model: str = "sonnet", timeout: int = 180) -> str:
    proc = subprocess.run(
        [claude_bin, "-p", "--model", model,
         "--allowedTools", "WebSearch WebFetch"],
        input=question,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )
    out = (proc.stdout or "").strip()
    if proc.returncode != 0 or not out:
        raise RuntimeError(f"claude 失敗 rc={proc.returncode} stderr={proc.stderr!r}")
    return out
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest tests/test_ask.py -q`
Expected: 8 passed。

- [ ] **Step 5: Commit**

```bash
git add ask.py tests/test_ask.py
git commit -m "feat: 重試工具與 claude -p 呼叫

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: 組信內容與寫記錄檔

**Files:**
- Modify: `ask.py`
- Test: `tests/test_ask.py`

**Interfaces:**
- Consumes：`today_tw()` 產生的日期字串格式 `"YYYY-MM-DD"`。
- Produces:
  - `compose_email(qa_pairs: list[tuple[str, str]], date_str: str) -> tuple[str, str]`：回傳 `(subject, body)`。
  - `write_log(log_dir: pathlib.Path, date_str: str, qa_pairs: list[tuple[str, str]]) -> pathlib.Path`：寫出 `log_dir/f"{date_str}.md"`，回傳該路徑。

- [ ] **Step 1: 寫失敗測試**

```python
# tests/test_ask.py 追加
def test_compose_email_has_subject_and_all_qa():
    subject, body = ask.compose_email(
        [("今天天氣", "多雲"), ("Q2", "A2")], "2026-06-20")
    assert "2026-06-20" in subject
    assert "今天天氣" in body and "多雲" in body
    assert "Q2" in body and "A2" in body


def test_write_log_creates_file_with_content(tmp_path):
    p = ask.write_log(tmp_path, "2026-06-20", [("今天天氣", "多雲")])
    assert p == tmp_path / "2026-06-20.md"
    text = p.read_text(encoding="utf-8")
    assert "2026-06-20" in text
    assert "今天天氣" in text and "多雲" in text
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest tests/test_ask.py -q -k "compose_email or write_log"`
Expected: FAIL（`AttributeError`）。

- [ ] **Step 3: 寫最小實作**

```python
# ask.py 追加
def compose_email(qa_pairs: list[tuple[str, str]], date_str: str) -> tuple[str, str]:
    subject = f"每日 Claude 問答 {date_str}"
    blocks = [f"Q: {q}\n\n{a}" for q, a in qa_pairs]
    body = f"{date_str} 每日 Claude 問答\n\n" + "\n\n---\n\n".join(blocks) + "\n"
    return subject, body


def write_log(log_dir: Path, date_str: str,
              qa_pairs: list[tuple[str, str]]) -> Path:
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"{date_str}.md"
    blocks = [f"## Q: {q}\n\n{a}" for q, a in qa_pairs]
    text = f"# {date_str} 每日 Claude 問答\n\n" + "\n\n".join(blocks) + "\n"
    path.write_text(text, encoding="utf-8")
    return path
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest tests/test_ask.py -q`
Expected: 10 passed。

- [ ] **Step 5: Commit**

```bash
git add ask.py tests/test_ask.py
git commit -m "feat: 組信內容與寫記錄檔

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Gmail SMTP 寄信

**Files:**
- Modify: `ask.py`
- Test: `tests/test_ask.py`

**Interfaces:**
- Produces:
  - `send_email(subject: str, body: str, smtp_user: str, smtp_password: str, mail_to: str) -> None`：用 Gmail SSL（`smtp.gmail.com:465`）寄出純文字 UTF-8 信；失敗則 raise。

- [ ] **Step 1: 寫失敗測試**

```python
# tests/test_ask.py 追加
class _FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.logged_in = None
        self.sent = None
        _FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def login(self, user, pw):
        self.logged_in = (user, pw)

    def send_message(self, msg):
        self.sent = msg


def test_send_email_logs_in_and_sends(monkeypatch):
    _FakeSMTP.instances.clear()
    monkeypatch.setattr(ask.smtplib, "SMTP_SSL", _FakeSMTP)
    ask.send_email("主旨", "內文", "me@gmail.com", "app-pw", "to@gmail.com")
    smtp = _FakeSMTP.instances[-1]
    assert smtp.host == "smtp.gmail.com" and smtp.port == 465
    assert smtp.logged_in == ("me@gmail.com", "app-pw")
    assert smtp.sent["Subject"] == "主旨"
    assert smtp.sent["To"] == "to@gmail.com"
    assert smtp.sent["From"] == "me@gmail.com"
    assert smtp.sent.get_content().strip() == "內文"
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest tests/test_ask.py::test_send_email_logs_in_and_sends -q`
Expected: FAIL（`AttributeError: module 'ask' has no attribute 'send_email'`）。

- [ ] **Step 3: 寫最小實作**

```python
# ask.py 追加（import 區加入 smtplib 與 EmailMessage）
import smtplib
from email.message import EmailMessage


def send_email(subject: str, body: str, smtp_user: str,
               smtp_password: str, mail_to: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = mail_to
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as smtp:
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(msg)
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python -m pytest tests/test_ask.py -q`
Expected: 11 passed。

- [ ] **Step 5: Commit**

```bash
git add ask.py tests/test_ask.py
git commit -m "feat: Gmail SMTP 寄信

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: main 主流程串接

**Files:**
- Modify: `ask.py`
- Test: `tests/test_ask.py`

**Interfaces:**
- Consumes：`today_tw`、`already_sent`、`read_questions`、`with_retries`、`ask_claude`、`compose_email`、`send_email`、`write_log`。
- Produces:
  - `main() -> int`：讀環境變數設定，跑「防重複 → 問 → 寄 → 寫 log」全流程；已寄過回 `0` 且不寄信；正常完成回 `0`。
  - 環境變數：`GMAIL_ADDRESS`、`GMAIL_APP_PASSWORD`、`MAIL_TO`、`CLAUDE_BIN`（預設 `claude`）、`CLAUDE_MODEL`（預設 `sonnet`）、`QUESTIONS_FILE`（預設 `questions.txt`）、`LOG_DIR`（預設 `log`）。

- [ ] **Step 1: 寫失敗測試**

```python
# tests/test_ask.py 追加
def test_main_skips_when_already_sent(tmp_path, monkeypatch):
    (tmp_path / "log").mkdir()
    (tmp_path / "log" / f"{ask.today_tw()}.md").write_text("x", encoding="utf-8")
    (tmp_path / "questions.txt").write_text("Q1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOG_DIR", "log")
    monkeypatch.setenv("QUESTIONS_FILE", "questions.txt")
    sent = {"called": False}
    monkeypatch.setattr(ask, "send_email",
                        lambda *a, **k: sent.__setitem__("called", True))
    assert ask.main() == 0
    assert sent["called"] is False


def test_main_asks_sends_and_logs(tmp_path, monkeypatch):
    (tmp_path / "questions.txt").write_text("今天天氣\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOG_DIR", "log")
    monkeypatch.setenv("QUESTIONS_FILE", "questions.txt")
    monkeypatch.setenv("GMAIL_ADDRESS", "me@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "pw")
    monkeypatch.setenv("MAIL_TO", "to@gmail.com")
    monkeypatch.setattr(ask, "ask_claude", lambda q, **k: f"答:{q}")
    captured = {}
    monkeypatch.setattr(ask, "send_email",
                        lambda subj, body, u, p, to: captured.update(
                            subj=subj, body=body, to=to))
    assert ask.main() == 0
    assert "答:今天天氣" in captured["body"]
    assert captured["to"] == "to@gmail.com"
    assert (tmp_path / "log" / f"{ask.today_tw()}.md").exists()
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python -m pytest tests/test_ask.py -q -k main`
Expected: FAIL（`AttributeError: module 'ask' has no attribute 'main'`）。

- [ ] **Step 3: 寫最小實作**

```python
# ask.py 追加（import 區加入 os、sys）
import os
import sys


def main() -> int:
    log_dir = Path(os.environ.get("LOG_DIR", "log"))
    questions_file = Path(os.environ.get("QUESTIONS_FILE", "questions.txt"))
    claude_bin = os.environ.get("CLAUDE_BIN", "claude")
    model = os.environ.get("CLAUDE_MODEL", "sonnet")

    date_str = today_tw()
    if already_sent(log_dir, date_str):
        print(f"[skip] {date_str} 已寄過，跳過")
        return 0

    questions = read_questions(questions_file)
    qa_pairs = [(q, with_retries(lambda q=q: ask_claude(q, claude_bin=claude_bin,
                                                         model=model)))
                for q in questions]

    subject, body = compose_email(qa_pairs, date_str)
    smtp_user = os.environ["GMAIL_ADDRESS"]
    smtp_password = os.environ["GMAIL_APP_PASSWORD"]
    mail_to = os.environ.get("MAIL_TO", smtp_user)
    with_retries(lambda: send_email(subject, body, smtp_user, smtp_password, mail_to))

    write_log(log_dir, date_str, qa_pairs)
    print(f"[done] {date_str} 已寄出並記錄")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 跑全部測試確認通過**

Run: `python -m pytest -q`
Expected: 13 passed。

- [ ] **Step 5: Commit**

```bash
git add ask.py tests/test_ask.py
git commit -m "feat: main 主流程串接

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: GitHub Actions 排程 workflow

**Files:**
- Create: `.github/workflows/daily.yml`

**Interfaces:**
- Consumes：repo 根目錄的 `ask.py`、`questions.txt`；Secrets `CLAUDE_CODE_OAUTH_TOKEN`、`GMAIL_ADDRESS`、`GMAIL_APP_PASSWORD`、`MAIL_TO`。

- [ ] **Step 1: 建立 workflow**

```yaml
# .github/workflows/daily.yml
name: daily-ask

on:
  schedule:
    - cron: "0 22 * * *"   # 台灣 06:00
    - cron: "10 22 * * *"  # 台灣 06:10 補觸發
  workflow_dispatch: {}

concurrency:
  group: daily-ask
  cancel-in-progress: false

permissions:
  contents: write

jobs:
  ask:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Claude Code
        run: npm install -g @anthropic-ai/claude-code

      - name: Run daily ask
        env:
          CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          GMAIL_ADDRESS: ${{ secrets.GMAIL_ADDRESS }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
          MAIL_TO: ${{ secrets.MAIL_TO }}
        run: python ask.py

      - name: Commit log
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add log/
          git diff --staged --quiet || git commit -m "log: 每日問答記錄 [skip ci]"
          git push
```

- [ ] **Step 2: 驗證 YAML 語法正確**

Run: `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/daily.yml',encoding='utf-8')); print('yaml ok')"`
Expected: 印出 `yaml ok`（無例外）。若本機未裝 PyYAML，可改 `python -m pip install pyyaml` 後再跑。

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/daily.yml
git commit -m "ci: 每日排程 workflow

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: README 設定與部署指南

**Files:**
- Create: `README.md`

**Interfaces:**
- 無程式介面；提供使用者一次性設定步驟。

- [ ] **Step 1: 建立 README**

````markdown
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
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README 設定與部署指南

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 部署後手動驗收（使用者執行）

1. 完成 README 的 4 個一次性設定步驟並 push。
2. Actions 手動觸發 `daily-ask`，確認：信箱收到「每日 Claude 問答」、`log/` 新增當天記錄、答案內含實際永和區天氣（代表 WebSearch 生效）。
3. 隔天確認 06:00 左右自動寄達。
```
