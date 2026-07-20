#!/usr/bin/env python3
"""게이트 3종의 판정 기준 디렉토리 해석 테스트 (표준 라이브러리만).

`cd <다른저장소> && git …` 오탐(false positive) 해소와, 그 수정이 새 우회 구멍
(하위 디렉토리로 cd 하면 게이트가 꺼지는 것)을 만들지 않았는지를 함께 검증한다.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS = os.path.dirname(HERE)
CGATE = os.path.join(HOOKS, "git_workflow-commit-gate.py")
SGATE = os.path.join(HOOKS, "git_workflow-stage-gate.py")
PGATE = os.path.join(HOOKS, "git_workflow-push-gate.py")


def _git(cwd, *args):
    return subprocess.run(["git", "-C", cwd, *args],
                          capture_output=True, text=True, check=True)


def _init_repo(with_bundle=True):
    cwd = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", "-b", "main", cwd], check=True)
    _git(cwd, "config", "user.email", "t@t")
    _git(cwd, "config", "user.name", "t")
    _git(cwd, "config", "commit.gpgsign", "false")
    if with_bundle:
        d = os.path.join(cwd, "docs", "claude_guideline", "git_workflow")
        os.makedirs(d)
        open(os.path.join(d, "git_workflow.md"), "w").close()
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


# ---------- 오탐 해소 (debt-011 본체) ----------

def test_commit_gate_no_false_positive_on_other_repo():
    """cd <번들 미설치 타 저장소> && git commit → 간섭하면 안 됨."""
    proj = _init_repo()                      # 세션 cwd (게이트 활성, 타 세션 활동)
    _commit(proj, "a.txt", "base")
    _touch_session(proj, "OTHER", "their.txt")
    other = _init_repo(with_bundle=False)    # 실제 대상 (번들 없음)
    _commit(other, "x.txt", "x")
    out = _run(CGATE, proj, "cd %s && git commit -m x" % other, "MINE")
    assert not _denied(out), f"타 저장소 커밋을 프로젝트 기준으로 오판: {out.stdout}"


def test_stage_gate_no_false_positive_on_other_repo():
    proj = _init_repo()
    _commit(proj, "a.txt", "base")
    _touch_session(proj, "OTHER", "their.txt")
    other = _init_repo(with_bundle=False)
    out = _run(SGATE, proj, "cd %s && git add f1.py f2.py" % other, "MINE")
    assert not _denied(out), f"타 저장소 staging 을 오판: {out.stdout}"


def test_push_gate_no_false_positive_on_other_repo():
    """실제 발현 사례 재현 — 미러 push 가 프로젝트 기준으로 deny 되던 건."""
    proj = _init_repo()
    _commit(proj, "a.txt", "base")
    _touch_session(proj, "OTHER", "their.txt")   # 프로젝트엔 타 세션 활동
    other = _init_repo(with_bundle=False)
    _commit(other, "x.txt", "x")
    out = _run(PGATE, proj, "cd %s && git push fito origin/main:main" % other, "MINE")
    assert not _denied(out), f"타 저장소 push 를 오판: {out.stdout}"


def test_quoted_cd_path_with_space():
    """따옴표로 감싼 공백 포함 경로도 해석해야 함(실제 프로젝트 경로에 공백 있음)."""
    proj = _init_repo()
    _commit(proj, "a.txt", "base")
    _touch_session(proj, "OTHER", "their.txt")
    base = tempfile.mkdtemp()
    other = os.path.join(base, "repo with space")
    os.makedirs(other)
    subprocess.run(["git", "init", "-q", "-b", "main", other], check=True)
    _git(other, "config", "user.email", "t@t")
    _git(other, "config", "user.name", "t")
    _commit(other, "x.txt", "x")
    out = _run(CGATE, proj, 'cd "%s" && git commit -m x' % other, "MINE")
    assert not _denied(out), f"따옴표 경로 해석 실패: {out.stdout}"


# ---------- 우회 구멍 미발생 (회귀 방지) ----------

def test_cd_subdir_still_gated():
    """같은 저장소 하위로 cd 해도 게이트가 꺼지면 안 됨 (toplevel 기준 활성화)."""
    proj = _init_repo()
    _commit(proj, "a.txt", "base")
    sub = os.path.join(proj, "docs")
    os.makedirs(sub, exist_ok=True)
    _touch_session(proj, "OTHER", "their.txt")
    out = _run(CGATE, proj, "cd %s && git commit -m x" % sub, "MINE")
    assert _denied(out), "하위 디렉토리 cd 로 게이트가 무력화됨(우회 구멍)"


def test_cd_with_variable_stays_conservative():
    """cd $VAR 는 해석 불가 → 세션 cwd 기준 유지(보수적 deny)."""
    proj = _init_repo()
    _commit(proj, "a.txt", "base")
    _touch_session(proj, "OTHER", "their.txt")
    out = _run(CGATE, proj, "cd $TARGET && git commit -m x", "MINE")
    assert _denied(out), "변수 cd 인데 기준이 바뀜(보수적이어야 함)"


def test_no_cd_unchanged_behavior():
    """cd 없는 명령은 종전과 동일하게 세션 cwd 기준."""
    proj = _init_repo()
    _commit(proj, "a.txt", "base")
    _touch_session(proj, "OTHER", "their.txt")
    out = _run(CGATE, proj, "git commit -m x", "MINE")
    assert _denied(out), "cd 없는 main 커밋은 종전대로 차단돼야 함"


def test_repo_path_with_trailing_space_still_gated():
    """저장소 경로가 공백으로 끝나도 게이트가 살아 있어야 함.

    회귀 방지: `rev-parse --show-toplevel` 결과에 .strip() 를 쓰면 후행 공백이
    지워져 룰 파일을 못 찾고 게이트 3종이 조용히 비활성화된다(실제 프로젝트
    경로가 `…/LGIT-C6-Cobot ` 처럼 공백으로 끝나 발현).
    """
    base = tempfile.mkdtemp()
    proj = os.path.join(base, "repo trailing ")   # ← 후행 공백
    os.makedirs(proj)
    subprocess.run(["git", "init", "-q", "-b", "main", proj], check=True)
    _git(proj, "config", "user.email", "t@t")
    _git(proj, "config", "user.name", "t")
    _git(proj, "config", "commit.gpgsign", "false")
    d = os.path.join(proj, "docs", "claude_guideline", "git_workflow")
    os.makedirs(d)
    open(os.path.join(d, "git_workflow.md"), "w").close()
    _commit(proj, "a.txt", "base")
    _touch_session(proj, "OTHER", "their.txt")
    out = _run(CGATE, proj, "git commit -m x", "MINE")
    assert _denied(out), "후행 공백 경로에서 게이트가 비활성화됨(.strip 회귀)"


def test_nonexistent_cd_path_stays_conservative():
    """존재하지 않는 경로로 cd → 기준 유지(보수적)."""
    proj = _init_repo()
    _commit(proj, "a.txt", "base")
    _touch_session(proj, "OTHER", "their.txt")
    out = _run(CGATE, proj, "cd /nonexistent/xyz123 && git commit -m x", "MINE")
    assert _denied(out), "없는 경로 cd 인데 기준이 바뀜(보수적이어야 함)"


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
