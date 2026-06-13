#!/usr/bin/env bash
# install.sh — kuks_claude_agent_setup 자산 번들 선택 설치
#
# 사용법:
#   ./install.sh                          # 설치 가능한 번들 목록 출력
#   ./install.sh <번들> <타깃-프로젝트-루트>  # 번들 하나를 타깃에 설치
#
# 예:
#   ./install.sh user_instruction ~/myproject
#
# 동작:
#   1) <번들> 폴더를 <타깃>/docs/claude_guideline/<번들>/ 로 복사 (claude.snippet.md 제외)
#   2) <번들>/claude.snippet.md 를 <타깃>/CLAUDE.md 에 append (중복 시 스킵)
#   CLAUDE.md 는 절대 덮어쓰지 않고 append 만 한다.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

list_bundles() {
  echo "설치 가능한 번들:"
  local found=0
  for d in "$REPO_DIR"/*/; do
    if [ -f "${d}claude.snippet.md" ]; then
      echo "  - $(basename "$d")"
      found=1
    fi
  done
  [ "$found" -eq 1 ] || echo "  (없음)"
}

if [ $# -lt 2 ]; then
  echo "사용법: ./install.sh <번들> <타깃-프로젝트-루트>"
  echo
  list_bundles
  exit 1
fi

BUNDLE="$1"
TARGET="$2"
SRC="$REPO_DIR/$BUNDLE"

# 검증
[ -d "$SRC" ] || { echo "오류: 번들 '$BUNDLE' 없음"; echo; list_bundles; exit 1; }
[ -f "$SRC/claude.snippet.md" ] || { echo "오류: '$BUNDLE' 는 설치 불가 (claude.snippet.md 없음)"; exit 1; }
[ -d "$TARGET" ] || { echo "오류: 타깃 경로 없음: $TARGET"; exit 1; }

# 1) 번들 규칙 복사 (등록 스니펫은 설치 산출물에서 제외)
DEST="$TARGET/docs/claude_guideline/$BUNDLE"
mkdir -p "$DEST"
cp -r "$SRC"/. "$DEST"/
rm -f "$DEST/claude.snippet.md"
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
