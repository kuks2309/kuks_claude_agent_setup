#!/usr/bin/env python3
"""PreToolUse(Bash) 훅 — git staging 게이트.

한 세션이 '자기 소유가 아닌 파일'을 staging 하는 것(타 세션 미커밋 파일 캡처)을 차단한다.
공유 working tree·다중 탭(한 창)이라 worktree 격리가 불가능할 때의 캡처 방지책.

소유 판정: git_workflow-track.py 가 기록한 .git/git_workflow/sessions/<session_id>/touched.
차단(하드 DENY):
  (1) 광역 staging — git add 의 -A/./-u/-p/-i 등, git commit -a/--all
  (2) 명시 경로 중 이 세션 소유가 아닌 것, glob/광역 pathspec
override: 명령에 `gw:allow-foreign` 주석 또는 env GW_ALLOW_FOREIGN=1.

self-contained: Claude Code 네이티브 session_id + .git 내부 목록. OMC 비의존.
계약: stdin JSON → 차단 시 permissionDecision=deny(JSON, exit 0), 통과 시 무출력 exit 0.
한계(정직): 셸 파싱 휴리스틱(eval·xargs·alias 우회 가능), 훅 미설치 세션 우회,
          `cd <경로>` 는 반영하나 변수·명령치환(`cd $D`)은 해석 불가 → 세션 cwd 기준 유지(보수적),
          Bash 로만 만든 변경은 미추적→false-deny(override 로 해소), `git commit <path>` 미검사.
"""
import json
import os
import re
import shlex
import subprocess
import sys

RULE_MD = "docs/claude_guideline/git_workflow/git_workflow.md"
SEG_SEP = re.compile(r"&&|\|\||;|\n|\|")
BROAD_FLAGS = {"-A", "--all", "-u", "--update", "-p", "--patch",
               "-i", "--interactive", "--no-ignore-removal"}
BROAD_PATHS = {".", ":/", ":", "*"}
GLOB = re.compile(r"[*?\[]")
CD_RE = re.compile(r"^\s*cd\s+(?P<path>\"[^\"]*\"|'[^']*'|[^\s;&|]+)\s*$")


def effective_cwd(cmd, base):
    """명령 안의 선행 `cd <경로>` 를 반영한 판정 기준 디렉토리.

    `cd <다른저장소> && git …` 처럼 대상 저장소가 세션 cwd 와 다를 때 그 저장소를
    기준으로 판정하기 위함(오탐 방지). 해석 불가(변수·명령치환·`cd -`)면 base 유지.
    """
    cur = base
    for seg in SEG_SEP.split(cmd):
        m = CD_RE.match(seg.strip())
        if not m:
            continue
        p = m.group("path")
        if p[:1] in ("\"", "'"):
            p = p[1:-1]
        if "$" in p or "`" in p or p == "-":
            return base  # 해석 불가 → 보수적으로 원래 기준 유지
        cand = os.path.normpath(p if os.path.isabs(p) else os.path.join(cur, p))
        if os.path.isdir(cand):
            cur = cand
    return cur


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))
    sys.exit(0)


def git_dir(cwd):
    try:
        out = subprocess.run(["git", "-C", cwd, "rev-parse", "--absolute-git-dir"],
                             capture_output=True, text=True, timeout=3)
        if out.returncode == 0:
            return out.stdout.rstrip("\n")  # 경로 후행 공백 보존(.strip 금지)
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def touched_set(gd, sid):
    p = os.path.join(gd, "git_workflow", "sessions", sid, "touched")
    try:
        with open(p, encoding="utf-8") as f:
            return {ln.strip() for ln in f if ln.strip()}
    except OSError:
        return set()


