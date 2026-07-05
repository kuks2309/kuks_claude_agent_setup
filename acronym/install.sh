#!/usr/bin/env bash
# install.sh — 영어 약자 표기 번들 전역 설치 (~/.claude)
#
# 사용법:
#   ./install.sh                  # CLAUDE.md 규칙 등록 + Stop 검토 훅 등록
#   (CLAUDE_HOME 환경변수로 설치 루트 변경 가능 — 테스트용)
#
# 동작:
#   1) 규칙(acronym.md) + Stop 검토 훅(acronym-review.py)을 $CLAUDE_HOME/acronym/ 로 복사
#   2) claude.snippet.md 를 $CLAUDE_HOME/CLAUDE.md 에 append (마커 중복방지)
#   3) $CLAUDE_HOME/settings.json 에 Stop 검토 훅 멱등 등록 (기존 보존, 사전 백업)
#   * 마이그레이션: 옛 훅(acronym-reminder.sh / acronym-check.py)의 파일과 settings 등록을 제거.
#
# 검토 훅은 답변을 마친 뒤 후보 약자를 제시해 AI 가 스스로 병기 누락을 보완하게 한다
# (위반 단정·강제 재작성 아님 — 규칙 본문은 acronym.md 참조).

set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
DEST="$CLAUDE_HOME/acronym"

# 1) 규칙·검토 훅 복사 + 옛 훅 파일 정리
mkdir -p "$DEST"
cp "$SRC/acronym.md"               "$DEST/acronym.md"
cp "$SRC/hooks/acronym-review.py"  "$DEST/acronym-review.py"
chmod +x "$DEST/acronym-review.py"
rm -f "$DEST/acronym-reminder.sh" "$DEST/acronym-check.py"  # 옛 훅 파일 제거
echo "✓ 규칙·검토 훅 복사: $DEST (옛 훅 파일 정리됨)"

# 2) CLAUDE.md 등록 (마커 중복방지)
CLAUDE_MD="$CLAUDE_HOME/CLAUDE.md"
MARKER="kuks_agent_setup:acronym"
touch "$CLAUDE_MD"
if grep -qF "$MARKER" "$CLAUDE_MD"; then
  echo "• CLAUDE.md 등록 이미 존재 — 스킵"
else
  printf '\n' >> "$CLAUDE_MD"
  cat "$SRC/claude.snippet.md" >> "$CLAUDE_MD"
  echo "✓ CLAUDE.md 등록 추가"
fi

# 3) settings.json 훅 등록 (사전 백업 후 python 멱등 merge)
#    - 등록: Stop = acronym-review.py
#    - 제거: 옛 acronym-reminder.sh(UserPromptSubmit) / acronym-check.py(Stop) 등록
SETTINGS="$CLAUDE_HOME/settings.json"
[ -f "$SETTINGS" ] && cp "$SETTINGS" "$SETTINGS.bak" && echo "✓ 백업: $SETTINGS.bak"
python3 - "$SETTINGS" "$DEST" <<'PYEOF'
import json, sys
settings_path, dest = sys.argv[1], sys.argv[2]
review = f"python3 {dest}/acronym-review.py"
# 옛 등록 식별용 부분문자열 (경로가 달라도 파일명으로 매칭)
stale = ("acronym-reminder.sh", "acronym-check.py")
try:
    with open(settings_path, encoding="utf-8") as f:
        cfg = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    cfg = {}
hooks = cfg.setdefault("hooks", {})

def strip_stale():
    removed = 0
    for event in list(hooks):
        groups = hooks[event]
        for g in groups:
            before = g.get("hooks", [])
            after = [h for h in before if not any(s in h.get("command", "") for s in stale)]
            removed += len(before) - len(after)
            g["hooks"] = after
        # 빈 그룹/이벤트 정리
        hooks[event] = [g for g in groups if g.get("hooks")]
        if not hooks[event]:
            del hooks[event]
    return removed

def ensure(event, cmd, timeout):
    groups = hooks.setdefault(event, [])
    for g in groups:
        for h in g.get("hooks", []):
            if h.get("command") == cmd:
                return "스킵"
    groups.append({"hooks": [{"type": "command", "command": cmd, "timeout": timeout}]})
    return "추가"

n = strip_stale()
a = ensure("Stop", review, 10)
with open(settings_path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
print(f"✓ settings.json: 옛 훅 등록 {n}건 제거, Stop 검토 훅={a}")
PYEOF

echo "완료: acronym → $CLAUDE_HOME (적용은 세션 재시작 후)"
