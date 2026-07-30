#!/usr/bin/env python3
"""session_workflow 회귀 시험 — 미회수 브랜치 경고 + write-guard 판정.

임시 git 저장소를 실제로 만들어(커밋·브랜치·날짜 조작) 훅을 subprocess 로 구동한다.
표준 라이브러리만 사용. 실행: python3 test_session_workflow.py  (성공 시 exit 0)
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
import session_state as ss  # noqa: E402

GUARD = os.path.join(HOOKS, "session_workflow-write-guard.py")
PASS, FAIL = [], []


def ok(name):
    PASS.append(name)
    print("  PASS " + name)


def no(name, detail=""):
    FAIL.append(name)
    print("  FAIL %s: %s" % (name, detail))


def git(repo, *args, **kw):
    env = dict(os.environ)
    env.update(kw.pop("env", {}))
    return subprocess.run(["git", "-C", repo] + list(args),
                          capture_output=True, text=True, env=env)


def make_repo():
    """규칙 설치본을 가진 임시 저장소. main + session/* 브랜치 3종."""
    repo = tempfile.mkdtemp()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    git(repo, "config", "commit.gpgsign", "false")
    rule = os.path.join(repo, "docs", "claude_guideline", "session_workflow")
    os.makedirs(rule)
    with open(os.path.join(rule, "session_workflow.md"), "w") as f:
        f.write("rule\n")
    with open(os.path.join(repo, "tracked.txt"), "w") as f:
        f.write("base\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "init")

    def commit_on(branch, name, when):
        git(repo, "checkout", "-q", "-b", branch)
        with open(os.path.join(repo, name), "w") as f:
            f.write(name + "\n")
        git(repo, "add", name)
        git(repo, "commit", "-q", "-m", name,
            env={"GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when})
        git(repo, "checkout", "-q", "main")

    commit_on("session/old", "old.txt", "2020-01-01T00:00:00+09:00")   # 방치·미반영
    commit_on("session/fresh", "fresh.txt", "now")                     # 오늘 → 제외
    commit_on("session/merged", "merged.txt", "2020-01-01T00:00:00+09:00")
    git(repo, "merge", "-q", "--no-ff", "-m", "merge", "session/merged")
    return repo


def guard(repo, sid, tool, path):
    """write-guard 실행 → (판정, 사유). 무출력이면 ('pass', '')."""
    payload = json.dumps({"session_id": sid, "cwd": repo, "tool_name": tool,
                          "tool_input": {"file_path": path}})
    r = subprocess.run([sys.executable, GUARD], input=payload,
                       capture_output=True, text=True)
    out = r.stdout.strip()
    if not out:
        return "pass", ""
    d = json.loads(out)["hookSpecificOutput"]
    return d["permissionDecision"], d["permissionDecisionReason"]


def main():
    repo = make_repo()
    try:
        print("== 미회수 세션 브랜치 경고 ==")
        got = ss.unmerged_session_branches(repo, min_days=1)
        names = [b for b, _, _ in got]
        if names == ["session/old"]:
            ok("branch_only_unmerged_and_stale")
        else:
            no("branch_only_unmerged_and_stale", "결과=%s (기대 session/old 만)" % names)
        if got and got[0][2] == 1 and got[0][1] > 1000:
            ok("branch_counts")
        else:
            no("branch_counts", "미반영/방치일=%s" % (got[0][1:] if got else None))
        if ss.unmerged_session_branches(repo, min_days=99999) == []:
            ok("branch_threshold_respected")
        else:
            no("branch_threshold_respected", "기준일 초과인데 보고됨")

        print("== write-guard ==")
        root = ss.state_root(repo)
        os.makedirs(ss.active_dir(root), exist_ok=True)
        sid, other = "mine", "other"
        ss.save_session(root, other, {"purpose": "타 세션", "started_at": "-",
                                      "last_seen": "-", "alerted": []})
        with open(ss.touched_path(root, other), "w") as f:
            f.write("tracked.txt\n")            # 남이 만지는 중(추적본)
        with open(ss.touched_path(root, sid), "w") as f:
            f.write("mine.txt\n")               # 내 산출물
        for name in ("untracked.txt", "mine.txt"):
            with open(os.path.join(repo, name), "w") as f:
                f.write("x\n")

        cases = [
            ("new_path_pass", "pass", "Write", "brand-new.txt"),
            ("existing_untracked_ask", "ask", "Write", "untracked.txt"),
            ("tracked_pass", "pass", "Write", "tracked.txt"),   # 남의 touched 확인 후 순서 주의
            ("edit_tool_pass", "pass", "Edit", "untracked.txt"),
            ("own_touched_pass", "pass", "Write", "mine.txt"),
            ("outside_repo_pass", "pass", "Write", "/tmp/outside-sw-test.txt"),
        ]
        for name, want, tool, rel in cases:
            path = rel if rel.startswith("/") else os.path.join(repo, rel)
            got_dec, _ = guard(repo, sid, tool, path)
            # tracked.txt 는 타 세션 touched 라 ask 가 기대값 — 케이스 표에서 분리 검사
            if name == "tracked_pass":
                if got_dec == "ask":
                    ok("other_session_touched_ask")
                else:
                    no("other_session_touched_ask", "실제=%s" % got_dec)
                continue
            if got_dec == want:
                ok(name)
            else:
                no(name, "기대=%s 실제=%s" % (want, got_dec))

        # 타 세션 touched 를 비우면 같은 추적본은 통과해야 한다(추적본 덮어쓰기는 add/add 아님)
        os.remove(ss.touched_path(root, other))
        got_dec, _ = guard(repo, sid, "Write", os.path.join(repo, "tracked.txt"))
        if got_dec == "pass":
            ok("tracked_pass")
        else:
            no("tracked_pass", "실제=%s" % got_dec)

        # 규칙 미설치 저장소면 무간섭
        os.remove(os.path.join(repo, "docs", "claude_guideline",
                               "session_workflow", "session_workflow.md"))
        got_dec, _ = guard(repo, sid, "Write", os.path.join(repo, "untracked.txt"))
        if got_dec == "pass":
            ok("rule_gate_noop")
        else:
            no("rule_gate_noop", "미설치인데 개입: %s" % got_dec)
    finally:
        shutil.rmtree(repo, ignore_errors=True)

    print("-- 결과: PASS=%d FAIL=%d --" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
