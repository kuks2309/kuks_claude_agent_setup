# session_workflow 번들 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 다중 세션 생애주기(목적 선언 게이트 → 레지스트리·충돌 경보 → 종료 handoff)를 자기완결 번들 `session_workflow/` 로 구현한다.

**Architecture:** 4개 훅(SessionStart·UserPromptSubmit·PostToolUse·SessionEnd)이 `.git/session_workflow/` 상태 저장소를 결정적으로 관리하고, 공유 로직은 `session_state.py` 헬퍼 1개에 모은다(DRY). 각 세션은 자기 이름 파일에만 쓴다(잠금 불요). 스펙: [2026-07-12-session-workflow-design.md](2026-07-12-session-workflow-design.md).

**Tech Stack:** Python 3 표준 라이브러리만(훅), bash(install.sh). 테스트 프레임워크 없음 — 저장소 관례대로 SIL(셸 호출) 검증.

## Global Constraints

- **자기완결**: 훅은 표준 라이브러리만, 타 번들(git_workflow·user_instruction)·OMC 비의존. SSOT 문서에 자매 SSOT 하이퍼링크 0.
- **graceful**: 모든 훅은 (1) 활성화 게이트 = `docs/claude_guideline/session_workflow/session_workflow.md` 존재, (2) 비-git → no-op, (3) 최상위 try/except 로 **항상 exit 0**.
- **시각은 KST**(UTC+9), 형식 `YYYY-MM-DD HH:MM`.
- **기존 번들 파일 수정 금지** (git_workflow·user_instruction 등 불가침). 수정 대상 기존 파일은 루트 `README.md` 뿐.
- **커밋 규약**: `type(scope): subject` + `Co-Authored-By: Claude <noreply@anthropic.com>` 푸터. **명시 staging**(`git add <경로>`, `-A`/`.` 금지 — stage-gate 훅 활성). **커밋·푸시는 사용자 명시 트리거("커밋"/"푸쉬")에만** — 각 태스크의 커밋 스텝은 사용자 승인 후 실행한다. 푸시는 `origin`·`fito` 양쪽.
- **파일별 승인 규약**: 각 태스크의 파일 작성 전 사용자 명시 승인을 받는다(저장소 운영 규약).
- 작업 디렉터리: `/home/amap/Project/claude_code/kuks_claude_skill_setup` (branch `main`, solo 모드). `docs/design/2026-07-01-session-isolation-plan.md` 는 타 세션 미커밋 파일 — staging 에 절대 포함하지 않는다.
- SIL 스크래치 경로(이하 `$T`): `/tmp/claude-1000/-home-amap-Project-claude-code/5db6f94c-168b-46a8-b05d-f44b080ddae6/scratchpad/swtest`

**공통 SIL 준비 블록** (각 태스크의 테스트 스텝에서 재사용; `$SW` = 번들 소스 폴더):

```bash
SW=/home/amap/Project/claude_code/kuks_claude_skill_setup/session_workflow
T=/tmp/claude-1000/-home-amap-Project-claude-code/5db6f94c-168b-46a8-b05d-f44b080ddae6/scratchpad/swtest
rm -rf "$T" && mkdir -p "$T/docs/claude_guideline/session_workflow"
git -C "$T" init -q
touch "$T/docs/claude_guideline/session_workflow/session_workflow.md"   # 활성화 게이트 충족
```

---

### Task 1: 상태 공유 헬퍼 `session_state.py`

**Files:**
- Create: `session_workflow/hooks/session_state.py`

**Interfaces:**
- Consumes: 없음 (표준 라이브러리만)
- Produces (Task 2~5 가 사용):
  - `kst_now_str() -> str` — `"YYYY-MM-DD HH:MM"`
  - `rule_active(cwd) -> bool`, `git_common_dir(cwd) -> str|None`, `repo_top(cwd) -> str|None`
  - `state_root(cwd) -> str|None` — 게이트 통과 시 `<git-common-dir>/session_workflow`, 아니면 `None`
  - `active_dir(root)`, `handoff_dir(root)`, `session_json(root, sid)`, `touched_path(root, sid) -> str`
  - `load_session(root, sid) -> dict|None`, `save_session(root, sid, meta)`, `ensure_session(root, sid) -> dict`
  - `read_touched(root, sid) -> list[str]`, `list_other_active(root, sid) -> list[(sid, meta)]`
  - `is_stale(meta) -> bool` (last_seen > `STALE_HOURS`=24h), `one_line(text, limit=120) -> str`
  - `format_handoff(short, meta, ended, uncommitted, touched) -> str`, `parse_handoff_summary(path) -> (purpose, count)`
  - 상수 `STALE_HOURS=24`, `HANDOFF_KEEP_DAYS=14`, 정규식 `PURPOSE_RE` (`목적:`/`purpose:` + 전각 콜론 허용)
  - meta dict 형식: `{"purpose": str|None, "started_at": str, "last_seen": str, "alerted": list[str]}`

- [ ] **Step 1: 파일 작성**

