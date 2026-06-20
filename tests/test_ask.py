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


def test_read_questions_skips_blank_and_strips(tmp_path):
    f = tmp_path / "questions.txt"
    f.write_text("今天新北市永和區天氣如何\n\n  另一題  \n", encoding="utf-8")
    assert ask.read_questions(f) == ["今天新北市永和區天氣如何", "另一題"]


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
