#!/usr/bin/env python3
"""SessionStart 훅 — 세션 레지스트리 등록 + 활성 세션·handoff·목적 게이트 예고 주입.

부수 정리: handoff 14일 경과분 삭제. 잔류(stale) active 항목은 삭제하지 않고
표시만(살아있는 세션 오판 방지 — touched 정보 보존). 항상 exit 0.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import session_state as ss  # noqa: E402

HANDOFF_SHOW = 5
TOUCHED_SHOW = 10


def gc_handoffs(root):
    hd = ss.handoff_dir(root)
    cutoff = time.time() - ss.HANDOFF_KEEP_DAYS * 86400
    try:
        names = os.listdir(hd)
    except OSError:
        return
    for n in names:
        p = os.path.join(hd, n)
        try:
            if os.path.getmtime(p) < cutoff:
                os.remove(p)
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

    meta = ss.ensure_session(root, sid)  # resume 시 기존 목적 보존
    try:
        ss.save_session(root, sid, meta)
    except OSError:
        return
    gc_handoffs(root)

    lines = ["[SESSION-WORKFLOW — 세션 시작]"]

    others = ss.list_other_active(root, sid)
    if others:
        lines.append("활성 세션:")
        for osid, om in others:
            purpose = ss.one_line(om.get("purpose") or "(미등록)")
            stale = ss.is_stale(om)
            mark = " ⚠ 잔류 의심(비정상 종료 가능)" if stale else ""
            lines.append(f"- {osid[:8]} · 목적: {purpose} · 최근 활동: "
                         f"{om.get('last_seen', '?')}{mark}")
            if stale:
                t = ss.read_touched(root, osid)
                lines += [f"    - {p}" for p in t[:TOUCHED_SHOW]]
                if len(t) > TOUCHED_SHOW:
                    lines.append(f"    - …외 {len(t) - TOUCHED_SHOW}개")
    else:
        lines.append("다른 활성 세션 없음.")

    behind = ss.behind_origin_main(cwd)
    if behind:
        lines.append(f"⚠ 공유 트리가 원격(origin) 대비 {behind}커밋 낡음(stale) — "
                     "광역 수정·재배치·삭제 작업 전에 최신화(pull) 또는 세션 worktree "
                     "사용을 사용자와 1줄 확인하세요.")

    hd = ss.handoff_dir(root)
    try:
        hs = sorted((os.path.join(hd, n) for n in os.listdir(hd)
                     if n.endswith(".md")),
                    key=os.path.getmtime, reverse=True)
    except OSError:
        hs = []
    if hs:
        lines.append(f"대기 인수인계(handoff) {len(hs)}건:")
        for p in hs[:HANDOFF_SHOW]:
            purpose, count = ss.parse_handoff_summary(p)
            lines.append(f"- {os.path.basename(p)} · 목적: {purpose} · "
                         f"미커밋 {count}개 → 전문: {p}")
        lines.append("픽업은 사용자 동의 후 — 처리 완료 시 해당 handoff 파일을 삭제하세요.")

    if not meta.get("purpose"):
        lines.append("본 세션 목적 미선언 상태입니다. 첫 응답에서 사용자에게 세션 목적을 "
                     "묻고 `목적: …` 형식 입력을 안내하세요.")
    print("\n".join(lines))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
