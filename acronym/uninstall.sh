#!/usr/bin/env bash
# uninstall.sh — 영어 약자 표기 번들 전역 제거 (~/.claude). install.sh 의 역(逆).
#
# 사용법:
#   ./uninstall.sh                # ~/.claude 에서 acronym 흔적 제거
#   (CLAUDE_HOME 환경변수로 제거 루트 변경 가능 — 테스트용)
#
# 동작 (install 3단계를 역순으로):
#   1) settings.json 에서 acronym 훅 등록 제거 (review + 옛 reminder/check 흔적, 다른 훅 보존, 사전 백업)
#   2) CLAUDE.md 에서 스니펫(마커+규칙 줄) 제거 (사전 백업)
#   3) $CLAUDE_HOME/acronym/ 파일·디렉토리 제거
#
# 주의: .bak 로 '복원'하지 않는다. 옛 .bak 에는 이전 구성(reminder+check)이 들어있어
#       복원하면 제거하려던 옛 훅이 되살아난다. 그래서 외과적 제거만 한다. 멱등(이미 없어도 안전).

set -euo pipefail

CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
DEST="$CLAUDE_HOME/acronym"

# 1) settings.json 훅 등록 제거 (사전 백업)
SETTINGS="$CLAUDE_HOME/settings.json"
if [ -f "$SETTINGS" ]; then
  cp "$SETTINGS" "$SETTINGS.bak" && echo "✓ 백업: $SETTINGS.bak"
  python3 - "$SETTINGS" <<'PYEOF'
import json, sys
p = sys.argv[1]
targets = ("acronym-review.py", "acronym-reminder.sh", "acronym-check.py")
try:
    with open(p, encoding="utf-8") as f:
        cfg = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    print("• settings.json 파싱 불가 — 스킵"); sys.exit(0)
hooks = cfg.get("hooks", {})
removed = 0
for event in list(hooks):
    groups = hooks[event]
    for g in groups:
        before = g.get("hooks", [])
        after = [h for h in before if not any(t in h.get("command", "") for t in targets)]
        removed += len(before) - len(after)
        g["hooks"] = after
    hooks[event] = [g for g in groups if g.get("hooks")]  # 빈 그룹 정리
    if not hooks[event]:
        del hooks[event]                                    # 빈 이벤트 정리
with open(p, "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"✓ settings.json: acronym 훅 등록 {removed}건 제거")
PYEOF
else
  echo "• settings.json 없음 — 스킵"
fi

# 2) CLAUDE.md 스니펫 제거 (마커 앵커, 사전 백업)
CLAUDE_MD="$CLAUDE_HOME/CLAUDE.md"
if [ -f "$CLAUDE_MD" ]; then
  cp "$CLAUDE_MD" "$CLAUDE_MD.bak" && echo "✓ 백업: $CLAUDE_MD.bak"
  python3 - "$CLAUDE_MD" <<'PYEOF'
import re, sys
p = sys.argv[1]
marker = "kuks_agent_setup:acronym"
lines = open(p, encoding="utf-8").read().split("\n")
out, i, removed = [], 0, 0
while i < len(lines):
    if marker in lines[i]:
        removed += 1; i += 1
        # 마커 다음의 스니펫 본문(빈 줄/다음 <!-- 마커/EOF 전까지) 제거
        while i < len(lines) and lines[i].strip() != "" and not lines[i].lstrip().startswith("<!--"):
            removed += 1; i += 1
        continue
    out.append(lines[i]); i += 1
text = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).rstrip("\n") + "\n"
open(p, "w", encoding="utf-8").write(text)
print(f"✓ CLAUDE.md: 스니펫 {removed}줄 제거" if removed else "• CLAUDE.md: 스니펫 없음 — 스킵")
PYEOF
else
  echo "• CLAUDE.md 없음 — 스킵"
fi

# 3) acronym 디렉토리 제거
if [ -d "$DEST" ]; then
  rm -f "$DEST/acronym.md" "$DEST/acronym-review.py" \
        "$DEST/acronym-reminder.sh" "$DEST/acronym-check.py"
  rm -rf "$DEST/__pycache__"
  rmdir "$DEST" 2>/dev/null && echo "✓ $DEST 제거" || echo "✓ acronym 파일 제거 ($DEST 에 다른 파일 남아 디렉토리는 보존)"
else
  echo "• $DEST 없음 — 스킵"
fi

echo "완료: acronym 제거 → $CLAUDE_HOME (적용은 세션 재시작 후)"
