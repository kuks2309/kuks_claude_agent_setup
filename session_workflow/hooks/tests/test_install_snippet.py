#!/usr/bin/env python3
"""install.sh 의 CLAUDE.md 등록 블록 갱신 시험 (표준 라이브러리만).

CLAUDE.md 는 모델이 매 세션 읽는 규칙 진입점이다. 마커가 있다고 등록을 건너뛰면
규칙 본문(session_workflow.md)만 갱신되고 진입점 문구는 옛 것으로 남아, 개정한
규칙이 이미 설치된 프로젝트에 닿지 않는다. 그래서 재설치는 블록을 다시 쓴다.

검증: 대상 블록만 최신 스니펫과 일치 / 다른 번들 마커 블록 보존 / 사용자 문단 보존
     / 마커가 없으면 새로 추가.

실행: python3 tests/test_install_snippet.py   (종료코드 0=전체 통과)
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLE = os.path.dirname(os.path.dirname(HERE))          # session_workflow/
INSTALL = os.path.join(BUNDLE, "install.sh")
SNIPPET = os.path.join(BUNDLE, "claude.snippet.md")
MARKER = "kuks_agent_setup:session_workflow"
PASS, FAIL = 0, 0


def ok(name):
    global PASS
    PASS += 1
    print("  PASS " + name)


def no(name, detail=""):
    global FAIL
    FAIL += 1
    print("  FAIL %s: %s" % (name, detail))


def make_target(claude_md_text=None):
    d = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", d], check=True)
    if claude_md_text is not None:
        with open(os.path.join(d, "CLAUDE.md"), "w", encoding="utf-8") as f:
            f.write(claude_md_text)
    return d


def run_install(target):
    return subprocess.run(["bash", INSTALL, target], capture_output=True, text=True)


def read(target):
    with open(os.path.join(target, "CLAUDE.md"), encoding="utf-8") as f:
        return f.read()


def snippet_body():
    with open(SNIPPET, encoding="utf-8") as f:
        return f.read().rstrip("\n").split("\n")[-1]      # 마커 다음 본문 줄


OLD = (
    "# 프로젝트\n\n"
    "<!-- %s -->\n"
    "- 옛 문구: 타 세션 상태는 경보 1줄로 제한한다.\n\n"
    "<!-- kuks_agent_setup:other -->\n"
    "- 다른 번들 줄\n\n"
    "사용자가 직접 쓴 문단\n"
) % MARKER


def main():
    print("== 마커가 있으면 블록을 최신 스니펫으로 다시 쓴다 ==")
    t = make_target(OLD)
    run_install(t)
    body = read(t)
    ok("refreshed") if snippet_body() in body else no("refreshed", "최신 스니펫 문구 없음")
    ok("old_text_gone") if "옛 문구" not in body else no("old_text_gone", "옛 문구 잔존")
    ok("other_bundle_kept") if "다른 번들 줄" in body else no("other_bundle_kept", "타 번들 블록 소실")
    ok("user_text_kept") if "사용자가 직접 쓴 문단" in body else no("user_text_kept", "사용자 문단 소실")
    ok("single_marker") if body.count(MARKER) == 1 else no("single_marker", "마커 %d개" % body.count(MARKER))
    shutil.rmtree(t, ignore_errors=True)

    print("== 마커가 없으면 새로 추가한다 ==")
    t = make_target("# 프로젝트\n\n사용자 문단\n")
    run_install(t)
    body = read(t)
    ok("appended") if MARKER in body and snippet_body() in body else no("appended", "등록 추가 안 됨")
    ok("append_keeps_user") if "사용자 문단" in body else no("append_keeps_user", "사용자 문단 소실")
    shutil.rmtree(t, ignore_errors=True)

    print("== 두 번 설치해도 중복되지 않는다(멱등) ==")
    t = make_target(OLD)
    run_install(t)
    run_install(t)
    body = read(t)
    ok("idempotent") if body.count(MARKER) == 1 else no("idempotent", "마커 %d개" % body.count(MARKER))
    shutil.rmtree(t, ignore_errors=True)

    print("\n-- 결과: PASS=%d FAIL=%d --" % (PASS, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
