#!/usr/bin/env bash
# install.sh — user_instruction 번들 설치 (폴더 자기완결)
#
# 사용법: ./install.sh <타깃-프로젝트-루트>
#   예:   ./install.sh ~/myproject
#
# 동작:
#   1) recording.md + 훅(reminder·merge·session_record) 을 <타깃>/docs/claude_guideline/user_instruction/ 로 복사
#   2) claude.snippet.md 를 <타깃>/CLAUDE.md 에 append (덮어쓰기 아님, 중복 시 스킵)
#   3) .claude/settings.json 에 UserPromptSubmit(reminder)+SessionEnd(merge) 훅 멱등 등록
#   4) .gitignore 에 docs/user_instructions/sessions/ 추가 (세션별 전이 파일)
#   설치 산출물: 규칙(recording.md)·훅. install.sh·claude.snippet.md 는 복사하지 않는다.

set -euo pipefail

BUNDLE="user_instruction"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TARGET="${1:-}"
[ -n "$TARGET" ] || { echo "사용법: ./install.sh <타깃-프로젝트-루트>"; exit 1; }
[ -d "$TARGET" ] || { echo "오류: 타깃 경로 없음: $TARGET"; exit 1; }

# 1) 규칙 파일 복사 (등록 스니펫 제외, install.sh 는 .md 아니라 자동 제외)
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

# 강제 훅 — 세션 격리 기록/병합 (모델 비의존)
mkdir -p "$DEST/hooks"
for hf in user_instruction-reminder.py user_instruction-merge.py session_record.py; do
  if [ -f "$SRC/hooks/$hf" ]; then
    cp "$SRC/hooks/$hf" "$DEST/hooks/$hf"
    chmod +x "$DEST/hooks/$hf" 2>/dev/null || true
  fi
done
echo "✓ 훅 복사: docs/claude_guideline/$BUNDLE/hooks/ (reminder·merge·session_record)"

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

  # .gitignore 에 세션별 전이 파일 디렉터리 추가 (멱등)
  GI="$TARGET/.gitignore"
  LINE="docs/user_instructions/sessions/"
  touch "$GI"
  grep -qxF "$LINE" "$GI" || { printf '%s\n' "$LINE" >> "$GI"; echo "✓ .gitignore: $LINE 추가"; }
fi

echo "완료: $BUNDLE → $TARGET"