def parse_git(tokens):
    """tokens → (subcmd, args, cdir) for first git invocation, else None."""
    i, n = 0, len(tokens)
    while i < n and tokens[i] != "git":
        i += 1
    if i >= n:
        return None
    i += 1
    cdir = None
    while i < n and tokens[i].startswith("-"):
        if tokens[i] == "-C" and i + 1 < n:
            cdir = tokens[i + 1]
            i += 2
            continue
        i += 1
    if i >= n:
        return None
    return tokens[i], tokens[i + 1:], cdir


def commit_is_broad(args):
    for a in args:
        if a == "--all":
            return True
        if a.startswith("-") and not a.startswith("--") and "a" in a:
            return True  # -a, -am, -ma …
    return False


def check_add(args, base, touched):
    paths = []
    for a in args:
        if a in BROAD_FLAGS:
            return "광역 staging 플래그(%s) — 이 세션 외 파일까지 쓸어 담을 수 있어 금지." % a
        if a == "--":
            continue
        if a.startswith("-"):
            continue  # -v/-n/-f 등 무해 플래그
        if a in BROAD_PATHS or GLOB.search(a):
            return "광역/glob 경로(%s) — 개별 파일을 검증할 수 없어 금지." % a
        paths.append(a)
    if not paths:
        return None  # `git add` (경로 없음) → 무해
    foreign = [p for p in paths
               if os.path.abspath(os.path.join(base, p)) not in touched]
    if foreign:
        return ("이 세션 소유가 아닌 파일 staging 시도: %s. 이 세션이 만든 파일만 명시 staging 하세요."
                % ", ".join(foreign))
    return None


def hint(touched, cwd):
    if not touched:
        return " (이 세션 추적 파일 없음 — Bash 로 만든 파일이면 `# gw:allow-foreign` 로 허용.)"
    rels = [os.path.relpath(p, cwd) if p.startswith(cwd) else p for p in sorted(touched)]
    return " 이 세션 소유: " + ", ".join(rels[:20]) + (" …" if len(rels) > 20 else "")


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        return
    if data.get("tool_name") != "Bash":
        return
    cmd = str((data.get("tool_input") or {}).get("command", ""))
    if not cmd or "git" not in cmd:
        return
    if "add" not in cmd and "commit" not in cmd:
        return

    cwd = effective_cwd(cmd, data.get("cwd") or os.getcwd())
    # 활성화 판정은 저장소 최상위 기준 — 하위 디렉토리로 cd 해도 게이트가 꺼지지 않게.
    gr = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                        capture_output=True, text=True)
    root = gr.stdout.rstrip("\n") if gr.returncode == 0 else cwd
    if not os.path.isfile(os.path.join(root, *RULE_MD.split("/"))):
        return  # 번들 미설치 저장소 → 간섭 안 함
    if "gw:allow-foreign" in cmd or \
            os.environ.get("GW_ALLOW_FOREIGN", "").lower() in ("1", "true", "yes"):
        return  # override

    gd = git_dir(cwd)
    if not gd:
        return
    touched = touched_set(gd, data.get("session_id") or "unknown")

    for seg in SEG_SEP.split(cmd):
        seg = seg.strip()
        if not seg or "git" not in seg:
            continue
        try:
            tokens = shlex.split(seg)
        except ValueError:
            if re.search(r"git\s+(-C\s+\S+\s+)?(add|commit)\b", seg):
                deny("git staging 명령을 안전하게 파싱할 수 없습니다(셸 인용 복잡). "
                     "명시 경로로 단순화하거나 `# gw:allow-foreign` 를 쓰세요.")
            continue
        parsed = parse_git(tokens)
        if not parsed:
            continue
        sub, args, cdir = parsed
        if sub == "add":
            reason = check_add(args, cdir or cwd, touched)
            if reason:
                deny(reason + hint(touched, cwd))
        elif sub == "commit" and commit_is_broad(args):
            deny("git commit -a/--all 은 index 를 우회해 이 세션 외 변경까지 커밋할 수 있어 금지. "
                 "git add <이 세션 파일> 후 git commit 하세요." + hint(touched, cwd))


if __name__ == "__main__":
    main()
