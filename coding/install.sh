#!/usr/bin/env bash
# install.sh — coding 번들 설치 (폴더 자기완결)
#
# 사용법: ./install.sh <타깃-프로젝트-루트> [도메인...|--all]
#   도메인: ros2-coding embedded-coding numeric-coding concurrency-coding memory-coding
#
# 동작:
#   1) 코어(coding.md·conventions.md·stack.md·adr-template.md) + checks/ → docs/claude_guideline/coding/
#   2) 선택 도메인(domains/<d>.md) 복사 (--all 이면 전부)
#   3) .pre-commit / ci 템플릿 복사(.sample, 덮어쓰기 금지)
#   4) 타깃 .gitignore 에 .omc/ 추가 (OMC creep 차단)
#   5) claude.snippet.md → CLAUDE.md append (마커 중복방지)
#   설치 산출물은 규칙·이빨뿐 — install.sh·claude.snippet.md 는 복사하지 않는다.
set -euo pipefail

BUNDLE="coding"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
[ -n "$TARGET" ] || { echo "사용법: ./install.sh <타깃-프로젝트-루트> [도메인...|--all] [--status]"; exit 1; }
[ -d "$TARGET" ] || { echo "오류: 타깃 경로 없음: $TARGET"; exit 1; }
shift || true

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
  local f d c
  for f in coding.md conventions.md stack.md adr-template.md; do
    printf '%s\t%s\n' "$SRC/$f" "$DEST/$f"
  done
  for c in "$SRC/checks/"*.sh; do
    [ -f "$c" ] || continue
    printf '%s\t%s\n' "$c" "$DEST/checks/$(basename "$c")"
  done
  for c in "$SRC/hooks/"*.py; do
    [ -f "$c" ] || continue
    printf '%s\t%s\n' "$c" "$DEST/hooks/$(basename "$c")"
  done
  for c in "$SRC/tests/"*.sh; do
    [ -f "$c" ] || continue
    printf '%s\t%s\n' "$c" "$DEST/tests/$(basename "$c")"
  done
  if [ -f "$SRC/.pre-commit-config.yaml" ]; then
    printf '%s\t%s\n' "$SRC/.pre-commit-config.yaml" "$DEST/pre-commit-config.sample.yaml"
  fi
  if [ -d "$SRC/ci" ]; then
    for c in "$SRC/ci/"*.yml; do
      [ -f "$c" ] || continue
      printf '%s\t%s\n' "$c" "$DEST/ci/$(basename "$c")"
    done
  fi
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

mkdir -p "$DEST/domains" "$DEST/checks"