```python
#!/usr/bin/env python3
"""session_workflow 상태 공유 로직 — 경로·레지스트리·handoff 형식 helper.

4개 훅(start·gate·track·end)이 동일 상태 형식을 쓰도록 한 곳에 둔다(DRY).
표준 라이브러리만 사용(self-contained). 상태는 .git 내부(항상 비커밋)의
session_workflow/ 아래: active/<sid>.json · active/<sid>.touched · handoff/<sid>.md.
각 세션은 자기 이름 파일에만 쓴다(공유 rewrite 없음 → 잠금 불요).
"""
import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
STALE_HOURS = 24          # last_seen 이보다 오래되면 잔류 의심
HANDOFF_KEEP_DAYS = 14    # handoff 자동 정리 기한
PURPOSE_RE = re.compile(r"^\s*(?:목적|purpose)\s*[::]\s*(.+)$",
                        re.IGNORECASE | re.DOTALL)


def kst_now():
    return datetime.now(KST)


def kst_now_str():
    return kst_now().strftime("%Y-%m-%d %H:%M")


def rule_active(cwd):
    return os.path.isfile(os.path.join(
        cwd, "docs", "claude_guideline", "session_workflow",
        "session_workflow.md"))


def git_common_dir(cwd):
    """worktree 안전한 공유 git dir(절대경로). 비-git 이면 None."""
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, timeout=3)
        if out.returncode == 0:
            p = out.stdout.strip()
            return p if os.path.isabs(p) else os.path.abspath(
                os.path.join(cwd, p))
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def repo_top(cwd):
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=3)
        if out.returncode == 0:
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def state_root(cwd):
    """상태 저장소 루트. 규칙 미설치·비-git 이면 None(no-op 게이트)."""
    if not rule_active(cwd):
        return None
    gd = git_common_dir(cwd)
    return os.path.join(gd, "session_workflow") if gd else None


def active_dir(root):
    return os.path.join(root, "active")


def handoff_dir(root):
    return os.path.join(root, "handoff")


def session_json(root, sid):
    return os.path.join(active_dir(root), sid + ".json")


def touched_path(root, sid):
    return os.path.join(active_dir(root), sid + ".touched")


def load_session(root, sid):
    try:
        with open(session_json(root, sid), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def save_session(root, sid, meta):
    os.makedirs(active_dir(root), exist_ok=True)
    with open(session_json(root, sid), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)


def ensure_session(root, sid):
    """세션 항목 보장(SessionStart 누락·resume 대비). 기존 meta 보존."""
    meta = load_session(root, sid)
    if meta is None:
        now = kst_now_str()
        meta = {"purpose": None, "started_at": now,
                "last_seen": now, "alerted": []}
    return meta


def read_touched(root, sid):
    try:
        with open(touched_path(root, sid), encoding="utf-8") as f:
            return [ln.strip() for ln in f if ln.strip()]
    except OSError:
        return []


def list_other_active(root, sid):
    """[(other_sid, meta)] — 자기 제외, 손상 json 무시, 이름순."""
    out = []
    try:
        names = os.listdir(active_dir(root))
    except OSError:
        return out
    for n in sorted(names):
        if not n.endswith(".json"):
            continue
        osid = n[:-5]
        if osid == sid:
            continue
        meta = load_session(root, osid)
        if meta is not None:
            out.append((osid, meta))
    return out


def is_stale(meta):
    try:
        seen = datetime.strptime(
            meta.get("last_seen", ""), "%Y-%m-%d %H:%M").replace(tzinfo=KST)
    except ValueError:
        return True
    return kst_now() - seen > timedelta(hours=STALE_HOURS)


def one_line(text, limit=120):
    s = " ".join(str(text).split())
    return s if len(s) <= limit else s[:limit] + "…"


def format_handoff(short, meta, ended, uncommitted, touched):
    lines = [
        f"# 세션 인수인계 · sess:{short}",
        f"- 목적: {one_line(meta.get('purpose') or '(미등록)')}",
        f"- 시작: {meta.get('started_at', '?')} (KST) · 종료: {ended} (KST)",
        f"- 미커밋 파일 ({len(uncommitted)}개):",
    ]
    lines += [f"  - {p}" for p in uncommitted]
    lines.append(f"- 이 세션 수정 파일 전체: {len(touched)}개")
    return "\n".join(lines) + "\n"


def parse_handoff_summary(path):
    """handoff 파일에서 (목적, 미커밋 개수) 요약 추출. 실패 시 ('?', '?')."""
    purpose, count = "?", "?"
    try:
        with open(path, encoding="utf-8") as f:
            for ln in f:
                if ln.startswith("- 목적: "):
                    purpose = ln[len("- 목적: "):].strip()
                m = re.match(r"^- 미커밋 파일 \((\d+)개\)", ln)
                if m:
                    count = m.group(1)
    except OSError:
        pass
    return purpose, count
```

- [ ] **Step 2: 스모크 테스트**

공통 SIL 준비 블록 실행 후:

```bash
python3 - "$T" <<'EOF'
import sys, os
sys.path.insert(0, "/home/amap/Project/claude_code/kuks_claude_skill_setup/session_workflow/hooks")
import session_state as ss
t = sys.argv[1]
root = ss.state_root(t)
assert root and root.endswith(".git/session_workflow"), root
meta = ss.ensure_session(root, "sessA0000001")
assert meta["purpose"] is None and meta["alerted"] == []
ss.save_session(root, "sessA0000001", meta)
assert ss.load_session(root, "sessA0000001") == meta
assert ss.list_other_active(root, "sessA0000001") == []
assert ss.is_stale({"last_seen": "2020-01-01 00:00"}) is True
assert ss.is_stale({"last_seen": ss.kst_now_str()}) is False
m = ss.PURPOSE_RE.match("목적: 훅 개발")
assert m and m.group(1) == "훅 개발"
assert ss.PURPOSE_RE.match("purpose: test").group(1) == "test"
assert ss.PURPOSE_RE.match("안녕하세요") is None
h = ss.format_handoff("sessA000", meta, ss.kst_now_str(), ["a.md"], ["a.md", "b.md"])
open(os.path.join(t, "h.md"), "w").write(h)
assert ss.parse_handoff_summary(os.path.join(t, "h.md")) == ("(미등록)", "1")
assert ss.state_root("/") is None          # 규칙 미설치 → None
print("OK")
EOF
```

Expected: `OK`

- [ ] **Step 3: 커밋 (사용자 "커밋" 승인 후)**

