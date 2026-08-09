#!/usr/bin/env python3
"""coding 번들 §6 게이트 — 코드를 고친 턴에 함수표 갱신을 마주치게 한다.

담당 분담: §2(선독)는 `coding-inventory-gate.py`(PreToolUse)가 수정 직전에 막고,
§6(후속 갱신)은 본 훅이 Stop 시점에 확인한다. `⟦CI:index-fresh⟧` 는 커밋 시점
검사라 **커밋하지 않는 턴에서는 표 갱신이 강제되지 않는다** — 그 구간이 비어 있으면
표 갱신이 "코드 다 끝내고 나중에"로 미뤄지고 그대로 남지 않는다.

판정은 단순하게 둔다(a안): 이번 턴에 고친 코드 파일의 **커버 표를 같은 턴에 고쳤는가**.
인터페이스가 안 바뀐 내부 로직 수정은 §6 상 갱신 불요인데 본 훅은 그것을 구분하지
않으므로, 메시지에 예외를 명시하고 **판단은 모델에게 맡긴다**(대면만 강제). 시그니처
변화를 파싱해 정확도를 올리는 방식은 언어별 파서를 들이는 만큼 실패 지점이 늘어난다.

표 탐색은 `coding-inventory-gate.py` 의 `covering_tables()` 를 그대로 재사용한다 —
읽기 쪽이 요구한 표와 쓰기 쪽이 검사하는 표가 어긋나지 않게 하기 위해서다.

계약(Claude Code Stop): stdin JSON → stderr + exit 2 = 종료 차단(모델이 점검·보완 후
다시 마침), 그 외 exit 0. `stop_hook_active` 로 검토는 최대 1패스.
"""
import importlib.util
import json
import os
import sys

MAX_SHOWN = 5          # 경보에 나열할 파일 수 상한
EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")


def load_gate():
    """같은 폴더의 게이트 모듈 — 표 탐색 로직을 1곳만 유지한다."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "coding-inventory-gate.py")
    if not os.path.isfile(path):
        return None
    try:
        spec = importlib.util.spec_from_file_location("coding_gate", path)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def turn_edits(transcript_path):
    """이번 턴(마지막 실제 사용자 텍스트 이후)의 Edit/Write 대상 경로.

    거부·실패한 호출(tool_result 의 is_error)은 제외한다 — PreToolUse 에 막힌 Write 는
    transcript 에 tool_use 로 남지만 파일을 바꾸지 않았으므로 세면 오탐이 된다."""
    try:
        with open(transcript_path, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return []
    parsed, last_user = [], -1
    for i, line in enumerate(lines):
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            parsed.append(None)
            continue
        parsed.append(obj)
        if obj.get("type") == "user" or obj.get("role") == "user":
            content = (obj.get("message") or obj).get("content", "")
            if isinstance(content, str) and content.strip():
                last_user = i
            elif isinstance(content, list):
                has_text = any(isinstance(c, dict) and c.get("type") == "text"
                               for c in content)
                has_result = any(isinstance(c, dict) and c.get("type") == "tool_result"
                                 for c in content)
                if has_text and not has_result:
                    last_user = i
    uses, bad = [], set()
    for obj in parsed[last_user + 1:]:
        if not obj:
            continue
        content = (obj.get("message") or obj).get("content")
        if not isinstance(content, list):
            continue
        for c in content:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use":
                uses.append(c)
            elif c.get("type") == "tool_result" and c.get("is_error"):
                bad.add(c.get("tool_use_id"))
    out = []
    for u in uses:
        if u.get("name") not in EDIT_TOOLS or u.get("id") in bad:
            continue
        p = (u.get("input") or {}).get("file_path") \
            or (u.get("input") or {}).get("notebook_path")
        if p:
            out.append(p)
    return out


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if data.get("stop_hook_active"):
        return 0                       # 검토 루프 1패스 제한

    cwd = data.get("cwd") or os.getcwd()
    g = load_gate()
    if g is None or not g.rule_active(cwd):
        return 0

    edited = turn_edits(data.get("transcript_path", ""))
    if not edited:
        return 0

    base = g.repo_top(cwd) or os.path.realpath(cwd)
    rels = [r for r in (g.rel_to(base, p) for p in edited) if r]
    touched = set(rels)

    stale = []
    for rel in rels:
        if os.path.splitext(rel)[1].lower() not in g.CODE_EXT:
            continue                   # 코드 파일만 대상
        tables = g.covering_tables(base, rel)
        if not tables:
            continue                   # 표 부재는 PreToolUse 게이트 소관 — 이중 경보 금지
        if any(t in touched for t in tables):
            continue                   # 같은 턴에 표를 고쳤다
        stale.append((rel, tables))

    if not stale:
        return 0

    listed = "\n".join(
        f"  · {rel}\n      → {tables[0]}" + (f" 외 {len(tables) - 1}건" if len(tables) > 1 else "")
        for rel, tables in stale[:MAX_SHOWN])
    more = f"\n  … 외 {len(stale) - MAX_SHOWN}건" if len(stale) > MAX_SHOWN else ""
    sys.stderr.write(
        "[CODING — 표 갱신 점검] 이번 턴에 코드를 고쳤는데 해당 함수표를 갱신하지 "
        "않았습니다:\n"
        f"{listed}{more}\n"
        "coding.md §6 은 함수·전역변수의 **추가·삭제·시그니처 변경** 시 같은 작업 "
        "단위에서 표를 갱신하도록 요구합니다 — 미루면 다음 작업이 낡은 표를 읽습니다. "
        "해당하면 지금 표를 갱신하고 마치십시오.\n"
        "인터페이스가 그대로인 **내부 로직**만 바꿨다면 갱신 불요이므로 그대로 마쳐도 "
        "됩니다(표는 인터페이스 수준 현황만 담습니다).\n")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except Exception:
        sys.exit(0)                    # 훅 결함이 턴 종료를 막지 않는다
