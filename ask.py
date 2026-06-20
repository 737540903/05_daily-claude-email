from datetime import datetime, timezone, timedelta
from pathlib import Path
import subprocess
import time
import smtplib
from email.message import EmailMessage
import os
import sys

TW_TZ = timezone(timedelta(hours=8))


def _clean(s: str) -> str:
    """去除前後空白與隱形字元(BOM/零寬字元)，避免汙染金鑰或信箱地址。"""
    return s.replace("﻿", "").replace("​", "").strip()


def today_tw() -> str:
    return datetime.now(TW_TZ).strftime("%Y-%m-%d")


def already_sent(log_dir: Path, date_str: str) -> bool:
    return (Path(log_dir) / f"{date_str}.md").exists()


def read_questions(path: Path) -> list[str]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [s.strip() for s in lines if s.strip()]


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
        err = (proc.stderr or "").strip()
        raise RuntimeError(
            f"claude 失敗 rc={proc.returncode} stdout={out!r} stderr={err!r}")
    return out


def main() -> int:
    log_dir = Path(os.environ.get("LOG_DIR", "log"))
    questions_file = Path(os.environ.get("QUESTIONS_FILE", "questions.txt"))
    claude_bin = os.environ.get("CLAUDE_BIN", "claude")
    model = os.environ.get("CLAUDE_MODEL", "sonnet")

    # 防呆：Secret 若夾帶前後空白/換行/隱形字元(BOM)會造成認證或收件失敗
    tok = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if tok and _clean(tok) != tok:
        os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = _clean(tok)

    date_str = today_tw()
    if already_sent(log_dir, date_str):
        print(f"[skip] {date_str} 已寄過，跳過")
        return 0

    questions = read_questions(questions_file)
    qa_pairs = [(q, with_retries(lambda q=q: ask_claude(q, claude_bin=claude_bin,
                                                         model=model)))
                for q in questions]

    subject, body = compose_email(qa_pairs, date_str)
    smtp_user = _clean(os.environ["GMAIL_ADDRESS"])
    # Gmail 應用程式密碼常以 4 組 4 碼顯示（含空白），SMTP 需去除空白
    smtp_password = _clean(os.environ["GMAIL_APP_PASSWORD"]).replace(" ", "")
    mail_to = _clean(os.environ.get("MAIL_TO", smtp_user))
    with_retries(lambda: send_email(subject, body, smtp_user, smtp_password, mail_to))

    write_log(log_dir, date_str, qa_pairs)
    print(f"[done] {date_str} 已寄出並記錄")
    return 0


if __name__ == "__main__":
    sys.exit(main())
