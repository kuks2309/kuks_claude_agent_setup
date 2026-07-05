#!/usr/bin/env bash
# install.sh — computer_use 우산 번들 전역 설치 (~/.claude): 읽기(capture)+쓰기(action)
#
# 사용법:
#   ./install.sh                 # 파일 배치 + OS 의존성 설치 + preflight
#   ./install.sh --no-deps       # 의존성 설치 생략(파일 배치만; 테스트/오프라인)
#   ./install.sh --check         # preflight 만 수행(설치 안 함)
#   CLAUDE_HOME=/tmp/x ./install.sh --no-deps   # 설치 루트 변경(테스트용)
#
# 배치:
#   capture_screen.py, computer_action.py     -> $CLAUDE_HOME/
#   skills/capture-test, skills/computer-use  -> $CLAUDE_HOME/skills/
#   agents/computer-operator.md               -> $CLAUDE_HOME/agents/
#   claude.snippet.md                         -> $CLAUDE_HOME/CLAUDE.md (marker 중복방지)
#
# 전역 설치이므로 설치 후 어느 프로젝트에서든 computer-use / capture-test 스킬 사용 가능. 멱등.
set -euo pipefail

NO_DEPS=0; CHECK_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --no-deps) NO_DEPS=1 ;;
    --check) CHECK_ONLY=1 ;;
    *) echo "unknown arg: $arg" >&2; exit 64 ;;
  esac
done

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"

preflight() {
  echo "[PREFLIGHT]"
  if [ "$(uname)" = "Linux" ]; then
    if [ -n "${WAYLAND_DISPLAY:-}" ] || [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
      echo "  ✗ Wayland 감지 — 미지원(X11 필요). 중단." >&2; return 1
    fi
    if [ -z "${DISPLAY:-}" ]; then
      echo "  ✗ DISPLAY 미설정 — X11 세션 필요. 중단." >&2; return 1
    fi
    command -v xdotool >/dev/null 2>&1 && echo "  xdotool ✓" || echo "  · xdotool 없음 → 의존성 설치 단계에서 설치"
    echo "  X11 session ✓"
  fi
  command -v python3 >/dev/null 2>&1 && echo "  python3 ✓" || { echo "  ✗ python3 없음" >&2; return 1; }
}

install_deps() {
  [ "$NO_DEPS" = "1" ] && { echo "[DEPS] 생략(--no-deps)"; return 0; }
  echo "[DEPS]"
  if [ "$(uname)" = "Linux" ]; then
    sudo apt-get install -y xdotool x11-utils
    python3 -m pip install --user pillow mss
  else
    python3 -m pip install --user pyautogui pillow mss
  fi
}

place() {
  echo "[PLACE] -> $CLAUDE_HOME"
  mkdir -p "$CLAUDE_HOME" "$CLAUDE_HOME/skills" "$CLAUDE_HOME/agents"
  cp "$SRC/capture_screen.py"  "$CLAUDE_HOME/capture_screen.py"
  cp "$SRC/computer_action.py" "$CLAUDE_HOME/computer_action.py"
  chmod +x "$CLAUDE_HOME/capture_screen.py" "$CLAUDE_HOME/computer_action.py"
  for sk in capture-test computer-use; do
    rm -rf "$CLAUDE_HOME/skills/$sk"
    cp -r "$SRC/skills/$sk" "$CLAUDE_HOME/skills/$sk"
  done
  cp "$SRC/agents/computer-operator.md" "$CLAUDE_HOME/agents/computer-operator.md"
  echo "  capture_screen.py · computer_action.py · skills(capture-test,computer-use) · agent 배치"
}

register_claude_md() {
  local md="$CLAUDE_HOME/CLAUDE.md" marker="kuks_agent_setup:computer_use"
  touch "$md"
  if grep -qF "$marker" "$md"; then
    echo "[CLAUDE.md] 등록 이미 존재 — 스킵"
  else
    printf '\n' >> "$md"; cat "$SRC/claude.snippet.md" >> "$md"
    echo "[CLAUDE.md] 등록 추가"
  fi
}

preflight
[ "$CHECK_ONLY" = "1" ] && { echo "preflight only — done."; exit 0; }
install_deps
place
register_claude_md
echo "완료: computer_use → $CLAUDE_HOME (적용은 세션 재시작 후). 다른 프로젝트에서 computer-use / capture-test 스킬 사용 가능."
