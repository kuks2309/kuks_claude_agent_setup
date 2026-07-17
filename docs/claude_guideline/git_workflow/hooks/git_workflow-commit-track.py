#!/usr/bin/env python3
"""PostToolUse(Bash) 훅 — 이 세션이 만든 커밋 해시를 기록.

push-gate 가 '이 세션 커밋 vs 타 세션 커밋'을 판정하도록, git commit 실행 후 새 HEAD 를
.git/git_workflow/sessions/<session_id>/commits 에 누적한다(.git 내부라 비-커밋·세션별 분리).

self-contained: Claude Code 네이티브 session_id + .git 내부. 계약: stdin JSON → 부수효과, 항상 exit 0.
한계(정직): 셸 파싱 휴리스틱. `git commit` no-op(스테이징 0)이어도 현재 HEAD 를 기록할 수 있으나
          dedup 으로 완화. merge/rebase/cherry-pick 로 만든 커밋은 미추적(그 경우 push-gate 가
          false-deny → override 로 해소).
"""
import json
import os
import subprocess
import sys

RULE_MD = "docs/claude_guideline/git_workflow/git_workflow.md"


def _git(cwd, *args):
    try:
        out = subprocess.run(["git", "-C", cwd, *args],
                             capture_output=True, text=True, timeout=3)
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
    if data.get("tool_name") != "Bash":
        return
    cmd = str((data.get("tool_input") or {}).get("command", ""))
    if "git" not in cmd or "commit" not in cmd:
        return

    cwd = data.get("cwd") or os.getcwd()
    if not os.path.isfile(os.path.join(cwd, *RULE_MD.split("/"))):
        return  # 번들 미설치 → 간섭 안 함
    gd = _git(cwd, "rev-parse", "--absolute-git-dir")
    if not gd:
        return
    h = _git(cwd, "rev-parse", "HEAD")
    if not h:
        return

    sid = data.get("session_id") or "unknown"
    d = os.path.join(gd, "git_workflow", "sessions", sid)
    rec = os.path.join(d, "commits")
    try:
        existing = set()
        if os.path.isfile(rec):
            with open(rec, encoding="utf-8") as f:
                existing = {ln.strip() for ln in f if ln.strip()}
        if h not in existing:
            os.makedirs(d, exist_ok=True)
            with open(rec, "a", encoding="utf-8") as f:
                f.write(h + "\n")
    except OSError:
        return


if __name__ == "__main__":
    main()
