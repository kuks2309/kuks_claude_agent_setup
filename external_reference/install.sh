#!/usr/bin/env bash
# install.sh — external_reference 번들 설치 (코어 + 선택 도메인)
#
# 사용법:
#   ./install.sh <타깃-프로젝트-루트>                   # 코어만
#   ./install.sh <타깃-프로젝트-루트> embedded ros2     # 코어 + 지정 도메인
#   ./install.sh <타깃-프로젝트-루트> --all             # 코어 + 모든 도메인
#
# 동작:
#   1) handling.md(코어)를 <타깃>/docs/claude_guideline/external_reference/ 로 복사
#   2) 지정 도메인(domains/<도메인>.md)을 .../external_reference/domains/ 로 복사
#   3) claude.snippet.md 를 <타깃>/CLAUDE.md 에 append (마커 중복방지)

set -euo pipefail

BUNDLE="external_reference"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

list_domains() {
  echo "사용 가능한 도메인:"
  for f in "$SRC"/domains/*.md; do echo "  - $(basename "$f" .md)"; done
}

STATUS_ONLY=0
ARGS=()
for arg in "$@"; do
  case "$arg" in
    --status) STATUS_ONLY=1 ;;
    *) ARGS+=("$arg") ;;
  esac
done
set -- "${ARGS[@]}"

TARGET="${1:-}"
if [ -z "$TARGET" ]; then
  echo "사용법: ./install.sh <타깃-프로젝트-루트> [도메인... | --all] [--status]"
  echo
  list_domains
  exit 1
fi
[ -d "$TARGET" ] || { echo "오류: 타깃 경로 없음: $TARGET"; exit 1; }
shift

DEST="$TARGET/docs/claude_guideline/$BUNDLE"
RECORD_FILE="$TARGET/docs/claude_guideline/INSTALLED.md"
INSTALL_ARGS="$*"
[ -n "$INSTALL_ARGS" ] || INSTALL_ARGS="-"

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
  echo "✓ 설치 기록: docs/claude_guideline/INSTALLED.md ($BUNDLE @ $commit)"
}

# 설치본 ↔ 저장소 내용 대조 쌍(원본<TAB>설치본). 번들별로 복사 대상과 일치시켜 유지.
drift_pairs() {
  printf '%s\t%s\n' "$SRC/handling.md" "$DEST/handling.md"
  printf '%s\t%s\n' "$SRC/coding_standards.md" "$DEST/coding_standards.md"
  if [ -f "$SRC/hooks/$BUNDLE-reminder.py" ]; then
    printf '%s\t%s\n' "$SRC/hooks/$BUNDLE-reminder.py" "$DEST/hooks/$BUNDLE-reminder.py"
  fi
  local f d
  if [ -d "$DEST/domains" ]; then
    for f in "$DEST/domains/"*.md; do
      [ -f "$f" ] || continue
      d="$(basename "$f")"
      printf '%s\t%s\n' "$SRC/domains/$d" "$f"
    done
  fi
}

status_check() {
  echo "[STATUS] $BUNDLE @ $TARGET"
  local line
  line="$(grep "^| $BUNDLE |" "$RECORD_FILE" 2>/dev/null | tail -1)" || true
  if [ -z "$line" ]; then
    echo "  ✗ 설치 기록 없음 — 구판 설치이거나 미설치. 재설치하면 기록이 생성됩니다."
    echo "  → cd $BUNDLE && ./install.sh <타깃>"
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
      echo "  ⚠ 설치본 누락: ${d#"$TARGET"/}"; drift=1
    elif ! diff -q "$s" "$d" >/dev/null 2>&1; then
      echo "  ⚠ 설치본 ≠ 저장소: ${d#"$TARGET"/}"; drift=1
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
    echo "  → 재설치 권장: cd $BUNDLE && ./install.sh <타깃>  (인자: $args_str)"
    exit 1
  fi
  echo "  → 최신"
  exit 0
}

[ "$STATUS_ONLY" = 1 ] && status_check

# 1) 코어 복사 (handling.md + coding_standards.md)
mkdir -p "$DEST"
cp "$SRC/handling.md" "$DEST/handling.md"
cp "$SRC/coding_standards.md" "$DEST/coding_standards.md"
echo "✓ 코어 복사: docs/claude_guideline/$BUNDLE/{handling.md, coding_standards.md}"

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

# 4) 설치 기록
record_install

echo "완료: $BUNDLE → $TARGET"