```bash
git -C /home/amap/Project/claude_code/kuks_claude_skill_setup add session_workflow/hooks/session_state.py
git -C /home/amap/Project/claude_code/kuks_claude_skill_setup commit -m "feat(session_workflow): 상태 공유 helper session_state.py

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: 수정 파일 추적 훅 `session_workflow-track.py`

**Files:**
- Create: `session_workflow/hooks/session_workflow-track.py`

**Interfaces:**
- Consumes: `session_state` 의 `state_root`, `repo_top`, `active_dir`, `touched_path`, `read_touched`
- Produces: `active/<sid>.touched` 파일 (repo 상대경로, 줄당 1개, dedup) — Task 3·5 가 읽음

- [ ] **Step 1: 파일 작성**

```python
#!/usr/bin/env python3
"""PostToolUse 훅 — 이 세션이 수정한 파일을 세션별 .touched 에 누적(자체 추적).

타 번들과 독립(자기완결·자체 데이터 경로). 저장:
.git/session_workflow/active/<sid>.touched (repo 상대경로, 줄당 1개, dedup).
계약(Claude Code PostToolUse): stdin JSON → 부수효과. 항상 exit 0.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import session_state as ss  # noqa: E402

TRACK_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        return
    if data.get("tool_name", "") not in TRACK_TOOLS:
        return
    ti = data.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("notebook_path")
    if not path:
        return
    cwd = data.get("cwd") or os.getcwd()
    root = ss.state_root(cwd)
    if not root:
        return
    top = ss.repo_top(cwd)
    if not top:
        return
    rel = os.path.relpath(os.path.abspath(path), top)
    if rel.startswith(".."):
        return  # 저장소 밖 파일은 추적하지 않음
    sid = data.get("session_id") or "unknown"
    try:
        os.makedirs(ss.active_dir(root), exist_ok=True)
        if rel not in set(ss.read_touched(root, sid)):
            with open(ss.touched_path(root, sid), "a", encoding="utf-8") as f:
                f.write(rel + "\n")
    except OSError:
        return


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
```

- [ ] **Step 2: SIL 테스트**

공통 SIL 준비 블록 실행 후:

```bash
J() { printf '{"tool_name":"%s","tool_input":{"file_path":"%s"},"cwd":"%s","session_id":"sessA0000001"}' "$1" "$2" "$T"; }
J Edit "$T/a.md"  | python3 "$SW/hooks/session_workflow-track.py"
J Edit "$T/a.md"  | python3 "$SW/hooks/session_workflow-track.py"   # dedup
J Write "$T/b.md" | python3 "$SW/hooks/session_workflow-track.py"
J Bash "$T/c.md"  | python3 "$SW/hooks/session_workflow-track.py"   # 비추적 도구
J Edit /etc/hosts | python3 "$SW/hooks/session_workflow-track.py"   # 저장소 밖
cat "$T/.git/session_workflow/active/sessA0000001.touched"
```

Expected (정확히 2줄):

```
a.md
b.md
```

비-git no-op 확인:

```bash
N=$T-nogit && rm -rf "$N" && mkdir -p "$N/docs/claude_guideline/session_workflow"
touch "$N/docs/claude_guideline/session_workflow/session_workflow.md"
printf '{"tool_name":"Edit","tool_input":{"file_path":"%s/x.md"},"cwd":"%s","session_id":"s"}' "$N" "$N" \
  | python3 "$SW/hooks/session_workflow-track.py"; echo "exit=$?"
ls "$N" | sort
```

Expected: `exit=0`, `ls` 에 `docs` 만(상태 디렉터리 미생성).

- [ ] **Step 3: 커밋 (사용자 "커밋" 승인 후)**

```bash
git -C /home/amap/Project/claude_code/kuks_claude_skill_setup add session_workflow/hooks/session_workflow-track.py
git -C /home/amap/Project/claude_code/kuks_claude_skill_setup commit -m "feat(session_workflow): 세션별 수정 파일 추적 훅(track)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: 목적 게이트·충돌 경보 훅 `session_workflow-gate.py`

**Files:**
- Create: `session_workflow/hooks/session_workflow-gate.py`

**Interfaces:**
- Consumes: `session_state` 의 `state_root`, `ensure_session`, `save_session`, `read_touched`, `list_other_active`, `one_line`, `kst_now_str`, `PURPOSE_RE`
- Produces: stdout 주입 텍스트(목적 게이트 / 등록 확인 / 충돌 경보), meta 갱신(`purpose`·`last_seen`·`alerted`)

- [ ] **Step 1: 파일 작성**

```python
#!/usr/bin/env python3
"""UserPromptSubmit 훅 — 목적 선언 게이트 + 파일 충돌 경보 + last_seen 갱신.

목적 미등록이면 매 프롬프트 '목적부터 확인' 지시를 주입(모델 준수 비의존 강제).
'목적: …' 프롬프트는 verbatim 등록(재선언 = 덮어쓰기). 충돌 경보는 이 세션 touched 와
타 활성 세션 touched 의 신규 교집합만 1회(alerted 에 '<osid>:<path>' 로 기록).
계약: stdin JSON → stdout 주입. 항상 exit 0.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import session_state as ss  # noqa: E402


def conflict_lines(root, sid, meta):
    mine = set(ss.read_touched(root, sid))
    if not mine:
        return []
    alerted = set(meta.get("alerted") or [])
    lines = []
    for osid, ometa in ss.list_other_active(root, sid):
        for p in sorted(mine & set(ss.read_touched(root, osid))):
            key = f"{osid}:{p}"
            if key in alerted:
                continue
            alerted.add(key)
            purpose = ss.one_line(ometa.get("purpose") or "(미등록)")
            lines.append(f"- `{p}` — 세션 {osid[:8]}(목적: {purpose})도 수정 중")
    meta["alerted"] = sorted(alerted)
    return lines


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        return
    prompt = str(data.get("prompt", ""))
    cwd = data.get("cwd") or os.getcwd()
    root = ss.state_root(cwd)
    if not root:
        return
    sid = data.get("session_id") or "unknown"
    meta = ss.ensure_session(root, sid)
    meta["last_seen"] = ss.kst_now_str()

    out = []
    m = ss.PURPOSE_RE.match(prompt)
    if m:
        meta["purpose"] = m.group(1).strip()
        out.append("[SESSION-WORKFLOW] 세션 목적 등록 완료: "
                   + ss.one_line(meta["purpose"]))
    elif not meta.get("purpose"):
        out.append(
            "[SESSION-WORKFLOW — 목적 게이트]\n"
            "본 세션의 목적이 미등록입니다. 실질 작업 전에 사용자에게 세션 목적 1줄을 "
            "요청하고 `목적: …` 형식으로 입력하도록 안내하세요(입력 시 훅이 자동 등록). "
            "단발 질문이면 `목적: 단발 질문`으로 충분합니다."
        )

    conflicts = conflict_lines(root, sid, meta)
    if conflicts:
        out.append(
            "[SESSION-WORKFLOW — 파일 충돌 경보]\n"
            "다음 파일을 다른 활성 세션도 수정 중입니다. "
            "계속/중단/범위 조정을 사용자에게 1줄 확인 후 진행하세요:\n"
            + "\n".join(conflicts)
        )

    try:
        ss.save_session(root, sid, meta)
    except OSError:
        pass
    if out:
        print("\n\n".join(out))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
