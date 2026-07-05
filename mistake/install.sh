#!/usr/bin/env bash
# install.sh — mistake 번들 설치 (폴더 자기완결)
#
# 사용법: ./install.sh <타깃-프로젝트-루트>
#
# 동작:
#   1) mistake.md + checks/ + hooks/ 를 <타깃>/docs/claude_guideline/mistake/ 로 복사
#   2) entry 폴더 <타깃>/docs/claude-mistake/ 생성 (기존 내용 비파괴)
#   3) claude.snippet.md 를 <타깃>/CLAUDE.md 에 append (마커 중복방지)
#   4) SessionStart 훅(mistake-inject.py) 을 .claude/settings.json 에 멱등 등록
#   설치 산출물은 규칙·이빨·훅뿐 — install.sh·claude.snippet.md·README.md 는 복사하지 않는다.

set -euo pipefail

BUNDLE="mistake"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TARGET="${1:-}"
[ -n "$TARGET" ] || { echo "사용법: ./install.sh <타깃-프로젝트-루트>"; exit 1; }
[ -d "$TARGET" ] || { echo "오류: 타깃 경로 없음: $TARGET"; exit 1; }

# 1) 규칙 + 이빨 복사
DEST="$TARGET/docs/claude_guideline/$BUNDLE"
mkdir -p "$DEST/checks"
cp "$SRC/mistake.md" "$DEST/mistake.md"
cp "$SRC/checks/entry-lint.sh" "$DEST/checks/entry-lint.sh"
chmod +x "$DEST/checks/entry-lint.sh" 2>/dev/null || true
echo "✓ 규칙 복사: docs/claude_guideline/$BUNDLE/mistake.md"
echo "✓ 이빨 복사: docs/claude_guideline/$BUNDLE/checks/entry-lint.sh"

# 2) entry 폴더 생성 (비파괴)
mkdir -p "$TARGET/docs/claude-mistake"
echo "✓ entry 폴더: docs/claude-mistake/"

# 3) CLAUDE.md 등록 (마커 중복방지)
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

# 4) SessionStart 훅 — INDEX §메타 패턴·§미해결 항목 + open entry 목록 주입
if ls "$SRC/hooks/"*.py >/dev/null 2>&1; then
  mkdir -p "$DEST/hooks"
  cp "$SRC/hooks/"*.py "$DEST/hooks/"
  chmod +x "$DEST/hooks/"*.py 2>/dev/null || true
  echo "✓ 훅 복사: docs/claude_guideline/$BUNDLE/hooks/*.py"
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
    HOOK_BASE="\$CLAUDE_PROJECT_DIR/docs/claude_guideline/$BUNDLE/hooks"
    INJECT_CMD="$PYBIN \"$HOOK_BASE/$BUNDLE-inject.py\""
    "$PYBIN" - "$SETTINGS" "$INJECT_CMD" <<'PYEOF'
import json, sys
settings_path, inject_cmd = sys.argv[1], sys.argv[2]
try:
    with open(settings_path, encoding="utf-8") as f:
        cfg = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    cfg = {}
hooks = cfg.setdefault("hooks", {})
groups = hooks.setdefault("SessionStart", [])
if any(h.get("command") == inject_cmd for g in groups for h in g.get("hooks", [])):
    print("• settings.json SessionStart 훅 이미 존재 — 스킵")
else:
    groups.append({"hooks": [{"type": "command", "command": inject_cmd, "timeout": 5}]})
    print("✓ settings.json SessionStart 훅 등록")
with open(settings_path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
PYEOF
  fi
fi

echo "완료: $BUNDLE → $TARGET"
