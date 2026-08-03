#!/usr/bin/env python3
"""session_workflow-state-guard.py 회귀 시험.

훅을 실제 서브프로세스로 띄우고 stdin JSON 을 먹여 stdout 계약(ask / 무출력)을 검증한다.
활성화 게이트를 만족시키려고 임시 프로젝트 루트(규칙 파일만 있는 디렉터리)를 만들어 cwd 로 준다
— 번들 저장소 구조에 의존하지 않는다(self-contained).

케이스 출처: 최초 15건은 도입 세션(Big-AMR 설치본)에서 작성. 2026-08-03 독립 검증에서
드러난 결함 2건(빠른 탈출이 save_session·ensure_session 신호를 죽임 · handoff 예외가
따옴표에서 깨짐)의 회귀 케이스와 추가 우회 시도·견고성 항목을 덧붙였다.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.join(os.path.dirname(HERE), "session_workflow-state-guard.py")
RULE_MD = "docs/claude_guideline/session_workflow/session_workflow.md"

ASK, PASS = "ask", "pass"

CASES = [
    # (기대, 라벨, 명령, tool_name)
    (ASK, "실제 위반 재현 — save_session 직접 호출",
     'python3 -c "import session_state as ss; ss.save_session(root, sid, meta)"', "Bash"),
    (ASK, "회귀: 모듈명 없이 save_session 만 (빠른 탈출 결함)",
     'python3 -c "import s as x; x.save_session(1,2,3)"', "Bash"),
    (ASK, "회귀: ensure_session 만",
     'python3 -c "import s as x; x.ensure_session(1,2)"', "Bash"),
    (ASK, "상태 파일 rm (handoff 아님)",
     "rm .git/session_workflow/active/8fde06da.json", "Bash"),
    (ASK, "리다이렉션 쓰기",
     'echo "{}" > .git/session_workflow/active/abc.json', "Bash"),
    (ASK, "append 리다이렉션",
     "echo x >> .git/session_workflow/active/abc.touched", "Bash"),
    (ASK, "tee 파이프 쓰기",
     'echo "{}" | tee .git/session_workflow/active/abc.json', "Bash"),
    (ASK, "heredoc 으로 상태 파일 작성",
     "cat > .git/session_workflow/active/abc.json <<EOF\n{}\nEOF", "Bash"),
    (ASK, "mv 로 상태 파일 교체",
     "mv /tmp/x.json .git/session_workflow/active/abc.json", "Bash"),
    (ASK, "truncate 로 비우기",
     "truncate -s 0 .git/session_workflow/active/abc.touched", "Bash"),
    (ASK, "상태 모듈 소스 sed -i",
     "sed -i s/a/b/ docs/claude_guideline/session_workflow/hooks/session_state.py", "Bash"),
    (ASK, "복합 명령 중 한 세그먼트가 쓰기",
     'cd /tmp && python3 -c "import session_state; session_state.save_session(1,2,3)"', "Bash"),
    (ASK, "cp 로 상태 파일 덮어쓰기",
     "cp /tmp/x.json .git/session_workflow/active/abc.json", "Bash"),
    (ASK, "handoff 디렉터리지만 .md 아닌 파일 삭제",
     "rm .git/session_workflow/handoff/abc.json", "Bash"),

    (PASS, "cat 읽기",
     "cat .git/session_workflow/active/8fde06da.touched", "Bash"),
    (PASS, "glob grep 읽기",
     'grep -l "INDEX.md" .git/session_workflow/active/*.touched', "Bash"),
    (PASS, "§0 유일 예외 — handoff 삭제",
     "rm .git/session_workflow/handoff/8fde06da.md", "Bash"),
    (PASS, "§0 예외 — 플래그 붙은 handoff 삭제",
     "rm -f .git/session_workflow/handoff/8fde06da.md", "Bash"),
    (PASS, "회귀: §0 예외 — 큰따옴표 경로",
     'rm -f "/abs/repo/.git/session_workflow/handoff/8fde06da.md"', "Bash"),
    (PASS, "회귀: §0 예외 — 작은따옴표 경로",
     "rm -f '/abs/repo/.git/session_workflow/handoff/8fde06da.md'", "Bash"),
    (PASS, "override 주석",
     'python3 -c "import session_state; session_state.save_session(1,2,3)"  # sw:allow-state-write',
     "Bash"),
    (PASS, "훅 디렉터리 ls — 상태 저장소 아님",
     "ls -la docs/claude_guideline/session_workflow/hooks/", "Bash"),
    (PASS, "상태 저장소 find 조회",
     'find "$(git rev-parse --absolute-git-dir)/session_workflow" -type f', "Bash"),
    (PASS, "번들 재설치(경로에 번들명 포함)",
     "cd /x/session_workflow && ./install.sh /y", "Bash"),
    (PASS, "무관한 명령",
     "git status --short --branch", "Bash"),
    (PASS, "Bash 아닌 툴",
     "rm .git/session_workflow/active/abc.json", "Write"),
    (PASS, "세션 무관 문자열만 포함",
     'echo "session_id 는 훅이 넣는다"', "Bash"),
]


def run(cmd, tool_name, cwd):
    payload = json.dumps({
        "tool_name": tool_name,
        "tool_input": {"command": cmd},
        "cwd": cwd,
        "session_id": "test-session",
    })
    out = subprocess.run([sys.executable, GUARD], input=payload,
                         capture_output=True, text=True, timeout=10)
    if out.returncode != 0:
        return "error:rc=%d:%s" % (out.returncode, out.stderr.strip()[:200])
    if not out.stdout.strip():
        return PASS
    try:
        d = json.loads(out.stdout)
    except (json.JSONDecodeError, ValueError):
        return "error:비-JSON 출력"
    hso = d.get("hookSpecificOutput") or {}
    if hso.get("hookEventName") != "PreToolUse":
        return "error:hookEventName 누락"
    return hso.get("permissionDecision") or "error:decision 누락"


def main():
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, os.path.dirname(RULE_MD)))
    with open(os.path.join(root, RULE_MD), "w", encoding="utf-8") as f:
        f.write("rule\n")
    fails = 0
    try:
        for expect, label, cmd, tool in CASES:
            got = run(cmd, tool, root)
            ok = (got == expect)
            fails += (not ok)
            print("%s  %-8s (기대 %-4s) %s" % ("PASS" if ok else "FAIL", got, expect, label))

        # 활성화 게이트 — 규칙 파일이 없는 프로젝트에는 간섭하지 않는다
        bare = tempfile.mkdtemp()
        got = run("rm .git/session_workflow/active/abc.json", "Bash", bare)
        ok = (got == PASS)
        fails += (not ok)
        print("%s  %-8s (기대 %-4s) %s" % ("PASS" if ok else "FAIL", got, PASS,
                                          "번들 미설치 프로젝트 — 무간섭"))
        shutil.rmtree(bare, ignore_errors=True)

        # 견고성 — 깨진 입력에 죽지 않는다(훅이 죽으면 Bash 도구 자체가 막힐 수 있다)
        for label, raw in [("빈 stdin", ""), ("비-JSON", "not json"),
                           ("tool_input 없음", '{"tool_name":"Bash"}')]:
            r = subprocess.run([sys.executable, GUARD], input=raw,
                               capture_output=True, text=True, timeout=10)
            ok = (r.returncode == 0 and not r.stdout.strip())
            fails += (not ok)
            print("%s  %-8s (기대 %-4s) 견고성: %s"
                  % ("PASS" if ok else "FAIL", "rc=%d" % r.returncode, PASS, label))
    finally:
        shutil.rmtree(root, ignore_errors=True)

    total = len(CASES) + 4
    print("\n%d/%d 통과" % (total - fails, total))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
