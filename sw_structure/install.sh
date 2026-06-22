#!/usr/bin/env bash
# install.sh — sw_structure 번들 설치 (코어 전용, 도메인 없음)
#
# 사용법:
#   ./install.sh <타깃-프로젝트-루트>
#
# 동작:
#   1) structure.md(코어)를 <타깃>/docs/claude_guideline/sw_structure/ 로 복사
#   2) claude.snippet.md 를 <타깃>/CLAUDE.md 에 append (마커 중복방지)

set -euo pipefail

BUNDLE="sw_structure"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TARGET="${1:-}"
if [ -z "$TARGET" ]; then
  echo "사용법: ./install.sh <타깃-프로젝트-루트>"
  exit 1
fi
[ -d "$TARGET" ] || { echo "오류: 타깃 경로 없음: $TARGET"; exit 1; }

DEST="$TARGET/docs/claude_guideline/$BUNDLE"

# 1) 코어 복사
mkdir -p "$DEST"
cp "$SRC/structure.md" "$DEST/structure.md"
echo "✓ 코어 복사: docs/claude_guideline/$BUNDLE/structure.md"

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

echo "완료: $BUNDLE → $TARGET"
