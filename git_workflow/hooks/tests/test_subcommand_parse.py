#!/usr/bin/env python3
"""gw_common.git_subcommands / runs_git 판정 테스트.

배경: 훅들이 진입 판정에 부분문자열 매칭(`"commit" in cmd`)을 써서, git 을 호출하지
않는 명령(문자열에 단어만 든 명령·`.git/…/commits` 파일 읽기)을 커밋/푸시로 오인했다.
그 결과 (1) 소유권 기록이 오염되어 push-gate 판정이 무너지고 (2) 무관한 명령이 차단됐다.

실행: python3 tests/test_subcommand_parse.py   (종료코드 0=전체 통과)
self-contained: 표준 라이브러리만.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gw_common as gw  # noqa: E402

# (명령, 기대 하위명령 목록)
CASES = [
    # --- 실제 git 호출 (탐지되어야 함) ---
    ("git commit -m 'x'", ["commit"]),
    ("git push origin main", ["push"]),
    ("git add path/to/file", ["add"]),
    ("git status --porcelain", ["status"]),
    ("git -C /repo push origin main", ["push"]),
    ("git -c user.name=x -C /r commit --amend", ["commit"]),
    ("/usr/bin/git push fito main", ["push"]),
    ("cd /repo && git commit -m a && git push origin main", ["commit", "push"]),
    ("GIT_AUTHOR_NAME=x git commit -m y", ["commit"]),
    ("sudo git push origin main", ["push"]),
    ("git --git-dir /r/.git commit -m z", ["commit"]),

    # --- git 호출 아님 (구판이 오탐하던 것 — 탐지되면 안 됨) ---
    ("echo git commit", []),
    ("echo 'git push origin main'", []),
    ("grep -n commit git_workflow/hooks/git_workflow-commit-track.py", []),
    ("for d in .git/git_workflow/sessions/*/; do cat \"$d/commits\"; done", []),
    ("ls .git/git_workflow/sessions/", []),
    ("cat notes-about-push.md", []),
    ("wc -l docs/commit-guide.md", []),
    ("python3 -c \"print('git commit')\"", []),

    # --- git 호출이지만 대상 하위명령이 아님 ---
    ("git log --oneline HEAD..origin/main", ["log"]),
    ("git diff --stat HEAD origin/main", ["diff"]),
    ("git rev-list --count origin/main...HEAD", ["rev-list"]),

    # --- 백슬래시 줄 이음: 한 명령으로 이어져야 한다 ---
    # (먼저 `\n` 으로 쪼개면 여러 줄 `git add` 가 '파싱 불가'로 차단된다 — 실측 사례)
    ("git add a.py \\\n    b.py \\\n    c.py", ["add"]),
    ("git commit -m x \\\n    -- mine.txt", ["commit"]),
]

# 줄 이음 정규화 — 세그먼트가 쪼개지지 않고 인자가 보존되는지
CONT = [
    ("git add a.py \\\n    b.py", 1, ["a.py", "b.py"]),
    ("git add a.py && git commit -m x", 2, None),
]

# runs_git(cmd, *subs) 계약 — 게이트 진입 판정에 쓰이는 형태 그대로
RUNS = [
    ("git commit -m x", ("commit",), True),
    ("echo git commit", ("commit",), False),
    ("git add f && git commit -m x", ("add", "commit"), True),
    ("grep push README.md", ("push",), False),
    ("git push origin main", ("push",), True),
    ("", ("push",), False),
]


def main():
    fail = 0
    print("=== git_subcommands ===")
    for cmd, want in CASES:
        got = gw.git_subcommands(cmd)
        ok = got == want
        fail += 0 if ok else 1
        print(("  PASS " if ok else "  FAIL ") + repr(cmd)[:58].ljust(60) + "-> " +
              repr(got) + ("" if ok else "  (기대 %r)" % (want,)))

    print("=== runs_git ===")
    for cmd, subs, want in RUNS:
        got = gw.runs_git(cmd, *subs)
        ok = got is want
        fail += 0 if ok else 1
        print(("  PASS " if ok else "  FAIL ") + (repr(cmd)[:40] + " " + repr(subs))[:58].ljust(60) +
              "-> " + repr(got) + ("" if ok else "  (기대 %r)" % (want,)))

    print("=== 줄 이음 정규화 (segments / git_calls) ===")
    for cmd, nseg, want_args in CONT:
        segs = gw.segments(cmd)
        ok = len(segs) == nseg
        if want_args is not None:
            args = gw.git_calls(cmd)[0][1] if gw.git_calls(cmd) else []
            ok = ok and args == want_args
        fail += 0 if ok else 1
        print(("  PASS " if ok else "  FAIL ") + repr(cmd)[:58].ljust(60) +
              "-> 세그먼트 %d" % len(segs) + ("" if ok else "  (기대 %d/%r)" % (nseg, want_args)))

    total = len(CASES) + len(RUNS) + len(CONT)
    print("\n%d/%d 통과, 실패 %d 건" % (total - fail, total, fail))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
