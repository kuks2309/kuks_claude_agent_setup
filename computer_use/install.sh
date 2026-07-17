#!/usr/bin/env bash
# install.sh — computer_use 우산 번들 전역 설치 (~/.claude): 읽기(capture)+쓰기(action)
#
# 사용법:
#   ./install.sh                 # 파일 배치 + OS 의존성 설치 + preflight
#   ./install.sh --no-deps       # 의존성 설치 생략(파일 배치만; 테스트/오프라인)
#   ./install.sh --check         # preflight 만 수행(설치 안 함)
#   ./install.sh --status        # 설치본 낡음 점검(설치 안 함)
#   CLAUDE_HOME=/tmp/x ./install.sh --no-deps   # 설치 루트 변경(테스트용)
#
# 배치:
#   capture_screen.py, computer_action.py     -> $CLAUDE_HOME/
#   skills/capture-test, skills/computer-use  -> $CLAUDE_HOME/skills/
#   agents/computer-operator.md               -> $CLAUDE_HOME/agents/
#   claude.snippet.md                         -> $CLAUDE_HOME/CLAUDE.md (marker 중복방지)
#
# 설치 성공 시 $CLAUDE_HOME/INSTALLED.md 에 자기 행 기록(커밋·날짜·인자). --check(preflight-only) 는 기록하지 않는다.
# --status 판정: 최신(exit 0) / 재설치 권장(exit 1) / 기록 없음(exit 2)
#
# 전역 설치이므로 설치 후 어느 프로젝트에서든 computer-use / capture-test 스킬 사용 가능. 멱등.
set -euo pipefail

BUNDLE="computer_use"
NO_DEPS=0; CHECK_ONLY=0; STATUS_ONLY=0
ARGS_REST=()
for arg in "$@"; do
  case "$arg" in
    --no-deps) NO_DEPS=1 ;;
    --check) CHECK_ONLY=1 ;;
    --status) STATUS_ONLY=1 ;;
    *) echo "unknown arg: $arg" >&2; exit 64 ;;
  esac
  [ "$arg" != "--status" ] && ARGS_REST+=("$arg")
done
INSTALL_ARGS="${ARGS_REST[*]:-}"
[ -z "$INSTALL_ARGS" ] && INSTALL_ARGS="-"

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
RECORD_FILE="$CLAUDE_HOME/INSTALLED.md"

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

# ---- 설치 기록·점검 공통 ----

bundle_commit() {
  local c
  if c="$(git -C "$SRC" rev-parse --short HEAD 2>/dev/null)"; then
    [ -n "$(git -C "$SRC" status --porcelain -- . 2>/dev/null)" ] && c="${c}+dirty"
    echo "$c"
  else
    echo "unknown"
  fi
}

record_install() {
  local commit today tmp
  commit="$(bundle_commit)"
  today="$(date +%F)"
  mkdir -p "$(dirname "$RECORD_FILE")"
  if [ ! -f "$RECORD_FILE" ]; then
    printf '# 설치된 번들 기록\n\n`install.sh` 가 자동 갱신 — 수동 편집 금지. 업데이트 절차는 번들 저장소 README "업데이트" 절 참조.\n\n| 번들 | 설치 커밋 | 날짜 | 인자 |\n| --- | --- | --- | --- |\n' > "$RECORD_FILE"
  fi
  tmp="$RECORD_FILE.tmp.$$"
  grep -v "^| $BUNDLE |" "$RECORD_FILE" > "$tmp" || true
  printf '| %s | %s | %s | %s |\n' "$BUNDLE" "$commit" "$today" "$INSTALL_ARGS" >> "$tmp"
  mv "$tmp" "$RECORD_FILE"
  echo "✓ 설치 기록: \$CLAUDE_HOME/INSTALLED.md ($BUNDLE @ $commit)"
}

# 설치본 ↔ 저장소 내용 대조 쌍(원본<TAB>설치본). place() 가 복사하는 대상과 일치시켜 유지.
drift_pairs() {
  printf '%s\t%s\n' "$SRC/capture_screen.py" "$CLAUDE_HOME/capture_screen.py"
  printf '%s\t%s\n' "$SRC/computer_action.py" "$CLAUDE_HOME/computer_action.py"
  printf '%s\t%s\n' "$SRC/skills/capture-test/SKILL.md" "$CLAUDE_HOME/skills/capture-test/SKILL.md"
  printf '%s\t%s\n' "$SRC/skills/computer-use/SKILL.md" "$CLAUDE_HOME/skills/computer-use/SKILL.md"
  printf '%s\t%s\n' "$SRC/agents/computer-operator.md" "$CLAUDE_HOME/agents/computer-operator.md"
}

