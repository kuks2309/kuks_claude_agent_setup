#!/usr/bin/env python3
"""session_record.py + user_instruction-reminder.py 단위 테스트 (표준 라이브러리만)."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # hooks/ 를 import 경로에
import session_record as sr  # noqa: E402


def test_format_and_parse_roundtrip():
    block = sr.format_entry("2026-07-01 14:30", "abcd1234", 'do "X" now')
    assert "## 2026-07-01 14:30 (KST) · sess:abcd1234" in block
    assert '> "do \\"X\\" now"' in block or '> "do "X" now"' in block
    entries = sr.parse_entries(block)
    assert len(entries) == 1
    assert entries[0][0] == "2026-07-01 14:30"


def test_parse_multiple_newest_first_preserved():
    text = (
        sr.format_entry("2026-07-01 15:00", "aaaa1111", "second")
        + sr.format_entry("2026-07-01 14:00", "aaaa1111", "first")
    )
    entries = sr.parse_entries(text)
    assert [e[0] for e in entries] == ["2026-07-01 15:00", "2026-07-01 14:00"]


def test_parse_ignores_nonentry_noise():
    text = "leading junk\n\n" + sr.format_entry("2026-07-01 14:00", "b2", "x")
    entries = sr.parse_entries(text)
    assert len(entries) == 1


# --- user_instruction-reminder.py (하위프로세스 실행) ---

def _run_reminder(cwd, prompt, session_id):
    hook = os.path.join(os.path.dirname(HERE), "user_instruction-reminder.py")
    payload = json.dumps({"prompt": prompt, "session_id": session_id, "cwd": cwd})
    return subprocess.run([sys.executable, hook], input=payload,
                          capture_output=True, text=True, timeout=5)


def _activate_rule(cwd):
    d = os.path.join(cwd, "docs", "claude_guideline", "user_instruction")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "recording.md"), "w").close()


def test_reminder_records_to_own_session_file():
    with tempfile.TemporaryDirectory() as cwd:
        _activate_rule(cwd)
        _run_reminder(cwd, "first instruction", "1111aaaa-x")
        f = os.path.join(cwd, "docs", "user_instructions", "sessions", "1111aaaa-x.md")
        assert os.path.isfile(f)
        assert "first instruction" in open(f, encoding="utf-8").read()


def test_reminder_isolates_other_sessions():
    with tempfile.TemporaryDirectory() as cwd:
        _activate_rule(cwd)
        _run_reminder(cwd, "session A secret", "AAAA-a")
        out = _run_reminder(cwd, "session B prompt", "BBBB-b")
        # 세션 B 주입 stdout 에 세션 A 원문이 새어들면 안 됨
        assert "session A secret" not in out.stdout
        assert "session B prompt" in out.stdout  # 자기 기록은 참조로 주입


def test_reminder_noop_without_rule():
    with tempfile.TemporaryDirectory() as cwd:
        out = _run_reminder(cwd, "x", "CCCC-c")
        assert out.stdout.strip() == ""
        assert not os.path.exists(os.path.join(cwd, "docs", "user_instructions"))


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                fails += 1
                print(f"FAIL {name}: {e}")
    sys.exit(1 if fails else 0)
