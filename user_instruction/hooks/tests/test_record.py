#!/usr/bin/env python3
"""session_record.py 단위 테스트 (표준 라이브러리만, 프레임워크 비의존)."""
import os
import sys

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
