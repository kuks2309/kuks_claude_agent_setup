#!/usr/bin/env python3
"""PostToolUse(Bash) 훅 — 이 세션이 만든 커밋 해시를 대상 저장소에 기록.

push-gate 가 '이 세션 커밋 vs 타 세션 커밋'을 판정하도록, git commit 실행 후 새 HEAD 를
<repo>/.git/git_workflow/sessions/<session_id>/commits 에 누적한다(.git 내부·세션별 분리).

대상 저장소는 명령에서 해석(gw_common.resolve_repo) — 워크스페이스 루트 세션이
`cd <subdir> && git commit` 해도 그 하위 저장소에 기록된다.

self-contained. 계약: stdin JSON → 부수효과, 항상 exit 0.
한계(정직): 셸 파싱 휴리스틱. no-op 커밋도 현재 HEAD 기록 가능하나 dedup 으로 완화.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gw_common as gw  # noqa: E402


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
    repo = gw.resolve_repo(cmd, cwd)
    if not gw.rule_active(repo):
        return  # 번들 미설치 저장소 → 간섭 안 함
    gd = gw.git_dir(repo)
    h = gw.run_git(repo, "rev-parse", "HEAD")
    if not gd or not h:
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
