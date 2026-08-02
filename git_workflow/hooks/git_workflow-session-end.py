#!/usr/bin/env python3
"""SessionEnd 훅 — 이 세션의 session/<id> 브랜치를 main 에 안전 병합.

세션이 자기 worktree(session/<id> 브랜치)에서 작업했으면 종료 시 git_workflow-session.sh 로
main 에 자동 병합·push·정리(브랜치 삭제)한다. 브랜치가 없으면(공유 main 에서 작업) no-op.
충돌이면 병합 보류(브랜치 보존, 사용자 수동 병합).

self-contained: git_workflow-session.sh 위임. 계약: stdin JSON → 부수효과, 항상 exit 0.
비-git cwd(워크스페이스 세션)면 직속 하위 git 저장소에서 session/<id> 브랜치 보유 repo 를
찾아 그 repo 에서 end 를 수행한다(링크드 worktree 는 .git 이 파일이라 자연 제외).
한계(정직): 네트워크 push 를 동반하므로 timeout 여유 필요(설치 시 60s). 세션이 worktree 를
          안 썼으면(공유 main 커밋) 이 훅은 no-op — 그 경우 격리 효과 없음(워크플로 준수 필요).
          하위 저장소 탐색은 워크스페이스 직속 1 단계만(중첩 깊이 2+ 미탐색).
"""
import json
import os
import subprocess
import sys

RULE_MD = "docs/claude_guideline/git_workflow/git_workflow.md"


def is_git_repo(d):
    return subprocess.run(["git", "-C", d, "rev-parse", "--git-dir"],
                          capture_output=True).returncode == 0


def repos_with_session_branch(cwd, sid8):
    """비-git cwd 직속 하위 중 session/<sid8> 브랜치를 가진 main repo 목록."""
    out = []
    try:
        entries = sorted(os.listdir(cwd))
    except OSError:
        return out
    for name in entries:
        d = os.path.join(cwd, name)
        if not os.path.isdir(os.path.join(d, ".git")):
            continue  # .git 이 파일인 링크드 worktree·비저장소 제외
        r = subprocess.run(["git", "-C", d, "show-ref", "--verify", "--quiet",
                            "refs/heads/session/" + sid8], capture_output=True)
        if r.returncode == 0:
            out.append(d)
    return out


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        return

    cwd = data.get("cwd") or os.getcwd()
    if not os.path.isfile(os.path.join(cwd, *RULE_MD.split("/"))):
        return  # 번들 미설치 → no-op
    sid = data.get("session_id") or ""
    if not sid:
        return
    sid8 = sid[:8]

    script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "git_workflow-session.sh")
    if not os.path.isfile(script):
        return
    targets = [cwd] if is_git_repo(cwd) else repos_with_session_branch(cwd, sid8)
    for target in targets:
        try:
            subprocess.run(["bash", script, "end", sid8], cwd=target,
                           capture_output=True, text=True, timeout=90)
        except (OSError, subprocess.SubprocessError):
            pass  # 병합 실패해도 세션 종료는 진행(브랜치 보존됨)


if __name__ == "__main__":
    main()
