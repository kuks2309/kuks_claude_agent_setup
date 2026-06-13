#!/usr/bin/env bash
# install.sh — 영어 약자 표기 번들 전역 설치 (~/.claude)
#
# 사용법: ./install.sh
#   (CLAUDE_HOME 환경변수로 설치 루트 변경 가능 — 테스트용)
#
# 동작:
#   1) 규칙·훅을 $CLAUDE_HOME/acronym/ 로 복사
#   2) claude.snippet.md 를 $CLAUDE_HOME/CLAUDE.md 에 append (마커 중복방지)
#   3) $CLAUDE_HOME/settings.json 에 UserPromptSubmit·Stop 훅 멱등 등록 (기존 보존, 사전 백업)

set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
DEST="$CLAUDE_HOME/acronym"

# 1) 규칙·훅 복사
mkdir -p "$DEST"
cp "$SRC/acronym.md"               "$DEST/acronym.md"
cp "$SRC/hooks/acronym-reminder.sh" "$DEST/acronym-reminder.sh"
cp "$SRC/hooks/acronym-check.py"    "$DEST/acronym-check.py"
chmod +x "$DEST/acronym-reminder.sh" "$DEST/acronym-check.py"
echo "✓ 규칙·훅 복사: $DEST"

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
SETTINGS="$CLAUDE_HOME/settings.json"
[ -f "$SETTINGS" ] && cp "$SETTINGS" "$SETTINGS.bak" && echo "✓ 백업: $SETTINGS.bak"
python3 - "$SETTINGS" "$DEST" <<'PYEOF'
import json, sys
settings_path, dest = sys.argv[1], sys.argv[2]
reminder = f"bash {dest}/acronym-reminder.sh"
check = f"python3 {dest}/acronym-check.py"
try:
    with open(settings_path, encoding="utf-8") as f:
        cfg = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    cfg = {}
hooks = cfg.setdefault("hooks", {})

def ensure(event, cmd, timeout):
    groups = hooks.setdefault(event, [])
    for g in groups:
        for h in g.get("hooks", []):
            if h.get("command") == cmd:
                return "스킵"
    groups.append({"hooks": [{"type": "command", "command": cmd, "timeout": timeout}]})
    return "추가"

a = ensure("UserPromptSubmit", reminder, 5)
b = ensure("Stop", check, 10)
with open(settings_path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
print(f"✓ settings.json 훅 등록: UserPromptSubmit={a}, Stop={b}")
PYEOF

echo "완료: acronym → $CLAUDE_HOME (적용은 세션 재시작 후)"
