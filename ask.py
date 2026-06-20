from datetime import datetime, timezone, timedelta
from pathlib import Path
import subprocess
import time
import smtplib
from email.message import EmailMessage

TW_TZ = timezone(timedelta(hours=8))


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
        raise RuntimeError(f"claude 失敗 rc={proc.returncode} stderr={proc.stderr!r}")
    return out
