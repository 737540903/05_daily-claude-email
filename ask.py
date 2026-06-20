from datetime import datetime, timezone, timedelta
from pathlib import Path

TW_TZ = timezone(timedelta(hours=8))


def today_tw() -> str:
    return datetime.now(TW_TZ).strftime("%Y-%m-%d")


def already_sent(log_dir: Path, date_str: str) -> bool:
    return (Path(log_dir) / f"{date_str}.md").exists()
