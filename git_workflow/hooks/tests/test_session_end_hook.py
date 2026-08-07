#!/usr/bin/env python3
"""SessionEnd 훅 래퍼(git_workflow-session-end.py) 계약 시험 (표준 라이브러리만).

이 래퍼가 프로덕션에서 실제로 자동 병합을 일으키는 유일한 진입점이다. session.sh 를
직접 호출하는 시험만 있으면 스크립트는 멀쩡한데 **훅이 안 불리는** 상태를 놓친다 —
"설치돼 있으니 동작할 것"이라는 가정이 로컬 main 55커밋 발산을 만든 그 구조다.

검증: stdin JSON → 세션 브랜치가 origin/main 에 병합·push 되고 worktree·브랜치가 정리되는가
     / 룰 미설치 저장소는 무간섭 / 브랜치 없으면 무해 / 세션 id 를 8자로 줄여 브랜치를 찾는가
     / 항상 exit 0 (종료 흐름을 막지 않는다)

실행: python3 tests/test_session_end_hook.py   (종료코드 0=전체 통과)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS = os.path.dirname(HERE)
HOOK = os.path.join(HOOKS, "git_workflow-session-end.py")
SESSION_SH = os.path.join(HOOKS, "git_workflow-session.sh")
PASS, FAIL = 0, 0


def ok(name):
    global PASS
    PASS += 1
    print("  PASS " + name)


def no(name, detail=""):
    global FAIL
    FAIL += 1
    print("  FAIL %s: %s" % (name, detail))


def git(cwd, *args):
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True)


def setup(with_rule=True):
    """bare origin/fito + 클론 1개. with_rule=False 면 번들 미설치 저장소."""
    root = tempfile.mkdtemp()
    subprocess.run(["git", "init", "--bare", "-q", os.path.join(root, "origin.git")], check=True)
    subprocess.run(["git", "init", "--bare", "-q", os.path.join(root, "fito.git")], check=True)
    repo = os.path.join(root, "repo")
    subprocess.run(["git", "clone", "-q", os.path.join(root, "origin.git"), repo], check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t"), ("commit.gpgsign", "false")):
        git(repo, "config", k, v)
    git(repo, "remote", "add", "fito", os.path.join(root, "fito.git"))
    if with_rule:
        d = os.path.join(repo, "docs", "claude_guideline", "git_workflow")
        os.makedirs(d)
        open(os.path.join(d, "git_workflow.md"), "w").close()
    with open(os.path.join(repo, "file.txt"), "w") as f:
        f.write("base\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "init")
    git(repo, "branch", "-M", "main")
    git(repo, "push", "-q", "-u", "origin", "main")
    git(repo, "push", "-q", "fito", "main")
    git(repo, "fetch", "-q", "origin")
    return root, repo


def start_session(repo, sid):
    subprocess.run(["bash", SESSION_SH, "start", sid], cwd=repo,
                   capture_output=True, text=True)
    return os.path.join(os.path.dirname(repo),
                        os.path.basename(repo) + "-ses-" + sid[:8])


def work(wt, name):
    with open(os.path.join(wt, name), "w", encoding="utf-8") as f:
        f.write("세션 작업\n")
    git(wt, "add", "-A")
    git(wt, "commit", "-q", "-m", "session work")


def run_hook(repo, sid):
    payload = json.dumps({"session_id": sid, "cwd": repo, "reason": "clear"})
    return subprocess.run([sys.executable, HOOK], input=payload,
                          capture_output=True, text=True, timeout=180)


FULL_SID = "abcd1234-5678-90ab-cdef-1234567890ab"   # 앞 8자 = abcd1234


def main():
    print("== 래퍼 호출만으로 병합·push·정리가 일어나는가 ==")
    root, repo = setup()
    wt = start_session(repo, FULL_SID)
    work(wt, "hooked.txt")
    r = run_hook(repo, FULL_SID)
    ok("exit0") if r.returncode == 0 else no("exit0", "rc=%d %s" % (r.returncode, r.stderr[:120]))
    git(repo, "fetch", "-q", "origin")
    merged = git(repo, "cat-file", "-e", "origin/main:hooked.txt").returncode == 0
    ok("merged_to_origin") if merged else no("merged_to_origin", "훅으로는 병합이 안 일어남")
    gone = git(repo, "show-ref", "--verify", "--quiet",
               "refs/heads/session/" + FULL_SID[:8]).returncode != 0
    ok("branch_cleaned") if gone else no("branch_cleaned", "브랜치 잔존")
    ok("worktree_cleaned") if not os.path.isdir(wt) else no("worktree_cleaned", "worktree 잔존")
    git(repo, "fetch", "-q", "fito")
    same = (git(repo, "rev-parse", "origin/main").stdout ==
            git(repo, "rev-parse", "fito/main").stdout)
    ok("fito_mirrored") if same else no("fito_mirrored", "미러 불일치")
    ok("local_main_synced") if (git(repo, "rev-parse", "main").stdout ==
                                git(repo, "rev-parse", "origin/main").stdout) \
        else no("local_main_synced", "로컬 main 미동기화")
    shutil.rmtree(root, ignore_errors=True)

    print("== 번들 미설치 저장소는 무간섭 ==")
    root, repo = setup(with_rule=False)
    wt = start_session(repo, FULL_SID)
    work(wt, "untouched.txt")
    r = run_hook(repo, FULL_SID)
    ok("noop_exit0") if r.returncode == 0 else no("noop_exit0", "rc=%d" % r.returncode)
    still = git(repo, "show-ref", "--verify", "--quiet",
                "refs/heads/session/" + FULL_SID[:8]).returncode == 0
    ok("noop_branch_kept") if still else no("noop_branch_kept", "미설치인데 브랜치를 건드림")
    shutil.rmtree(root, ignore_errors=True)

    print("== 세션 브랜치가 없으면 무해하게 통과 ==")
    root, repo = setup()
    r = run_hook(repo, FULL_SID)
    ok("no_branch_exit0") if r.returncode == 0 else no("no_branch_exit0", "rc=%d" % r.returncode)
    shutil.rmtree(root, ignore_errors=True)

    print("== session_id 누락도 무해 ==")
    root, repo = setup()
    r = subprocess.run([sys.executable, HOOK],
                       input=json.dumps({"cwd": repo}), capture_output=True,
                       text=True, timeout=60)
    ok("no_sid_exit0") if r.returncode == 0 else no("no_sid_exit0", "rc=%d" % r.returncode)
    shutil.rmtree(root, ignore_errors=True)

    print("\n-- 결과: PASS=%d FAIL=%d --" % (PASS, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
