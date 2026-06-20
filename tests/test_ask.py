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
