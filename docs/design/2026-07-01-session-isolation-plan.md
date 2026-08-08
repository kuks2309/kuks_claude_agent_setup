# 세션 격리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 다중 동시 세션에서 지시 기록·커밋이 세션 간 누수되지 않도록 `user_instruction`·`git_workflow` 번들 hook 을 세션 격리형으로 전환한다.

**Architecture:** (A) UserPromptSubmit hook 이 프롬프트를 `docs/user_instructions/sessions/{session_id}.md` 에 결정적 기록하고 자기 세션 기록만 주입, SessionEnd hook 이 자기 파일만 `user_instructions.md` 로 flock 병합. (B) 신규 PreToolUse(Bash) hook 이 blanket `git add`/`commit -a` 를 exit 2 로 차단하고 명시 경로 staging 은 통과.

**Tech Stack:** Python 3 (표준 라이브러리만: `json`, `os`, `sys`, `fcntl`, `datetime`, `re`, `shlex`, `subprocess`), Bash(install.sh), Claude Code hooks(UserPromptSubmit/SessionEnd/PreToolUse).

## Global Constraints

- **Self-contained**: OMC 등 외부 도구 비의존. 표준 라이브러리 외 import 금지.
- **Graceful**: 규칙 파일 부재·비-git·JSON 파싱 실패 시 조용히 no-op(hook 은 항상 exit 0, 단 PreToolUse 차단만 exit 2).
- **세션 격리 불변식**: 어떤 세션도 다른 세션의 `sessions/{other_id}.md` 를 읽거나 수정하지 않는다(병합 GC 예외: age>7d orphan 만).
- **KST 시각**: `datetime.now(timezone(timedelta(hours=9)))`, 형식 `YYYY-MM-DD HH:MM (KST)`.
- **엔트리 형식(단일 SSOT)**: 헤더 `## {YYYY-MM-DD HH:MM} (KST) · sess:{short8}`, 본문 `> "{원문}"`, 구분 `---`. 제목·요약 슬롯 없음.
- **주입 상한**: 자기 세션 최근 **5개** 엔트리만 주입, 초과 시 "…(이전 생략)".
- **커밋 규율(구현 시)**: 파일별 명시 승인 후 1 커밋. `git add -A`/`.` 금지(본 작업이 만드는 규칙을 작업 중에도 준수). Co-Authored-By 트레일러 포함.

---

## File Structure

**user_instruction 번들**
- `user_instruction/hooks/user_instruction-reminder.py` — (재작성) UserPromptSubmit: 결정적 기록 + 자기세션 주입
- `user_instruction/hooks/user_instruction-merge.py` — (신규) SessionEnd: 자기 파일 병합 + orphan GC
- `user_instruction/hooks/session_record.py` — (신규) 공유 로직 모듈: 엔트리 형식·파싱·경로 helper (두 hook 이 import)
- `user_instruction/hooks/tests/test_record.py` — (신규) reminder hook 테스트
- `user_instruction/hooks/tests/test_merge.py` — (신규) merge hook 테스트
- `user_instruction/recording.md` — (수정) sessions/ 구조·hook 기록·read-as-task 금지 규칙
- `user_instruction/claude.snippet.md` — (수정) 등록 문구
- `user_instruction/install.sh` — (수정) SessionEnd 훅 등록 + `.gitignore` 에 `sessions/` 추가

**git_workflow 번들**
- `git_workflow/hooks/git_workflow-staging-guard.py` — (신규) PreToolUse(Bash): blanket-add 차단
- `git_workflow/hooks/tests/test_staging_guard.py` — (신규) 차단/통과 테스트
- `git_workflow/install.sh` — (수정) PreToolUse 훅 등록

> `hooks/session_record.py` 로 엔트리 형식·파싱을 한 곳에 두어 reminder(쓰기)와 merge(읽기)가 형식 불일치로 깨지지 않게 한다(DRY).

---

## Task 1: session_record.py — 공유 기록 로직 모듈

**Files:**
- Create: `user_instruction/hooks/session_record.py`
- Test: `user_instruction/hooks/tests/test_record.py` (일부)

**Interfaces:**
- Consumes: 없음(표준 라이브러리만)
- Produces:
  - `kst_now_str() -> str` — `"YYYY-MM-DD HH:MM"` (KST)
  - `sessions_dir(cwd: str) -> str` — `{cwd}/docs/user_instructions/sessions`
  - `log_path(cwd: str) -> str` — `{cwd}/docs/user_instructions/user_instructions.md`
  - `rule_active(cwd: str) -> bool` — `docs/claude_guideline/user_instruction/recording.md` 존재 여부
  - `format_entry(ts: str, short: str, prompt: str) -> str` — 엔트리 블록 문자열(끝에 `\n`)
  - `parse_entries(text: str) -> list[tuple[str, str]]` — `[(ts_key, block), ...]` (ts_key = `"YYYY-MM-DD HH:MM"`)
  - `HEADER_RE` — `re.compile(r"^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \(KST\) · sess:")`

- [ ] **Step 1: Write the failing test**

Create `user_instruction/hooks/tests/test_record.py`:

