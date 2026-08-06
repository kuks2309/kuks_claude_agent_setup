#!/usr/bin/env python3
"""PreToolUse(Bash) 훅 — 커밋이 **타 세션 산출물을 함께 담는 것**을 차단.

커밋은 파괴적이지 않다. 작업트리를 건드리지 않고 현재 상태를 박제할 뿐이라, 다른
세션이 살아있다는 사실 자체는 커밋을 막을 이유가 못 된다. 실제 피해는 커밋의
**스코프가 열려 있을 때** 생긴다 — 맨몸 `git commit` 은 공유 index 를 통째로 담으므로
다른 세션이 `git add` 해 둔 파일이 내 커밋 메시지 아래 실려 `main` 에 올라간다.

그래서 판정 질문을 "누가 살아있나"에서 **"이 커밋이 무엇을 담나"** 로 바꾼다.

  git commit -- <경로>              → 경로가 남의 것이 아니면 통과 (타 세션 수 무관)
  git commit (맨몸)                  → index 에 **남의 staged 파일**이 있을 때만 deny
  git commit -a                      → 위 + 남의 dirty 추적 파일이 있을 때만 deny
  git commit --amend                 → HEAD 가 이 세션 커밋이 아니면 deny (남의 이력 재작성)
  그 외                              → 통과

이전 판정("타 세션 활동 중 + 보호 브랜치 → 무조건 deny")은 정당한 경로 한정 커밋마다
발동했다. 정당한 동작마다 뜨는 게이트는 override 를 반사적으로 붙이게 만들고, 그러면
정작 위험한 맨몸 커밋에도 같이 붙어 게이트가 무력화된다(실측: 한 세션이 경로 한정
커밋 5회를 전부 override 로 통과시켰고 피해는 0이었다).

소유 판정은 **남의 것이라고 증명된 파일**(다른 세션의 track.py touched)만 본다 —
아무도 주장하지 않는 파일을 남의 것으로 단정해 정당한 작업을 막지 않는다.

override: 명령에 `gw:allow-main-commit` 주석 또는 env GW_ALLOW_MAIN_COMMIT=1.
self-contained. 계약: stdin JSON → 차단 시 permissionDecision=deny(JSON, exit 0), 통과 시 무출력 exit 0.
한계(정직): 셸 파싱 휴리스틱(eval·alias·xargs 우회 가능), 훅 미설치 세션은 미보호,
          `cd <경로>` 는 반영하나 변수·명령치환(`cd $D`)은 해석 불가 → 세션 cwd 기준 유지,
          **Bash 로만 만든 남의 파일은 touched 에 없어 미검출**(소유 미상 → 통과),
          rebase/merge 중 커밋·detached HEAD 는 대상 외.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gw_common as gw  # noqa: E402

RULE_MD = "docs/claude_guideline/git_workflow/git_workflow.md"

# `git commit` 의 옵션 중 **다음 토큰을 값으로 먹는** 것 — 그 값을 경로로 오인하면 안 된다
# (`git commit -m x` 의 x 는 메시지이지 경로가 아니다). `--opt=value` 형태는 토큰 하나라
# 별도 처리 불요. 값이 선택적인 `-S`/`--gpg-sign` 은 붙여 쓰는 형태뿐이라 제외 —
# 포함하면 뒤따르는 경로를 먹어 스코프를 잘못 넓힌다.
COMMIT_OPTS_WITH_VALUE = {
    "-m", "--message", "-F", "--file", "--author", "--date",
    "-c", "--reedit-message", "-C", "--reuse-message",
    "--fixup", "--squash", "--cleanup", "--trailer", "--pathspec-from-file",
}
ALL_FLAGS = {"-a", "--all"}
# 묶음 단축 플래그(`-am`) 해석용 — 값을 받는 글자와, 스코프를 전체로 넓히는 글자.
SHORT_OPTS_WITH_VALUE = set("mFcC")
SHORT_ALL_LETTERS = set("a")


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


def commit_args(cmd):
    """첫 `git commit` 호출의 인자 목록(없으면 None)."""
    for sub, args in gw.git_calls(cmd):
        if sub == "commit":
            return args
    return None


def commit_scope(args):
    """(kind, paths, amend) — kind 는 'paths' | 'all' | 'index'.

    'paths' 는 그 경로만 담는 부분 커밋(공유 index 의 나머지는 건드리지 않는다).
    파싱이 모호하면 보수적으로 'index'(맨몸)로 본다 — 그래도 판정은 '남의 staged 가
    있는가' 이므로 없으면 통과한다.
    """
    amend = "--amend" in args
    if "--" in args:
        paths = [a for a in args[args.index("--") + 1:] if a]
        return ("paths" if paths else "index"), paths, amend

    paths, skip, all_flag = [], False, False
    for a in args:
        if skip:
            skip = False
            continue
        if a in COMMIT_OPTS_WITH_VALUE:
            skip = True
            continue
        if a in ALL_FLAGS:
            all_flag = True
            continue
        if a.startswith("--") or a == "-":
            continue
        if a.startswith("-"):
            # 묶음 단축 플래그(`-am`) — 문자 단위로 읽는다. 값을 받는 글자를 만나면
            # 그 뒤는 값이므로(붙어 있거나 다음 토큰) 거기서 중단한다. 통째로 보면
            # `-mabc` 의 'a' 를 `--all` 로 오인해 스코프를 잘못 넓힌다.
            letters = a[1:]
            for idx, ch in enumerate(letters):
                if ch in SHORT_OPTS_WITH_VALUE:
                    if idx == len(letters) - 1:
                        skip = True   # 값은 다음 토큰
                    break
                if ch in SHORT_ALL_LETTERS:
                    all_flag = True
            continue
        paths.append(a)

    if all_flag:
        return "all", paths, amend
    if paths:
        return "paths", paths, amend
    return "index", paths, amend


def staged(root):
    return [p for p in (_git(root, "diff", "--cached", "--name-only") or "").split("\n") if p]


def dirty_tracked(root):
    return [p for p in (_git(root, "diff", "--name-only") or "").split("\n") if p]


def foreign(root, rels, owned_by_others):
    """상대경로 목록 중 **다른 세션이 소유를 주장한** 것만."""
    return [p for p in rels
            if os.path.abspath(os.path.join(root, p)) in owned_by_others]


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

    gd = _git(cwd, "rev-parse", "--absolute-git-dir")
    if not gd:
        return
    sid = data.get("session_id") or "unknown"
    owned = gw.other_session_touched(gd, sid)
    if not owned:
        return  # 남의 소유 주장 자체가 없음 → 담길 남의 것도 없다

    args = commit_args(cmd)
    if args is None:
        return
    kind, paths, amend = commit_scope(args)

    if amend:
        head = _git(root, "rev-parse", "HEAD")
        mine = set()
        try:
            with open(os.path.join(gd, "git_workflow", "sessions", sid, "commits"),
                      encoding="utf-8") as f:
                mine = {ln.strip() for ln in f if ln.strip()}
        except OSError:
            pass
        if head and mine and head not in mine:
            deny(
                "`--amend` 대상(HEAD %s)이 이 세션 커밋이 아닙니다 — 남의 커밋을 재작성하면\n"
                "그 세션의 이력이 사라지고 이미 push 된 경우 발산합니다.\n"
                "→ 새 커밋으로 만드세요. 의도적이면 명령에 `# gw:allow-main-commit`."
                % (head[:7],)
            )

    if kind == "paths":
        bad = foreign(root, paths, owned)
        hint = "커밋 경로에서 위 파일을 빼세요"
    elif kind == "all":
        bad = foreign(root, staged(root) + dirty_tracked(root), owned)
        hint = "`-a` 대신 `git commit -- <내 파일>` 로 좁히세요"
    else:  # index — 맨몸 커밋
        bad = foreign(root, staged(root), owned)
        hint = "`git commit -- <내 파일>` 로 좁히세요(남의 staged 는 그대로 남습니다)"

    if not bad:
        return  # 담기는 것 중 남의 것이 없음 → 통과 (다른 세션이 몇이든 무관)

    shown = "\n".join("  - " + p for p in bad[:10])
    more = "\n  … 외 %d개" % (len(bad) - 10) if len(bad) > 10 else ""
    deny(
        "이 커밋이 **다른 세션의 파일**을 함께 담습니다:\n"
        "%s%s\n"
        "→ %s.\n"
        "→ 의도적 통합 커밋이면 명령에 `# gw:allow-main-commit` 를 붙이세요."
        % (shown, more, hint)
    )


if __name__ == "__main__":
    main()
