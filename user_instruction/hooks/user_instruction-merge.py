#!/usr/bin/env python3
"""SessionEnd 훅 — 이 세션의 sessions/{id}.md 를 user_instructions.md 로 병합.

세션 격리: 자기 세션 파일만 병합·삭제한다. orphan(크래시로 남은 비-자기 파일)은
mtime>7일인 것만 보수적으로 회수(live 세션 파일은 7일 내라 안전). 공유 로그
rewrite 는 flock 으로 직렬화(동시 종료 시 lost-write 방지).

self-contained: 표준 라이브러리만. 계약: stdin JSON → 부수효과, 항상 exit 0.
"""
import fcntl
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import session_record as sr  # noqa: E402

ORPHAN_AGE = 7 * 86400


def _merge_blocks(cwd, blocks):
    """blocks(엔트리 문자열들)를 기존 로그와 시간 역순 병합 후 rewrite. flock 보호."""
    log = sr.log_path(cwd)
    os.makedirs(os.path.dirname(log), exist_ok=True)
    lock = log + ".lock"
    with open(lock, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            existing = ""
            if os.path.isfile(log):
                with open(log, encoding="utf-8") as f:
                    existing = f.read()
            entries = sr.parse_entries(existing)
            for b in blocks:
                entries.extend(sr.parse_entries(b))
            # ts_key 내림차순(문자열 정렬이 시간순과 일치하는 형식), 안정 정렬
            entries.sort(key=lambda e: e[0], reverse=True)
            merged = "".join(b for _, b in entries)
            tmp = log + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(merged)
            os.replace(tmp, log)
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        return

    cwd = data.get("cwd") or os.getcwd()
    if not sr.rule_active(cwd):
        return

    session_id = data.get("session_id") or "unknown"
    sess_dir = sr.sessions_dir(cwd)
    if not os.path.isdir(sess_dir):
        return

    own = os.path.join(sess_dir, session_id + ".md")
    to_merge = []       # (path, text)
    # 1) 자기 세션 파일
    if os.path.isfile(own):
        try:
            with open(own, encoding="utf-8") as f:
                to_merge.append((own, f.read()))
        except OSError:
            pass
    # 2) orphan GC: 비-자기 & mtime>7d
    now = time.time()
    for name in os.listdir(sess_dir):
        if not name.endswith(".md"):
            continue
        p = os.path.join(sess_dir, name)
        if p == own:
            continue
        try:
            if now - os.path.getmtime(p) > ORPHAN_AGE:
                with open(p, encoding="utf-8") as f:
                    to_merge.append((p, f.read()))
        except OSError:
            continue

    if not to_merge:
        return
    _merge_blocks(cwd, [text for _, text in to_merge])
    for p, _ in to_merge:
        try:
            os.remove(p)
        except OSError:
            pass


if __name__ == "__main__":
    main()
