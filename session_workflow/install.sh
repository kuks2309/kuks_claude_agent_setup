#!/usr/bin/env bash
# install.sh — session_workflow 번들 설치 (폴더 자기완결)
#
# 사용법: ./install.sh <타깃-프로젝트-루트>
#   예:   ./install.sh ~/myproject
#        ./install.sh <타깃-프로젝트-루트> --status   # 설치본 낡음 점검(설치 안 함)
#
# 동작:
#   1) session_workflow.md + 훅 7개를 <타깃>/docs/claude_guideline/session_workflow/ 로 복사
#   2) claude.snippet.md 를 <타깃>/CLAUDE.md 에 append (마커 중복 스킵)
#   3) .claude/settings.json 에 SessionStart·UserPromptSubmit·PreToolUse(Write·Bash)·PostToolUse·SessionEnd 훅 멱등 등록
#   4) 설치 성공 시 <타깃>/docs/claude_guideline/INSTALLED.md 에 자기 행 기록(커밋·날짜·인자)
#   상태는 .git/session_workflow/ (비커밋) — .gitignore 불요.
#   설치 산출물: 규칙(session_workflow.md)·훅. install.sh·claude.snippet.md 는 복사하지 않는다.
#
# --status 판정: 최신(exit 0) / 재설치 권장(exit 1) / 기록 없음(exit 2)

set -euo pipefail

BUNDLE="session_workflow"
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
  local f base
  for f in "$SRC"/*.md; do
    base="$(basename "$f")"
    [ "$base" = "claude.snippet.md" ] && continue
    printf '%s\t%s\n' "$f" "$DEST/$base"
  done
  local hf
  for hf in session_state.py session_workflow-start.py session_workflow-gate.py \
            session_workflow-track.py session_workflow-write-guard.py \
            session_workflow-state-guard.py session_workflow-end.py; do
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

# 1) 규칙 파일 복사 (등록 스니펫 제외)
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
# python 은 등록 블록 갱신(아래)과 settings.json 훅 등록(§4) 양쪽에서 쓰므로 먼저 해석한다.
PYBIN=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1; then PYBIN="$c"; break; fi
done
touch "$CLAUDE_MD"
if grep -qF "$MARKER" "$CLAUDE_MD"; then
  # 등록 블록 = 마커 줄부터 다음 빈 줄·다른 번들 마커·EOF 직전까지(스니펫 = 마커 + 단락 1개).
  # 그 범위를 현재 claude.snippet.md 로 덮어써, 모델이 매 세션 읽는 규칙 진입점
  # (CLAUDE.md)의 문구를 규칙 본문과 일치시킨다.
  if [ -n "${PYBIN:-}" ] && "$PYBIN" - "$CLAUDE_MD" "$SRC/claude.snippet.md" "$MARKER" <<'PYEOF'
import sys
md_path, snip_path, marker = sys.argv[1:4]
lines = open(md_path, encoding="utf-8").read().split("\n")
snippet = open(snip_path, encoding="utf-8").read().rstrip("\n").split("\n")
out, i, replaced = [], 0, False
while i < len(lines):
    if marker in lines[i] and not replaced:
        i += 1
        while i < len(lines) and lines[i].strip() != "" and "kuks_agent_setup:" not in lines[i]:
            i += 1
        out += snippet
        replaced = True
        continue
    out.append(lines[i]); i += 1
if not replaced:
    sys.exit(1)
open(md_path, "w", encoding="utf-8").write("\n".join(out))
PYEOF
  then
    echo "✓ CLAUDE.md 등록 갱신(기존 블록 교체)"
  else
    echo "• CLAUDE.md 등록 이미 존재 — 갱신 실패, 수동 확인 필요"
  fi
else
  printf '\n' >> "$CLAUDE_MD"
  cat "$SRC/claude.snippet.md" >> "$CLAUDE_MD"
  echo "✓ CLAUDE.md 등록 추가"
fi

# 3) 훅 복사
mkdir -p "$DEST/hooks"
for hf in session_state.py session_workflow-start.py session_workflow-gate.py \
          session_workflow-track.py session_workflow-write-guard.py \
          session_workflow-state-guard.py session_workflow-end.py; do
  cp "$SRC/hooks/$hf" "$DEST/hooks/$hf"
  chmod +x "$DEST/hooks/$hf" 2>/dev/null || true
done
echo "✓ 훅 복사: docs/claude_guideline/$BUNDLE/hooks/"

# 4) settings.json 훅 멱등 등록
if [ -z "$PYBIN" ]; then
  echo "⚠ python3/python 없음 — settings.json 훅 등록 건너뜀. 수동 등록 필요."
else
  mkdir -p "$TARGET/.claude"
  SETTINGS="$TARGET/.claude/settings.json"
  [ -f "$SETTINGS" ] && cp "$SETTINGS" "$SETTINGS.bak" && echo "✓ 백업: .claude/settings.json.bak"
  H="\$CLAUDE_PROJECT_DIR/docs/claude_guideline/$BUNDLE/hooks"
  "$PYBIN" - "$SETTINGS" \
    "$PYBIN \"$H/session_workflow-start.py\"" \
    "$PYBIN \"$H/session_workflow-gate.py\"" \
    "$PYBIN \"$H/session_workflow-track.py\"" \
    "$PYBIN \"$H/session_workflow-end.py\"" \
    "$PYBIN \"$H/session_workflow-write-guard.py\"" \
    "$PYBIN \"$H/session_workflow-state-guard.py\"" <<'PYEOF'
import json, sys
settings_path, start, gate, track, end, guard, state_guard = sys.argv[1:8]
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

def ensure_end_before_merge(cmd, timeout):
    """SessionEnd 는 세션 브랜치 자동 병합 훅(git_workflow-session-end)보다 앞에 등록.

    병합 훅이 세션 worktree 를 제거한 뒤에는 handoff 를 만들 수 없으므로 순서가 계약.
    기존 등록이 있어도 제거 후 병합 훅 바로 앞(없으면 말미)에 재삽입 — 멱등·자가 교정.
    """
    groups = hooks.setdefault("SessionEnd", [])
    def mine(g):
        return any(h.get("command") == cmd for h in g.get("hooks", []))
    existed = any(mine(g) for g in groups)
    kept = [g for g in groups if not mine(g)]
    idx = next((i for i, g in enumerate(kept)
                if any("git_workflow-session-end" in (h.get("command") or "")
                       for h in g.get("hooks", []))), len(kept))
    kept.insert(idx, {"hooks": [{"type": "command", "command": cmd,
                                 "timeout": timeout}]})
    hooks["SessionEnd"] = kept
    return "추가(병합 훅 앞)" if not existed else "순서 보장(병합 훅 앞)"

a = ensure("SessionStart", start, 10)
b = ensure("UserPromptSubmit", gate, 5)
c = ensure("PostToolUse", track, 5, matcher="Write|Edit|MultiEdit|NotebookEdit")
d = ensure_end_before_merge(end, 10)
e = ensure("PreToolUse", guard, 5, matcher="Write")
g = ensure("PreToolUse", state_guard, 5, matcher="Bash")
with open(settings_path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
print(f"✓ settings.json 훅 등록: SessionStart={a}, UserPromptSubmit={b}, "
      f"PostToolUse={c}, SessionEnd={d}, PreToolUse(Write)={e}, PreToolUse(Bash)={g}")
PYEOF
fi

# 5) 설치 기록
record_install

echo "완료: $BUNDLE → $TARGET"
