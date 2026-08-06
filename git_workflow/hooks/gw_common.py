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
# 백슬래시 줄 이음(`\` + 개행) — 세그먼트 분할 **전에** 한 줄로 이어야 한다.
# 먼저 `\n` 으로 쪼개면 `git add a \` / `b \` / `c` 가 세 명령으로 보여, 정당한
# 여러 줄 명령이 "파싱 불가"로 차단된다(실측: 5개 경로를 줄 이음으로 나열한 git add).
LINE_CONT_RE = re.compile(r"\\[ \t]*\r?\n")
CD_RE = re.compile(r"^\s*cd\s+(\"[^\"]*\"|'[^']*'|[^\s;&|]+)\s*$")

# git 전역 옵션 중 **다음 토큰을 값으로 먹는** 것들(하위명령 탐색 시 건너뛰기).
# `--opt=value` 형태는 토큰 하나라 별도 처리 불필요.
GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace",
                       "--config-env", "--super-prefix"}
# 명령 위치 판정: 선행 `VAR=값` 대입과, 뒤 명령을 그대로 실행하는 무인자 래퍼만 투명 취급.
# 인자를 받는 래퍼(`timeout 5 …`)는 일부러 제외 — 잘못 건너뛰면 엉뚱한 토큰을 명령으로 오인한다.
ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
TRANSPARENT_WRAPPERS = {"sudo", "env", "nohup", "command", "exec", "time"}


def run_git(repo, *args, timeout=3):
    try:
        r = subprocess.run(["git", "-C", repo, *args],
                           capture_output=True, text=True, timeout=timeout)
        return r.stdout.rstrip("\n") if r.returncode == 0 else None  # 경로 후행 공백 보존
    except (OSError, subprocess.SubprocessError):
        return None


def join_line_continuations(command):
    """`\\` + 개행을 공백으로 이어 한 줄로 만든다(세그먼트 분할 전 정규화)."""
    return LINE_CONT_RE.sub(" ", command or "")


def segments(command):
    """명령을 셸 세그먼트로 분할 — 줄 이음을 먼저 정규화한다."""
    return SEG_SEP.split(join_line_continuations(command))


def _tokens(command):
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def git_subcommands(command):
    """명령에서 **실제로 호출된 git 하위명령** 목록 반환 (예: ["commit", "push"]).

    부분문자열 매칭(`"commit" in cmd`)의 오탐을 없애기 위한 공용 판정기. 그 방식은
    `.git/…/commits` 파일을 *읽기*만 하는 명령이나 "add" 를 포함한 단어(`address`·
    `readd`)에도 발동해, 훅이 엉뚱한 명령을 커밋/푸시로 오인한다(소유권 기록 오염).

    세그먼트(`&&`·`;`·`|`…)별로 토큰화 → `git` 토큰 탐색 → 전역 옵션(값 있는 것은
    2토큰) 건너뛰기 → 첫 비-옵션 토큰을 하위명령으로 취한다.

    `git` 는 **명령 위치에 있을 때만** git 호출로 본다(선행 `VAR=값` 대입과 소수의
    래퍼는 건너뜀). 인자로 등장하는 `git`(예: `echo git commit`, `grep git file`)은
    호출이 아니므로 무시 — 위치를 안 보면 이것들이 전부 오탐이 된다.

    한계(정직): 셸 파싱 휴리스틱이라 `eval`·`xargs`·git alias·따옴표 안의 명령은
              해석하지 못하고, 인자를 받는 래퍼(`timeout 5 git push`)도 놓친다.
              오탐은 없애고 미탐은 남긴다 — 게이트가 조용히 통과시키는 편이
              엉뚱한 차단·오기록보다 안전하다(전자는 사용자가 알아채고 재시도하지만,
              후자는 소유권 기록을 오염시켜 게이트 판정 자체를 무너뜨린다).
    """
    return [sub for sub, _ in git_calls(command)]


def git_calls(command):
    """명령의 git 호출을 `(하위명령, 그 뒤 인자들)` 목록으로 반환.

    `git_subcommands` 의 하부 구현 — 게이트가 하위명령뿐 아니라 **인자(스코프)** 까지
    봐야 할 때 쓴다(예: `git commit -- <경로>` 인지 맨몸 `git commit` 인지).
    """
    found = []
    for seg in segments(command):
        toks = _tokens(seg)
        i, n = 0, len(toks)
        # 명령 위치까지 전진: 선행 환경변수 대입(VAR=값)·투명 래퍼만 건너뛴다.
        while i < n and (ENV_ASSIGN_RE.match(toks[i]) or toks[i] in TRANSPARENT_WRAPPERS):
            i += 1
        if i >= n or os.path.basename(toks[i]) != "git":
            continue  # 명령 위치가 git 이 아님 → 이 세그먼트는 git 호출 아님
        i += 1
        while i < n and toks[i].startswith("-"):
            if toks[i] in GIT_OPTS_WITH_VALUE:
                i += 2
                continue
            i += 1
        if i < n:
            found.append((toks[i], toks[i + 1:]))
    return found


def other_session_touched(gd, sid):
    """**다른 세션이 소유를 주장한** 파일들의 절대경로 집합.

    "내 것이 아니다"(미상 포함)가 아니라 "남의 것이라고 증명된다"만 담는다. 게이트는
    실증된 피해에만 발동해야 하며, 아무 세션도 주장하지 않는 파일(예: Bash 로만 만들어
    추적되지 않은 산출물)을 남의 것으로 단정해 정당한 작업을 막으면 안 된다.
    """
    root = os.path.join(gd, "git_workflow", "sessions")
    owned = set()
    try:
        entries = os.listdir(root)
    except OSError:
        return owned
    for other in entries:
        if other == sid:
            continue
        try:
            with open(os.path.join(root, other, "touched"), encoding="utf-8") as f:
                owned |= {ln.strip() for ln in f if ln.strip()}
        except OSError:
            continue
    return owned


def runs_git(command, *subcommands):
    """명령이 주어진 git 하위명령 중 하나라도 실제로 호출하는가."""
    if not command:
        return False
    got = git_subcommands(command)
    return any(s in got for s in subcommands)


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
    for seg in segments(command):
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