```

- [ ] **Step 2: SIL 테스트**

공통 SIL 준비 블록 실행 후:

```bash
G() { printf '{"prompt":"%s","cwd":"%s","session_id":"sessA0000001"}' "$1" "$T" \
  | python3 "$SW/hooks/session_workflow-gate.py"; }
echo "--1--"; G "안녕하세요"                       # 게이트 주입
echo "--2--"; G "목적: 훅 SIL 테스트"              # 등록
echo "--3--"; G "다음 작업 진행"                   # 게이트 없음(무출력)
python3 -c "import json;print(json.load(open('$T/.git/session_workflow/active/sessA0000001.json'))['purpose'])"
```

Expected: `--1--` 뒤 `[SESSION-WORKFLOW — 목적 게이트]` 블록, `--2--` 뒤 `[SESSION-WORKFLOW] 세션 목적 등록 완료: 훅 SIL 테스트`, `--3--` 뒤 무출력, 마지막 줄 `훅 SIL 테스트`.

충돌 경보 (1회성) 확인:

```bash
A="$T/.git/session_workflow/active"
printf 'a.md\n' > "$A/sessA0000001.touched"
printf '{"purpose":"리팩토링","started_at":"2026-07-12 08:00","last_seen":"2026-07-12 08:00","alerted":[]}' > "$A/sessB0000002.json"
printf 'a.md\nz.md\n' > "$A/sessB0000002.touched"
echo "--4--"; G "계속 진행"                        # 신규 교집합 a.md → 경보
echo "--5--"; G "계속 진행"                        # 이미 경보됨 → 무출력
```

Expected: `--4--` 뒤 `[SESSION-WORKFLOW — 파일 충돌 경보]` + `` - `a.md` — 세션 sessB000(목적: 리팩토링)도 수정 중 ``, `--5--` 뒤 무출력.

- [ ] **Step 3: 커밋 (사용자 "커밋" 승인 후)**

```bash
git -C /home/amap/Project/claude_code/kuks_claude_skill_setup add session_workflow/hooks/session_workflow-gate.py
git -C /home/amap/Project/claude_code/kuks_claude_skill_setup commit -m "feat(session_workflow): 목적 선언 게이트·파일 충돌 경보 훅(gate)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: 세션 시작 훅 `session_workflow-start.py`

**Files:**
- Create: `session_workflow/hooks/session_workflow-start.py`

**Interfaces:**
- Consumes: `session_state` 의 `state_root`, `ensure_session`, `save_session`, `list_other_active`, `is_stale`, `read_touched`, `one_line`, `handoff_dir`, `parse_handoff_summary`, `HANDOFF_KEEP_DAYS`
- Produces: stdout 주입(활성 세션·잔류 의심·대기 handoff·목적 게이트 예고), `active/<sid>.json` 등록, 14일 경과 handoff 삭제

- [ ] **Step 1: 파일 작성**

```python
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
```

- [ ] **Step 2: SIL 테스트**

공통 SIL 준비 블록 실행 후 (타 세션 1개 = 잔류, handoff 1건 사전 배치):

```bash
A="$T/.git/session_workflow/active"; H="$T/.git/session_workflow/handoff"
mkdir -p "$A" "$H"
printf '{"purpose":"리팩토링","started_at":"2026-07-10 08:00","last_seen":"2026-07-10 08:00","alerted":[]}' > "$A/sessB0000002.json"
printf 'src/old.py\n' > "$A/sessB0000002.touched"
printf -- '# 세션 인수인계 · sess:sessC000\n- 목적: 문서 정리\n- 시작: 2026-07-11 09:00 (KST) · 종료: 2026-07-11 10:00 (KST)\n- 미커밋 파일 (2개):\n  - d1.md\n  - d2.md\n- 이 세션 수정 파일 전체: 3개\n' > "$H/sessC0000003.md"
printf '{"cwd":"%s","session_id":"sessA0000001"}' "$T" | python3 "$SW/hooks/session_workflow-start.py"
ls "$A"
```

Expected 출력에 포함: `활성 세션:`, `- sessB000 · 목적: 리팩토링 · 최근 활동: 2026-07-10 08:00 ⚠ 잔류 의심(비정상 종료 가능)`, 그 아래 `    - src/old.py`, `대기 인수인계(handoff) 1건:` + `sessC0000003.md · 목적: 문서 정리 · 미커밋 2개`, 마지막에 목적 게이트 예고. `ls` 에 `sessA0000001.json` 생성 확인.

resume(목적 보존) 확인:

```bash
python3 - "$T" <<'EOF'
import sys, json
p = sys.argv[1] + "/.git/session_workflow/active/sessA0000001.json"
m = json.load(open(p)); m["purpose"] = "이미 등록된 목적"
json.dump(m, open(p, "w"), ensure_ascii=False)
EOF
printf '{"cwd":"%s","session_id":"sessA0000001"}' "$T" | python3 "$SW/hooks/session_workflow-start.py" | tail -1
```

Expected: 마지막 줄이 목적 게이트 예고가 **아님** (handoff 안내 또는 세션 목록).

- [ ] **Step 3: 커밋 (사용자 "커밋" 승인 후)**

