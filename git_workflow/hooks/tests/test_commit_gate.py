#!/usr/bin/env python3
"""git_workflow-commit-gate.py + push-gate 첫-push 강화 테스트 (표준 라이브러리만).

실제 임시 git 저장소를 만들어 브랜치·세션 touched 기록을 구성하고
훅을 하위프로세스로 실행해 차단(deny JSON)/통과(무출력)를 검증한다.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS = os.path.dirname(HERE)
GATE = os.path.join(HOOKS, "git_workflow-commit-gate.py")
PUSH_GATE = os.path.join(HOOKS, "git_workflow-push-gate.py")


def _git(cwd, *args):
    return subprocess.run(["git", "-C", cwd, *args],
                          capture_output=True, text=True, check=True)


def _init_repo():
    cwd = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", "-b", "main", cwd], check=True)
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


def _touch_session(cwd, sid, path):
    d = os.path.join(cwd, ".git", "git_workflow", "sessions", sid)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "touched"), "a", encoding="utf-8") as f:
        f.write(os.path.join(cwd, path) + "\n")


def _run(hook, cwd, command, sid):
    payload = json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": command},
                          "session_id": sid, "cwd": cwd})
    return subprocess.run([sys.executable, hook], input=payload,
                          capture_output=True, text=True, timeout=5)


def _denied(out):
    return "deny" in out.stdout and "permissionDecision" in out.stdout


# ---------- commit-gate: 핵심 차단 ----------

def _stage_foreign(cwd, name="their.txt"):
    """타 세션이 소유를 주장하고 index 에 올려둔 파일을 만든다."""
    _touch_session(cwd, "OTHER", name)
    with open(os.path.join(cwd, name), "w", encoding="utf-8") as f:
        f.write("남의 작업\n")
    _git(cwd, "add", name)
    return name


def test_blocks_bare_commit_that_captures_foreign_staged():
    """맨몸 `git commit` 은 공유 index 를 통째로 담는다 — 남의 staged 가 있으면 차단."""
    cwd = _init_repo()
    _commit(cwd, "a.txt", "base")
    _stage_foreign(cwd)
    out = _run(GATE, cwd, "git commit -m x", "MINE")
    assert _denied(out), f"남의 staged 를 담는 맨몸 커밋인데 통과됨: {out.stdout}"
    assert "their.txt" in out.stdout, "담기는 남의 파일을 지목하지 않음"


def test_allows_bare_commit_when_nothing_foreign_staged():
    """타 세션이 활동 중이어도 index 에 남의 것이 없으면 통과 — 커밋은 박제일 뿐이다."""
    cwd = _init_repo()
    _commit(cwd, "a.txt", "base")
    _touch_session(cwd, "OTHER", "their.txt")   # 활동 중이지만 staged 는 아님
    _touch_session(cwd, "MINE", "mine.txt")
    with open(os.path.join(cwd, "mine.txt"), "w", encoding="utf-8") as f:
        f.write("내 작업\n")
    _git(cwd, "add", "mine.txt")
    out = _run(GATE, cwd, "git commit -m x", "MINE")
    assert not _denied(out), f"담기는 남의 것이 없는데 차단됨: {out.stdout}"


def test_allows_path_limited_commit_despite_foreign_staged():
    """경로 한정 커밋은 index 의 나머지를 건드리지 않는다 — 남의 staged 가 있어도 통과."""
    cwd = _init_repo()
    _commit(cwd, "a.txt", "base")
    _stage_foreign(cwd)
    _touch_session(cwd, "MINE", "mine.txt")
    with open(os.path.join(cwd, "mine.txt"), "w", encoding="utf-8") as f:
        f.write("내 작업\n")
    _git(cwd, "add", "mine.txt")
    out = _run(GATE, cwd, "git commit -m x -- mine.txt", "MINE")
    assert not _denied(out), f"경로 한정 커밋인데 차단됨: {out.stdout}"


def test_blocks_path_limited_commit_of_foreign_path():
    """경로 한정이라도 그 경로가 남의 것이면 차단."""
    cwd = _init_repo()
    _commit(cwd, "a.txt", "base")
    _stage_foreign(cwd)
    out = _run(GATE, cwd, "git commit -m x -- their.txt", "MINE")
    assert _denied(out), f"남의 경로를 지정했는데 통과됨: {out.stdout}"


def test_blocks_commit_all_with_foreign_dirty():
    """`-a` 는 추적 파일 수정분을 전부 담는다 — 남의 dirty 가 있으면 차단."""
    cwd = _init_repo()
    _commit(cwd, "their.txt", "base")           # 추적 상태로 만든 뒤
    _touch_session(cwd, "OTHER", "their.txt")
    with open(os.path.join(cwd, "their.txt"), "a", encoding="utf-8") as f:
        f.write("남의 수정\n")                   # 미스테이지 수정
    out = _run(GATE, cwd, "git commit -am x", "MINE")
    assert _denied(out), f"-a 가 남의 수정을 담는데 통과됨: {out.stdout}"


def test_message_value_not_treated_as_path():
    """`-m their.txt` 의 값을 경로로 오인하면 안 된다(스코프 오판)."""
    cwd = _init_repo()
    _commit(cwd, "a.txt", "base")
    _touch_session(cwd, "OTHER", "their.txt")   # staged 는 아님
    out = _run(GATE, cwd, "git commit -m their.txt", "MINE")
    assert not _denied(out), f"메시지 값을 경로로 오인해 차단됨: {out.stdout}"


def test_allows_main_commit_when_single_session():
    cwd = _init_repo()
    _commit(cwd, "a.txt", "base")
    _touch_session(cwd, "MINE", "mine.txt")     # 내 세션만
    out = _run(GATE, cwd, "git commit -m x", "MINE")
    assert not _denied(out), "단일 세션이면 §2 기본대로 통과해야 함"


def test_allows_session_branch_commit():
    cwd = _init_repo()
    _commit(cwd, "a.txt", "base")
    _git(cwd, "checkout", "-q", "-b", "session/abc123")
    _touch_session(cwd, "OTHER", "their.txt")   # 타 세션 있어도
    out = _run(GATE, cwd, "git commit -m x", "MINE")
    assert not _denied(out), "비-보호 브랜치 커밋은 통과해야 함"


def test_override_token():
    cwd = _init_repo()
    _commit(cwd, "a.txt", "base")
    _touch_session(cwd, "OTHER", "their.txt")
    out = _run(GATE, cwd, "git commit -m x  # gw:allow-main-commit", "MINE")
    assert not _denied(out), "override 토큰이 있으면 통과해야 함"


def test_ignores_non_commit():
    cwd = _init_repo()
    _commit(cwd, "a.txt", "base")
    _touch_session(cwd, "OTHER", "their.txt")
    out = _run(GATE, cwd, "git status", "MINE")
    assert not _denied(out) and out.returncode == 0


def test_ignores_add_only():
    """`git add` 는 stage-gate 소관 — commit-gate 가 간섭하면 안 됨."""
    cwd = _init_repo()
    _commit(cwd, "a.txt", "base")
    _touch_session(cwd, "OTHER", "their.txt")
    out = _run(GATE, cwd, "git add somefile.txt", "MINE")
    assert not _denied(out), "add 만 있는 명령을 차단하면 안 됨"


def test_no_interference_when_bundle_absent():
    cwd = _init_repo()
    os.remove(os.path.join(cwd, "docs", "claude_guideline",
                           "git_workflow", "git_workflow.md"))
    _commit(cwd, "a.txt", "base")
    _touch_session(cwd, "OTHER", "their.txt")
    out = _run(GATE, cwd, "git commit -m x", "MINE")
    assert not _denied(out), "번들 미설치 프로젝트는 간섭하면 안 됨"


# ---------- push-gate: 첫-push 구멍 강화 ----------

def test_push_first_push_blocked_when_other_session_active():
    cwd = _init_repo()
    _commit(cwd, "a.txt", "base")          # origin/main ref 없음(첫 push)
    _touch_session(cwd, "OTHER", "their.txt")
    out = _run(PUSH_GATE, cwd, "git push origin main", "MINE")
    assert _denied(out), f"첫 push + 타 세션 활동인데 통과됨: {out.stdout}"


def test_push_first_push_allowed_when_single_session():
    cwd = _init_repo()
    _commit(cwd, "a.txt", "base")
    _touch_session(cwd, "MINE", "mine.txt")
    out = _run(PUSH_GATE, cwd, "git push origin main", "MINE")
    assert not _denied(out), "단일 세션 첫 push 는 통과해야 함(회귀 방지)"


def test_push_first_push_override():
    cwd = _init_repo()
    _commit(cwd, "a.txt", "base")
    _touch_session(cwd, "OTHER", "their.txt")
    out = _run(PUSH_GATE, cwd, "git push origin main  # gw:allow-main-push", "MINE")
    assert not _denied(out), "override 토큰이 있으면 통과해야 함"


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