# 1) 코어 + 이빨
for f in coding.md conventions.md stack.md adr-template.md; do cp "$SRC/$f" "$DEST/$f"; done
cp "$SRC"/checks/*.sh "$DEST/checks/"
chmod +x "$DEST"/checks/*.sh
echo "✓ 코어 3 + ADR 템플릿 + 이빨 $(ls "$SRC"/checks/*.sh 2>/dev/null | wc -l | tr -d ' ') 복사 → docs/claude_guideline/$BUNDLE/"

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

# 강제 훅 2종
#   reminder       (UserPromptSubmit) — 트리거 감지 시 규칙 SOP 주입 [1세대: 주입]
#   inventory-gate (PreToolUse/PostToolUse) — 함수표 선독을 차단으로 강제 [2세대: 차단]
# 주입만으로는 "표 갱신은 코딩 끝나고" 미루기를 막지 못한 실사격 사례가 있어 차단을 더했다.
if [ -d "$SRC/hooks" ]; then
  mkdir -p "$DEST/hooks"
  for h in "$SRC/hooks/"*.py; do
    [ -f "$h" ] || continue
    cp "$h" "$DEST/hooks/$(basename "$h")"
    chmod +x "$DEST/hooks/$(basename "$h")" 2>/dev/null || true
    echo "✓ 훅 복사: docs/claude_guideline/$BUNDLE/hooks/$(basename "$h")"
  done
  if [ -d "$SRC/tests" ]; then
    mkdir -p "$DEST/tests"
    for t in "$SRC/tests/"*.sh; do
      [ -f "$t" ] || continue
      cp "$t" "$DEST/tests/$(basename "$t")"
      echo "✓ 테스트 복사: docs/claude_guideline/$BUNDLE/tests/$(basename "$t")"
    done
  fi

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
    HOOK_BASE="$PYBIN \"\$CLAUDE_PROJECT_DIR/docs/claude_guideline/$BUNDLE/hooks"
    REMIND_CMD="$HOOK_BASE/$BUNDLE-reminder.py\""
    GATE_CMD="$HOOK_BASE/$BUNDLE-inventory-gate.py\""
    RECORD_CMD="$HOOK_BASE/$BUNDLE-record-gate.py\""
    "$PYBIN" - "$SETTINGS" "$REMIND_CMD" "$GATE_CMD" "$RECORD_CMD" \
              "$([ -f "$SRC/hooks/$BUNDLE-reminder.py" ] && echo 1 || echo 0)" \
              "$([ -f "$SRC/hooks/$BUNDLE-inventory-gate.py" ] && echo 1 || echo 0)" \
              "$([ -f "$SRC/hooks/$BUNDLE-record-gate.py" ] && echo 1 || echo 0)" <<'PYEOF'
import json, sys
(settings_path, remind, gate, record,
 has_remind, has_gate, has_record) = sys.argv[1:8]
try:
    with open(settings_path, encoding="utf-8") as f:
        cfg = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    cfg = {}
hooks = cfg.setdefault("hooks", {})

def ensure(event, cmd, timeout, matcher=None):
    groups = hooks.setdefault(event, [])
    if any(h.get("command") == cmd for g in groups for h in g.get("hooks", [])):
        return "스킵"
    g = {"hooks": [{"type": "command", "command": cmd, "timeout": timeout}]}
    if matcher is not None:
        g["matcher"] = matcher
    groups.append(g)
    return "추가"

msg = []
if has_remind == "1":
    msg.append("UserPromptSubmit(reminder)=" + ensure("UserPromptSubmit", remind, 5))
if has_gate == "1":
    # PreToolUse 는 코드 수정을 차단, PostToolUse(Read) 는 읽은 표를 기록 — 둘이 한 쌍
    msg.append("PreToolUse(gate)=" + ensure(
        "PreToolUse", gate, 10, matcher="Write|Edit|MultiEdit|NotebookEdit"))
    msg.append("PostToolUse(read-track)=" + ensure(
        "PostToolUse", gate, 5, matcher="Read"))
if has_record == "1":
    # Stop — §6 표 갱신 확인. ⟦CI:index-fresh⟧ 는 커밋 시점이라 커밋 없는 턴이 빈다.
    msg.append("Stop(record-gate)=" + ensure("Stop", record, 10))
with open(settings_path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
print("✓ settings.json 훅 등록: " + ", ".join(msg))
PYEOF
  fi
fi

# 6) .clang-format 자동 고정 — C 계열 코드 존재 + 스타일 미선택이면 기본 Allman 생성 (stack.md §1)
if [ ! -f "$TARGET/.clang-format" ] && \
   find "$TARGET" -name .git -prune -o -type f \
     \( -name '*.c' -o -name '*.cc' -o -name '*.cpp' -o -name '*.h' -o -name '*.hpp' \) \
     -print -quit 2>/dev/null | grep -q .; then
  printf '# stack.md §1 기본 — Microsoft 스타일(Allman 중괄호 포함). 변경은 ADR + 전체 재포맷 1커밋.\nBasedOnStyle: Microsoft\n' \
    > "$TARGET/.clang-format"
  echo "✓ .clang-format 자동 생성(BasedOnStyle: Microsoft — Allman) — 기존 C 계열 전체가 format 검사 대상"
fi

# 7) 설치 기록
record_install

echo "완료: $BUNDLE → $TARGET"
echo "  다음: pre-commit install (로컬 강제) · ci/ 워크플로 활성 (서버 강제) · 무-CI 면 README 의 수동 재생성 따름"
