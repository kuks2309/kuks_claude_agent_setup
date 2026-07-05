#!/usr/bin/env python3
"""user_instruction 세션 기록 공유 로직 — 엔트리 형식·파싱·경로 helper.

reminder(쓰기)와 merge(읽기)가 동일 형식을 쓰도록 형식/파싱을 한 곳에 둔다(DRY).
표준 라이브러리만 사용(self-contained).
"""
import os
import re
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
HEADER_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \(KST\) · sess:")


def kst_now_str():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M")


def sessions_dir(cwd):
    return os.path.join(cwd, "docs", "user_instructions", "sessions")


def log_path(cwd):
    return os.path.join(cwd, "docs", "user_instructions", "user_instructions.md")


def rule_active(cwd):
    rule = os.path.join(cwd, "docs", "claude_guideline",
                        "user_instruction", "recording.md")
    return os.path.isfile(rule)


def format_entry(ts, short, prompt):
    """엔트리 블록(끝에 개행 포함). 원문은 큰따옴표만 이스케이프해 인용 보존."""
    safe = prompt.replace("\n", " ").strip()
    return (
        f"## {ts} (KST) · sess:{short}\n\n"
        f"> \"{safe}\"\n\n"
        f"---\n\n"
    )


def parse_entries(text):
    """텍스트에서 (ts_key, block) 목록을 문서 순서대로 추출. 헤더 없는 노이즈는 무시."""
    lines = text.splitlines(keepends=True)
    entries = []
    cur_ts = None
    cur = []
    for ln in lines:
        m = HEADER_RE.match(ln)
        if m:
            if cur_ts is not None:
                entries.append((cur_ts, "".join(cur)))
            cur_ts = m.group(1)
            cur = [ln]
        elif cur_ts is not None:
            cur.append(ln)
    if cur_ts is not None:
        entries.append((cur_ts, "".join(cur)))
    return entries
