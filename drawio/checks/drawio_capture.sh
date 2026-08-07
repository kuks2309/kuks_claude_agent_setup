#!/usr/bin/env bash
# drawio_capture.sh — .drawio 를 GUI 로 띄워 창을 캡처한다 (Layer B 시각 검증).
#
# 린트(drawio_lint.py, Layer A)가 통과한 뒤 실행한다. 좌표로 계산되지 않는 결함
# (전체 균형·가독성·미관)은 픽셀을 봐야만 판정할 수 있기 때문이다.
#
# 두 가지 방식이 있다.
#   기본  : GUI 창을 띄워 computer-use 로 창을 캡처 (편집기 화면 그대로)
#   --export: drawio 내보내기로 UI 크롬 없는 순수 다이어그램 PNG
#             (xvfb 로 돌아 디스플레이 없이도 동작 — 원격·CI 가능)
#
# 사용법:
#   ./drawio_capture.sh <file.drawio> [--project DIR] [--keep-open]
#                       [--no-fit] [--wait SEC]
#   ./drawio_capture.sh <file.drawio> --export [--scale N] [--project DIR]
#   ./drawio_capture.sh --check                 환경 점검만
#
# 출력: <project>/experiments/capture/ 아래 PNG (capture_screen.py 규약)
#       stdout 마지막 줄 = CAPTURED <png경로>
#
# 요구: drawio 데스크톱. 기본 방식은 추가로 X11 디스플레이 + computer_use 번들
#       전역 설치(~/.claude/capture_screen.py, ~/.claude/computer_action.py).
# 제약: 기본 방식은 디스플레이가 필요해 원격 무인 세션·CI 에서 쓸 수 없다.
#       그런 환경에서는 --export 를 쓰거나 Layer A(drawio_lint.py)만 강제한다.
set -uo pipefail

CAPTURE="$HOME/.claude/capture_screen.py"
ACTION="$HOME/.claude/computer_action.py"

FILE=""
PROJECT=""
KEEP_OPEN=0
DO_FIT=1
WAIT_SEC=6
CHECK_ONLY=0
EXPORT_MODE=0
SCALE=2

while [ $# -gt 0 ]; do
  case "$1" in
    --check)       CHECK_ONLY=1 ;;
    --project)     PROJECT="${2:-}"; shift ;;
    --keep-open)   KEEP_OPEN=1 ;;
    --no-fit)      DO_FIT=0 ;;
    --export)      EXPORT_MODE=1 ;;
    --scale)       SCALE="${2:-2}"; shift ;;
    --wait)        WAIT_SEC="${2:-6}"; shift ;;
    -*)            echo "unknown arg: $1" >&2; exit 64 ;;
    *)             FILE="$1" ;;
  esac
  shift
done

# ── drawio 실행 파일 탐색 ─────────────────────────────────────────────
find_drawio() {
  local c
  for c in drawio drawio-desktop; do
    command -v "$c" >/dev/null 2>&1 && { command -v "$c"; return 0; }
  done
  for c in "$HOME/.local/opt/drawio/drawio" "$HOME/.local/bin/drawio" \
           /opt/drawio/drawio /opt/drawio-desktop/drawio; do
    [ -x "$c" ] && { echo "$c"; return 0; }
  done
  for c in "$HOME"/Applications/drawio*.AppImage "$HOME"/Downloads/drawio*.AppImage; do
    [ -x "$c" ] && { echo "$c"; return 0; }
  done
  if command -v flatpak >/dev/null 2>&1 &&
     flatpak info com.jgraph.drawio.desktop >/dev/null 2>&1; then
    echo "flatpak run com.jgraph.drawio.desktop"; return 0
  fi
  return 1
}

install_hint() {
  cat >&2 <<'EOF'
✗ drawio 데스크톱을 찾을 수 없습니다. 아래 중 하나로 설치하세요.

  # AppImage (권장 · 루트 불필요)
  mkdir -p ~/.local/opt/drawio && cd ~/.local/opt/drawio
  # gh CLI 가 있으면:
  gh release download --repo jgraph/drawio-desktop \
     --pattern 'drawio-x86_64-*.AppImage' --dir .
  # 없으면 (자산명이 drawio-x86_64-<버전>.AppImage 이므로 패턴 주의):
  curl -fL -o drawio.AppImage "$(curl -fsSL \
    https://api.github.com/repos/jgraph/drawio-desktop/releases/latest \
    | grep -o '"browser_download_url": *"[^"]*drawio-x86_64-[^"]*\.AppImage"' \
    | head -1 | cut -d'"' -f4)"
  mv -f drawio-x86_64-*.AppImage drawio.AppImage 2>/dev/null
  chmod +x drawio.AppImage && ln -sf drawio.AppImage drawio

  # 또는 flatpak
  flatpak install -y flathub com.jgraph.drawio.desktop
EOF
}

