#!/usr/bin/env python3
"""git_workflow-tree-gate.py 테스트 (표준 라이브러리만).

실제 임시 git 저장소에 '내 세션'/'타 세션' 미커밋 변경을 구성하고, 트리 전역
파괴 명령이 차단(deny JSON)되는지·경로 한정과 단독 사용은 통과하는지 검증한다.

회귀 대상(2026-08-05 사고): `git stash push` + `reset --hard` 가 다른 세션이
staged 해 둔 파일까지 걷어갔다.

실행: python3 tests/test_tree_gate.py   (종료코드 0=전체 통과)
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS = os.path.dirname(HERE)
GATE = os.path.join(HOOKS, "git_workflow-tree-gate.py")

MINE = "sess-mine"
OTHER = "sess-other"
PASS = 0
FAIL = 0


def ok(name):
    global PASS
    PASS += 1
    print("  PASS " + name)


def no(name, detail=""):
    global FAIL
    FAIL += 1
    print("  FAIL " + name + ((": " + detail) if detail else ""))


def _git(cwd, *args):
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True)


def _init_repo():
    cwd = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", "-b", "main", cwd], check=True)
    _git(cwd, "config", "user.email", "t@t")
    _git(cwd, "config", "user.name", "t")
    _git(cwd, "config", "commit.gpgsign", "false")
    d = os.path.join(cwd, "docs", "claude_guideline", "git_workflow")
    os.makedirs(d)
    open(os.path.join(d, "git_workflow.md"), "w").close()   # 룰 활성 게이트
    for f in ("mine.txt", "other.txt"):
        with open(os.path.join(cwd, f), "w", encoding="utf-8") as fh:
            fh.write("base\n")
    _git(cwd, "add", "-A")
    _git(cwd, "commit", "-q", "-m", "init")
    return cwd


def _touch_session(cwd, sid, path):
    d = os.path.join(cwd, ".git", "git_workflow", "sessions", sid)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "touched"), "a", encoding="utf-8") as f:
        f.write(os.path.join(cwd, path) + "\n")


def _dirty(cwd, path, staged=False):
    with open(os.path.join(cwd, path), "a", encoding="utf-8") as f:
        f.write("edit\n")
    if staged:
        _git(cwd, "add", path)


def _run(cwd, command, sid=MINE):
    payload = json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": command},
                          "session_id": sid, "cwd": cwd})
    r = subprocess.run([sys.executable, GATE], input=payload,
                       capture_output=True, text=True)
    return r.stdout.strip()


def denied(out):
    if not out:
        return False
    try:
        return json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"
    except (ValueError, KeyError):
        return False


def case(name, command, want_deny, setup=None):
    cwd = _init_repo()
    _touch_session(cwd, MINE, "mine.txt")
    _touch_session(cwd, OTHER, "other.txt")
    if setup:
        setup(cwd)
    out = _run(cwd, command)
    got = denied(out)
    if got is want_deny:
        ok(name)
    else:
        no(name, "deny=%s (기대 %s)" % (got, want_deny))


def both_dirty(cwd):
    _dirty(cwd, "mine.txt")
    _dirty(cwd, "other.txt", staged=True)   # 타 세션이 staged 해 둔 상태


def only_mine_dirty(cwd):
    _dirty(cwd, "mine.txt")


def main():
    print("== 타 세션 미커밋 변경이 있을 때: 전역 파괴 명령 차단 ==")
    case("stash_push_denied", "git stash push -m x", True, both_dirty)
    case("stash_bare_denied", "git stash", True, both_dirty)
    case("reset_hard_denied", "git reset --hard origin/main", True, both_dirty)
    case("checkout_dot_denied", "git checkout -- .", True, both_dirty)
    case("restore_dot_denied", "git restore .", True, both_dirty)
    case("clean_fd_denied", "git clean -fd", True, both_dirty)

    print("== 경로 한정·조회형은 통과 ==")
    case("stash_pathspec_ok", "git stash push -- mine.txt", False, both_dirty)
    case("stash_msg_pathspec_ok", "git stash push -m x -- mine.txt", False, both_dirty)
    case("stash_msg_only_denied", "git stash push -m x", True, both_dirty)  # -m 값을 경로로 오인 금지
    case("stash_list_ok", "git stash list", False, both_dirty)
    case("checkout_path_ok", "git checkout -- mine.txt", False, both_dirty)
    case("reset_soft_ok", "git reset --soft HEAD~1", False, both_dirty)
    case("reset_mixed_ok", "git reset HEAD", False, both_dirty)

    print("== 타 세션 변경이 없으면 통과 (혼자 쓰는 트리를 막지 않음) ==")
    case("only_mine_ok", "git reset --hard", False, only_mine_dirty)
    case("clean_tree_ok", "git reset --hard", False, None)

    print("== override / 비대상 ==")
    case("override_ok", "git reset --hard  # gw:allow-tree-wide", False, both_dirty)
    case("not_git_call_ok", "echo git reset --hard", False, both_dirty)
    case("unwatched_subcmd_ok", "git status --porcelain", False, both_dirty)

    print("\n-- 결과: PASS=%d FAIL=%d --" % (PASS, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
