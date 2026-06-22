#!/usr/bin/env bash
# install.sh — external_reference 번들 설치 (코어 + 선택 도메인)
#
# 사용법:
#   ./install.sh <타깃-프로젝트-루트>                   # 코어만
#   ./install.sh <타깃-프로젝트-루트> embedded ros2     # 코어 + 지정 도메인
#   ./install.sh <타깃-프로젝트-루트> --all             # 코어 + 모든 도메인
#
# 동작:
#   1) handling.md(코어)를 <타깃>/docs/claude_guideline/external_reference/ 로 복사
#   2) 지정 도메인(domains/<도메인>.md)을 .../external_reference/domains/ 로 복사
#   3) claude.snippet.md 를 <타깃>/CLAUDE.md 에 append (마커 중복방지)

set -euo pipefail

BUNDLE="external_reference"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

list_domains() {
  echo "사용 가능한 도메인:"
  for f in "$SRC"/domains/*.md; do echo "  - $(basename "$f" .md)"; done
}

TARGET="${1:-}"
if [ -z "$TARGET" ]; then
  echo "사용법: ./install.sh <타깃-프로젝트-루트> [도메인... | --all]"
  echo
  list_domains
  exit 1
fi
[ -d "$TARGET" ] || { echo "오류: 타깃 경로 없음: $TARGET"; exit 1; }
shift

DEST="$TARGET/docs/claude_guideline/$BUNDLE"

# 1) 코어 복사 (handling.md + coding_standards.md)
mkdir -p "$DEST"
cp "$SRC/handling.md" "$DEST/handling.md"
cp "$SRC/coding_standards.md" "$DEST/coding_standards.md"
echo "✓ 코어 복사: docs/claude_guideline/$BUNDLE/{handling.md, coding_standards.md}"

# 2) 도메인 선택 복사
DOMAINS=()
if [ "${1:-}" = "--all" ]; then
  for f in "$SRC"/domains/*.md; do DOMAINS+=("$(basename "$f" .md)"); done
else
  DOMAINS=("$@")
fi
if [ ${#DOMAINS[@]} -gt 0 ]; then
  mkdir -p "$DEST/domains"
  for d in "${DOMAINS[@]}"; do
    if [ -f "$SRC/domains/$d.md" ]; then
      cp "$SRC/domains/$d.md" "$DEST/domains/$d.md"
      echo "  ✓ 도메인: $d"
    else
      echo "  ⚠ 도메인 없음(스킵): $d"
    fi
  done
else
  echo "• 도메인 미지정 — 코어만 설치"
fi

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