preflight() {
  local ok=0
  if DRAWIO="$(find_drawio)"; then
    echo "✓ drawio: $DRAWIO"
  else
    install_hint; ok=1
  fi

  if [ "$EXPORT_MODE" = 1 ]; then
    if command -v xvfb-run >/dev/null 2>&1; then
      echo "✓ xvfb-run: $(command -v xvfb-run) (디스플레이 불요)"
    elif [ -n "${DISPLAY:-}" ]; then
      echo "• xvfb-run 없음 — 현재 DISPLAY 로 내보내기 (창이 잠깐 뜸)"
    else
      echo "✗ xvfb-run 도 DISPLAY 도 없음 — 내보내기 불가" >&2
      echo "  설치: sudo apt-get install -y xvfb" >&2
      ok=1
    fi
    return $ok
  fi

  [ -f "$CAPTURE" ] && echo "✓ capture_screen.py: $CAPTURE" || {
    echo "✗ $CAPTURE 없음 — computer_use 번들을 설치하세요 (cd computer_use && ./install.sh)" >&2; ok=1; }
  [ -f "$ACTION" ] && echo "✓ computer_action.py: $ACTION" || {
    echo "✗ $ACTION 없음 — computer_use 번들을 설치하세요" >&2; ok=1; }
  if [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
    echo "✓ 디스플레이: DISPLAY=${DISPLAY:-}${WAYLAND_DISPLAY:+ WAYLAND=$WAYLAND_DISPLAY}"
    [ -n "${WAYLAND_DISPLAY:-}" ] && [ -z "${DISPLAY:-}" ] &&
      echo "⚠ Wayland 전용 세션은 미지원 (X11 필요)" >&2
  else
    echo "✗ 디스플레이 없음 — GUI 캡처 불가." >&2
    echo "  → --export 로 내보내기(디스플레이 불요)하거나 Layer A 린트만 사용하세요." >&2
    ok=1
  fi
  return $ok
}

if [ "$CHECK_ONLY" = 1 ]; then
  preflight; exit $?
fi

[ -n "$FILE" ] || { echo "사용법: ./drawio_capture.sh <file.drawio> [--project DIR]" >&2; exit 1; }
[ -f "$FILE" ] || { echo "오류: 파일 없음: $FILE" >&2; exit 1; }
preflight >/dev/null || { preflight; exit 1; }

DRAWIO="$(find_drawio)"
FILE_ABS="$(cd "$(dirname "$FILE")" && pwd)/$(basename "$FILE")"
BASE="$(basename "$FILE")"
STEM="${BASE%.drawio}"
[ -n "$PROJECT" ] || PROJECT="$(dirname "$FILE_ABS")"

# ── --export: UI 크롬 없는 순수 다이어그램 PNG ────────────────────────
if [ "$EXPORT_MODE" = 1 ]; then
  OUTDIR="$PROJECT/experiments/capture"
  mkdir -p "$OUTDIR"
  PNG="$OUTDIR/$(date +%Y%m%d_%H%M%S)_drawio-export-$STEM.png"
  RUNNER=()
  command -v xvfb-run >/dev/null 2>&1 && RUNNER=(xvfb-run -a)
  echo "→ 내보내는 중: $BASE (scale=$SCALE)"
  # shellcheck disable=SC2086
  if ! "${RUNNER[@]}" $DRAWIO --no-sandbox -x -f png --scale "$SCALE" -b 20 \
        -o "$PNG" "$FILE_ABS" 2>&1 | grep -v "VAAPI\|GPU\|dbus\|libva"; then
    :
  fi
  if [ ! -f "$PNG" ]; then
    echo "✗ 내보내기 실패" >&2
    exit 1
  fi
  echo "✓ $PNG"
  echo
  echo "다음: 이 PNG 를 Read 도구로 열어 references/visual-checklist.md 를 검토하세요."
  echo "CAPTURED $PNG"
  exit 0
fi

# ── 실행 전 창 목록 스냅샷 ────────────────────────────────────────────
# 후보는 실행 후 "새로 생긴 창"으로 한정한다. 제목 매칭만으로는 파일명이나
# "drawio" 를 제목에 담은 다른 창(편집기·터미널)이 잡힌다.
list_ids() {
  python3 - "$CAPTURE" <<'PY' 2>/dev/null || true
import json, subprocess, sys
try:
    out = subprocess.run([sys.executable, sys.argv[1], "--mode", "list"],
                         capture_output=True, text=True, timeout=20).stdout
    for w in json.loads(out[out.index("["):out.rindex("]") + 1]):
        print(w["id"])
except Exception:
    pass
PY
}
BEFORE_IDS="$(list_ids)"

# ── 창 띄우기 ─────────────────────────────────────────────────────────
echo "→ 여는 중: $DRAWIO $BASE"
# shellcheck disable=SC2086
$DRAWIO --no-sandbox "$FILE_ABS" >/dev/null 2>&1 &
DRAWIO_PID=$!

# ── 창 등장 대기 (새로 생긴 drawio 창) ────────────────────────────────
find_window() {
  python3 - "$CAPTURE" "$STEM" "$BEFORE_IDS" <<'PY'
import json, subprocess, sys
cap, stem, before = sys.argv[1], sys.argv[2], set(sys.argv[3].split())
try:
    out = subprocess.run([sys.executable, cap, "--mode", "list"],
                         capture_output=True, text=True, timeout=20).stdout
    wins = json.loads(out[out.index("["):out.rindex("]") + 1])
except Exception:
    sys.exit(1)

fresh = [w for w in wins if str(w.get("id")) not in before]
if not fresh:
    sys.exit(1)


def title(w):
    return (w.get("title") or "").lower()


# 새 창 중에서도 drawio 앱 창을 고른다: 제목이 "<파일> - draw.io" 형태
cands = [w for w in fresh if title(w).endswith("draw.io")
         or title(w).endswith("drawio")]
if not cands:
    cands = [w for w in fresh if stem.lower() in title(w)]
if not cands:                       # 제목이 아직 안 붙은 초기 창은 제외하지 않는다
    cands = [w for w in fresh if (w.get("w") or 0) >= 400
             and (w.get("h") or 0) >= 300]
if not cands:
    sys.exit(1)
w = max(cands, key=lambda w: (w.get("w") or 0) * (w.get("h") or 0))
print(f"{w['id']}\t{w.get('w')}x{w.get('h')}\t{w.get('title','')}")
PY
}

WIN=""
for _ in $(seq 1 "$WAIT_SEC"); do
  sleep 1
  WIN="$(find_window || true)"
  [ -n "$WIN" ] && break
done
if [ -z "$WIN" ]; then
  echo "✗ drawio 창을 찾지 못했습니다 (${WAIT_SEC}s 대기). --wait 를 늘려보세요." >&2
  [ "$KEEP_OPEN" = 1 ] || kill "$DRAWIO_PID" 2>/dev/null
  exit 1
fi
WIN_ID="$(printf '%s' "$WIN" | cut -f1)"
echo "✓ 창: $WIN"
sleep 2   # 캔버스 최초 렌더 여유

# ── 화면 정리 (computer-use 키 입력) ──────────────────────────────────
send_key() { python3 "$ACTION" key --keys "$1" >/dev/null 2>&1 || true; }

# 패널 접기 단축키는 넣지 않는다 — Ctrl+Shift+P 는 데스크톱 WM 이 가로채
# 창 개요를 띄운다. UI 크롬 없는 이미지가 필요하면 --export 를 쓴다.
if [ "$DO_FIT" = 1 ]; then
  python3 "$ACTION" click --x 1 --y 1 >/dev/null 2>&1 || true   # 창 포커스
  sleep 0.5
  send_key "ctrl+shift+h"    # Fit Page
  sleep 1
fi

# ── 캡처 ──────────────────────────────────────────────────────────────
OUT="$(python3 "$CAPTURE" --mode window --window-id "$WIN_ID" \
        --project "$PROJECT" --label "drawio-$STEM" 2>&1)"
echo "$OUT"
PNG="$(printf '%s' "$OUT" | grep -oE '(/[^ "]+)+\.png' | tail -1)"

if [ "$KEEP_OPEN" = 0 ]; then
  kill "$DRAWIO_PID" 2>/dev/null
  wait "$DRAWIO_PID" 2>/dev/null
  echo "✓ drawio 종료"
fi

if [ -z "$PNG" ] || [ ! -f "$PNG" ]; then
  echo "✗ 캡처 실패 — 위 출력을 확인하세요." >&2
  exit 1
fi
echo
echo "다음: 이 PNG 를 Read 도구로 열어 references/visual-checklist.md 를 검토하세요."
echo "CAPTURED $PNG"
