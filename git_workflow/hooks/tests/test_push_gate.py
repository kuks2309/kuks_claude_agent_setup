#!/usr/bin/env python3
"""git_workflow-commit-track.py + git_workflow-push-gate.py 테스트 (표준 라이브러리만).

실제 임시 git 저장소를 만들어 커밋·원격추적 ref·세션 커밋목록을 구성하고
훅을 하위프로세스로 실행해 차단(deny JSON)/통과(무출력)를 검증한다.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS = os.path.dirname(HERE)
GATE = os.path.join(HOOKS, "git_workflow-push-gate.py")
TRACK = os.path.join(HOOKS, "git_workflow-commit-track.py")


def _git(cwd, *args):
    return subprocess.run(["git", "-C", cwd, *args],
                          capture_output=True, text=True, check=True)


def _init_repo():
    cwd = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", cwd], check=True)
    _git(cwd, "config", "user.email", "t@t")
    _git(cwd, "config", "user.name", "t")
    _git(cwd, "config", "commit.gpgsign", "false")
    d = os.path.join(cwd, "docs", "claude_guideline", "git_workflow")
    os.makedirs(d)
    open(os.path.join(d, "git_workflow.md"), "w").close()  # 룰 활성 게이트
    return cwd


def _commit(cwd, fname, msg):
    with open(os.path.join(cwd, fname), "w", encoding="utf-8") as f:
        f.write(msg)
    _git(cwd, "add", fname)
    _git(cwd, "commit", "-q", "-m", msg)
    return _git(cwd, "rev-parse", "HEAD").stdout.strip()


def _set_origin_main(cwd, sha):
    _git(cwd, "update-ref", "refs/remotes/origin/main", sha)


def _record_session_commit(cwd, sid, sha):
    d = os.path.join(cwd, ".git", "git_workflow", "sessions", sid)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "commits"), "a", encoding="utf-8") as f:
        f.write(sha + "\n")


def _run(hook, cwd, command, sid):
    payload = json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": command},
                          "session_id": sid, "cwd": cwd})
    return subprocess.run([sys.executable, hook], input=payload,
                          capture_output=True, text=True, timeout=5)


def _denied(out):
    return "deny" in out.stdout and "permissionDecision" in out.stdout


# ---------- push-gate ----------

def test_gate_allows_when_all_commits_owned():
    cwd = _init_repo()
    base = _commit(cwd, "a.txt", "base")
    _set_origin_main(cwd, base)
    c1 = _commit(cwd, "b.txt", "mine1")
    c2 = _commit(cwd, "c.txt", "mine2")
    _record_session_commit(cwd, "S1", c1)
    _record_session_commit(cwd, "S1", c2)
    out = _run(GATE, cwd, "git push origin main", "S1")
    assert not _denied(out), f"내 커밋만인데 차단됨: {out.stdout}"


def test_gate_blocks_foreign_commit():
    cwd = _init_repo()
    base = _commit(cwd, "a.txt", "base")
    _set_origin_main(cwd, base)
    foreign = _commit(cwd, "other.txt", "타세션")   # 기록 안 함 → foreign
    mine = _commit(cwd, "mine.txt", "mine")
    _record_session_commit(cwd, "S1", mine)
    out = _run(GATE, cwd, "git push origin main", "S1")
    assert _denied(out), f"타 세션 커밋 섞였는데 통과됨: {out.stdout}"
    assert foreign[:7] in out.stdout  # 차단 메시지에 foreign 커밋 명시


def test_gate_allows_session_branch():
    cwd = _init_repo()
    base = _commit(cwd, "a.txt", "base")
    _set_origin_main(cwd, base)
    _commit(cwd, "other.txt", "타세션")  # foreign 있어도
    out = _run(GATE, cwd, "git push origin session/abc123", "S1")
    assert not _denied(out), "비-main 브랜치 push 는 통과해야 함"


def test_gate_override_token():
    cwd = _init_repo()
    base = _commit(cwd, "a.txt", "base")
    _set_origin_main(cwd, base)
    _commit(cwd, "other.txt", "타세션")  # foreign
    out = _run(GATE, cwd, "git push origin main  # gw:allow-main-push", "S1")
    assert not _denied(out), "override 토큰이 있으면 통과해야 함"


def test_gate_allows_when_no_tracking_ref():
    cwd = _init_repo()
    _commit(cwd, "a.txt", "base")
    _commit(cwd, "b.txt", "x")  # origin/main ref 없음
    out = _run(GATE, cwd, "git push origin main", "S1")
    assert not _denied(out), "원격추적 ref 없으면(첫 push) 통과해야 함"


def test_gate_ignores_non_push():
    cwd = _init_repo()
    out = _run(GATE, cwd, "git status", "S1")
    assert not _denied(out) and out.returncode == 0


# ---------- commit-track ----------

def test_commit_track_records_head():
    cwd = _init_repo()
    _commit(cwd, "a.txt", "base")
    head = _git(cwd, "rev-parse", "HEAD").stdout.strip()
    # commit-track 을 'git commit' 명령 직후처럼 실행
    _run(TRACK, cwd, "git commit -m x", "S9")
    rec = os.path.join(cwd, ".git", "git_workflow", "sessions", "S9", "commits")
    assert os.path.isfile(rec), "commits 파일 미생성"
    assert head in open(rec, encoding="utf-8").read()


def test_commit_track_dedup():
    cwd = _init_repo()
    _commit(cwd, "a.txt", "base")
    _run(TRACK, cwd, "git commit -m x", "S9")
    _run(TRACK, cwd, "git commit -m x", "S9")  # 같은 HEAD 재기록
    rec = os.path.join(cwd, ".git", "git_workflow", "sessions", "S9", "commits")
    lines = [ln for ln in open(rec, encoding="utf-8").read().splitlines() if ln.strip()]
    assert len(lines) == 1, f"중복 기록됨: {lines}"


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                fails += 1
                print(f"FAIL {name}: {e}")
            except Exception as e:  # noqa: BLE001
                fails += 1
                print(f"ERROR {name}: {type(e).__name__}: {e}")
    sys.exit(1 if fails else 0)
