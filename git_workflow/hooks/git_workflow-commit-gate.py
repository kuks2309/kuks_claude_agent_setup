#!/usr/bin/env python3
"""PreToolUse(Bash) 훅 — 보호 브랜치(main/master) 직접 커밋 게이트.

공유 워킹트리·다중 세션(한 창 다중 탭)에서 각 세션이 공유 `main` 위에 직접 커밋해
이력이 교차되는 것을 하드 차단한다(§2-1 세션 브랜치 강제). push-gate 는 push 시점만,
stage-gate 는 staging 파일 소유권만 검사하므로 '커밋 시점' 이 무방비였던 구멍을 닫는다.

판정: (1) HEAD 가 보호 브랜치이고 (2) §2-1 적용조건(단일 워킹트리를 다른 세션도 수정 중)
      이면 DENY. 단일 세션이면 §2 기본(main 직접 커밋)이 정상이므로 통과.

override: 명령에 `gw:allow-main-commit` 주석 또는 env GW_ALLOW_MAIN_COMMIT=1.
self-contained. 계약: stdin JSON → 차단 시 permissionDecision=deny(JSON, exit 0), 통과 시 무출력 exit 0.
한계(정직): 셸 파싱 휴리스틱(eval·alias·xargs 우회 가능), 훅 미설치 세션은 미보호,
          `cd <경로>` 는 반영하나 변수·명령치환(`cd $D`)은 해석 불가 → 세션 cwd 기준 유지(보수적),
          detached HEAD·rebase/merge 중 커밋은 판정 대상 외(통과), 타 세션 판정은
          track.py 가 남긴 touched 기록에 의존하므로 그 세션이 훅 미설치면 미검출.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gw_common as gw  # noqa: E402

RULE_MD = "docs/claude_guideline/git_workflow/git_workflow.md"
PROTECTED = {"main", "master"}


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))
    sys.exit(0)


def _git(cwd, *args):
    try:
        out = subprocess.run(["git", "-C", cwd, *args],
                             capture_output=True, text=True, timeout=3)
        if out.returncode == 0:
            return out.stdout.rstrip("\n")  # 경로 후행 공백 보존(.strip 금지)
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def has_commit_subcmd(cmd):
    """cmd 안에 실제 `git commit` 호출이 있으면 True (git add 등은 무시).

    판정은 공용 `gw.runs_git` 에 위임한다. 이전 구현은 shlex 실패 시 정규식
    `git\\s+…commit\\b` 로 fallback 했는데, 그 정규식이 **문자열 안의** `git commit`
    (파이썬 스크립트·echo·테스트 데이터)까지 잡아 무관한 명령을 deny 했다.
    공용 판정기는 `git` 이 **명령 위치**에 있을 때만 호출로 인정한다.
    """
    return gw.runs_git(cmd, "commit")


def other_sessions_active(gd, sid):
    """이 세션 외 다른 세션이 이 워킹트리에서 파일을 수정했으면 True (§2-1 적용조건)."""
    root = os.path.join(gd, "git_workflow", "sessions")
    try:
        entries = os.listdir(root)
    except OSError:
        return False
    for other in entries:
        if other == sid:
            continue
        p = os.path.join(root, other, "touched")
        try:
            with open(p, encoding="utf-8") as f:
                if any(ln.strip() for ln in f):
                    return True
        except OSError:
            continue
    return False


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        return
    if data.get("tool_name") != "Bash":
        return
    cmd = str((data.get("tool_input") or {}).get("command", ""))
    if not has_commit_subcmd(cmd):
        return

    cwd = gw.target_dir(cmd, data.get("cwd") or os.getcwd())
    # 활성화 판정은 저장소 최상위 기준 — 하위 디렉토리로 cd 해도 게이트가 꺼지지 않게.
    root = _git(cwd, "rev-parse", "--show-toplevel") or cwd
    if not os.path.isfile(os.path.join(root, *RULE_MD.split("/"))):
        return  # 번들 미설치 저장소 → 간섭 안 함
    if "gw:allow-main-commit" in cmd or \
            os.environ.get("GW_ALLOW_MAIN_COMMIT", "").lower() in ("1", "true", "yes"):
        return  # override
    if not has_commit_subcmd(cmd):
        return

    gd = _git(cwd, "rev-parse", "--absolute-git-dir")
    if not gd:
        return
    branch = _git(cwd, "rev-parse", "--abbrev-ref", "HEAD")
    if not branch or branch == "HEAD" or branch not in PROTECTED:
        return  # detached 또는 비-보호 브랜치(session/…) → 통과

    sid = data.get("session_id") or "unknown"
    if not other_sessions_active(gd, sid):
        return  # 단일 세션 → §2 기본(main 직접 커밋) 정상

    deny(
        "공유 워킹트리를 다른 세션도 수정 중인데 보호 브랜치 `%s` 에 직접 커밋하려 합니다"
        "(git_workflow §2-1: 세션 산출물은 `session/<id>` 로 격리, main 반영은 사용자 소관).\n"
        "→ 별도 워킹트리에서 세션 브랜치로 커밋하세요:\n"
        "   git worktree add ../kkw-session-%s -b session/%s\n"
        "   (그 트리에서 이 세션 산출물만 명시 staging 후 커밋 → git push -u origin session/%s)\n"
        "공유 HEAD 가 전역 이동하므로 `git switch`/`checkout -b` 는 쓰지 마세요.\n"
        "의도적 통합 커밋이면 명령에 `# gw:allow-main-commit` 를 붙이세요."
        % (branch, sid[:8], sid[:8], sid[:8])
    )


if __name__ == "__main__":
    main()
