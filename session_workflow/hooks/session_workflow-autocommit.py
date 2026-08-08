#!/usr/bin/env python3
"""SessionEnd 훅 — 이 세션 touched 중 미커밋 파일만 자동 commit·push·병합(결정적).

정책(사용자 결정 2026-07-31): 세션 종료 시 '해당 작업 관련 파일만' 커밋·푸쉬·머지.
- 대상 = 이 세션 touched ∩ git dirty. 단 (a) 다른 활성 세션도 touched 인 파일(혼입)과
  (b) 공유 가변 로그(EXCLUDE_PREFIXES)는 제외 — 남는 잔여는 handoff(end 훅) 소관.
- 커밋은 `git commit --only -- <경로>` (부분 커밋) — 공유 index 의 타 세션 staged
  내용을 쓸어가지 않는다.
- 공유 트리 세션: 로컬 커밋 후 임시 worktree 에서 origin/<브랜치> 최신 위 cherry-pick
  push(+fito 미러) — 타 세션의 미푸시 커밋은 실어가지 않는다.
- 세션 worktree(session/<id> 브랜치): 커밋만 수행 — push·병합은 자동 병합 훅 소관.
- 실패(커밋·충돌·push) 시 작업 내용 보존 + handoff/<sid>-autocommit.md 에 사유 기록.
계약: stdin JSON → 부수효과. 항상 exit 0. 네트워크 push 동반 — 설치 timeout 90s.
"""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import session_state as ss  # noqa: E402

EXCLUDE_PREFIXES = ("docs/user_instructions/",)
PUSH_RETRIES = 3


def git(args, cwd, timeout=15):
    """(rc, stdout, stderr) — stdout 은 원문 그대로(porcelain 선행 공백 보존)."""
    try:
        r = subprocess.run(["git"] + args, cwd=cwd, capture_output=True,
                           text=True, timeout=timeout)
        return r.returncode, (r.stdout or ""), (r.stderr or "").strip()
    except (OSError, subprocess.SubprocessError):
        return 1, "", "exec-fail"


def dirty_of(top, paths):
    """paths 중 git 이 미커밋(변경·미추적)으로 보고하는 파일."""
    if not paths:
        return []
    rc, out, _ = git(["status", "--porcelain", "--"] + paths, top)
    res = []
    if rc != 0:
        return res
    for ln in out.splitlines():
        if len(ln) > 3:
            p = ln[3:].strip().strip('"')
            if " -> " in p:
                p = p.split(" -> ", 1)[1]
            res.append(p)
    return res


def note(root, sid, text):
    try:
        os.makedirs(ss.handoff_dir(root), exist_ok=True)
        with open(os.path.join(ss.handoff_dir(root), sid + "-autocommit.md"),
                  "w", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        pass


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        return
    cwd = data.get("cwd") or os.getcwd()
    root = ss.state_root(cwd)
    if not root:
        return
    sid = data.get("session_id") or "unknown"
    short = sid[:8]
    touched = ss.read_touched(root, sid)
    top = ss.repo_top(cwd)
    if not touched or not top:
        return  # 산출물 없음 또는 비-git(커밋 개념 없음)

    others = set()
    for osid, _ in ss.list_other_active(root, sid):
        others.update(ss.read_touched(root, osid))
    files = [p for p in touched if p not in others
             and not any(p.startswith(x) for x in EXCLUDE_PREFIXES)]
    files = dirty_of(top, files)
    if not files:
        return

    meta = ss.load_session(root, sid) or {}
    purpose = ss.one_line(meta.get("purpose") or "(미등록)")
    msg = (f"chore(session): {purpose} — 세션 종료 자동 커밋 (sess:{short})\n\n"
           "Co-Authored-By: Claude <noreply@anthropic.com>")
    # 미추적 파일은 pathspec 매칭을 위해 add 필요 — 대상 경로만 add 하고
    # 커밋은 --only 라 타 세션 staged 는 커밋에 실리지 않는다.
    git(["add", "--"] + files, top, 15)
    rc, _, err = git(["commit", "--only", "-m", msg, "--"] + files, top, 30)
    if rc != 0:
        note(root, sid, f"# 자동 커밋 실패 · sess:{short}\n- 사유: {err[:300]}\n"
                        "- 대상(미커밋 보존): " + ", ".join(files) + "\n")
        return
    _, new, _ = git(["rev-parse", "HEAD"], top)
    new = new.strip()
    _, branch, _ = git(["rev-parse", "--abbrev-ref", "HEAD"], top)
    branch = branch.strip()
    if branch.startswith("session/"):
        return  # push·병합은 세션 브랜치 자동 병합 훅 소관

    if git(["rev-parse", "--verify", "-q", f"origin/{branch}"], top)[0] != 0:
        git(["fetch", "origin"], top, 20)
        if git(["rev-parse", "--verify", "-q", f"origin/{branch}"], top)[0] != 0:
            note(root, sid, f"# 자동 커밋 push 생략 · sess:{short}\n"
                            f"- 로컬 커밋 {new[:8]} 생성됨 — origin/{branch} 부재\n")
            return

    tmp = os.path.join(tempfile.mkdtemp(prefix="sw-ac-"), "wt")
    ok = False
    conflict = False
    if git(["worktree", "add", "--detach", tmp, f"origin/{branch}"], top, 20)[0] == 0:
        for _ in range(PUSH_RETRIES):
            git(["fetch", "origin"], top, 20)
            git(["reset", "--hard", f"origin/{branch}"], tmp, 15)
            if git(["cherry-pick", "-x", new], tmp, 30)[0] != 0:
                git(["cherry-pick", "--abort"], tmp)
                conflict = True
                break
            if git(["push", "origin", f"HEAD:{branch}"], tmp, 30)[0] == 0:
                ok = True
                _, remotes, _ = git(["remote"], top)
                if "fito" in remotes.split():
                    git(["push", "fito", f"HEAD:{branch}"], tmp, 30)
                break
        git(["worktree", "remove", "--force", tmp], top)
    if not ok:
        why = "origin 과 같은 줄 충돌" if conflict else "push 반복 실패"
        note(root, sid, f"# 자동 커밋 push 보류 · sess:{short}\n"
                        f"- 로컬 커밋 {new[:8]} 은 생성됨({', '.join(files)})\n"
                        f"- 사유: {why} — 수동 반영 필요\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
