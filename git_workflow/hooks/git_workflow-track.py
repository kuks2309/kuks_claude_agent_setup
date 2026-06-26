#!/usr/bin/env python3
"""PostToolUse 훅 — 파일 수정 도구 사용 시 '이 세션이 만진 파일'을 세션별로 기록.

배경: working tree(파일시스템)는 모든 세션이 공유하므로 git status 에 타 세션의 미커밋
변경이 섞인다. 본 훅이 Claude Code 네이티브 session_id 로 세션별 수정 파일 목록을 .git
내부에 누적해, 커밋 시 reminder 훅이 '이 세션 파일만' staging 하도록 grounding 데이터를 준다.

self-contained: OMC 등 외부 도구 비의존. 저장 위치는 .git 내부(항상 비-커밋, 비-동기).
계약(Claude Code PostToolUse): stdin JSON → 부수효과(파일 기록). 항상 exit 0.
"""
import json
import os
import subprocess
import sys

TRACK_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")


def git_dir(cwd):
    """worktree·submodule 안전하게 절대 git-dir 해석. 비-git 이면 None."""
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--absolute-git-dir"],
            capture_output=True, text=True, timeout=3,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        return

    if data.get("tool_name", "") not in TRACK_TOOLS:
        return

    ti = data.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("notebook_path")
    if not path:
        return

    cwd = data.get("cwd") or os.getcwd()
    gd = git_dir(cwd)
    if not gd:
        return  # git 저장소 아님 → no-op

    session_id = data.get("session_id") or "unknown"
    sess_dir = os.path.join(gd, "git_workflow", "sessions", session_id)
    touched = os.path.join(sess_dir, "touched")
    ap = os.path.abspath(path)
    try:
        os.makedirs(sess_dir, exist_ok=True)
        existing = set()
        if os.path.isfile(touched):
            with open(touched, encoding="utf-8") as f:
                existing = {ln.strip() for ln in f if ln.strip()}
        if ap not in existing:
            with open(touched, "a", encoding="utf-8") as f:
                f.write(ap + "\n")
    except OSError:
        return


if __name__ == "__main__":
    main()