```bash
git -C /home/amap/Project/claude_code/kuks_claude_skill_setup add session_workflow/hooks/session_workflow-start.py
git -C /home/amap/Project/claude_code/kuks_claude_skill_setup commit -m "feat(session_workflow): 세션 시작 레지스트리·주입 훅(start)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: 세션 종료 훅 `session_workflow-end.py`

**Files:**
- Create: `session_workflow/hooks/session_workflow-end.py`

**Interfaces:**
- Consumes: `session_state` 의 `state_root`, `repo_top`, `load_session`, `read_touched`, `format_handoff`, `kst_now_str`, `handoff_dir`, `session_json`, `touched_path`
- Produces: 미커밋 잔여 시 `handoff/<sid>.md` (Task 4 의 `parse_handoff_summary` 가 읽는 형식), 자기 active 파일 삭제

- [ ] **Step 1: 파일 작성**

```python
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
```

- [ ] **Step 2: SIL 테스트**

공통 SIL 준비 블록 실행 후 (미커밋 1 + 커밋됨 1):

```bash
A="$T/.git/session_workflow/active"; mkdir -p "$A"
echo dirty > "$T/un.md"                      # 미추적(미커밋)
echo clean > "$T/co.md"
git -C "$T" add co.md && git -C "$T" -c user.email=t@t -c user.name=t commit -qm init
printf '{"purpose":"종료 테스트","started_at":"2026-07-12 08:00","last_seen":"2026-07-12 09:00","alerted":[]}' > "$A/sessA0000001.json"
printf 'un.md\nco.md\n' > "$A/sessA0000001.touched"
printf '{"cwd":"%s","session_id":"sessA0000001"}' "$T" | python3 "$SW/hooks/session_workflow-end.py"
echo "--handoff--"; cat "$T/.git/session_workflow/handoff/sessA0000001.md"
echo "--active--"; ls "$A" 2>/dev/null | wc -l
```

Expected: handoff 에 `- 목적: 종료 테스트`, `- 미커밋 파일 (1개):` + `  - un.md` (co.md 없음), `- 이 세션 수정 파일 전체: 2개`. `--active--` 는 `0` (자기 파일 삭제).

전부 커밋 시 handoff 미생성 확인:

```bash
git -C "$T" add un.md && git -C "$T" -c user.email=t@t -c user.name=t commit -qm second
rm -f "$T/.git/session_workflow/handoff/sessA0000001.md"
printf '{"purpose":"x","started_at":"2026-07-12 08:00","last_seen":"2026-07-12 09:00","alerted":[]}' > "$A/sessA0000001.json"
printf 'un.md\nco.md\n' > "$A/sessA0000001.touched"
printf '{"cwd":"%s","session_id":"sessA0000001"}' "$T" | python3 "$SW/hooks/session_workflow-end.py"
ls "$T/.git/session_workflow/handoff/" 2>/dev/null | wc -l; ls "$A" | wc -l
```

Expected: `0` 과 `0` (handoff 미생성 + 레지스트리 해제).

- [ ] **Step 3: 커밋 (사용자 "커밋" 승인 후)**

```bash
git -C /home/amap/Project/claude_code/kuks_claude_skill_setup add session_workflow/hooks/session_workflow-end.py
git -C /home/amap/Project/claude_code/kuks_claude_skill_setup commit -m "feat(session_workflow): 종료 handoff 박제·레지스트리 해제 훅(end)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: 생애주기 SOP SSOT `session_workflow.md`

**Files:**
- Create: `session_workflow/session_workflow.md`

**Interfaces:**
- Consumes: 없음 (자기완결 규칙 문서 — 자매 SSOT 하이퍼링크 0)
- Produces: 활성화 게이트 대상 경로 규칙(`docs/claude_guideline/session_workflow/session_workflow.md`) — 모든 훅의 `rule_active` 가 이 설치 경로 존재를 검사

- [ ] **Step 1: 파일 작성** (아래 전문 그대로)

````markdown
# 세션 워크플로 (다중 세션 진행·종료)

> **본 파일은 지시용.** 한 저장소를 공유하는 다중 세션의 생애주기(시작→진행→종료→인수인계) 규칙의 self-contained 단일 근원(Single Source of Truth).

본 코어는 self-contained 다 — 본문 외 가이드라인·도구·Skill 의존 0.

## 설치

본 번들 폴더(`session_workflow/`)의 `install.sh` 로 설치한다:

```bash
cd session_workflow && ./install.sh <타깃-프로젝트-루트>
```

스크립트가 (1) `session_workflow.md` 와 훅 5개(`session_state.py`·start·gate·track·end)를 `docs/claude_guideline/session_workflow/` 아래로 복사, (2) 등록 스니펫(`claude.snippet.md`)을 타깃 `CLAUDE.md` 에 append, (3) `.claude/settings.json` 에 SessionStart·UserPromptSubmit·PostToolUse·SessionEnd 훅을 멱등 등록한다.

**활성화 게이트**: 본 파일이 `docs/claude_guideline/session_workflow/session_workflow.md` 경로에 없으면 본 룰과 모든 훅은 비활성(no-op).

## 0. 상태 저장소 (훅 소관 — 모델 수동 편집 금지)

상태는 `.git/session_workflow/` (git 내부 = 항상 비커밋, worktree 는 공유 git dir 기준 통일)에 있으며 **훅이 결정적으로 관리**한다:

| 경로 | 내용 | 쓰기 주체 |
|---|---|---|
| `active/<session_id>.json` | 목적·시작/최근 활동 시각(KST)·경보 이력 | start·gate 훅 |
| `active/<session_id>.touched` | 이 세션이 수정한 파일(저장소 상대경로) | track 훅 |
| `handoff/<session_id>.md` | 종료 시 미커밋 잔여 인수인계 | end 훅 |

각 세션은 자기 이름 파일에만 쓴다(경합 구조적 부재). 모델이 직접 편집하는 경우는 **handoff 픽업 완료 후 해당 handoff 파일 삭제** 하나뿐이다.

## 1. 시작 — 목적 선언 게이트

- SessionStart 훅이 세션을 레지스트리에 등록하고 ① 다른 활성 세션(목적·최근 활동·잔류 의심) ② 대기 handoff ③ 목적 게이트 예고를 주입한다.
- **모델**: 목적 미등록 상태에서는 실질 작업 전에 사용자에게 세션 목적 1줄을 요청하고 `목적: …` 형식 입력을 안내한다. 훅이 매 프롬프트 이 지시를 반복 주입한다(누락 불가).
- **사용자**: `목적: <이 세션이 할 일 1줄>` 로 입력 → 훅이 verbatim 등록·게이트 해제. 재선언은 덮어쓰기(목적 변경 허용). 단발 질문 세션은 `목적: 단발 질문` 으로 충분.
- 등록된 목적은 충돌 경보·handoff·세션 산출 문서 제목(worklog 등 프로젝트 관례)의 기준이 된다. **목적에 비밀정보를 쓰지 않는다**(verbatim 저장 — 마스킹 불가).
- 다른 활성 세션의 목적·대기 handoff 와 범위가 겹치면 시작 시점에 사용자에게 1줄 확인으로 범위를 조정한다.