```python
#!/usr/bin/env python3
"""session_record.py 단위 테스트 (표준 라이브러리만, 프레임워크 비의존)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # hooks/ 를 import 경로에
import session_record as sr  # noqa: E402


def test_format_and_parse_roundtrip():
    block = sr.format_entry("2026-07-01 14:30", "abcd1234", 'do "X" now')
    assert "## 2026-07-01 14:30 (KST) · sess:abcd1234" in block
    assert '> "do \\"X\\" now"' in block or '> "do "X" now"' in block
    entries = sr.parse_entries(block)
    assert len(entries) == 1
    assert entries[0][0] == "2026-07-01 14:30"


def test_parse_multiple_newest_first_preserved():
    text = (
        sr.format_entry("2026-07-01 15:00", "aaaa1111", "second")
        + sr.format_entry("2026-07-01 14:00", "aaaa1111", "first")
    )
    entries = sr.parse_entries(text)
    assert [e[0] for e in entries] == ["2026-07-01 15:00", "2026-07-01 14:00"]


def test_parse_ignores_nonentry_noise():
    text = "leading junk\n\n" + sr.format_entry("2026-07-01 14:00", "b2", "x")
    entries = sr.parse_entries(text)
    assert len(entries) == 1


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
    sys.exit(1 if fails else 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 user_instruction/hooks/tests/test_record.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'session_record'`

- [ ] **Step 3: Write session_record.py**

Create `user_instruction/hooks/session_record.py`:

```python
#!/usr/bin/env python3
"""user_instruction 세션 기록 공유 로직 — 엔트리 형식·파싱·경로 helper.

reminder(쓰기)와 merge(읽기)가 동일 형식을 쓰도록 형식/파싱을 한 곳에 둔다(DRY).
표준 라이브러리만 사용(self-contained).
"""
import os
import re
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
HEADER_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \(KST\) · sess:")


def kst_now_str():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M")


def sessions_dir(cwd):
    return os.path.join(cwd, "docs", "user_instructions", "sessions")


def log_path(cwd):
    return os.path.join(cwd, "docs", "user_instructions", "user_instructions.md")


def rule_active(cwd):
    rule = os.path.join(cwd, "docs", "claude_guideline",
                        "user_instruction", "recording.md")
    return os.path.isfile(rule)


def format_entry(ts, short, prompt):
    """엔트리 블록(끝에 개행 포함). 원문은 큰따옴표만 이스케이프해 인용 보존."""
    safe = prompt.replace("\n", " ").strip()
    return (
        f"## {ts} (KST) · sess:{short}\n\n"
        f"> \"{safe}\"\n\n"
        f"---\n\n"
    )


def parse_entries(text):
    """텍스트에서 (ts_key, block) 목록을 문서 순서대로 추출. 헤더 없는 노이즈는 무시."""
    lines = text.splitlines(keepends=True)
    entries = []
    cur_ts = None
    cur = []
    for ln in lines:
        m = HEADER_RE.match(ln)
        if m:
            if cur_ts is not None:
                entries.append((cur_ts, "".join(cur)))
            cur_ts = m.group(1)
            cur = [ln]
        elif cur_ts is not None:
            cur.append(ln)
    if cur_ts is not None:
        entries.append((cur_ts, "".join(cur)))
    return entries
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 user_instruction/hooks/tests/test_record.py`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add user_instruction/hooks/session_record.py user_instruction/hooks/tests/test_record.py
git commit -m "feat(user_instruction): add session_record shared entry format/parse module

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: user_instruction-reminder.py — 결정적 기록 + 자기세션 주입

**Files:**
- Modify(재작성): `user_instruction/hooks/user_instruction-reminder.py`
- Test: `user_instruction/hooks/tests/test_record.py` (추가)

**Interfaces:**
- Consumes: `session_record` (Task 1) — `kst_now_str`, `sessions_dir`, `rule_active`, `format_entry`, `parse_entries`
- Produces: UserPromptSubmit hook. 부수효과: `sessions/{session_id}.md` prepend. stdout: 자기 세션 최근 5개 주입.

- [ ] **Step 1: Write the failing test (하위프로세스로 hook 실행)**

`user_instruction/hooks/tests/test_record.py` 에 추가:

```python
import json
import subprocess
import tempfile


def _run_reminder(cwd, prompt, session_id):
    hook = os.path.join(os.path.dirname(HERE), "user_instruction-reminder.py")
    payload = json.dumps({"prompt": prompt, "session_id": session_id, "cwd": cwd})
    out = subprocess.run([sys.executable, hook], input=payload,
                         capture_output=True, text=True, timeout=5)
    return out


def _activate_rule(cwd):
    d = os.path.join(cwd, "docs", "claude_guideline", "user_instruction")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "recording.md"), "w").close()


def test_reminder_records_to_own_session_file():
    with tempfile.TemporaryDirectory() as cwd:
        _activate_rule(cwd)
        _run_reminder(cwd, "first instruction", "1111aaaa-x")
        f = os.path.join(cwd, "docs", "user_instructions", "sessions", "1111aaaa-x.md")
        assert os.path.isfile(f)
        assert "first instruction" in open(f, encoding="utf-8").read()


def test_reminder_isolates_other_sessions():
    with tempfile.TemporaryDirectory() as cwd:
        _activate_rule(cwd)
        _run_reminder(cwd, "session A secret", "AAAA-a")
        out = _run_reminder(cwd, "session B prompt", "BBBB-b")
        # 세션 B 주입 stdout 에 세션 A 원문이 새어들면 안 됨
        assert "session A secret" not in out.stdout
        assert "session B prompt" in out.stdout  # 자기 기록은 참조로 주입


def test_reminder_noop_without_rule():
    with tempfile.TemporaryDirectory() as cwd:
        out = _run_reminder(cwd, "x", "CCCC-c")
        assert out.stdout.strip() == ""
        assert not os.path.exists(os.path.join(cwd, "docs", "user_instructions"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 user_instruction/hooks/tests/test_record.py`
Expected: FAIL — 기존 reminder 는 sessions/ 에 쓰지 않고 지시문만 출력 → `test_reminder_records_to_own_session_file` AssertionError

