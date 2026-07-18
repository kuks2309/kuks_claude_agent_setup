#!/usr/bin/env bash
# install.sh — user_instruction 번들 설치 (폴더 자기완결)
#
# 사용법: ./install.sh <타깃-프로젝트-루트>
#        ./install.sh <타깃-프로젝트-루트> --status   # 설치본 낡음 점검(설치 안 함)
#   예:   ./install.sh ~/myproject
#
# 동작:
#   1) recording.md + 훅(reminder·merge·session_record) 을 <타깃>/docs/claude_guideline/user_instruction/ 로 복사
#   2) claude.snippet.md 를 <타깃>/CLAUDE.md 에 append (덮어쓰기 아님, 중복 시 스킵)
#   3) .claude/settings.json 에 UserPromptSubmit(reminder)+SessionEnd(merge) 훅 멱등 등록
#   4) .gitignore 에 docs/user_instructions/sessions/ 추가 (세션별 전이 파일)
#   5) 설치 성공 시 <타깃>/docs/claude_guideline/INSTALLED.md 에 자기 행 기록(커밋·날짜·인자)
#   설치 산출물: 규칙(recording.md)·훅. install.sh·claude.snippet.md 는 복사하지 않는다.
#
# --status 판정: 최신(exit 0) / 재설치 권장(exit 1) / 기록 없음(exit 2)

set -euo pipefail

BUNDLE="user_instruction"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TARGET=""
STATUS_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --status) STATUS_ONLY=1 ;;
    -*) echo "unknown arg: $arg" >&2; exit 64 ;;
    *) TARGET="$arg" ;;
  esac
done
[ -n "$TARGET" ] || { echo "사용법: ./install.sh <타깃-프로젝트-루트> [--status]"; exit 1; }
[ -d "$TARGET" ] || { echo "오류: 타깃 경로 없음: $TARGET"; exit 1; }

DEST="$TARGET/docs/claude_guideline/$BUNDLE"
RECORD_FILE="$TARGET/docs/claude_guideline/INSTALLED.md"
INSTALL_ARGS="-"   # 도메인 선택 등 설치 인자 기록(이 번들은 없음)

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
  printf '%s\t%s\n' "$SRC/recording.md" "$DEST/recording.md"
  local hf
  for hf in user_instruction-reminder.py user_instruction-merge.py session_record.py; do
    [ -f "$SRC/hooks/$hf" ] || continue
    printf '%s\t%s\n' "$SRC/hooks/$hf" "$DEST/hooks/$hf"
  done
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

# 1) 규칙 파일 복사 (등록 스니펫 제외, install.sh 는 .md 아니라 자동 제외)
mkdir -p "$DEST"
for f in "$SRC"/*.md; do
  base="$(basename "$f")"
  [ "$base" = "claude.snippet.md" ] && continue
  cp "$f" "$DEST/$base"
done
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

# 강제 훅 — 세션 격리 기록/병합 (모델 비의존)
mkdir -p "$DEST/hooks"
for hf in user_instruction-reminder.py user_instruction-merge.py session_record.py; do
  if [ -f "$SRC/hooks/$hf" ]; then
    cp "$SRC/hooks/$hf" "$DEST/hooks/$hf"
    chmod +x "$DEST/hooks/$hf" 2>/dev/null || true
  fi
done
echo "✓ 훅 복사: docs/claude_guideline/$BUNDLE/hooks/ (reminder·merge·session_record)"

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
  REMINDER="$PYBIN \"\$CLAUDE_PROJECT_DIR/docs/claude_guideline/$BUNDLE/hooks/user_instruction-reminder.py\""
  MERGE="$PYBIN \"\$CLAUDE_PROJECT_DIR/docs/claude_guideline/$BUNDLE/hooks/user_instruction-merge.py\""
  "$PYBIN" - "$SETTINGS" "$REMINDER" "$MERGE" <<'PYEOF'
import json, sys
settings_path, reminder, merge = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(settings_path, encoding="utf-8") as f:
        cfg = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    cfg = {}
hooks = cfg.setdefault("hooks", {})

def ensure(event, cmd, timeout):
    groups = hooks.setdefault(event, [])
    if any(h.get("command") == cmd for g in groups for h in g.get("hooks", [])):
        return "스킵"
    groups.append({"hooks": [{"type": "command", "command": cmd, "timeout": timeout}]})
    return "추가"

a = ensure("UserPromptSubmit", reminder, 5)
b = ensure("SessionEnd", merge, 10)
with open(settings_path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
print(f"✓ settings.json 훅 등록: UserPromptSubmit={a}, SessionEnd={b}")
PYEOF

  # .gitignore 에 세션별 전이 파일 디렉터리 추가 (멱등)
  GI="$TARGET/.gitignore"
  LINE="docs/user_instructions/sessions/"
  touch "$GI"
  grep -qxF "$LINE" "$GI" || { printf '%s\n' "$LINE" >> "$GI"; echo "✓ .gitignore: $LINE 추가"; }
fi

# 5) 설치 기록
record_install

echo "완료: $BUNDLE → $TARGET"