## 2. 진행 — 레지스트리·파일 충돌 경보

- track 훅이 Write/Edit/NotebookEdit 파일을 세션별로 누적하고, gate 훅이 매 프롬프트 last_seen 을 갱신한다.
- 두 활성 세션의 수정 파일이 겹치면 **신규 교집합에 한해 1회** 경보가 주입된다: "파일 X 는 세션 Y(목적: Z)도 수정 중".
- **모델**: 경보 수신 시 진행을 멈추고 사용자에게 계속/중단/범위 조정을 1줄 확인한 후 진행한다. 경보는 권고(차단 아님) — staging/commit 강제는 본 번들 소관이 아니다.
- 원칙: **이 세션 산출물만 수정**한다. 타 세션이 만지는 파일이 꼭 필요하면 사용자 확인 후 진행.

## 3. 종료 — 2단 방어

**1단 (명시 종료 — 모델 수행)**: 사용자가 "세션 종료" 를 선언하면:

1. 이 세션 수정 파일 중 미커밋 산출물을 확인해 보고한다.
2. 커밋 여부를 사용자에게 확인한다(커밋은 사용자 명시 요청에만 — 이 세션 산출물만 명시 staging).
3. 결과 기록(worklog 등 프로젝트 관례)에 세션 목적을 제목으로 남긴다.
4. 잔여 미완 작업이 있으면 사용자에게 알리고 세션을 닫도록 안내한다.

**2단 (결정적 — SessionEnd 훅)**: 세션 종료 시 훅이 touched 중 미커밋 파일을 감지해 `handoff/<session_id>.md` 로 박제하고 레지스트리를 해제한다. 미커밋이 없으면 handoff 없이 조용히 해제한다. 1단을 잊어도 유실이 없다.

## 4. 인수인계 (handoff)

- 다음 세션 시작 시 SessionStart 훅이 대기 handoff(목적·미커밋 개수·전문 경로)를 주입한다.
- **모델**: handoff 픽업은 사용자 동의 후에만. 픽업한 세션이 처리를 완료하면 해당 handoff 파일을 삭제한다.
- 14일 경과 handoff 는 훅이 자동 정리한다.

## 5. 한계 (정직)

- **비정상 종료**(탭 강제 종료 등)는 SessionEnd 미발화 가능 → active 잔류. 다음 세션 시작 주입이 "잔류 의심"으로 표시하고 touched 를 노출하므로 수동 회수한다(자동 handoff 승격은 살아있는 세션 오판 위험으로 하지 않음).
- **Bash 로만 생성한 파일은 미추적**(도구 matcher 한계) → 충돌 경보·handoff 대상에서 빠질 수 있다.
- 충돌 감지는 **파일 단위**(라인 단위 아님).
- 목적·handoff 는 verbatim 저장 — 비밀정보 의미 마스킹 불가.
- python3 부재 시 훅 미동작 — 본 규칙 텍스트(절차)만 생존한다.

## 룰 (요약)

1. 세션 시작 시 목적 선언(`목적: …`) 전에는 실질 작업을 시작하지 않는다(사용자에게 요청).
2. 이 세션 산출물만 수정 — 충돌 경보 시 사용자 1줄 확인 후 진행.
3. "세션 종료" 선언 시: 미커밋 확인 → 커밋 여부 확인 → 결과 기록 → 닫기 안내.
4. handoff 는 사용자 동의 후 픽업, 완료 시 해당 파일 삭제.
5. 상태 저장소(`.git/session_workflow/`)는 훅 소관 — 모델 수동 편집 금지(handoff 삭제 예외).
````

- [ ] **Step 2: 검증** — 자매 SSOT 링크 0 확인:

```bash
grep -nE '\]\((\.\./|[a-z_]+/)' /home/amap/Project/claude_code/kuks_claude_skill_setup/session_workflow/session_workflow.md; echo "links=$?"
```

Expected: `links=1` (매치 없음 = 링크 0).

- [ ] **Step 3: 커밋 (사용자 "커밋" 승인 후)**

```bash
git -C /home/amap/Project/claude_code/kuks_claude_skill_setup add session_workflow/session_workflow.md
git -C /home/amap/Project/claude_code/kuks_claude_skill_setup commit -m "feat(session_workflow): 다중 세션 생애주기 SOP SSOT

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 7: 등록 스니펫 `claude.snippet.md`

**Files:**
- Create: `session_workflow/claude.snippet.md`

**Interfaces:**
- Consumes: 없음
- Produces: 마커 `kuks_agent_setup:session_workflow` — Task 8 install.sh 가 중복 방지에 사용

- [ ] **Step 1: 파일 작성** (아래 전문 그대로, 2줄)

```markdown
<!-- kuks_agent_setup:session_workflow -->
- 세션 생애주기(시작→진행→종료)는 session_workflow 훅이 관리한다: 세션 목적 선언 게이트(`목적: …` 입력 시 훅이 자동 등록), 활성 세션 레지스트리·파일 충돌 경보, 종료 시 미커밋 잔여 handoff 박제(규칙: docs/claude_guideline/session_workflow/session_workflow.md). 모델은 목적 미등록 상태에서 실질 작업 전에 사용자에게 목적을 확인한다.
```

- [ ] **Step 2: 커밋 (사용자 "커밋" 승인 후)**

```bash
git -C /home/amap/Project/claude_code/kuks_claude_skill_setup add session_workflow/claude.snippet.md
git -C /home/amap/Project/claude_code/kuks_claude_skill_setup commit -m "feat(session_workflow): CLAUDE.md 등록 스니펫

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 8: 설치 스크립트 `install.sh`

