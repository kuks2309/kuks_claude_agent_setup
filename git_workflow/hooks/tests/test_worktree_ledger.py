#!/usr/bin/env python3
"""세션 장부(touched)가 메인 트리와 링크드 worktree 에서 **같은 곳**인지 시험.

`--absolute-git-dir` 은 링크드 worktree 에서 `.git/worktrees/<name>` 을 가리킨다.
장부 경로가 트리마다 갈리면 세션 worktree 안에서는 장부가 비어 보이고, 그 트리의
**정당한 staging 이 전부 거부**된다 — 기록 분리를 위해 권장하는 바로 그 작업 공간이
쓸 수 없게 된다. 훅 전체가 `--git-common-dir` 로 수렴하는지 확인한다.

실행: python3 tests/test_worktree_ledger.py   (종료코드 0=전체 통과)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS = os.path.dirname(HERE)
sys.path.insert(0, HOOKS)
import gw_common as gw  # noqa: E402

STAGE_GATE = os.path.join(HOOKS, "git_workflow-stage-gate.py")
SID = "sess-mine"
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


def setup():
    """번들 설치본을 가진 저장소 + 링크드 worktree 하나."""
    root = tempfile.mkdtemp()
    repo = os.path.join(root, "repo")
    os.makedirs(repo)
    subprocess.run(["git", "init", "-q", "-b", "main", repo], check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t"), ("commit.gpgsign", "false")):
        git(repo, "config", k, v)
    d = os.path.join(repo, "docs", "claude_guideline", "git_workflow")
    os.makedirs(d)
    open(os.path.join(d, "git_workflow.md"), "w").close()
    with open(os.path.join(repo, "base.txt"), "w") as f:
        f.write("base\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "init")
    wt = os.path.join(root, "repo-ses-abc")
    git(repo, "worktree", "add", wt, "-b", "session/abc", "-q")
    return root, repo, wt


def common_dir(cwd):
    """장부가 실제로 놓이는 공유 git-dir — 훅 구현에 의존하지 않고 git 에 직접 묻는다.

    `gw.git_dir()` 로 기록하면 그 구현이 트리별로 갈려도 시험이 자기 일관적이 되어
    결함을 통과시킨다. 실사용에서 track 훅은 세션 cwd(메인 트리) 기준으로 기록하므로
    장부는 공유 `.git` 에 놓인다 — 그 조건을 그대로 모사한다.
    """
    out = subprocess.run(["git", "-C", cwd, "rev-parse", "--git-common-dir"],
                         capture_output=True, text=True)
    d = out.stdout.rstrip("\n")
    return d if os.path.isabs(d) else os.path.abspath(os.path.join(cwd, d))


def record(gd, path_abs):
    d = os.path.join(gd, "git_workflow", "sessions", SID)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "touched"), "a", encoding="utf-8") as f:
        f.write(path_abs + "\n")


def run_gate(cwd, command):
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command},
                          "session_id": SID, "cwd": cwd})
    r = subprocess.run([sys.executable, STAGE_GATE], input=payload,
                       capture_output=True, text=True)
    if not r.stdout.strip():
        return False
    try:
        return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
    except (ValueError, KeyError):
        return False


def main():
    root, repo, wt = setup()

    print("== 장부 경로가 두 트리에서 동일한가 ==")
    gd_main, gd_wt = gw.git_dir(repo), gw.git_dir(wt)
    ok("same_ledger_dir") if gd_main and gd_main == gd_wt \
        else no("same_ledger_dir", "메인=%s / worktree=%s" % (gd_main, gd_wt))
    ok("is_common_dir") if gd_main and not gd_main.rstrip("/").endswith(os.path.join("worktrees", "repo-ses-abc")) \
        else no("is_common_dir", "worktree 전용 git-dir 를 가리킴: %s" % gd_main)

    print("== worktree 안에서 내 파일 staging 이 통과하는가 ==")
    mine_wt = os.path.join(wt, "mine.txt")
    with open(mine_wt, "w", encoding="utf-8") as f:
        f.write("내 작업\n")
    record(common_dir(repo), mine_wt)   # track 은 공유 dir 에 기록한다
    ok("wt_add_allowed") if not run_gate(wt, "git add mine.txt") \
        else no("wt_add_allowed", "세션 worktree 의 정당한 staging 이 거부됨")

    print("== 그래도 남의 파일은 계속 막는가(게이트 무력화 아님) ==")
    other_wt = os.path.join(wt, "theirs.txt")
    with open(other_wt, "w", encoding="utf-8") as f:
        f.write("남의 작업\n")
    ok("wt_foreign_denied") if run_gate(wt, "git add theirs.txt") \
        else no("wt_foreign_denied", "장부에 없는 파일이 통과됨")

    print("== 메인 트리에서 기록한 소유가 worktree 에서도 보이는가 ==")
    mine_main = os.path.join(repo, "frommain.txt")
    with open(mine_main, "w", encoding="utf-8") as f:
        f.write("메인에서 만든 내 파일\n")
    record(common_dir(repo), mine_main)
    ok("cross_tree_visible") if not run_gate(repo, "git add frommain.txt") \
        else no("cross_tree_visible", "메인 트리 staging 이 거부됨")

    print("== 비-git 워크스페이스 세션이 하위 저장소를 고쳐도 장부에 남는가 ==")
    # 실사용 형태: 세션 cwd 는 워크스페이스(비-git), 수정 파일은 그 아래 저장소.
    # cwd 로만 git-dir 를 찾으면 해석이 실패해 track 이 조용히 아무것도 남기지 않고,
    # 그 장부에 의존하는 게이트 3종의 소유 판정이 통째로 무너진다.
    ws = os.path.dirname(repo)                      # repo 의 부모 = 비-git 워크스페이스
    sub_file = os.path.join(repo, "fromws.txt")
    with open(sub_file, "w", encoding="utf-8") as f:
        f.write("워크스페이스 세션이 만든 파일\n")
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": sub_file},
                          "session_id": SID, "cwd": ws})
    subprocess.run([sys.executable, os.path.join(HOOKS, "git_workflow-track.py")],
                   input=payload, capture_output=True, text=True)
    ledger = os.path.join(common_dir(repo), "git_workflow", "sessions", SID, "touched")
    recorded = os.path.isfile(ledger) and "fromws.txt" in open(ledger, encoding="utf-8").read()
    ok("nongit_cwd_recorded") if recorded \
        else no("nongit_cwd_recorded", "비-git cwd 세션의 수정이 장부에 안 남음")
    ok("nongit_add_allowed") if not run_gate(repo, "git add fromws.txt") \
        else no("nongit_add_allowed", "장부에 남았는데 staging 이 거부됨")

    shutil.rmtree(root, ignore_errors=True)
    print("\n-- 결과: PASS=%d FAIL=%d --" % (PASS, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
