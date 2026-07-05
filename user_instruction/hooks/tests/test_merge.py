#!/usr/bin/env python3
"""user_instruction-merge.py SessionEnd 병합 테스트."""
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import session_record as sr  # noqa: E402


def _activate_rule(cwd):
    d = os.path.join(cwd, "docs", "claude_guideline", "user_instruction")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "recording.md"), "w").close()


def _write_session(cwd, sid, entries):
    d = sr.sessions_dir(cwd)
    os.makedirs(d, exist_ok=True)
    text = "".join(sr.format_entry(ts, sid[:8], p) for ts, p in entries)
    with open(os.path.join(d, sid + ".md"), "w", encoding="utf-8") as f:
        f.write(text)


def _run_merge(cwd, sid):
    hook = os.path.join(os.path.dirname(HERE), "user_instruction-merge.py")
    payload = json.dumps({"session_id": sid, "cwd": cwd, "reason": "clear"})
    return subprocess.run([sys.executable, hook], input=payload,
                          capture_output=True, text=True, timeout=5)


def test_merge_moves_own_entries_and_deletes_file():
    with tempfile.TemporaryDirectory() as cwd:
        _activate_rule(cwd)
        _write_session(cwd, "SID-own", [("2026-07-01 14:00", "hello")])
        _run_merge(cwd, "SID-own")
        log = open(sr.log_path(cwd), encoding="utf-8").read()
        assert "hello" in log and "sess:SID-own"[:13] in log
        assert not os.path.exists(os.path.join(sr.sessions_dir(cwd), "SID-own.md"))


def test_merge_ignores_other_live_sessions():
    with tempfile.TemporaryDirectory() as cwd:
        _activate_rule(cwd)
        _write_session(cwd, "SID-a", [("2026-07-01 14:00", "a-live")])
        _write_session(cwd, "SID-b", [("2026-07-01 15:00", "b-live")])
        _run_merge(cwd, "SID-a")
        # 병합은 자기(SID-a)만, SID-b live 파일은 그대로
        assert os.path.exists(os.path.join(sr.sessions_dir(cwd), "SID-b.md"))
        log = open(sr.log_path(cwd), encoding="utf-8").read()
        assert "a-live" in log and "b-live" not in log


def test_merge_time_ordered_newest_first():
    with tempfile.TemporaryDirectory() as cwd:
        _activate_rule(cwd)
        # 기존 로그에 더 최신 엔트리 (log 부모 디렉터리 선생성)
        os.makedirs(os.path.dirname(sr.log_path(cwd)), exist_ok=True)
        with open(sr.log_path(cwd), "w", encoding="utf-8") as f:
            f.write(sr.format_entry("2026-07-01 16:00", "OLD-x", "existing-newer"))
        _write_session(cwd, "SID-x", [("2026-07-01 14:00", "older-merged")])
        _run_merge(cwd, "SID-x")
        entries = sr.parse_entries(open(sr.log_path(cwd), encoding="utf-8").read())
        assert [e[0] for e in entries] == ["2026-07-01 16:00", "2026-07-01 14:00"]


def test_merge_gc_orphan_older_than_7d():
    with tempfile.TemporaryDirectory() as cwd:
        _activate_rule(cwd)
        _write_session(cwd, "SID-self", [("2026-07-01 14:00", "self")])
        _write_session(cwd, "SID-orphan", [("2026-06-01 10:00", "orphan")])
        orphan = os.path.join(sr.sessions_dir(cwd), "SID-orphan.md")
        old = time.time() - 8 * 86400
        os.utime(orphan, (old, old))
        _run_merge(cwd, "SID-self")
        # orphan(>7d, 비-자기)은 GC 로 병합 후 삭제
        assert not os.path.exists(orphan)
        log = open(sr.log_path(cwd), encoding="utf-8").read()
        assert "orphan" in log


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
