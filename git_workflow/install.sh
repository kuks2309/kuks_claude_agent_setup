#!/usr/bin/env bash
# install.sh — git_workflow 번들 설치 (폴더 자기완결)
#
# 사용법: ./install.sh <타깃-프로젝트-루트>
#
# 동작:
#   1) git_workflow.md + hooks/*.py 를 <타깃>/docs/claude_guideline/git_workflow/ 로 복사
#   2) claude.snippet.md 를 <타깃>/CLAUDE.md 에 append (마커 중복방지)
#   3) 훅 5종을 .claude/settings.json 에 멱등 등록:
#      reminder(UserPromptSubmit) + track(PostToolUse·파일) + commit-track(PostToolUse·Bash)
#      + stage-gate(PreToolUse·Bash) + push-gate(PreToolUse·Bash)
#   설치 산출물은 규칙·훅뿐 — install.sh·claude.snippet.md 는 복사하지 않는다.

set -euo pipefail

BUNDLE="git_workflow"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TARGET="${1:-}"
[ -n "$TARGET" ] || { echo "사용법: ./install.sh <타깃-프로젝트-루트>"; exit 1; }
[ -d "$TARGET" ] || { echo "오류: 타깃 경로 없음: $TARGET"; exit 1; }

# 1) 규칙 복사
DEST="$TARGET/docs/claude_guideline/$BUNDLE"
mkdir -p "$DEST"
cp "$SRC/git_workflow.md" "$DEST/git_workflow.md"
echo "✓ 규칙 복사: docs/claude_guideline/$BUNDLE/git_workflow.md"

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

# 훅 3종 — (1) reminder: 트리거 게이트로 SOP+모드+세션 파일 주입(UserPromptSubmit)
#          (2) track: 파일 수정 도구 사용 시 세션별 수정 파일 기록(PostToolUse)
#          (3) stage-gate: git add/commit-a 가 타 세션 파일 캡처를 막음(PreToolUse·Bash)
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
    REMINDER_CMD="$PYBIN \"$HOOK_BASE/$BUNDLE-reminder.py\""
    TRACK_CMD="$PYBIN \"$HOOK_BASE/$BUNDLE-track.py\""
    GATE_CMD="$PYBIN \"$HOOK_BASE/$BUNDLE-stage-gate.py\""
    CTRACK_CMD="$PYBIN \"$HOOK_BASE/$BUNDLE-commit-track.py\""
    PUSHGATE_CMD="$PYBIN \"$HOOK_BASE/$BUNDLE-push-gate.py\""
    "$PYBIN" - "$SETTINGS" "$REMINDER_CMD" "$TRACK_CMD" "$GATE_CMD" "$CTRACK_CMD" "$PUSHGATE_CMD" <<'PYEOF'
import json, sys
settings_path = sys.argv[1]
reminder_cmd, track_cmd, gate_cmd, ctrack_cmd, pushgate_cmd = sys.argv[2:7]
try:
    with open(settings_path, encoding="utf-8") as f:
        cfg = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    cfg = {}
hooks = cfg.setdefault("hooks", {})

def register(event, cmd, matcher=None):
    groups = hooks.setdefault(event, [])
    if any(h.get("command") == cmd for g in groups for h in g.get("hooks", [])):
        print("• settings.json %s 훅 이미 존재 — 스킵" % event)
        return
    entry = {"hooks": [{"type": "command", "command": cmd, "timeout": 5}]}
    if matcher:
        entry["matcher"] = matcher
    groups.append(entry)
    print("✓ settings.json %s 훅 등록" % event)

register("UserPromptSubmit", reminder_cmd)
register("PostToolUse", track_cmd, matcher="Write|Edit|MultiEdit|NotebookEdit")
register("PostToolUse", ctrack_cmd, matcher="Bash")
register("PreToolUse", gate_cmd, matcher="Bash")
register("PreToolUse", pushgate_cmd, matcher="Bash")

with open(settings_path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
PYEOF
  fi
fi

echo "완료: $BUNDLE → $TARGET"