**Files:**
- Create: `session_workflow/install.sh` (실행권한 +x)

**Interfaces:**
- Consumes: Task 1~7 산출물 전부(복사 대상), 마커 `kuks_agent_setup:session_workflow`
- Produces: 타깃에 `docs/claude_guideline/session_workflow/{session_workflow.md,hooks/*.py}`, CLAUDE.md 등록, settings.json 4개 이벤트 훅 등록

- [ ] **Step 1: 파일 작성**

```bash
#!/usr/bin/env bash
# install.sh — session_workflow 번들 설치 (폴더 자기완결)
#
# 사용법: ./install.sh <타깃-프로젝트-루트>
#   예:   ./install.sh ~/myproject
#
# 동작:
#   1) session_workflow.md + 훅 5개를 <타깃>/docs/claude_guideline/session_workflow/ 로 복사
#   2) claude.snippet.md 를 <타깃>/CLAUDE.md 에 append (마커 중복 스킵)
#   3) .claude/settings.json 에 SessionStart·UserPromptSubmit·PostToolUse·SessionEnd 훅 멱등 등록
#   상태는 .git/session_workflow/ (비커밋) — .gitignore 불요.
#   설치 산출물: 규칙(session_workflow.md)·훅. install.sh·claude.snippet.md 는 복사하지 않는다.

set -euo pipefail

BUNDLE="session_workflow"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TARGET="${1:-}"
[ -n "$TARGET" ] || { echo "사용법: ./install.sh <타깃-프로젝트-루트>"; exit 1; }
[ -d "$TARGET" ] || { echo "오류: 타깃 경로 없음: $TARGET"; exit 1; }

# 1) 규칙 파일 복사 (등록 스니펫 제외)
DEST="$TARGET/docs/claude_guideline/$BUNDLE"
mkdir -p "$DEST"
for f in "$SRC"/*.md; do
  base="$(basename "$f")"
  [ "$base" = "claude.snippet.md" ] && continue
  cp "$f" "$DEST/$base"
done
echo "✓ 규칙 복사: docs/claude_guideline/$BUNDLE/"

# 2) CLAUDE.md 등록 (마커로 중복 방지)
CLAUDE_MD="$TARGET/CLAUDE.md"
MARKER="kuks_agent_setup:$BUNDLE"
touch "$CLAUDE_MD"
if grep -qF "$MARKER" "$CLAUDE_MD"; then
  echo "• CLAUDE.md 등록 이미 존재 — 스킵"
else
  printf '\n' >> "$CLAUDE_MD"
  cat "$SRC/claude.snippet.md" >> "$CLAUDE_MD"
  echo "✓ CLAUDE.md 등록 추가"
fi

# 3) 훅 복사
mkdir -p "$DEST/hooks"
for hf in session_state.py session_workflow-start.py session_workflow-gate.py \
          session_workflow-track.py session_workflow-end.py; do
  cp "$SRC/hooks/$hf" "$DEST/hooks/$hf"
  chmod +x "$DEST/hooks/$hf" 2>/dev/null || true
done
echo "✓ 훅 복사: docs/claude_guideline/$BUNDLE/hooks/"

# 4) settings.json 훅 멱등 등록
PYBIN=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1; then PYBIN="$c"; break; fi
done
if [ -z "$PYBIN" ]; then
  echo "⚠ python3/python 없음 — settings.json 훅 등록 건너뜀. 수동 등록 필요."
else
  mkdir -p "$TARGET/.claude"
  SETTINGS="$TARGET/.claude/settings.json"
  [ -f "$SETTINGS" ] && cp "$SETTINGS" "$SETTINGS.bak" && echo "✓ 백업: .claude/settings.json.bak"
  H="\$CLAUDE_PROJECT_DIR/docs/claude_guideline/$BUNDLE/hooks"
  "$PYBIN" - "$SETTINGS" \
    "$PYBIN \"$H/session_workflow-start.py\"" \
    "$PYBIN \"$H/session_workflow-gate.py\"" \
    "$PYBIN \"$H/session_workflow-track.py\"" \
    "$PYBIN \"$H/session_workflow-end.py\"" <<'PYEOF'
import json, sys
settings_path, start, gate, track, end = sys.argv[1:6]
try:
    with open(settings_path, encoding="utf-8") as f:
        cfg = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    cfg = {}
hooks = cfg.setdefault("hooks", {})

def ensure(event, cmd, timeout, matcher=None):
    groups = hooks.setdefault(event, [])
    if any(h.get("command") == cmd for g in groups for h in g.get("hooks", [])):
        return "스킵"
    g = {"hooks": [{"type": "command", "command": cmd, "timeout": timeout}]}
    if matcher is not None:
        g["matcher"] = matcher
    groups.append(g)
    return "추가"

a = ensure("SessionStart", start, 10)
b = ensure("UserPromptSubmit", gate, 5)
c = ensure("PostToolUse", track, 5, matcher="Write|Edit|MultiEdit|NotebookEdit")
d = ensure("SessionEnd", end, 10)
with open(settings_path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
print(f"✓ settings.json 훅 등록: SessionStart={a}, UserPromptSubmit={b}, "
      f"PostToolUse={c}, SessionEnd={d}")
PYEOF
fi

echo "완료: $BUNDLE → $TARGET"
```

- [ ] **Step 2: 설치·멱등 SIL 테스트**

```bash
SW=/home/amap/Project/claude_code/kuks_claude_skill_setup/session_workflow
chmod +x "$SW/install.sh"
I=/tmp/claude-1000/-home-amap-Project-claude-code/5db6f94c-168b-46a8-b05d-f44b080ddae6/scratchpad/swinstall
rm -rf "$I" && mkdir -p "$I" && git -C "$I" init -q
"$SW/install.sh" "$I"
echo "--2nd--"; "$SW/install.sh" "$I"
ls "$I/docs/claude_guideline/session_workflow" "$I/docs/claude_guideline/session_workflow/hooks"
grep -c "kuks_agent_setup:session_workflow" "$I/CLAUDE.md"
grep -c "session_workflow-start.py" "$I/.claude/settings.json"
python3 -c "import json;h=json.load(open('$I/.claude/settings.json'))['hooks'];print(sorted(h.keys()));print(h['PostToolUse'][0]['matcher'])"
```

