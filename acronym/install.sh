#!/usr/bin/env bash
# install.sh — 영어 약자 표기 번들 전역 설치 (~/.claude)
#
# 사용법:
#   ./install.sh                  # CLAUDE.md 규칙 등록 + Stop 검토 훅 등록
#   ./install.sh --status         # 설치본 낡음 점검(설치 안 함)
#   (CLAUDE_HOME 환경변수로 설치 루트 변경 가능 — 테스트용)
#
# 동작:
#   1) 규칙(acronym.md) + Stop 검토 훅(acronym-review.py)을 $CLAUDE_HOME/acronym/ 로 복사
#   2) claude.snippet.md 를 $CLAUDE_HOME/CLAUDE.md 에 append (마커 중복방지)
#   3) $CLAUDE_HOME/settings.json 에 Stop 검토 훅 멱등 등록 (기존 보존, 사전 백업)
#   4) 설치 성공 시 $CLAUDE_HOME/INSTALLED.md 에 자기 행 기록(커밋·날짜·인자)
#   * 마이그레이션: 옛 훅(acronym-reminder.sh / acronym-check.py)의 파일과 settings 등록을 제거.
#
# 검토 훅은 답변을 마친 뒤 후보 약자를 제시해 AI 가 스스로 병기 누락을 보완하게 한다
# (위반 단정·강제 재작성 아님 — 규칙 본문은 acronym.md 참조).
#
# --status 판정: 최신(exit 0) / 재설치 권장(exit 1) / 기록 없음(exit 2)

set -euo pipefail

BUNDLE="acronym"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
DEST="$CLAUDE_HOME/acronym"
RECORD_FILE="$CLAUDE_HOME/INSTALLED.md"

STATUS_ONLY=0
ARGS_REST=()
for arg in "$@"; do
  case "$arg" in
    --status) STATUS_ONLY=1 ;;
    *) ARGS_REST+=("$arg") ;;
  esac
done
INSTALL_ARGS="${ARGS_REST[*]:-}"
[ -z "$INSTALL_ARGS" ] && INSTALL_ARGS="-"

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

# 설치본 ↔ 저장소 내용 대조 쌍(원본<TAB>설치본).
drift_pairs() {
  printf '%s\t%s\n' "$SRC/acronym.md" "$DEST/acronym.md"
  printf '%s\t%s\n' "$SRC/hooks/acronym-review.py" "$DEST/acronym-review.py"
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

# 1) 규칙·검토 훅 복사 + 옛 훅 파일 정리
mkdir -p "$DEST"
cp "$SRC/acronym.md"               "$DEST/acronym.md"
cp "$SRC/hooks/acronym-review.py"  "$DEST/acronym-review.py"
chmod +x "$DEST/acronym-review.py"
rm -f "$DEST/acronym-reminder.sh" "$DEST/acronym-check.py"  # 옛 훅 파일 제거
echo "✓ 규칙·검토 훅 복사: $DEST (옛 훅 파일 정리됨)"

# 2) CLAUDE.md 등록 (마커 중복방지)
CLAUDE_MD="$CLAUDE_HOME/CLAUDE.md"
MARKER="kuks_agent_setup:acronym"
touch "$CLAUDE_MD"
if grep -qF "$MARKER" "$CLAUDE_MD"; then
  echo "• CLAUDE.md 등록 이미 존재 — 스킵"
else
  printf '\n' >> "$CLAUDE_MD"
  cat "$SRC/claude.snippet.md" >> "$CLAUDE_MD"
  echo "✓ CLAUDE.md 등록 추가"
fi

# 3) settings.json 훅 등록 (사전 백업 후 python 멱등 merge)
#    - 등록: Stop = acronym-review.py
#    - 제거: 옛 acronym-reminder.sh(UserPromptSubmit) / acronym-check.py(Stop) 등록
SETTINGS="$CLAUDE_HOME/settings.json"
[ -f "$SETTINGS" ] && cp "$SETTINGS" "$SETTINGS.bak" && echo "✓ 백업: $SETTINGS.bak"
python3 - "$SETTINGS" "$DEST" <<'PYEOF'
import json, sys
settings_path, dest = sys.argv[1], sys.argv[2]
review = f"python3 {dest}/acronym-review.py"
# 옛 등록 식별용 부분문자열 (경로가 달라도 파일명으로 매칭)
stale = ("acronym-reminder.sh", "acronym-check.py")
try:
    with open(settings_path, encoding="utf-8") as f:
        cfg = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    cfg = {}
hooks = cfg.setdefault("hooks", {})

def strip_stale():
    removed = 0
    for event in list(hooks):
        groups = hooks[event]
        for g in groups:
            before = g.get("hooks", [])
            after = [h for h in before if not any(s in h.get("command", "") for s in stale)]
            removed += len(before) - len(after)
            g["hooks"] = after
        # 빈 그룹/이벤트 정리
        hooks[event] = [g for g in groups if g.get("hooks")]
        if not hooks[event]:
            del hooks[event]
    return removed

def ensure(event, cmd, timeout):
    groups = hooks.setdefault(event, [])
    for g in groups:
        for h in g.get("hooks", []):
            if h.get("command") == cmd:
                return "스킵"
    groups.append({"hooks": [{"type": "command", "command": cmd, "timeout": timeout}]})
    return "추가"

n = strip_stale()
a = ensure("Stop", review, 10)
with open(settings_path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
print(f"✓ settings.json: 옛 훅 등록 {n}건 제거, Stop 검토 훅={a}")
PYEOF

# 4) 설치 기록
record_install

echo "완료: acronym → $CLAUDE_HOME (적용은 세션 재시작 후)"
