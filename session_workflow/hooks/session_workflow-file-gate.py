#!/usr/bin/env python3
"""PreToolUse 훅 — 다른 활성 세션이 수정 중인 파일의 Write/Edit 를 실행 전 차단.

충돌 '경보'(gate 훅)를 수정 시점 '차단'으로 승격: 대상 파일이 잔류 아닌 다른 활성
세션의 touched 에 있으면 도구 호출을 거부한다. 사용자 승인 후 자기 allow 목록
(active/<sid>.allow)에 경로를 추가하면 통과(명시 override — 자기 파일만 쓰기 원칙 유지).
이미 양쪽이 수정한 파일(혼입 기존 상태)·잔류 의심 세션 파일은 차단하지 않는다(경보 소관).
계약(Claude Code PreToolUse): exit 2 + stderr → 도구 차단·모델 피드백. 그 외 exit 0.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import session_state as ss  # noqa: E402

GATE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        return 0
    if data.get("tool_name", "") not in GATE_TOOLS:
        return 0
    ti = data.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("notebook_path")
    if not path:
        return 0
    cwd = data.get("cwd") or os.getcwd()
    root = ss.state_root(cwd)
    if not root:
        return 0
    base = ss.repo_top(cwd) or cwd
    rel = os.path.relpath(os.path.abspath(path), base)
    if rel.startswith(".."):
        return 0
    sid = data.get("session_id") or "unknown"
    if rel in set(ss.read_allow(root, sid)):
        return 0  # 사용자 승인된 override
    if rel in set(ss.read_touched(root, sid)):
        return 0  # 내 파일(혼입 파일 포함)은 통과 — 혼입 안내는 경보 소관
    for osid, ometa in ss.list_other_active(root, sid):
        if ss.is_stale(ometa):
            continue  # 잔류 의심 세션은 차단하지 않음(시작 주입 경고 소관)
        if rel in set(ss.read_touched(root, osid)):
            purpose = ss.one_line(ometa.get("purpose") or "(미등록)")
            sys.stderr.write(
                f"[SESSION-WORKFLOW — 파일 차단] `{rel}` 은 세션 {osid[:8]}"
                f"(목적: {purpose})가 수정 중입니다. 진행하려면 사용자에게 1줄로 "
                "확인받고, 승인 시에만 아래 allow 목록에 경로를 추가한 뒤 재시도하세요"
                f"(미승인 시 범위 조정): {ss.allow_path(root, sid)}\n")
            return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except Exception:
        sys.exit(0)
