#!/usr/bin/env bash
# install.sh — code_review 번들 설치 (코어 + 선택 도메인)
#
# 사용법:
#   ./install.sh <타깃-프로젝트-루트>                          # 코어만
#   ./install.sh <타깃-프로젝트-루트> ros2-review concurrency   # 코어 + 지정 도메인
#   ./install.sh <타깃-프로젝트-루트> --all                     # 코어 + 모든 도메인
#
# 동작:
#   1) review.md(코어)를 <타깃>/docs/claude_guideline/code_review/ 로 복사
#   2) 지정 도메인(domains/<도메인>.md)을 .../code_review/domains/ 로 복사
#   3) claude.snippet.md 를 <타깃>/CLAUDE.md 에 append (마커 중복방지)

set -euo pipefail

BUNDLE="code_review"
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

# 1) 코어 복사
mkdir -p "$DEST"
cp "$SRC/review.md" "$DEST/review.md"
echo "✓ 코어 복사: docs/claude_guideline/$BUNDLE/review.md"

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

echo "완료: $BUNDLE → $TARGET"
