#!/usr/bin/env python3
"""session_workflow 상태 공유 로직 — 경로·레지스트리·handoff 형식 helper.

4개 훅(start·gate·track·end)이 동일 상태 형식을 쓰도록 한 곳에 둔다(DRY).
표준 라이브러리만 사용(self-contained). 상태는 .git 내부(항상 비커밋)의
session_workflow/ 아래: active/<sid>.json · active/<sid>.touched · handoff/<sid>.md.
각 세션은 자기 이름 파일에만 쓴다(공유 rewrite 없음 → 잠금 불요).
"""
import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
STALE_HOURS = 24          # last_seen 이보다 오래되면 잔류 의심
HANDOFF_KEEP_DAYS = 14    # handoff 자동 정리 기한
PURPOSE_RE = re.compile(r"^\s*(?:목적|purpose)\s*[::]\s*(.+)$",
                        re.IGNORECASE | re.DOTALL)


def kst_now():
    return datetime.now(KST)


def kst_now_str():
    return kst_now().strftime("%Y-%m-%d %H:%M")


def rule_active(cwd):
    return os.path.isfile(os.path.join(
        cwd, "docs", "claude_guideline", "session_workflow",
        "session_workflow.md"))


def git_common_dir(cwd):
    """worktree 안전한 공유 git dir(절대경로). 비-git 이면 None."""
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, timeout=3)
        if out.returncode == 0:
            p = out.stdout.strip()
            return p if os.path.isabs(p) else os.path.abspath(
                os.path.join(cwd, p))
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def repo_top(cwd):
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=3)
        if out.returncode == 0:
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def state_root(cwd):
    """상태 저장소 루트. 규칙 미설치·비-git 이면 None(no-op 게이트)."""
    if not rule_active(cwd):
        return None
    gd = git_common_dir(cwd)
    return os.path.join(gd, "session_workflow") if gd else None


def active_dir(root):
    return os.path.join(root, "active")


def handoff_dir(root):
    return os.path.join(root, "handoff")


def session_json(root, sid):
    return os.path.join(active_dir(root), sid + ".json")


def touched_path(root, sid):
    return os.path.join(active_dir(root), sid + ".touched")


def load_session(root, sid):
    try:
        with open(session_json(root, sid), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def save_session(root, sid, meta):
    os.makedirs(active_dir(root), exist_ok=True)
    with open(session_json(root, sid), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)


def ensure_session(root, sid):
    """세션 항목 보장(SessionStart 누락·resume 대비). 기존 meta 보존."""
    meta = load_session(root, sid)
    if meta is None:
        now = kst_now_str()
        meta = {"purpose": None, "started_at": now,
                "last_seen": now, "alerted": []}
    return meta


def read_touched(root, sid):
    try:
        with open(touched_path(root, sid), encoding="utf-8") as f:
            return [ln.strip() for ln in f if ln.strip()]
    except OSError:
        return []


def list_other_active(root, sid):
    """[(other_sid, meta)] — 자기 제외, 손상 json 무시, 이름순."""
    out = []
    try:
        names = os.listdir(active_dir(root))
    except OSError:
        return out
    for n in sorted(names):
        if not n.endswith(".json"):
            continue
        osid = n[:-5]
        if osid == sid:
            continue
        meta = load_session(root, osid)
        if meta is not None:
            out.append((osid, meta))
    return out


def is_stale(meta):
    try:
        seen = datetime.strptime(
            meta.get("last_seen", ""), "%Y-%m-%d %H:%M").replace(tzinfo=KST)
    except ValueError:
        return True
    return kst_now() - seen > timedelta(hours=STALE_HOURS)


def one_line(text, limit=120):
    s = " ".join(str(text).split())
    return s if len(s) <= limit else s[:limit] + "…"


def format_handoff(short, meta, ended, uncommitted, touched):
    lines = [
        f"# 세션 인수인계 · sess:{short}",
        f"- 목적: {one_line(meta.get('purpose') or '(미등록)')}",
        f"- 시작: {meta.get('started_at', '?')} (KST) · 종료: {ended} (KST)",
        f"- 미커밋 파일 ({len(uncommitted)}개):",
    ]
    lines += [f"  - {p}" for p in uncommitted]
    lines.append(f"- 이 세션 수정 파일 전체: {len(touched)}개")
    return "\n".join(lines) + "\n"


def parse_handoff_summary(path):
    """handoff 파일에서 (목적, 미커밋 개수) 요약 추출. 실패 시 ('?', '?')."""
    purpose, count = "?", "?"
    try:
        with open(path, encoding="utf-8") as f:
            for ln in f:
                if ln.startswith("- 목적: "):
                    purpose = ln[len("- 목적: "):].strip()
                m = re.match(r"^- 미커밋 파일 \((\d+)개\)", ln)
                if m:
                    count = m.group(1)
    except OSError:
        pass
    return purpose, count