- [ ] **Step 3: 재작성 user_instruction-reminder.py**

Replace 전체 내용:

```python
#!/usr/bin/env python3
"""UserPromptSubmit 훅 — 사용자 지시를 이 세션 전용 파일에 결정적 기록 + 자기 세션만 주입.

세션 격리: docs/user_instructions/sessions/{session_id}.md 에만 쓰고, 참조 주입도
자기 세션 기록으로 한정한다. 다른 세션 기록은 절대 노출하지 않는다(교차 누수 차단).
병합은 SessionEnd(user_instruction-merge.py)가 담당.

self-contained: 표준 라이브러리만. 계약: stdin JSON → stdout 주입, 항상 exit 0.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import session_record as sr  # noqa: E402

INJECT_LIMIT = 5


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        return

    prompt = str(data.get("prompt", ""))
    if not prompt:
        return

    cwd = data.get("cwd") or os.getcwd()
    if not sr.rule_active(cwd):
        return  # graceful: 규칙 미설치 → no-op

    session_id = data.get("session_id") or "unknown"
    short = session_id[:8]

    sess_dir = sr.sessions_dir(cwd)
    own = os.path.join(sess_dir, session_id + ".md")
    entry = sr.format_entry(sr.kst_now_str(), short, prompt)
    try:
        os.makedirs(sess_dir, exist_ok=True)
        prior = ""
        if os.path.isfile(own):
            with open(own, encoding="utf-8") as f:
                prior = f.read()
        with open(own, "w", encoding="utf-8") as f:
            f.write(entry + prior)  # prepend(newest-on-top)
    except OSError:
        return  # 기록 실패해도 세션은 진행

    # 자기 세션 최근 N개만 참조 주입
    try:
        with open(own, encoding="utf-8") as f:
            entries = sr.parse_entries(f.read())
    except OSError:
        entries = []
    shown = entries[:INJECT_LIMIT]
    body = "".join(b for _, b in shown)
    more = "\n…(이전 생략)\n" if len(entries) > INJECT_LIMIT else ""
    print(
        "[USER-INSTRUCTION — 이 세션 기록(격리)]\n"
        "지시 원문은 이 세션 전용 파일에 자동 기록되었습니다. 아래는 **이 세션**의 최근 지시뿐입니다"
        "(다른 세션 기록은 보이지 않으며, docs/user_instructions/user_instructions.md 를 현재 작업 소스로 읽지 마세요):\n\n"
        + body + more
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 user_instruction/hooks/tests/test_record.py`
Expected: PASS (전체)

- [ ] **Step 5: Commit**

```bash
git add user_instruction/hooks/user_instruction-reminder.py user_instruction/hooks/tests/test_record.py
git commit -m "feat(user_instruction): deterministic per-session recording + isolated injection

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: user_instruction-merge.py — SessionEnd 병합 + orphan GC

**Files:**
- Create: `user_instruction/hooks/user_instruction-merge.py`
- Test: `user_instruction/hooks/tests/test_merge.py`

**Interfaces:**
- Consumes: `session_record` (Task 1) — `sessions_dir`, `log_path`, `rule_active`, `parse_entries`
- Produces: SessionEnd hook. 부수효과: 자기 `sessions/{id}.md` → `user_instructions.md` 병합(flock, 시간 역순), 자기 파일 삭제, orphan(mtime>7d) GC.

- [ ] **Step 1: Write the failing test**

Create `user_instruction/hooks/tests/test_merge.py`:

```python
#!/usr/bin/env python3
"""user_instruction-merge.py SessionEnd 병합 테스트."""
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import session_record as sr  # noqa: E402


def _activate_rule(cwd):
    d = os.path.join(cwd, "docs", "claude_guideline", "user_instruction")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "recording.md"), "w").close()


def _write_session(cwd, sid, entries):
    d = sr.sessions_dir(cwd)
    os.makedirs(d, exist_ok=True)
    text = "".join(sr.format_entry(ts, sid[:8], p) for ts, p in entries)
    with open(os.path.join(d, sid + ".md"), "w", encoding="utf-8") as f:
        f.write(text)


def _run_merge(cwd, sid):
    hook = os.path.join(os.path.dirname(HERE), "user_instruction-merge.py")
    payload = json.dumps({"session_id": sid, "cwd": cwd, "reason": "clear"})
    return subprocess.run([sys.executable, hook], input=payload,
                          capture_output=True, text=True, timeout=5)


def test_merge_moves_own_entries_and_deletes_file():
    with tempfile.TemporaryDirectory() as cwd:
        _activate_rule(cwd)
        _write_session(cwd, "SID-own", [("2026-07-01 14:00", "hello")])
        _run_merge(cwd, "SID-own")
        log = open(sr.log_path(cwd), encoding="utf-8").read()
        assert "hello" in log and "sess:SID-own"[:13] in log
        assert not os.path.exists(os.path.join(sr.sessions_dir(cwd), "SID-own.md"))


def test_merge_ignores_other_live_sessions():
    with tempfile.TemporaryDirectory() as cwd:
        _activate_rule(cwd)
        _write_session(cwd, "SID-a", [("2026-07-01 14:00", "a-live")])
        _write_session(cwd, "SID-b", [("2026-07-01 15:00", "b-live")])
        _run_merge(cwd, "SID-a")
        # 병합은 자기(SID-a)만, SID-b live 파일은 그대로
        assert os.path.exists(os.path.join(sr.sessions_dir(cwd), "SID-b.md"))
        log = open(sr.log_path(cwd), encoding="utf-8").read()
        assert "a-live" in log and "b-live" not in log