status_check() {
  echo "[STATUS] $BUNDLE @ $CLAUDE_HOME"
  local line
  line="$(grep "^| $BUNDLE |" "$RECORD_FILE" 2>/dev/null | tail -1)" || true
  if [ -z "$line" ]; then
    echo "  ✗ 설치 기록 없음 — 구판 설치이거나 미설치. 재설치하면 기록이 생성됩니다."
    echo "  → cd $BUNDLE && ./install.sh"
    exit 2
  fi
  local rec date_str args_str
  rec="$(echo "$line"      | awk -F'|' '{gsub(/^ +| +$/,"",$3); print $3}')"
  date_str="$(echo "$line" | awk -F'|' '{gsub(/^ +| +$/,"",$4); print $4}')"
  args_str="$(echo "$line" | awk -F'|' '{gsub(/^ +| +$/,"",$5); print $5}')"
  echo "  기록: $rec ($date_str, 인자: $args_str)"

  local stale=0 note_compare=""
  # 1) 설치본 내용 대조 (드리프트 = 낡음·로컬수정·누락의 직접 증거)
  local s d drift=0
  while IFS=$'\t' read -r s d; do
    [ -f "$s" ] || continue
    if [ ! -f "$d" ]; then
      echo "  ⚠ 설치본 누락: ${d#"$CLAUDE_HOME"/}"; drift=1
    elif ! diff -q "$s" "$d" >/dev/null 2>&1; then
      echo "  ⚠ 설치본 ≠ 저장소: ${d#"$CLAUDE_HOME"/}"; drift=1
    fi
  done < <(drift_pairs)
  [ "$drift" = 1 ] && stale=1
  [ "$drift" = 0 ] && echo "  설치본 내용: 저장소와 일치"

  # 2) 기록 커밋 → HEAD 변경 파일 (install.sh·claude.snippet.md 등 비복사 파일 변경 검출)
  local head base="${rec%+dirty}"
  if ! head="$(git -C "$SRC" rev-parse --short HEAD 2>/dev/null)"; then
    note_compare="번들 저장소가 git 이 아님 — 커밋 비교 생략"
  elif [ "$base" = "unknown" ]; then
    note_compare="기록 커밋 unknown — 커밋 비교 생략"
  elif ! git -C "$SRC" rev-parse --verify -q "$base^{commit}" >/dev/null 2>&1; then
    note_compare="기록 커밋 $base 를 저장소에서 찾을 수 없음(타 PC 미푸시 커밋?) — 커밋 비교 생략"
  else
    echo "  저장소: $head"
    local changed
    changed="$(git -C "$SRC" diff --name-only "$base..HEAD" -- . 2>/dev/null)" || true
    if [ -n "$changed" ]; then
      echo "  변경 파일 ($base..HEAD):"
      echo "$changed" | sed 's/^/    /'
      stale=1
      if echo "$changed" | grep -q "claude.snippet.md"; then
        echo "  ⚠ claude.snippet.md 변경 — 재설치는 마커 중복방지로 스킵하므로 CLAUDE.md 의 기존 등록 블록을 수동 갱신 필요"
      fi
    fi
    case "$rec" in *+dirty) echo "  ⚠ 기록이 +dirty (미커밋 상태에서 설치됨)";; esac
  fi
  [ -n "$note_compare" ] && echo "  ⚠ $note_compare"
  if [ -n "$(git -C "$SRC" status --porcelain -- . 2>/dev/null)" ]; then
    echo "  ⚠ 저장소 번들 폴더에 미커밋 변경 있음 (설치 전 커밋 권장)"
  fi

  if [ "$stale" = 1 ]; then
    echo "  → 재설치 권장: cd $BUNDLE && ./install.sh  (인자: $args_str)"
    exit 1
  fi
  echo "  → 최신"
  exit 0
}

[ "$STATUS_ONLY" = 1 ] && status_check

preflight
[ "$CHECK_ONLY" = "1" ] && { echo "preflight only — done."; exit 0; }
install_deps
place
register_claude_md

# 설치 기록
record_install

echo "완료: computer_use → $CLAUDE_HOME (적용은 세션 재시작 후). 다른 프로젝트에서 computer-use / capture-test 스킬 사용 가능."
