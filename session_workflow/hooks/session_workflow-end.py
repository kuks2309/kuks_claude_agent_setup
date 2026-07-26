#!/usr/bin/env python3
"""SessionEnd 훅 — 미커밋 산출물 감지 → handoff 박제 + 레지스트리 해제(2차 방어).

자기 파일(active/<sid>.json·.touched)만 삭제 — 타 세션 불가침.
미커밋이 없으면 handoff 를 만들지 않는다(노이즈 최소). 항상 exit 0.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import session_state as ss  # noqa: E402


def uncommitted(top, paths):
    """touched 중 git 미커밋(작업트리/인덱스 변경·미추적) 파일 목록."""
    out = []
    if not paths:
        return out
    try:
        r = subprocess.run(
            ["git", "-C", top, "status", "--porcelain", "--"] + paths,
            capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return out
        for ln in r.stdout.splitlines():
            if len(ln) > 3:
                p = ln[3:].strip().strip('"')
                if " -> " in p:
                    p = p.split(" -> ", 1)[1]
                out.append(p)
    except (OSError, subprocess.SubprocessError):
        pass
    return out


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
    meta = ss.load_session(root, sid)
    touched = ss.read_touched(root, sid)

    if meta is not None and touched:
        top = ss.repo_top(cwd)
        if top:
            un = uncommitted(top, touched)
            if un:
                try:
                    os.makedirs(ss.handoff_dir(root), exist_ok=True)
                    hp = os.path.join(ss.handoff_dir(root), sid + ".md")
                    with open(hp, "w", encoding="utf-8") as f:
                        f.write(ss.format_handoff(
                            sid[:8], meta, ss.kst_now_str(), un, touched))
                except OSError:
                    pass

    for p in (ss.session_json(root, sid), ss.touched_path(root, sid)):
        try:
            os.remove(p)
        except OSError:
            pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