def test_merge_time_ordered_newest_first():
    with tempfile.TemporaryDirectory() as cwd:
        _activate_rule(cwd)
        # 기존 로그에 더 최신 엔트리
        with open(sr.log_path(cwd), "w", encoding="utf-8") as f:
            f.write(sr.format_entry("2026-07-01 16:00", "OLD-x", "existing-newer"))
        _write_session(cwd, "SID-x", [("2026-07-01 14:00", "older-merged")])
        _run_merge(cwd, "SID-x")
        entries = sr.parse_entries(open(sr.log_path(cwd), encoding="utf-8").read())
        assert [e[0] for e in entries] == ["2026-07-01 16:00", "2026-07-01 14:00"]


def test_merge_gc_orphan_older_than_7d():
    with tempfile.TemporaryDirectory() as cwd:
        _activate_rule(cwd)
        _write_session(cwd, "SID-self", [("2026-07-01 14:00", "self")])
        _write_session(cwd, "SID-orphan", [("2026-06-01 10:00", "orphan")])
        orphan = os.path.join(sr.sessions_dir(cwd), "SID-orphan.md")
        old = time.time() - 8 * 86400
        os.utime(orphan, (old, old))
        _run_merge(cwd, "SID-self")
        # orphan(>7d, 비-자기)은 GC 로 병합 후 삭제
        assert not os.path.exists(orphan)
        log = open(sr.log_path(cwd), encoding="utf-8").read()
        assert "orphan" in log


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
    sys.exit(1 if fails else 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 user_instruction/hooks/tests/test_merge.py`
Expected: FAIL — `user_instruction-merge.py` 없음 → 모든 테스트 실패

- [ ] **Step 3: Write user_instruction-merge.py**

Create `user_instruction/hooks/user_instruction-merge.py`:

```python
#!/usr/bin/env python3
"""SessionEnd 훅 — 이 세션의 sessions/{id}.md 를 user_instructions.md 로 병합.

세션 격리: 자기 세션 파일만 병합·삭제한다. orphan(크래시로 남은 비-자기 파일)은
mtime>7일인 것만 보수적으로 회수(live 세션 파일은 7일 내라 안전). 공유 로그
rewrite 는 flock 으로 직렬화(동시 종료 시 lost-write 방지).

self-contained: 표준 라이브러리만. 계약: stdin JSON → 부수효과, 항상 exit 0.
"""
import fcntl
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import session_record as sr  # noqa: E402

ORPHAN_AGE = 7 * 86400


def _merge_blocks(cwd, blocks):
    """blocks(엔트리 문자열들)를 기존 로그와 시간 역순 병합 후 rewrite. flock 보호."""
    log = sr.log_path(cwd)
    os.makedirs(os.path.dirname(log), exist_ok=True)
    lock = log + ".lock"
    with open(lock, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            existing = ""
            if os.path.isfile(log):
                with open(log, encoding="utf-8") as f:
                    existing = f.read()
            entries = sr.parse_entries(existing)
            for b in blocks:
                entries.extend(sr.parse_entries(b))
            # ts_key 내림차순(문자열 정렬이 시간순과 일치하는 형식), 안정 정렬
            entries.sort(key=lambda e: e[0], reverse=True)
            merged = "".join(b for _, b in entries)
            tmp = log + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(merged)
            os.replace(tmp, log)
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        return

    cwd = data.get("cwd") or os.getcwd()
    if not sr.rule_active(cwd):
        return

    session_id = data.get("session_id") or "unknown"
    sess_dir = sr.sessions_dir(cwd)
    if not os.path.isdir(sess_dir):
        return

    own = os.path.join(sess_dir, session_id + ".md")
    to_merge = []       # (path, text)
    # 1) 자기 세션 파일
    if os.path.isfile(own):
        try:
            with open(own, encoding="utf-8") as f:
                to_merge.append((own, f.read()))
        except OSError:
            pass
    # 2) orphan GC: 비-자기 & mtime>7d
    now = time.time()
    for name in os.listdir(sess_dir):
        if not name.endswith(".md"):
            continue
        p = os.path.join(sess_dir, name)
        if p == own:
            continue
        try:
            if now - os.path.getmtime(p) > ORPHAN_AGE:
                with open(p, encoding="utf-8") as f:
                    to_merge.append((p, f.read()))
        except OSError:
            continue

    if not to_merge:
        return
    _merge_blocks(cwd, [text for _, text in to_merge])
    for p, _ in to_merge:
        try:
            os.remove(p)
        except OSError:
            pass


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 user_instruction/hooks/tests/test_merge.py`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add user_instruction/hooks/user_instruction-merge.py user_instruction/hooks/tests/test_merge.py
git commit -m "feat(user_instruction): SessionEnd merge of own session log with flock + orphan GC

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: recording.md + claude.snippet.md — 규칙 문서 갱신

**Files:**
- Modify: `user_instruction/recording.md`
- Modify: `user_instruction/claude.snippet.md`

**Interfaces:**
- Consumes: Task 1–3 의 동작(hook 이 기록·병합)
- Produces: 문서. 코드 의존 없음. (테스트 없음 — 문서 정합만)

- [ ] **Step 1: recording.md §3 교체 (기록 주체·구조)**

`## 3. 기록` 섹션을 다음으로 교체:

```markdown
## 3. 기록 (hook 이 자동 수행 — 세션 격리)

기록은 **`user_instruction-reminder.py`(UserPromptSubmit hook)가 결정적으로** 수행한다. 모델이
수동으로 파일을 열어 기록하지 않는다(누락·일괄기록 실패 원천 제거).

- 각 세션의 지시는 `docs/user_instructions/sessions/{session_id}.md` 에만 prepend 된다(세션 전용).
- 형식: `## YYYY-MM-DD HH:MM (KST) · sess:{short8}` + `> "원문"` + `---`.
- **다른 세션 파일을 읽거나 `user_instructions.md` 를 현재 작업 소스로 취급하지 않는다**(교차 누수 차단).
- 세션 종료 시 `user_instruction-merge.py`(SessionEnd hook)가 자기 파일만 `user_instructions.md`
  단일 누적 로그로 시간 역순 병합하고 세션 파일을 정리한다.

`docs/user_instructions/sessions/` 는 `.gitignore` 대상(전이적). 커밋 대상은 병합 결과
`docs/user_instructions/user_instructions.md` 뿐이다.
```

- [ ] **Step 2: recording.md §4 경계에 read 금지 한 줄 추가**

`## 4. 경계` 말미에 추가:

```markdown
- **읽기 금지**: 다른 세션의 `sessions/*.md`, 그리고 병합 로그를 "현재 지시"로 재해석하는 것. 현재 세션 맥락은 hook 이 주입하는 자기 세션 최근 5개로 충분하다.
```

- [ ] **Step 3: claude.snippet.md 문구 갱신**

기존 "지시 원문을 docs/user_instructions/user_instructions.md 맨 위에 즉시 prepend 기록한다" 문장을 다음으로 교체:

```markdown
- 사용자 지시는 UserPromptSubmit hook 이 이 세션 전용 파일(docs/user_instructions/sessions/{session_id}.md)에 자동 기록하고 SessionEnd 에 단일 누적 로그로 병합한다. 모델은 다른 세션 기록·병합 로그를 현재 작업 소스로 읽지 않는다(세션 격리).
```

- [ ] **Step 4: 정합 확인**

Run: `grep -n "user_instructions.md" user_instruction/recording.md user_instruction/claude.snippet.md`
Expected: 남은 언급이 모두 "병합 결과/누적 로그" 맥락인지 육안 확인(현재 작업 소스로 지시하는 문구 없음).

- [ ] **Step 5: Commit**

```bash
git add user_instruction/recording.md user_instruction/claude.snippet.md
git commit -m "docs(user_instruction): rules reflect per-session recording + merge isolation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: user_instruction/install.sh — SessionEnd 등록 + gitignore

**Files:**
- Modify: `user_instruction/install.sh`

**Interfaces:**
- Consumes: Task 2·3 의 hook 파일명
- Produces: 설치기. `.claude/settings.json` 에 UserPromptSubmit(reminder)+SessionEnd(merge) 멱등 등록, 타깃 `.gitignore` 에 sessions/ 추가.

- [ ] **Step 1: hook 복사 대상에 merge + session_record 추가**

`install.sh` 의 hook 복사 블록(현재 `$HOOK_PY` 단일 복사)을 다음으로 교체(세 파일 복사):

```bash
# 강제 훅 — 세션 격리 기록/병합
mkdir -p "$DEST/hooks"
for hf in user_instruction-reminder.py user_instruction-merge.py session_record.py; do
  if [ -f "$SRC/hooks/$hf" ]; then
    cp "$SRC/hooks/$hf" "$DEST/hooks/$hf"
    chmod +x "$DEST/hooks/$hf" 2>/dev/null || true
  fi
done
echo "✓ 훅 복사: docs/claude_guideline/$BUNDLE/hooks/ (reminder·merge·session_record)"
```

- [ ] **Step 2: settings.json 등록을 UserPromptSubmit + SessionEnd 로 확장**

기존 python heredoc 등록 블록을 다음으로 교체(두 이벤트 멱등 등록):

```bash
PYBIN=""
for c in python3 python; do command -v "$c" >/dev/null 2>&1 && { PYBIN="$c"; break; }; done
if [ -z "$PYBIN" ]; then
  echo "⚠ python3/python 없음 — settings.json 훅 등록 건너뜀. 수동 등록 필요."
else
  mkdir -p "$TARGET/.claude"
  SETTINGS="$TARGET/.claude/settings.json"
  [ -f "$SETTINGS" ] && cp "$SETTINGS" "$SETTINGS.bak" && echo "✓ 백업: .claude/settings.json.bak"
  REMINDER="$PYBIN \"\$CLAUDE_PROJECT_DIR/docs/claude_guideline/$BUNDLE/hooks/user_instruction-reminder.py\""
  MERGE="$PYBIN \"\$CLAUDE_PROJECT_DIR/docs/claude_guideline/$BUNDLE/hooks/user_instruction-merge.py\""
  "$PYBIN" - "$SETTINGS" "$REMINDER" "$MERGE" <<'PYEOF'
import json, sys
settings_path, reminder, merge = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(settings_path, encoding="utf-8") as f:
        cfg = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    cfg = {}
hooks = cfg.setdefault("hooks", {})

def ensure(event, cmd, timeout):
    groups = hooks.setdefault(event, [])
    if any(h.get("command") == cmd for g in groups for h in g.get("hooks", [])):
        return "스킵"
    groups.append({"hooks": [{"type": "command", "command": cmd, "timeout": timeout}]})
    return "추가"

a = ensure("UserPromptSubmit", reminder, 5)
b = ensure("SessionEnd", merge, 10)
with open(settings_path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
print(f"✓ settings.json 훅 등록: UserPromptSubmit={a}, SessionEnd={b}")
PYEOF
fi
```

- [ ] **Step 3: .gitignore 에 sessions/ 추가 (멱등)**

Step 2 뒤에 추가:

```bash
GI="$TARGET/.gitignore"
LINE="docs/user_instructions/sessions/"
touch "$GI"
grep -qxF "$LINE" "$GI" || { printf '%s\n' "$LINE" >> "$GI"; echo "✓ .gitignore: $LINE 추가"; }
```

- [ ] **Step 4: 설치 스모크 테스트 (임시 타깃)**

Run:
```bash
T=$(mktemp -d); bash user_instruction/install.sh "$T" >/dev/null
python3 - "$T" <<'PY'
import json,sys,os
t=sys.argv[1]
cfg=json.load(open(os.path.join(t,".claude/settings.json")))
cmds=[h["command"] for e in ("UserPromptSubmit","SessionEnd") for g in cfg["hooks"].get(e,[]) for h in g["hooks"]]
assert any("reminder" in c for c in cmds), "reminder 미등록"
assert any("merge" in c for c in cmds), "merge 미등록"
assert "docs/user_instructions/sessions/" in open(os.path.join(t,".gitignore")).read()
for f in ("reminder","merge"): assert os.path.isfile(os.path.join(t,f"docs/claude_guideline/user_instruction/hooks/user_instruction-{f}.py"))
assert os.path.isfile(os.path.join(t,"docs/claude_guideline/user_instruction/hooks/session_record.py"))
print("SMOKE PASS")
PY
rm -rf "$T"
```
Expected: `SMOKE PASS`

- [ ] **Step 5: Commit**

```bash
git add user_instruction/install.sh
git commit -m "feat(user_instruction): install registers SessionEnd merge hook + gitignores sessions/

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: git_workflow-staging-guard.py — blanket-add 하드 게이트

**Files:**
- Create: `git_workflow/hooks/git_workflow-staging-guard.py`
- Test: `git_workflow/hooks/tests/test_staging_guard.py`

**Interfaces:**
- Consumes: stdin JSON(`tool_name`, `tool_input.command`, `session_id`, `cwd`)
- Produces: PreToolUse hook. blanket-add 감지 시 exit 2 + stderr; 아니면 exit 0. 순수 함수 `is_blanket_add(command) -> str|None`(매칭 문자열 또는 None).

- [ ] **Step 1: Write the failing test**

Create `git_workflow/hooks/tests/test_staging_guard.py`:

```python
#!/usr/bin/env python3
"""git_workflow-staging-guard.py 차단/통과 테스트."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.join(os.path.dirname(HERE), "git_workflow-staging-guard.py")
sys.path.insert(0, os.path.dirname(HERE))
import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location("guard", GUARD)


def _load():
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_unit_blanket_detection():
    g = _load()
    for cmd in ["git add -A", "git add --all", "git add .", "git add -u",
                "git commit -a -m x", "git commit -am 'x'", "git commit --all",
                "cd foo && git add -A", "git -C /r add ."]:
        assert g.is_blanket_add(cmd), f"차단돼야 함: {cmd}"
    for cmd in ["git add src/foo.py", "git commit -m 'x'", "git commit --amend",
                "git add -p", "git status", "grep -A 3 pattern file",
                "git add docs/a.md docs/b.md"]:
        assert not g.is_blanket_add(cmd), f"통과해야 함: {cmd}"


def _make_git_repo_with_rule():
    cwd = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", cwd], check=True)
    d = os.path.join(cwd, "docs", "claude_guideline", "git_workflow")
    os.makedirs(d)
    open(os.path.join(d, "git_workflow.md"), "w").close()
    return cwd


def _run(cwd, command):
    payload = json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": command},
                          "session_id": "abcd1234-x", "cwd": cwd})
    return subprocess.run([sys.executable, GUARD], input=payload,
                          capture_output=True, text=True, timeout=5)


def test_blocks_with_exit2():
    cwd = _make_git_repo_with_rule()
    out = _run(cwd, "git add -A")
    assert out.returncode == 2
    assert "세션 격리" in out.stderr


def test_allows_explicit_path():
    cwd = _make_git_repo_with_rule()
    out = _run(cwd, "git add src/x.py")
    assert out.returncode == 0


def test_noop_without_rule():
    cwd = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", cwd], check=True)
    out = _run(cwd, "git add -A")
    assert out.returncode == 0  # 규칙 미설치 → graceful


def test_noop_non_bash_tool():
    cwd = _make_git_repo_with_rule()
    payload = json.dumps({"tool_name": "Read", "tool_input": {}, "cwd": cwd})
    out = subprocess.run([sys.executable, GUARD], input=payload,
                         capture_output=True, text=True, timeout=5)
    assert out.returncode == 0


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print(f"PASS {name}")
            except AssertionError as e:
                fails += 1; print(f"FAIL {name}: {e}")
    sys.exit(1 if fails else 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 git_workflow/hooks/tests/test_staging_guard.py`
Expected: FAIL — guard 파일 없음(`FileNotFoundError`/import 실패)

- [ ] **Step 3: Write git_workflow-staging-guard.py**

Create `git_workflow/hooks/git_workflow-staging-guard.py`:

```python
#!/usr/bin/env python3
"""PreToolUse(Bash) 훅 — blanket git add/commit -a 를 차단(세션 격리 하드 게이트).

working tree 는 모든 세션 공유라 `git add -A`/`.`/`commit -a` 는 다른 세션의 미커밋
변경까지 staging 한다. 본 훅이 이를 exit 2 로 차단하고, 명시 경로 staging 으로 유도한다.
차단 메시지에 git_workflow-track.py 가 기록한 '이 세션 수정 파일' 목록을 실어 grounding.

self-contained: 표준 라이브러리만. 계약: stdin JSON → 차단 시 exit 2 + stderr, else exit 0.
"""
import json
import os
import shlex
import subprocess
import sys

RULE_MD = "docs/claude_guideline/git_workflow/git_workflow.md"


def _segments(command):
    """&&, ||, ;, | , 개행으로 분리한 명령 세그먼트."""
    out, buf, i = [], [], 0
    seps = ("&&", "||", ";", "|", "\n")
    while i < len(command):
        two = command[i:i + 2]
        if two in ("&&", "||"):
            out.append("".join(buf)); buf = []; i += 2; continue
        if command[i] in (";", "|", "\n"):
            out.append("".join(buf)); buf = []; i += 1; continue
        buf.append(command[i]); i += 1
    out.append("".join(buf))
    return [s.strip() for s in out if s.strip()]


def _tokens(seg):
    try:
        return shlex.split(seg)
    except ValueError:
        return seg.split()


def _subcmd_and_args(tokens):
    """git 글로벌옵션(-C dir 등) 건너뛰고 (subcmd, args) 반환. git 아니면 (None, [])."""
    if not tokens or os.path.basename(tokens[0]) != "git":
        return None, []
    i = 1
    while i < len(tokens):
        t = tokens[i]
        if t in ("-C", "-c", "--git-dir", "--work-tree", "--namespace"):
            i += 2; continue
        if t.startswith("-"):
            i += 1; continue
        return t, tokens[i + 1:]
    return None, []


def _short_flag_has(args, letter):
    for a in args:
        if a.startswith("-") and not a.startswith("--") and letter in a[1:]:
            return True
    return False


def is_blanket_add(command):
    """차단 대상이면 매칭 세그먼트 문자열, 아니면 None."""
    for seg in _segments(command):
        sub, args = _subcmd_and_args(_tokens(seg))
        if sub == "add":
            if "-A" in args or "--all" in args or "-u" in args or "." in args:
                return seg
        elif sub == "commit":
            if "--all" in args or _short_flag_has(args, "a"):
                return seg
    return None


def _git_dir(cwd):
    try:
        r = subprocess.run(["git", "-C", cwd, "rev-parse", "--absolute-git-dir"],
                           capture_output=True, text=True, timeout=3)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _touched_hint(gd, session_id):
    if not gd or not session_id:
        return ""
    p = os.path.join(gd, "git_workflow", "sessions", session_id, "touched")
    if not os.path.isfile(p):
        return ""
    try:
        with open(p, encoding="utf-8") as f:
            files = [ln.strip() for ln in f if ln.strip()]
    except OSError:
        return ""
    if not files:
        return ""
    return "\n이 세션이 수정한 파일(이것만 명시 add):\n" + "\n".join("  - " + x for x in files)


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        return  # exit 0

    if data.get("tool_name") != "Bash":
        return
    command = str((data.get("tool_input") or {}).get("command", ""))
    if not command:
        return

    cwd = data.get("cwd") or os.getcwd()
    if not os.path.isfile(os.path.join(cwd, *RULE_MD.split("/"))):
        return  # graceful: 규칙 미설치
    gd = _git_dir(cwd)
    if not gd:
        return  # 비-git

    matched = is_blanket_add(command)
    if not matched:
        return

    hint = _touched_hint(gd, data.get("session_id", ""))
    sys.stderr.write(
        "[GIT-WORKFLOW 세션 격리 — blanket staging 차단]\n"
        f"차단된 명령: `{matched}`\n"
        "working tree 는 모든 세션이 공유하므로 `git add -A`/`.`/`--all`/`-u`·`git commit -a` 는 "
        "다른 세션의 미커밋 변경까지 staging 합니다. **이 세션이 수정한 파일만 명시 경로로** add 하세요.\n"
        f"{hint}\n"
        "예: git add <경로1> <경로2> && git diff --cached --name-only  # 위 목록의 부분집합인지 검증\n"
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 git_workflow/hooks/tests/test_staging_guard.py`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add git_workflow/hooks/git_workflow-staging-guard.py git_workflow/hooks/tests/test_staging_guard.py
git commit -m "feat(git_workflow): PreToolUse hard gate blocking blanket git add/commit -a

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: git_workflow/install.sh — PreToolUse 등록

**Files:**
- Modify: `git_workflow/install.sh`

**Interfaces:**
- Consumes: Task 6 의 guard 파일명
- Produces: 설치기. 기존 UserPromptSubmit(reminder)+PostToolUse(track) 등록에 PreToolUse(Bash matcher, guard) 멱등 추가.

> **선행 확인**: 현재 `git_workflow/install.sh` 를 Read 해 hook 복사 목록과 settings.json 등록 python 블록의 정확한 형태를 확인한 뒤 아래를 반영한다(이 번들 install.sh 는 Task 5 와 세부가 다를 수 있음).

- [ ] **Step 1: guard 를 hook 복사 목록에 추가**

install.sh 의 hook 복사 루프(reminder·track 복사부)에 `git_workflow-staging-guard.py` 를 포함시킨다. 복사 대상 배열/루프에 파일명 한 줄 추가:

```bash
for hf in git_workflow-reminder.py git_workflow-track.py git_workflow-staging-guard.py; do
  [ -f "$SRC/hooks/$hf" ] && cp "$SRC/hooks/$hf" "$DEST/hooks/$hf" && chmod +x "$DEST/hooks/$hf" 2>/dev/null || true
done
```

- [ ] **Step 2: settings.json 에 PreToolUse(Bash matcher) 멱등 등록**

기존 등록 python 블록에 PreToolUse 를 추가한다. matcher 는 `Bash`:

```python
def ensure_matcher(event, matcher, cmd, timeout):
    groups = hooks.setdefault(event, [])
    for g in groups:
        if g.get("matcher") == matcher and any(h.get("command") == cmd for h in g.get("hooks", [])):
            return "스킵"
    groups.append({"matcher": matcher,
                   "hooks": [{"type": "command", "command": cmd, "timeout": timeout}]})
    return "추가"

guard = f'{PYBIN} "$CLAUDE_PROJECT_DIR/docs/claude_guideline/git_workflow/hooks/git_workflow-staging-guard.py"'
c = ensure_matcher("PreToolUse", "Bash", guard, 5)
```

(shell 변수 `$PYBIN`·heredoc 컨텍스트는 기존 블록 형태에 맞춰 삽입. `guard` 커맨드 문자열의 `$CLAUDE_PROJECT_DIR` 는 heredoc 이 quoted(`<<'PYEOF'`)이면 리터럴 유지되도록 shell 에서 조립해 argv 로 전달.)

- [ ] **Step 3: 설치 스모크 테스트 (임시 git 타깃)**

Run:
```bash
T=$(mktemp -d); git init -q "$T"; bash git_workflow/install.sh "$T" >/dev/null
python3 - "$T" <<'PY'
import json,sys,os
t=sys.argv[1]; cfg=json.load(open(os.path.join(t,".claude/settings.json")))
pre=[ (g.get("matcher"), h["command"]) for g in cfg["hooks"].get("PreToolUse",[]) for h in g["hooks"] ]
assert any(m=="Bash" and "staging-guard" in c for m,c in pre), f"PreToolUse guard 미등록: {pre}"
assert os.path.isfile(os.path.join(t,"docs/claude_guideline/git_workflow/hooks/git_workflow-staging-guard.py"))
print("SMOKE PASS")
PY
rm -rf "$T"
```
Expected: `SMOKE PASS`

- [ ] **Step 4: 회귀 확인 (기존 훅 유지)**

Run: 위 스모크의 `cfg` 에서 UserPromptSubmit(reminder)·PostToolUse(track) 가 여전히 존재하는지 육안/assert 확인(기존 등록 파괴 없음).

- [ ] **Step 5: Commit**

```bash
git add git_workflow/install.sh
git commit -m "feat(git_workflow): install registers PreToolUse staging guard (Bash matcher)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: SIL 통합 검증 + 재설치

**Files:**
- Create: `user_instruction/experiments/SIL/2026-07-01_session-isolation/README.md`
- Create: `git_workflow/experiments/SIL/2026-07-01_session-isolation/README.md`

**Interfaces:**
- Consumes: Task 1–7 전체
- Produces: SIL 회고 문서. 실 배포(세 프로젝트 재설치)는 사용자 승인 후.

- [ ] **Step 1: 전체 테스트 일괄 실행**

Run:
```bash
python3 user_instruction/hooks/tests/test_record.py
python3 user_instruction/hooks/tests/test_merge.py
python3 git_workflow/hooks/tests/test_staging_guard.py
```
Expected: 세 스크립트 모두 exit 0, 전부 PASS.

- [ ] **Step 2: 동시 세션 시나리오 수동 재현 (2 세션)**

임시 프로젝트에 두 번들 설치 후, 서로 다른 session_id 로 reminder 를 각각 호출 → `sessions/` 에 2개 독립 파일·상호 비노출 확인. 각 session_id 로 merge 호출 → 병합·정리 확인. `git add -A` payload → exit 2 확인. 절차·결과를 SIL README 에 기록.

- [ ] **Step 3: SIL README 작성 (양 번들)**

`experiments/SIL/_template/README.md` 형식을 따라 각 번들에 회고 entry(시나리오·기대·실측·형식 결함) 작성.

- [ ] **Step 4: Commit**

```bash
git add user_instruction/experiments/SIL/2026-07-01_session-isolation/README.md \
        git_workflow/experiments/SIL/2026-07-01_session-isolation/README.md
git commit -m "test(session-isolation): SIL retrospective for concurrent-session isolation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 5: 배포 (사용자 승인 게이트)**

세 프로젝트 재설치는 **사용자 명시 승인 후** 각 프로젝트에 `bash user_instruction/install.sh <proj>` · `bash git_workflow/install.sh <proj>` 실행. 설치 후 세션 재시작 필요 안내. (원격 push 는 파일별 승인·dual-remote 정책 준수.)

---

## Self-Review

**Spec coverage:**
- §4.1 결정적 기록 → Task 2. §4.2 자기세션 주입(N=5) → Task 2(INJECT_LIMIT). §4.3 SessionEnd 병합·flock·GC → Task 3. §5 blanket-add 하드게이트 → Task 6. §6 flock/orphan/비-git/gitignore → Task 3·5·6. §7 인벤토리 전부 → Task 1–7. §8 SIL → Task 8. 교차참조(§7) code_review/issue_fix 문서 점검은 동작 무변경이라 별도 태스크 없이 Task 4 정합확인 범위에서 육안 처리(코드 영향 없음). **커버리지 갭 없음.**
- 비밀정보 마스킹(§6 한계): 의도적 비목표 — 태스크 없음(설계 명시).

**Placeholder scan:** 모든 코드 스텝에 완전한 코드 포함. Task 7 은 기존 install.sh 형태 의존이라 "선행 Read" 를 명시하고 삽입 조각을 완전 코드로 제공(유일한 조건부는 기존 파일 형태 확인 — placeholder 아님).

**Type consistency:** `session_record` API(`kst_now_str`/`sessions_dir`/`log_path`/`rule_active`/`format_entry`/`parse_entries`/`HEADER_RE`)를 Task 1 에서 정의하고 Task 2·3 에서 동일 시그니처로 소비. guard 의 `is_blanket_add(command)->str|None` 를 Task 6 정의·테스트 일치. 불일치 없음.
