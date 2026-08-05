#!/usr/bin/env python3
"""PreToolUse(Bash) 훅 — 공유 워킹트리에서 **트리 전역 파괴 명령** 차단.

stage-gate 는 `git add` 의 소유권만, commit-gate 는 커밋 시점만, push-gate 는 push
시점만 본다. 그 사이에 뚫려 있던 것이 **작업트리를 통째로 되돌리는 명령**이다:
`git stash`(경로 미지정)·`reset --hard`·`checkout -- .`·`clean -fd` 는 타 세션이
공유 트리에 만들어 둔 미커밋·staged 작업까지 함께 걷어간다.

실제 사고(2026-08-05): 발산 정리 중 실행한 `git stash push` + `reset --hard` 가
다른 세션이 staged 해 둔 번들 14파일(~1,900줄)을 함께 걷어갔다. 백업이 있어
복구했지만, 그 세션은 자기 index 가 통째로 비워진 채 작업을 이어가고 있었다.

판정: (1) 명령이 트리 전역 파괴 계열이고 (2) 현재 dirty 파일 중 **이 세션 소유가
      아닌 것**이 있으면 DENY. 소유 판정은 track.py 의 touched 기록.
      내 파일만 dirty 면 통과 — 혼자 쓰는 트리를 막지 않는다.

override: 명령에 `gw:allow-tree-wide` 주석 또는 env GW_ALLOW_TREE_WIDE=1.
self-contained. 계약: stdin JSON → 차단 시 permissionDecision=deny(JSON, exit 0),
                    통과 시 무출력 exit 0.
한계(정직): 셸 파싱 휴리스틱(eval·xargs·alias 우회 가능), 훅 미설치 세션은 미보호,
          Bash 로만 만든 변경은 touched 에 없어 false-deny 가능(override 로 해소),
          `git switch`/`checkout <브랜치>` 의 공유 HEAD 전역 이동은 본 훅 대상 외.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gw_common as gw  # noqa: E402

# 트리 전역 파괴 계열로 감시할 하위명령
WATCHED = ("stash", "reset", "checkout", "restore", "clean")


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))
    sys.exit(0)


def _seg_tokens(command):
    """세그먼트별 (하위명령, 그 뒤 인자들). git 호출이 아닌 세그먼트는 제외."""
    out = []
    for seg in gw.SEG_SEP.split(command):
        toks = gw._tokens(seg)
        i, n = 0, len(toks)
        while i < n and (gw.ENV_ASSIGN_RE.match(toks[i]) or toks[i] in gw.TRANSPARENT_WRAPPERS):
            i += 1
        if i >= n or os.path.basename(toks[i]) != "git":
            continue
        i += 1
        while i < n and toks[i].startswith("-"):
            if toks[i] in gw.GIT_OPTS_WITH_VALUE:
                i += 2
                continue
            i += 1
        if i < n:
            out.append((toks[i], toks[i + 1:]))
    return out


# 하위명령별로 **다음 토큰을 값으로 먹는** 옵션 — 그 값을 경로로 오인하면 안 된다
# (예: `git stash push -m x` 의 x 는 메시지이지 경로가 아니다).
OPTS_WITH_VALUE = {
    "stash": {"-m", "--message"},
    "checkout": {"-b", "-B", "--orphan", "--conflict", "--pathspec-from-file"},
    "restore": {"-s", "--source", "--conflict", "--pathspec-from-file"},
    "clean": {"-e", "--exclude"},
}


def _has_pathspec(args, opts_with_value=()):
    """인자에 경로 제한이 있으면 True (`--` 뒤 경로, 또는 비-옵션 경로 인자)."""
    if "--" in args:
        return len(args[args.index("--") + 1:]) > 0
    skip = False
    for a in args:
        if skip:
            skip = False
            continue
        if a in opts_with_value:
            skip = True
            continue
        if a.startswith("-"):
            continue
        if a in (".", "./"):
            return False   # `.` 은 트리 전체 — 경로 제한으로 치지 않는다
        return True        # 그 밖의 비-옵션 인자 = 경로/리비전 지정
    return False


def tree_wide_reason(subcmd, args):
    """이 호출이 '트리 전역 파괴'면 사람이 읽을 사유, 아니면 None."""
    if subcmd == "stash":
        # `git stash list/show` 등 조회형은 무해
        sub = next((a for a in args if not a.startswith("-")), None)
        if sub in ("list", "show", "drop", "clear", "branch"):
            return None
        if sub in (None, "push", "save", "-u", "--include-untracked"):
            rest = [a for a in args if a not in ("push", "save")]
            if not _has_pathspec(rest, OPTS_WITH_VALUE["stash"]):
                return "`git stash`(경로 미지정) — 작업트리의 모든 변경을 걷어갑니다"
        return None
    if subcmd == "reset":
        if "--hard" in args:
            return "`git reset --hard` — 작업트리의 모든 미커밋 변경을 파기합니다"
        return None
    if subcmd in ("checkout", "restore"):
        if any(a in (".", "./") for a in args):
            return "`git %s .` — 작업트리 전체를 되돌립니다" % subcmd
        return None
    if subcmd == "clean":
        if any(a.startswith("-") and "f" in a.lstrip("-") for a in args):
            return "`git clean -f…` — 미추적 파일을 삭제합니다"
        return None
    return None


def _touched(gd, sid):
    p = os.path.join(gd, "git_workflow", "sessions", sid, "touched")
    try:
        with open(p, encoding="utf-8") as f:
            return {ln.strip() for ln in f if ln.strip()}
    except OSError:
        return set()


def foreign_dirty(repo, gd, sid):
    """dirty 파일 중 이 세션 소유가 아닌 것들(상대경로 목록)."""
    st = gw.run_git(repo, "status", "--porcelain")
    if not st:
        return []
    mine = _touched(gd, sid)
    out = []
    for ln in st.split("\n"):
        if len(ln) < 4:
            continue
        path = ln[3:].strip().strip('"')
        if " -> " in path:            # rename: 신규 경로 기준
            path = path.split(" -> ", 1)[1]
        if os.path.abspath(os.path.join(repo, path)) not in mine:
            out.append(path)
    return out


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        return
    if data.get("tool_name") != "Bash":
        return
    cmd = str((data.get("tool_input") or {}).get("command", ""))
    if not gw.runs_git(cmd, *WATCHED):
        return
    if "gw:allow-tree-wide" in cmd or \
            os.environ.get("GW_ALLOW_TREE_WIDE", "").lower() in ("1", "true", "yes"):
        return  # override

    cwd = data.get("cwd") or os.getcwd()
    repo = gw.resolve_repo(cmd, cwd)
    if not gw.rule_active(repo):
        return  # 번들 미설치 저장소 → 간섭 안 함
    gd = gw.git_dir(repo)
    if not gd:
        return

    reason = None
    for subcmd, args in _seg_tokens(cmd):
        reason = tree_wide_reason(subcmd, args)
        if reason:
            break
    if not reason:
        return

    sid = data.get("session_id") or "unknown"
    foreign = foreign_dirty(repo, gd, sid)
    if not foreign:
        return  # 내 변경만 dirty → 혼자 쓰는 트리, 막지 않는다

    shown = "\n".join("  - " + p for p in foreign[:10])
    more = "\n  … 외 %d개" % (len(foreign) - 10) if len(foreign) > 10 else ""
    deny(
        "%s\n"
        "이 워킹트리에 **다른 세션의 미커밋 변경**이 있어 함께 사라집니다:\n"
        "%s%s\n"
        "→ 경로를 한정하세요(예: `git stash push -- <내 파일>`, `git checkout -- <내 파일>`).\n"
        "→ 꼭 전역으로 해야 하면 백업 후 명령에 `# gw:allow-tree-wide` 를 붙이세요."
        % (reason, shown, more)
    )


if __name__ == "__main__":
    main()
