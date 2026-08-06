#!/usr/bin/env python3
"""비정상 종료 세션의 handoff 복구 시험 (session_workflow-start.py).

배경: handoff 는 SessionEnd 훅에서만 만들어지는데 그 훅은 **정상 종료에서만** 돈다.
크래시·강제 종료된 세션의 미커밋 산출물은 아무 기록도 남지 않아 '누구 것인지 모르는
파일'로 공유 트리에 남는다(실제: drawio 번들 15파일이 소유 세션 종료 후 미추적 방치,
handoff 폴더는 비어 있었음). start 훅이 그 공백을 메우는지 검증한다.

실행: python3 tests/test_stale_handoff.py   (종료코드 0=전체 통과)
표준 라이브러리만 사용.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS = os.path.dirname(HERE)
sys.path.insert(0, HOOKS)
import session_state as ss  # noqa: E402

START = os.path.join(HOOKS, "session_workflow-start.py")
END = os.path.join(HOOKS, "session_workflow-end.py")
PASS, FAIL = 0, 0

DEAD = "dead1111-1111-1111-1111-111111111111"
LIVE = "live2222-2222-2222-2222-222222222222"
ME = "me333333-3333-3333-3333-333333333333"


def ok(name):
    global PASS
    PASS += 1
    print("  PASS " + name)


def no(name, detail=""):
    global FAIL
    FAIL += 1
    print("  FAIL %s: %s" % (name, detail))


def git(repo, *args):
    return subprocess.run(["git", "-C", repo] + list(args),
                          capture_output=True, text=True)


def make_repo():
    repo = tempfile.mkdtemp()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    git(repo, "config", "commit.gpgsign", "false")
    d = os.path.join(repo, "docs", "claude_guideline", "session_workflow")
    os.makedirs(d)
    open(os.path.join(d, "session_workflow.md"), "w").close()   # 룰 활성 게이트
    with open(os.path.join(repo, "base.txt"), "w") as f:
        f.write("base\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "init")
    return repo


def register(repo, sid, purpose, hours_ago, touched_rel):
    """세션을 레지스트리에 등록. hours_ago 로 잔류 여부를 조작."""
    root = ss.state_root(repo)
    os.makedirs(ss.active_dir(root), exist_ok=True)
    seen = (ss.kst_now() - __import__("datetime").timedelta(hours=hours_ago))
    meta = {"purpose": purpose,
            "started_at": seen.strftime("%Y-%m-%d %H:%M"),
            "last_seen": seen.strftime("%Y-%m-%d %H:%M"),
            "alerted": []}
    with open(ss.session_json(root, sid), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    if touched_rel:
        with open(ss.touched_path(root, sid), "w", encoding="utf-8") as f:
            f.write("\n".join(touched_rel) + "\n")
    return root


def run_hook(hook, repo, sid):
    payload = json.dumps({"session_id": sid, "cwd": repo, "source": "startup"})
    return subprocess.run([sys.executable, hook], input=payload,
                          capture_output=True, text=True)


def handoff_exists(root, sid):
    return os.path.isfile(os.path.join(ss.handoff_dir(root), sid + ".md"))


def main():
    print("== 비정상 종료 세션: 미커밋 있으면 handoff 복구 ==")
    repo = make_repo()
    with open(os.path.join(repo, "orphan.txt"), "w") as f:   # 미추적 산출물
        f.write("죽은 세션의 작업\n")
    root = register(repo, DEAD, "죽은 세션", hours_ago=48, touched_rel=["orphan.txt"])
    register(repo, ME, "내 세션", hours_ago=0, touched_rel=[])
    run_hook(START, repo, ME)
    if handoff_exists(root, DEAD):
        ok("stale_with_uncommitted_recovered")
        body = open(os.path.join(ss.handoff_dir(root), DEAD + ".md"), encoding="utf-8").read()
        ok("handoff_lists_file") if "orphan.txt" in body else no("handoff_lists_file", body[:80])
        ok("handoff_marks_abnormal") if "비정상 종료 추정" in body else no("handoff_marks_abnormal")
        ok("handoff_warns_before_pickup") if "픽업 전에" in body \
            else no("handoff_warns_before_pickup", "살아있을 수 있다는 경고 없음")
    else:
        no("stale_with_uncommitted_recovered", "handoff 미생성")
        no("handoff_lists_file", "선행 실패")
        no("handoff_marks_abnormal", "선행 실패")
        no("handoff_warns_before_pickup", "선행 실패")

    print("== 살아있는 세션은 복구 대상 아님 ==")
    repo = make_repo()
    with open(os.path.join(repo, "wip.txt"), "w") as f:
        f.write("작업 중\n")
    root = register(repo, LIVE, "살아있는 세션", hours_ago=0, touched_rel=["wip.txt"])
    register(repo, ME, "내 세션", hours_ago=0, touched_rel=[])
    run_hook(START, repo, ME)
    ok("live_session_untouched") if not handoff_exists(root, LIVE) \
        else no("live_session_untouched", "살아있는 세션에 handoff 생성됨")

    print("== 미커밋이 없으면 handoff 없음(노이즈 최소) ==")
    repo = make_repo()
    root = register(repo, DEAD, "죽었지만 다 커밋함", hours_ago=48, touched_rel=["base.txt"])
    register(repo, ME, "내 세션", hours_ago=0, touched_rel=[])
    run_hook(START, repo, ME)
    ok("clean_stale_no_handoff") if not handoff_exists(root, DEAD) \
        else no("clean_stale_no_handoff", "미커밋 없는데 handoff 생성")

    print("== 기존 handoff 는 덮어쓰지 않음(픽업 중 보호) ==")
    repo = make_repo()
    with open(os.path.join(repo, "orphan.txt"), "w") as f:
        f.write("작업\n")
    root = register(repo, DEAD, "죽은 세션", hours_ago=48, touched_rel=["orphan.txt"])
    register(repo, ME, "내 세션", hours_ago=0, touched_rel=[])
    os.makedirs(ss.handoff_dir(root), exist_ok=True)
    hp = os.path.join(ss.handoff_dir(root), DEAD + ".md")
    with open(hp, "w", encoding="utf-8") as f:
        f.write("픽업 중 — 건드리지 말 것\n")
    run_hook(START, repo, ME)
    ok("existing_handoff_preserved") if "픽업 중" in open(hp, encoding="utf-8").read() \
        else no("existing_handoff_preserved", "덮어써짐")

    print("== 회귀: 정상 종료(end 훅)는 그대로 handoff 를 남긴다 ==")
    repo = make_repo()
    with open(os.path.join(repo, "mywork.txt"), "w") as f:
        f.write("내 작업\n")
    root = register(repo, ME, "정상 종료 세션", hours_ago=0, touched_rel=["mywork.txt"])
    run_hook(END, repo, ME)
    ok("graceful_end_handoff") if handoff_exists(root, ME) \
        else no("graceful_end_handoff", "정상 종료인데 handoff 없음")
    ok("graceful_end_deregistered") if not os.path.isfile(ss.session_json(root, ME)) \
        else no("graceful_end_deregistered", "레지스트리 미해제")

    print("\n-- 결과: PASS=%d FAIL=%d --" % (PASS, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
