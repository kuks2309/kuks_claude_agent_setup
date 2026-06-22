#!/usr/bin/env bash
# install.sh — issue_fix 번들 설치 (폴더 자기완결)
#
# 사용법: ./install.sh <타깃-프로젝트-루트>
#
# 동작:
#   1) issue_fix.md 를 <타깃>/docs/claude_guideline/issue_fix/ 로 복사
#   2) claude.snippet.md 를 <타깃>/CLAUDE.md 에 append (마커 중복방지)
#   설치 산출물은 규칙(issue_fix.md)뿐 — install.sh·claude.snippet.md 는 복사하지 않는다.
#   이슈 로그(docs/issues_and_fixes/issues_and_fixes.md)는 설치가 아니라 첫 기록 시 런타임 생성.

set -euo pipefail

BUNDLE="issue_fix"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TARGET="${1:-}"
[ -n "$TARGET" ] || { echo "사용법: ./install.sh <타깃-프로젝트-루트>"; exit 1; }
[ -d "$TARGET" ] || { echo "오류: 타깃 경로 없음: $TARGET"; exit 1; }

# 1) 규칙 복사
DEST="$TARGET/docs/claude_guideline/$BUNDLE"
mkdir -p "$DEST"
cp "$SRC/issue_fix.md" "$DEST/issue_fix.md"
echo "✓ 규칙 복사: docs/claude_guideline/$BUNDLE/issue_fix.md"

# 2) CLAUDE.md 등록 (마커 중복방지)
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

# 강제 훅 — 등록(수동 포인터)을 트리거 게이트로: 트리거 감지 시 규칙 SOP 주입
HOOK_PY="$BUNDLE-reminder.py"
if [ -f "$SRC/hooks/$HOOK_PY" ]; then
  mkdir -p "$DEST/hooks"
  cp "$SRC/hooks/$HOOK_PY" "$DEST/hooks/$HOOK_PY"
  chmod +x "$DEST/hooks/$HOOK_PY" 2>/dev/null || true
  echo "✓ 훅 복사: docs/claude_guideline/$BUNDLE/hooks/$HOOK_PY"
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
    HOOK_CMD="$PYBIN \"\$CLAUDE_PROJECT_DIR/docs/claude_guideline/$BUNDLE/hooks/$HOOK_PY\""
    "$PYBIN" - "$SETTINGS" "$HOOK_CMD" <<'PYEOF'
import json, sys
settings_path, cmd = sys.argv[1], sys.argv[2]
try:
    with open(settings_path, encoding="utf-8") as f:
        cfg = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    cfg = {}
groups = cfg.setdefault("hooks", {}).setdefault("UserPromptSubmit", [])
exists = any(h.get("command") == cmd for g in groups for h in g.get("hooks", []))
if exists:
    print("• settings.json UserPromptSubmit 훅 이미 존재 — 스킵")
else:
    groups.append({"hooks": [{"type": "command", "command": cmd, "timeout": 5}]})
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print("✓ settings.json UserPromptSubmit 훅 등록")
PYEOF
  fi
fi

echo "완료: $BUNDLE → $TARGET"
