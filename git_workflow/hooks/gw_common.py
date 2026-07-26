#!/usr/bin/env python3
"""git_workflow 훅 공유 헬퍼 — 명령에서 '대상 git 저장소'를 해석.

워크스페이스(비-git) 루트에서 열린 세션이 `cd <subdir> && git …` 또는 `git -C <subdir> …`
로 하위 저장소를 다룰 때, 훅이 그 하위 저장소를 찾아 거기서 동작(기록·게이트)하게 한다.
이로써 훅을 워크스페이스에 설치해도 하위 저장소 작업이 세션별로 격리·기록된다.

self-contained: 표준 라이브러리만.
"""
import os
import re
import shlex
import subprocess

RULE_REL = "docs/claude_guideline/git_workflow/git_workflow.md"
SEG_SEP = re.compile(r"&&|\|\||;|\n|\|")
CD_RE = re.compile(r"^\s*cd\s+(\"[^\"]*\"|'[^']*'|[^\s;&|]+)\s*$")


def run_git(repo, *args, timeout=3):
    try:
        r = subprocess.run(["git", "-C", repo, *args],
                           capture_output=True, text=True, timeout=timeout)
        return r.stdout.rstrip("\n") if r.returncode == 0 else None  # 경로 후행 공백 보존
    except (OSError, subprocess.SubprocessError):
        return None


def _tokens(command):
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def target_dir(command, cwd):
    """명령이 향하는 작업 디렉터리(절대경로) 추정.

    두 버전 병합: (1) `git -C <dir>` 명시경로 우선, (2) 없으면 선행 `cd <dir>` 를
    **다단계 순차** 반영(quote 처리·isdir 검증). 변수·명령치환·`cd -` 은
    해석 불가라 **보수적으로 원래 cwd 유지**(엉뚱한 저장소로 오판 방지).
    """
    # (1) git -C <dir> — 첫 git 호출의 명시 경로
    toks = _tokens(command)
    for i, t in enumerate(toks):
        if os.path.basename(t) == "git":
            j = i + 1
            while j < len(toks) and toks[j].startswith("-"):
                if toks[j] in ("-C", "--git-dir", "--work-tree") and j + 1 < len(toks):
                    d = toks[j + 1]
                    return d if os.path.isabs(d) else os.path.normpath(os.path.join(cwd, d))
                j += 1
            break
    # (2) cd <dir> 다단계 (변수치환 방어·isdir 검증)
    cur = cwd
    for seg in SEG_SEP.split(command):
        m = CD_RE.match(seg.strip())
        if not m:
            continue
        p = m.group(1)
        if p[:1] in ("\"", "'"):
            p = p[1:-1]
        if "$" in p or "`" in p or p == "-":
            return cwd  # 해석 불가 → 보수적 원래 cwd
        cand = os.path.normpath(p if os.path.isabs(p) else os.path.join(cur, p))
        if os.path.isdir(cand):
            cur = cand
    return cur


def resolve_repo(command, cwd):
    """명령의 대상 git 저장소 toplevel(절대경로) 반환. 못 찾으면 None."""
    d = target_dir(command, cwd)
    return run_git(d, "rev-parse", "--show-toplevel")


def rule_active(repo):
    """해석된 저장소에 git_workflow 번들이 설치돼 있나(게이트 활성 조건)."""
    return bool(repo) and os.path.isfile(os.path.join(repo, *RULE_REL.split("/")))


def git_dir(repo):
    return run_git(repo, "rev-parse", "--absolute-git-dir")
