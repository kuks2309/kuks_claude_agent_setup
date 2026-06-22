#!/usr/bin/env bash
# install.sh — coding 번들 설치 (폴더 자기완결)
#
# 사용법: ./install.sh <타깃-프로젝트-루트> [도메인...|--all]
#   도메인: ros2-coding embedded-coding numeric-coding concurrency-coding memory-coding
#
# 동작:
#   1) 코어(coding.md·conventions.md·stack.md) + checks/ → docs/claude_guideline/coding/
#   2) 선택 도메인(domains/<d>.md) 복사 (--all 이면 전부)
#   3) .pre-commit / ci 템플릿 복사(.sample, 덮어쓰기 금지)
#   4) 타깃 .gitignore 에 .omc/ 추가 (OMC creep 차단)
#   5) claude.snippet.md → CLAUDE.md append (마커 중복방지)
#   설치 산출물은 규칙·이빨뿐 — install.sh·claude.snippet.md 는 복사하지 않는다.
set -euo pipefail

BUNDLE="coding"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TARGET="${1:-}"
[ -n "$TARGET" ] || { echo "사용법: ./install.sh <타깃-프로젝트-루트> [도메인...|--all]"; exit 1; }
[ -d "$TARGET" ] || { echo "오류: 타깃 경로 없음: $TARGET"; exit 1; }
shift || true

DEST="$TARGET/docs/claude_guideline/$BUNDLE"
mkdir -p "$DEST/domains" "$DEST/checks"

# 1) 코어 + 이빨
for f in coding.md conventions.md stack.md; do cp "$SRC/$f" "$DEST/$f"; done
cp "$SRC"/checks/*.sh "$DEST/checks/"
chmod +x "$DEST"/checks/*.sh
echo "✓ 코어 3 + 이빨 $(ls "$SRC"/checks/*.sh 2>/dev/null | wc -l | tr -d ' ') 복사 → docs/claude_guideline/$BUNDLE/"

# 2) 도메인 (선택 또는 --all)
AVAIL=$(cd "$SRC/domains" && ls ./*.md 2>/dev/null | sed 's|\./||;s/\.md$//' | tr '\n' ' ')
if [ "${1:-}" = "--all" ]; then
  for d in $AVAIL; do cp "$SRC/domains/$d.md" "$DEST/domains/$d.md"; echo "  + 도메인 $d"; done
else
  for d in "$@"; do
    if [ -f "$SRC/domains/$d.md" ]; then cp "$SRC/domains/$d.md" "$DEST/domains/$d.md"; echo "  + 도메인 $d"
    else echo "  ! 도메인 없음: $d  (가능: $AVAIL)"; fi
  done
fi

# 3) pre-commit / ci 템플릿 (.sample, 덮어쓰기 금지)
if [ -f "$SRC/.pre-commit-config.yaml" ]; then
  cp "$SRC/.pre-commit-config.yaml" "$DEST/pre-commit-config.sample.yaml"; echo "✓ pre-commit 템플릿(.sample)"
fi
if [ -d "$SRC/ci" ]; then
  mkdir -p "$DEST/ci"; cp "$SRC"/ci/*.yml "$DEST/ci/" 2>/dev/null || true; echo "✓ ci 템플릿"
fi

# 4) .omc/ gitignore (OMC creep 차단)
GI="$TARGET/.gitignore"; touch "$GI"
if ! grep -qxF '.omc/' "$GI"; then
  printf '\n# coding 번들: OMC 런타임 상태 비추적\n.omc/\n' >> "$GI"; echo "✓ .gitignore 에 .omc/ 추가"
fi

# 5) CLAUDE.md 등록 (마커 중복방지)
CLAUDE_MD="$TARGET/CLAUDE.md"; MARKER="kuks_agent_setup:$BUNDLE"; touch "$CLAUDE_MD"
if grep -qF "$MARKER" "$CLAUDE_MD"; then echo "• CLAUDE.md 등록 이미 존재 — 스킵"
else printf '\n' >> "$CLAUDE_MD"; cat "$SRC/claude.snippet.md" >> "$CLAUDE_MD"; echo "✓ CLAUDE.md 등록 추가"; fi

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
echo "  다음: pre-commit install (로컬 강제) · ci/ 워크플로 활성 (서버 강제) · 무-CI 면 README 의 수동 재생성 따름"