Expected: 1차 실행 `✓` 4종, 2차 실행 `• CLAUDE.md 등록 이미 존재 — 스킵` + `settings.json 훅 등록: …=스킵` 전부 스킵. `session_workflow.md` + 훅 5개 존재. 두 grep 모두 `1` (중복 없음). 마지막 출력 `['PostToolUse', 'SessionEnd', 'SessionStart', 'UserPromptSubmit']` 와 `Write|Edit|MultiEdit|NotebookEdit`.

- [ ] **Step 3: 커밋 (사용자 "커밋" 승인 후)**

```bash
git -C /home/amap/Project/claude_code/kuks_claude_skill_setup add session_workflow/install.sh
git -C /home/amap/Project/claude_code/kuks_claude_skill_setup commit -m "feat(session_workflow): 설치 스크립트(복사+등록+settings 멱등)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 9: README 등록 + E2E 2-세션 SIL

**Files:**
- Modify: `README.md` (자산 목록 표 + 설치 방식 bullet — git_workflow 행 아래에 추가)

**Interfaces:**
- Consumes: Task 1~8 완성 번들
- Produces: 저장소 문서 정합 + 전 구간 검증 증거

- [ ] **Step 1: README 자산 목록 표에 행 추가** (`git_workflow/` 행 바로 아래)

```markdown
| [session_workflow/](session_workflow/session_workflow.md) | 다중 세션 생애주기 — 목적 선언 게이트·활성 세션 레지스트리·파일 충돌 경보·종료 handoff | 프로젝트별 | `cd session_workflow && ./install.sh <타깃>` |
```

- [ ] **Step 2: README "설치 방식" 절에 bullet 추가** (`- **git_workflow**` 항목 바로 아래)

```markdown
- **session_workflow** — 코어(`session_workflow.md`) + 훅 5개(`session_state.py`·start·gate·track·end)를 `docs/claude_guideline/session_workflow/` 로 복사 + `CLAUDE.md` 등록 + `settings.json` 에 SessionStart·UserPromptSubmit·PostToolUse·SessionEnd 멱등 등록. 세션 목적(`목적: …`) 선언 게이트, 세션별 수정 파일 추적·충돌 경보, 종료 시 미커밋 잔여를 `.git/session_workflow/handoff/` 로 박제(상태는 .git 내부 = 비커밋).
```

- [ ] **Step 3: E2E 2-세션 SIL** (Task 8 의 설치본 `$I` 사용 — 설치된 훅 경로로 전 생애주기 재현)

```bash
I=/tmp/claude-1000/-home-amap-Project-claude-code/5db6f94c-168b-46a8-b05d-f44b080ddae6/scratchpad/swinstall
HK="$I/docs/claude_guideline/session_workflow/hooks"
SA=e2eA00000001; SB=e2eB00000002; SC=e2eC00000003
# ① A 시작 → 게이트 → 목적 등록
printf '{"cwd":"%s","session_id":"%s"}' "$I" "$SA" | python3 "$HK/session_workflow-start.py"
printf '{"prompt":"안녕","cwd":"%s","session_id":"%s"}' "$I" "$SA" | python3 "$HK/session_workflow-gate.py"
printf '{"prompt":"목적: A-기능 개발","cwd":"%s","session_id":"%s"}' "$I" "$SA" | python3 "$HK/session_workflow-gate.py"
# ② A 가 파일 수정 (track)
echo work > "$I/feat.md"
printf '{"tool_name":"Write","tool_input":{"file_path":"%s/feat.md"},"cwd":"%s","session_id":"%s"}' "$I" "$I" "$SA" | python3 "$HK/session_workflow-track.py"
# ③ B 시작 → A 가 활성 세션으로 보임 → B 목적 등록 → 같은 파일 수정 → B 에 충돌 경보
printf '{"cwd":"%s","session_id":"%s"}' "$I" "$SB" | python3 "$HK/session_workflow-start.py"
printf '{"prompt":"목적: B-문서 수정","cwd":"%s","session_id":"%s"}' "$I" "$SB" | python3 "$HK/session_workflow-gate.py"
printf '{"tool_name":"Edit","tool_input":{"file_path":"%s/feat.md"},"cwd":"%s","session_id":"%s"}' "$I" "$I" "$SB" | python3 "$HK/session_workflow-track.py"
echo "--conflict--"
printf '{"prompt":"진행","cwd":"%s","session_id":"%s"}' "$I" "$SB" | python3 "$HK/session_workflow-gate.py"
# ④ A 종료(미커밋) → handoff 생성
printf '{"cwd":"%s","session_id":"%s"}' "$I" "$SA" | python3 "$HK/session_workflow-end.py"
echo "--handoff--"; ls "$I/.git/session_workflow/handoff/"
# ⑤ C 시작 → handoff 주입 확인
echo "--C-start--"
printf '{"cwd":"%s","session_id":"%s"}' "$I" "$SC" | python3 "$HK/session_workflow-start.py"
```

Expected: ① 게이트 블록 → `목적 등록 완료: A-기능 개발`. ③ B 시작 주입에 `e2eA0000 · 목적: A-기능 개발`, `--conflict--` 뒤 `feat.md` 충돌 경보(세션 e2eA0000, 목적: A-기능 개발). ④ `--handoff--` 에 `e2eA00000001.md`. ⑤ `--C-start--` 주입에 활성 세션 B + `대기 인수인계(handoff) 1건` + `목적: A-기능 개발 · 미커밋 1개`.

- [ ] **Step 4: 커밋 (사용자 "커밋" 승인 후)**

```bash
git -C /home/amap/Project/claude_code/kuks_claude_skill_setup add README.md
git -C /home/amap/Project/claude_code/kuks_claude_skill_setup commit -m "docs(README): session_workflow 번들 등록

Co-Authored-By: Claude <noreply@anthropic.com>"
```

- [ ] **Step 5: (선택·사용자 "푸쉬" 승인 후)** `git push origin main && git push fito main`
