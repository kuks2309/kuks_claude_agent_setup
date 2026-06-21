#!/usr/bin/env bash
# install.sh — debt 번들 설치 (폴더 자기완결)
#
# 사용법: ./install.sh <타깃-프로젝트-루트>
#
# 동작:
#   1) debt.md + checks/ → docs/claude_guideline/debt/
#   2) registry 템플릿 → docs/debt/registry.md (기존 있으면 보존)
#   3) .pre-commit / ci 템플릿(.sample)
#   4) 타깃 .gitignore 에 .omc/ 추가 (OMC creep 차단)
#   5) claude.snippet.md → CLAUDE.md append (마커 중복방지)
set -euo pipefail

BUNDLE="debt"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TARGET="${1:-}"
[ -n "$TARGET" ] || { echo "사용법: ./install.sh <타깃-프로젝트-루트>"; exit 1; }
[ -d "$TARGET" ] || { echo "오류: 타깃 경로 없음: $TARGET"; exit 1; }

DEST="$TARGET/docs/claude_guideline/$BUNDLE"
mkdir -p "$DEST/checks" "$DEST/domains"

# 1) 규칙 + 도메인 + 이빨
cp "$SRC/debt.md" "$DEST/debt.md"
if ls "$SRC"/domains/*.md >/dev/null 2>&1; then
  cp "$SRC"/domains/*.md "$DEST/domains/"; echo "✓ 도메인 $(ls "$SRC"/domains/*.md | wc -l | tr -d ' ')(기술·이해·의도) 복사"
fi
cp "$SRC"/checks/*.sh "$DEST/checks/"
chmod +x "$DEST"/checks/*.sh
echo "✓ 규칙 + 이빨 $(ls "$SRC"/checks/*.sh 2>/dev/null | wc -l | tr -d ' ') 복사 → docs/claude_guideline/$BUNDLE/"

# 2) registry 템플릿 → docs/debt/registry.md (기존 보존)
if [ -f "$SRC/registry.template.md" ]; then
  mkdir -p "$TARGET/docs/debt"
  REG="$TARGET/docs/debt/registry.md"
  if [ -f "$REG" ]; then echo "• registry 이미 존재 — 보존"
  else cp "$SRC/registry.template.md" "$REG"; echo "✓ registry 템플릿 → docs/debt/registry.md"; fi
fi

# 3) pre-commit / ci 템플릿 (.sample)
if [ -f "$SRC/.pre-commit-config.yaml" ]; then
  cp "$SRC/.pre-commit-config.yaml" "$DEST/pre-commit-config.sample.yaml"; echo "✓ pre-commit 템플릿(.sample)"
fi
if [ -d "$SRC/ci" ]; then
  mkdir -p "$DEST/ci"; cp "$SRC"/ci/*.yml "$DEST/ci/" 2>/dev/null || true; echo "✓ ci 템플릿"
fi

# 4) .omc/ gitignore
GI="$TARGET/.gitignore"; touch "$GI"
if ! grep -qxF '.omc/' "$GI"; then
  printf '\n# debt 번들: OMC 런타임 상태 비추적\n.omc/\n' >> "$GI"; echo "✓ .gitignore 에 .omc/ 추가"
fi

# 5) CLAUDE.md 등록 (마커 중복방지)
CLAUDE_MD="$TARGET/CLAUDE.md"; MARKER="kuks_agent_setup:$BUNDLE"; touch "$CLAUDE_MD"
if grep -qF "$MARKER" "$CLAUDE_MD"; then echo "• CLAUDE.md 등록 이미 존재 — 스킵"
else printf '\n' >> "$CLAUDE_MD"; cat "$SRC/claude.snippet.md" >> "$CLAUDE_MD"; echo "✓ CLAUDE.md 등록 추가"; fi

echo "완료: $BUNDLE → $TARGET"
