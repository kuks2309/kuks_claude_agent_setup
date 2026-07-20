#!/usr/bin/env python3
"""UserPromptSubmit 훅 — git 작업 트리거 시 git_workflow SOP + '이번 세션 수정 파일' 강제 주입.

배경: CLAUDE.md 등록이 '수동 포인터'라 모델이 git_workflow.md 를 능동적으로 열지 않고
임의 커밋/푸시로 직행하는 절차 실패가 발생한다. 또한 working tree 는 모든 세션이 공유하므로
git status 에 타 세션 변경이 섞인다. 본 훅이 트리거 감지 시 (1) 모드 판정·커밋 규약·원격
정책 SOP 와 (2) git_workflow-track.py 가 기록한 '이 세션이 수정한 파일' 목록을 주입해
세션 격리 staging 을 grounding 한다.

self-contained: OMC 등 외부 도구 비의존. session_id·git-dir 는 Claude Code 네이티브.
계약(Claude Code UserPromptSubmit): stdin JSON → stdout 이 컨텍스트로 주입. 항상 exit 0.
"""
import json
import os
import re
import subprocess
import sys

TRIGGERS = (
    "커밋", "commit", "푸시", "push", "머지", "merge",
    "리베이스", "rebase", "pull request", "풀리퀘스트", "풀리퀘",
    "pr 올려", "pr 생성", "pr 만들", "pr 보내",
    "체크아웃", "checkout", "브랜치", "branch", "stash", "스태시",
    "cherry-pick", "체리픽", "force push", "force-push", "포스 푸시",
)

RULE_MD = "docs/claude_guideline/git_workflow/git_workflow.md"

DIRECTIVE = """[GIT-WORKFLOW SOP — 강제 게이트]
git 작업(commit/push/merge/PR/branch) 트리거가 감지되었습니다. 응답 전 반드시 아래를 선행하세요:

1. {rule} 를 Read 한다 (등록 사실만 알고 건너뛰지 말 것).
2. solo/team 모드를 판정하고, 커밋 규약(type(scope): subject + Co-Authored-By), 명시 staging(-A/. 금지), 다중 원격 push 정책을 따른다.
3. team 모드면 main 직접 push 금지 — 브랜치 → PR → 리뷰 ≥1 승인 → merge, 작성자 self-approve 금지.
4. 공유 브랜치 force-push 금지, 충돌은 로컬 rebase.""".format(rule=RULE_MD)


def _git(cwd, *args):
    try:
        out = subprocess.run(
            ["git", "-C", cwd, *args],
            capture_output=True, text=True, timeout=3,
        )
        if out.returncode == 0:
            return out.stdout.rstrip("\n")  # 경로 후행 공백 보존(.strip 금지)
    except (OSError, subprocess.SubprocessError):
        pass
    return None


MODE_RE = re.compile(r"git\s*협업\s*모드\s*:\s*(solo|team)", re.IGNORECASE)


def mode_section(cwd):
    """README → CLAUDE.md 순으로 협업 모드 선언을 찾는다. 없으면 문의·기록 강제."""
    if not cwd:
        return ""
    for fn in ("README.md", "CLAUDE.md"):
        try:
            with open(os.path.join(cwd, fn), encoding="utf-8") as f:
                m = MODE_RE.search(f.read())
        except OSError:
            continue
        if m:
            return (
                "\n\n[협업 모드] {fn} 선언: **{mode}**. 이 모드의 push·리뷰 정책을 따르세요."
            ).format(fn=fn, mode=m.group(1).lower())
    return (
        "\n\n[협업 모드 — 미선언, 진행 전 필수]\n"
        "README.md·CLAUDE.md 에 `git 협업 모드: solo|team` 선언이 없습니다. "
        "**자동 solo default 금지** — 먼저 사용자에게 solo/team 을 문의하고, 답을 README.md 에 "
        "`git 협업 모드: <solo|team>` 으로 기록한 뒤 그 모드로 작업하세요. "
        "(GitHub collaborator·CODEOWNERS·branch protection 자동 감지를 제안 근거로 활용 가능.)"
    )


def session_section(cwd, session_id):
    """track 훅이 기록한 '이 세션 수정 파일' 목록을 staging 한정 안내로 변환."""
    gd = _git(cwd, "rev-parse", "--absolute-git-dir")
    if not gd or not session_id:
        return ""
    touched = os.path.join(gd, "git_workflow", "sessions", session_id, "touched")
    if not os.path.isfile(touched):
        return (
            "\n\n[세션 격리 — 추적 없음]\n"
            "이 세션의 파일 추적 기록이 없습니다(추적 훅 미설치 또는 편집 0건). "
            "`git status` 로 이번 세션이 직접 만든 변경만 식별해 staging 하세요 — "
            "그 외 변경은 다른 세션 것일 수 있으니 건드리지 마세요."
        )
    try:
        with open(touched, encoding="utf-8") as f:
            files = [ln.strip() for ln in f if ln.strip()]
    except OSError:
        return ""
    if not files:
        return ""
    top = _git(cwd, "rev-parse", "--show-toplevel") or ""
    rel = [
        os.path.relpath(p, top) if top and p.startswith(top) else p
        for p in files
    ]
    listing = "\n".join("  - " + r for r in rel)
    return (
        "\n\n[세션 격리 — 이 세션 수정 파일만 staging]\n"
        "이 세션({sid})이 수정/생성한 파일은 다음뿐입니다:\n{listing}\n"
        "→ `git add` 는 위 목록으로 한정. `git status` 에 그 외 변경이 보이면 **다른 세션** 것일 수 있으니 "
        "건드리지 마세요(세션 격리). commit 직전 `git diff --cached --name-only` 가 위 목록의 부분집합인지 검증."
    ).format(sid=session_id[:8], listing=listing)


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        data = {}

    prompt = str(data.get("prompt", ""))
    if not prompt:
        return
    if not any(t in prompt.lower() for t in TRIGGERS):
        return

    cwd = data.get("cwd") or os.getcwd()
    if cwd and not os.path.isfile(os.path.join(cwd, *RULE_MD.split("/"))):
        return

    print(DIRECTIVE + mode_section(cwd) + session_section(cwd, data.get("session_id", "")))


if __name__ == "__main__":
    main()
