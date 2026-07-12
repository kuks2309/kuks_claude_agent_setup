#!/usr/bin/env python3
"""PreToolUse(Bash) 훅 — 보호 브랜치(main/master) 직접 push 게이트.

공유 워킹트리·다중 세션(한 창 다중 탭)에서 `git push … main` 이 '이 세션 것이 아닌
커밋'(타 탭의 미푸시 로컬 커밋)까지 함께 밀어버리는 것을 하드 차단한다.
판정: <remote>/<branch>..HEAD 의 커밋이 전부 git_workflow-commit-track.py 가 기록한
이 세션 커밋이면 통과, 하나라도 아니면 DENY(§2-1 세션 브랜치로 유도).

override: 명령에 `gw:allow-main-push` 주석 또는 env GW_ALLOW_MAIN_PUSH=1.
self-contained. 계약: stdin JSON → 차단 시 permissionDecision=deny(JSON, exit 0), 통과 시 무출력 exit 0.
한계(정직): 셸 파싱 휴리스틱(eval·alias·xargs 우회 가능); 원격추적 ref 미존재(첫 push)면
          판정 불가 → 통과; 로컬 ref 기준이라 stale 하면 false-deny 가능(그 경우 fetch+rebase 가 정답).
"""
import json
import os
import re
import shlex
import subprocess
import sys

RULE_MD = "docs/claude_guideline/git_workflow/git_workflow.md"
SEG_SEP = re.compile(r"&&|\|\||;|\n|\|")
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
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def parse_push(tokens):
    """tokens → (remote, branch) for a git push. branch = dest ref(src:dst→dst). 아니면 None."""
    i, n = 0, len(tokens)
    while i < n and os.path.basename(tokens[i]) != "git":
        i += 1
    if i >= n:
        return None
    i += 1
    while i < n and tokens[i].startswith("-"):
        if tokens[i] in ("-C", "-c", "--git-dir", "--work-tree") and i + 1 < n:
            i += 2
            continue
        i += 1
    if i >= n or tokens[i] != "push":
        return None
    pos = [t for t in tokens[i + 1:] if not t.startswith("-")]
    remote = pos[0] if len(pos) >= 1 else None
    branch = pos[1].split(":")[-1] if len(pos) >= 2 else None
    return remote, branch


def _resolve(cwd, remote, branch):
    if branch is None:
        branch = _git(cwd, "rev-parse", "--abbrev-ref", "HEAD")
    if remote is None:
        up = _git(cwd, "rev-parse", "--abbrev-ref", "@{upstream}")
        if up and "/" in up:
            remote = up.split("/", 1)[0]
    return remote, branch


def _session_commits(gd, sid):
    p = os.path.join(gd, "git_workflow", "sessions", sid, "commits")
    try:
        with open(p, encoding="utf-8") as f:
            return {ln.strip() for ln in f if ln.strip()}
    except OSError:
        return set()


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        return
    if data.get("tool_name") != "Bash":
        return
    cmd = str((data.get("tool_input") or {}).get("command", ""))
    if "git" not in cmd or "push" not in cmd:
        return

    cwd = data.get("cwd") or os.getcwd()
    if not os.path.isfile(os.path.join(cwd, *RULE_MD.split("/"))):
        return  # 번들 미설치 → 간섭 안 함
    if "gw:allow-main-push" in cmd or \
            os.environ.get("GW_ALLOW_MAIN_PUSH", "").lower() in ("1", "true", "yes"):
        return  # override

    gd = _git(cwd, "rev-parse", "--absolute-git-dir")
    if not gd:
        return
    sid = data.get("session_id") or "unknown"
    owned = _session_commits(gd, sid)

    for seg in SEG_SEP.split(cmd):
        seg = seg.strip()
        if "git" not in seg or "push" not in seg:
            continue
        try:
            tokens = shlex.split(seg)
        except ValueError:
            tokens = seg.split()
        parsed = parse_push(tokens)
        if not parsed:
            continue
        remote, branch = _resolve(cwd, parsed[0], parsed[1])
        if not branch or branch not in PROTECTED:
            continue  # 비-보호 브랜치(session/…) → 통과
        track = "refs/remotes/%s/%s" % (remote, branch) if remote else None
        if not track or _git(cwd, "rev-parse", "--verify", "-q", track) is None:
            continue  # 원격추적 ref 없음(첫 push) → 판정 불가, 통과
        rng = _git(cwd, "rev-list", "%s..HEAD" % track)
        commits = [c for c in (rng or "").split() if c]
        foreign = [c for c in commits if c not in owned]
        if foreign:
            subj = []
            for c in foreign[:8]:
                subj.append("  - " + (_git(cwd, "log", "-1", "--format=%h %s", c) or c[:7]))
            more = "\n  … 외 %d개" % (len(foreign) - 8) if len(foreign) > 8 else ""
            deny(
                "이 세션 것이 아닌 커밋이 %s/%s push 에 섞여 있습니다(공유 워킹트리 다중 세션):\n"
                "%s%s\n"
                "→ 이 세션 산출물만 올리려면 git_workflow §2-1 세션 브랜치를 쓰세요: 임시 worktree 에서 "
                "`session/%s` 로 cherry-pick 후 그 브랜치를 push(main 직접 push 금지, merge 는 사용자). "
                "의도적 통합 push 면 명령에 `# gw:allow-main-push` 를 붙이세요."
                % (remote, branch, "\n".join(subj), more, sid[:8])
            )


if __name__ == "__main__":
    main()
