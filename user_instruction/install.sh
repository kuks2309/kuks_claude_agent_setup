#!/usr/bin/env bash
# install.sh — user_instruction 번들 설치 (폴더 자기완결)
#
# 사용법: ./install.sh <타깃-프로젝트-루트>
#   예:   ./install.sh ~/myproject
#
# 동작:
#   1) recording.md 를 <타깃>/docs/claude_guideline/user_instruction/ 로 복사
#   2) claude.snippet.md 를 <타깃>/CLAUDE.md 에 append (덮어쓰기 아님, 중복 시 스킵)
#   설치 산출물은 규칙(recording.md)뿐 — install.sh·claude.snippet.md 는 복사하지 않는다.

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

echo "완료: $BUNDLE → $TARGET"
