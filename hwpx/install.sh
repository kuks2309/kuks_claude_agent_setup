#!/usr/bin/env bash
# install.sh — hwpx 번들 전역 설치 (~/.claude): 한글(HWP/HWPX) 문서 생성·편집 + PDF 렌더 검증 루프
#
# 사용법:
#   ./install.sh                 # 파일 배치 + 의존성 설치(setup_env.sh, ~350MB 다운로드 가능) + preflight
#   ./install.sh --no-deps       # 의존성 설치 생략(파일 배치만; 테스트/오프라인)
#   ./install.sh --check         # preflight 만 수행(설치 안 함)
#   ./install.sh --status        # 설치본 낡음 점검(설치 안 함)
#   CLAUDE_HOME=/tmp/x ./install.sh --no-deps   # 설치 루트 변경(테스트용)
#
# 배치:
#   skill/ (SKILL.md, scripts/, references/, assets/, evals/) -> $CLAUDE_HOME/skills/hwpx/
#   claude.snippet.md                                         -> $CLAUDE_HOME/CLAUDE.md (marker 중복방지)
#
# 의존성(설치 단계에서 setup_env.sh 가 루트 없이 구성):
#   포터블 LibreOffice 25.8 + H2Orestart 확장(Java/JRE 필요) + Nanum 폰트 + fontconfig 별칭
#   시스템 권장: poppler-utils(pdftoppm/pdftotext), default-jre  (없으면 preflight 가 안내)
#
# 설치 성공 시 $CLAUDE_HOME/INSTALLED.md 에 자기 행 기록(커밋·날짜·인자). --check 는 기록하지 않는다.
# --status 판정: 최신(exit 0) / 재설치 권장(exit 1) / 기록 없음(exit 2)
#
# 전역 설치이므로 설치 후 어느 프로젝트에서든 hwpx 스킬 사용 가능. 멱등.
set -euo pipefail

BUNDLE="hwpx"
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
  command -v python3 >/dev/null 2>&1 && echo "  python3 ✓" || { echo "  ✗ python3 없음" >&2; return 1; }
  command -v java >/dev/null 2>&1 && echo "  java ✓" \
    || echo "  · java 없음 → H2Orestart(HWPX 렌더) 불가. sudo apt install default-jre"
  command -v pdftoppm >/dev/null 2>&1 && echo "  pdftoppm ✓" \
    || echo "  · pdftoppm 없음 → sudo apt install poppler-utils (또는 pip install pypdfium2)"
  local so
  so="$(ls "$HOME"/.local/opt/libreoffice/opt/libreoffice*/program/soffice 2>/dev/null | tail -1 || true)"
  if [ -n "$so" ]; then echo "  포터블 LibreOffice ✓ ($so)"
  elif command -v soffice >/dev/null 2>&1; then echo "  · 시스템 soffice 만 존재 → H2Orestart 는 Java 지원 LibreOffice 필요(setup_env.sh 가 포터블 구성)"
  else echo "  · LibreOffice 없음 → 의존성 설치 단계(setup_env.sh)가 포터블 구성"
  fi
}

install_deps() {
  [ "$NO_DEPS" = "1" ] && { echo "[DEPS] 생략(--no-deps)"; return 0; }
  echo "[DEPS] setup_env.sh (포터블 LibreOffice + H2Orestart + Nanum 폰트, 루트 불필요)"
  bash "$CLAUDE_HOME/skills/hwpx/scripts/setup_env.sh"
  python3 -m pip install --user -q python-hwpx
  echo "  python-hwpx ✓"
}

place() {
  echo "[PLACE] -> $CLAUDE_HOME/skills/hwpx"
  mkdir -p "$CLAUDE_HOME/skills"
  rm -rf "$CLAUDE_HOME/skills/hwpx"
  cp -r "$SRC/skill" "$CLAUDE_HOME/skills/hwpx"
  chmod +x "$CLAUDE_HOME/skills/hwpx/scripts/"*.py "$CLAUDE_HOME/skills/hwpx/scripts/setup_env.sh"
  echo "  SKILL.md · scripts/ · references/ · assets/ · evals/ 배치"
}

register_claude_md() {
  local md="$CLAUDE_HOME/CLAUDE.md" marker="kuks_agent_setup:hwpx"
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
  printf '%s\t%s\n' "$SRC/skill/SKILL.md" "$CLAUDE_HOME/skills/hwpx/SKILL.md"
  printf '%s\t%s\n' "$SRC/skill/scripts/render_verify.py" "$CLAUDE_HOME/skills/hwpx/scripts/render_verify.py"
  printf '%s\t%s\n' "$SRC/skill/scripts/render_pdf.py" "$CLAUDE_HOME/skills/hwpx/scripts/render_pdf.py"
  printf '%s\t%s\n' "$SRC/skill/scripts/remove_paragraphs.py" "$CLAUDE_HOME/skills/hwpx/scripts/remove_paragraphs.py"
  printf '%s\t%s\n' "$SRC/skill/references/render-verify.md" "$CLAUDE_HOME/skills/hwpx/references/render-verify.md"
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
    fi
  fi
  [ -n "$note_compare" ] && echo "  · $note_compare"

  if [ "$stale" = 1 ]; then
    echo "  → 재설치 권장: cd $BUNDLE && ./install.sh"
    exit 1
  fi
  echo "  ✓ 최신"
  exit 0
}

# ---- main ----
[ "$STATUS_ONLY" = 1 ] && status_check
preflight
[ "$CHECK_ONLY" = 1 ] && { echo "[CHECK] preflight 완료 (설치 안 함)"; exit 0; }
place
install_deps
register_claude_md
record_install
echo "DONE — 사용: Claude Code 에서 '한글 보고서 만들어줘' 등 (hwpx 스킬 자동 발동)"
