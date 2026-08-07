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
    """세션 장부를 두는 **공유** git 디렉터리 절대경로. 비-git 이면 None.

    링크드 worktree 에서 `--absolute-git-dir` 은 `.git/worktrees/<name>` 로 갈린다.
    장부는 메인 트리와 세션 worktree 가 **같은 곳**을 봐야 소유 판정이 성립하므로
    `--git-common-dir`(둘 다 `.git` 하나로 수렴)을 쓴다.
    """
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, timeout=3,
        )
        if out.returncode == 0:
            d = out.stdout.rstrip("\n")     # 경로 후행 공백 보존(.strip 금지)
            return d if os.path.isabs(d) else os.path.abspath(os.path.join(cwd, d))
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
    ap = os.path.abspath(path if os.path.isabs(path) else os.path.join(cwd, path))
    # 장부는 **수정된 파일이 속한 저장소**에 기록한다. 세션 cwd 만 보면 워크스페이스
    # (비-git) 루트에서 열린 세션은 하위 저장소를 고쳐도 git-dir 해석이 실패해 조용히
    # 아무것도 남기지 않고, 그 장부에 의존하는 게이트 3종의 소유 판정이 무너진다.
    gd = git_dir(os.path.dirname(ap)) or git_dir(cwd)
    if not gd:
        return  # 파일도 cwd 도 git 저장소 밖 → no-op

    session_id = data.get("session_id") or "unknown"
    sess_dir = os.path.join(gd, "git_workflow", "sessions", session_id)
    touched = os.path.join(sess_dir, "touched")
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
