#!/usr/bin/env bash
# git_workflow-session.sh 통합 테스트 — 로컬 bare origin/fito 로 실제 worktree·병합·정리 검증.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION="$(dirname "$HERE")/git_workflow-session.sh"
PASS=0; FAIL=0
ok(){ echo "  PASS $1"; PASS=$((PASS+1)); }
no(){ echo "  FAIL $1: ${2:-}"; FAIL=$((FAIL+1)); }

setup(){
  # SPACE_SUFFIX 로 경로에 공백을 끼운 변형을 만든다(공백 경로 회귀 시험용).
  ROOT="$(mktemp -d)${SPACE_SUFFIX:-}"
  mkdir -p "$ROOT"
  git init --bare -q "$ROOT/origin.git"
  git init --bare -q "$ROOT/fito.git"
  git clone -q "$ROOT/origin.git" "$ROOT/repo"
  git -C "$ROOT/repo" config user.email t@t
  git -C "$ROOT/repo" config user.name t
  git -C "$ROOT/repo" config commit.gpgsign false
  git -C "$ROOT/repo" remote add fito "$ROOT/fito.git"
  mkdir -p "$ROOT/repo/docs/claude_guideline/git_workflow"
  echo rule > "$ROOT/repo/docs/claude_guideline/git_workflow/git_workflow.md"
  echo base > "$ROOT/repo/file.txt"
  git -C "$ROOT/repo" add -A
  git -C "$ROOT/repo" commit -q -m init
  git -C "$ROOT/repo" branch -M main
  git -C "$ROOT/repo" push -q -u origin main
  git -C "$ROOT/repo" push -q fito main
  git -C "$ROOT/repo" fetch -q origin
}
run(){ ( cd "$ROOT/repo" && bash "$SESSION" "$@" ); }

echo "== start =="
setup
run start SESSA >/dev/null 2>&1
WT="$ROOT/repo-ses-SESSA"
[ -d "$WT" ] && ok start_worktree || no start_worktree "worktree 없음"
git -C "$ROOT/repo" show-ref --verify --quiet refs/heads/session/SESSA && ok start_branch || no start_branch

echo "== end (clean merge) =="
echo "새 파일" > "$WT/newfile.txt"
git -C "$WT" add -A; git -C "$WT" commit -q -m "session work"
run end SESSA >/dev/null 2>&1; rc=$?
[ "$rc" = 0 ] && ok end_exit0 || no end_exit0 "exit=$rc"
git -C "$ROOT/repo" fetch -q origin
git -C "$ROOT/repo" cat-file -e origin/main:newfile.txt 2>/dev/null && ok merged_to_origin || no merged_to_origin "newfile origin/main 부재"
[ ! -d "$WT" ] && ok worktree_cleaned || no worktree_cleaned "worktree 잔존"
git -C "$ROOT/repo" show-ref --verify --quiet refs/heads/session/SESSA && no branch_deleted "브랜치 잔존" || ok branch_deleted
git -C "$ROOT/repo" fetch -q fito
[ "$(git -C "$ROOT/repo" rev-parse origin/main)" = "$(git -C "$ROOT/repo" rev-parse fito/main)" ] && ok fito_synced || no fito_synced "미러 불일치"

echo "== end (conflict → 보류) =="
setup
run start SESB >/dev/null 2>&1
WTB="$ROOT/repo-ses-SESB"
echo "B버전" > "$WTB/file.txt"; git -C "$WTB" add -A; git -C "$WTB" commit -q -m "B edit"
# main 을 충돌나게 전진(다른 세션이 file.txt 를 이미 바꿔 병합한 상황 모사)
echo "main버전" > "$ROOT/repo/file.txt"
git -C "$ROOT/repo" commit -aq -m "main edit"
git -C "$ROOT/repo" push -q origin main
run end SESB >/dev/null 2>&1; rc=$?
[ "$rc" = 3 ] && ok conflict_exit3 || no conflict_exit3 "exit=$rc (기대 3)"
git -C "$ROOT/repo" show-ref --verify --quiet refs/heads/session/SESB && ok branch_preserved || no branch_preserved "충돌인데 브랜치 삭제됨"
git -C "$ROOT/repo" fetch -q origin
[ "$(git -C "$ROOT/repo" show origin/main:file.txt)" = "main버전" ] && ok main_uncorrupted || no main_uncorrupted "main 오염"

echo "== start (훅·규칙 상속 링크) =="
setup
# 공유 트리에만 있는 미추적 설치본 — worktree 는 이것을 체크아웃하지 못한다.
mkdir -p "$ROOT/repo/.claude" "$ROOT/repo/docs/claude_guideline/session_workflow"
echo '{}' > "$ROOT/repo/.claude/settings.json"
echo rule > "$ROOT/repo/docs/claude_guideline/session_workflow/session_workflow.md"
run start SESC >/dev/null 2>&1
WTC="$ROOT/repo-ses-SESC"
[ -L "$WTC/.claude/settings.json" ] && ok link_settings || no link_settings "settings.json 링크 없음"
[ -f "$WTC/docs/claude_guideline/session_workflow/session_workflow.md" ] \
  && ok link_rule_reachable || no link_rule_reachable "링크 경유로 규칙 파일 도달 불가"
[ -L "$WTC/docs/claude_guideline/session_workflow" ] \
  && ok link_missing_bundle || no link_missing_bundle "미추적 번들이 링크되지 않음"
# 브랜치가 추적 중인 번들(git_workflow)은 실디렉터리로 보존 — 링크로 덮으면 안 됨
{ [ ! -L "$WTC/docs/claude_guideline/git_workflow" ] && \
  [ -f "$WTC/docs/claude_guideline/git_workflow/git_workflow.md" ]; } \
  && ok tracked_preserved || no tracked_preserved "추적본이 링크로 대체됨"

echo "== start (설치본이 전부 미추적일 때 = 디렉터리 통째 링크) =="
git -C "$ROOT/repo" rm -rq docs/claude_guideline
git -C "$ROOT/repo" commit -q -m "drop tracked guideline"
git -C "$ROOT/repo" push -q origin main
mkdir -p "$ROOT/repo/docs/claude_guideline/session_workflow"
echo rule > "$ROOT/repo/docs/claude_guideline/session_workflow/session_workflow.md"
run start SESD >/dev/null 2>&1
WTD="$ROOT/repo-ses-SESD"
[ -L "$WTD/docs/claude_guideline" ] && ok link_whole_dir || no link_whole_dir "디렉터리 통째 링크 실패"
[ -f "$WTD/docs/claude_guideline/session_workflow/session_workflow.md" ] \
  && ok link_whole_reachable || no link_whole_reachable "링크 경유 도달 불가"

# 회귀 방지: 병합은 임시 detached worktree 에서 일어나 origin 으로 push 되므로,
# refs/heads/main 을 갱신하지 않으면 origin 만 전진하고 공유 main 이 영구히 뒤처진다.
# (실제 사고: 로컬 main 이 origin/main 대비 55 커밋 뒤처진 채 발산)
echo "== end (로컬 main 동기화 — clean → fast-forward) =="
setup
run start SESE >/dev/null 2>&1
WTE="$ROOT/repo-ses-SESE"
echo "E작업" > "$WTE/e.txt"; git -C "$WTE" add -A; git -C "$WTE" commit -q -m "E work"
run end SESE >/dev/null 2>&1
[ "$(git -C "$ROOT/repo" rev-parse main)" = "$(git -C "$ROOT/repo" rev-parse origin/main)" ] \
  && ok local_main_ff || no local_main_ff "로컬 main 이 origin/main 과 불일치(발산)"
[ -f "$ROOT/repo/e.txt" ] && ok local_worktree_updated || no local_worktree_updated "작업트리에 병합 결과 미반영"

# 공유 트리에는 타 세션의 미커밋·미추적 파일이 상시 남는다. dirty 이면 무조건 보류하면
# 로컬 main 이 영영 동기화되지 못한다(실측). 덮어쓸 수 있는 것만 git 이 거부하게 맡긴다.
echo "== end (로컬 main 동기화 — 무관한 dirty·미추적은 ff 진행) =="
setup
run start SESF >/dev/null 2>&1
WTF="$ROOT/repo-ses-SESF"
echo "F작업" > "$WTF/f.txt"; git -C "$WTF" add -A; git -C "$WTF" commit -q -m "F work"
echo "미커밋 편집" >> "$ROOT/repo/file.txt"      # 병합이 건드리지 않는 파일
echo "미추적" > "$ROOT/repo/untracked.txt"       # ff 로 덮일 수 없는 것
run end SESF >/dev/null 2>&1
[ "$(git -C "$ROOT/repo" rev-parse main)" = "$(git -C "$ROOT/repo" rev-parse origin/main)" ] \
  && ok unrelated_dirty_ff || no unrelated_dirty_ff "무관한 dirty 인데 보류(영영 동기화 안 됨)"
[ "$(tail -1 "$ROOT/repo/file.txt")" = "미커밋 편집" ] \
  && ok dirty_preserved || no dirty_preserved "타 세션 미커밋 변경이 사라짐"
[ -f "$ROOT/repo/untracked.txt" ] && ok untracked_preserved || no untracked_preserved "미추적 파일 소실"

echo "== end (로컬 main 동기화 — 덮어쓸 dirty 는 보류 + 경고) =="
setup
run start SESF2 >/dev/null 2>&1
WTF2="$ROOT/repo-ses-SESF2"
echo "세션이 바꾼 내용" > "$WTF2/file.txt"        # 세션도 file.txt 를 건드리고
git -C "$WTF2" commit -aq -m "F2 edit file.txt"
echo "공유 트리 미커밋" >> "$ROOT/repo/file.txt"  # 공유 트리도 같은 파일을 미커밋 수정
OUT="$(run end SESF2 2>&1)"
[ "$(git -C "$ROOT/repo" rev-parse main)" != "$(git -C "$ROOT/repo" rev-parse origin/main)" ] \
  && ok clobbering_ff_deferred || no clobbering_ff_deferred "덮어쓸 dirty 인데 ff 강행"
echo "$OUT" | grep -q "보류" && ok clobber_warns || no clobber_warns "보류를 조용히 처리(경고 없음)"
grep -q "공유 트리 미커밋" "$ROOT/repo/file.txt" \
  && ok clobber_preserved || no clobber_preserved "타 세션 미커밋 변경이 사라짐"

echo "== end (임시 worktree admin 항목 정리) =="
setup
run start SESH >/dev/null 2>&1
echo "H작업" > "$ROOT/repo-ses-SESH/h.txt"
git -C "$ROOT/repo-ses-SESH" add -A; git -C "$ROOT/repo-ses-SESH" commit -q -m "H work"
run end SESH >/dev/null 2>&1
[ "$(git -C "$ROOT/repo" worktree list --porcelain | grep -c '^prunable')" = "0" ] \
  && ok no_prunable_leftover || no_prunable_leftover_fail=1
[ -n "${no_prunable_leftover_fail:-}" ] && no no_prunable_leftover "임시 worktree admin 항목 잔존"

echo "== end (로컬 main 동기화 — main 미체크아웃 → ref 갱신) =="
setup
git -C "$ROOT/repo" checkout --detach -q          # 공유 트리가 main 을 안 물고 있는 상태
run start SESG >/dev/null 2>&1
WTG="$ROOT/repo-ses-SESG"
echo "G작업" > "$WTG/g.txt"; git -C "$WTG" add -A; git -C "$WTG" commit -q -m "G work"
run end SESG >/dev/null 2>&1
[ "$(git -C "$ROOT/repo" rev-parse refs/heads/main)" = "$(git -C "$ROOT/repo" rev-parse origin/main)" ] \
  && ok detached_ref_updated || no detached_ref_updated "main ref 미갱신"

# 정리·생성 실패는 **드러나야** 한다. 오류를 삼키면 브랜치·디렉터리가 남아도 "정리됨"이
# 찍히고, 다음 start 가 '이미 존재'로 막힌다(실측: 이전 실행의 디렉터리가 남아 start 실패,
# 그때 생성된 브랜치만 남아 두 번째 실패를 부름).
echo "== start 실패 시 잔여 브랜치를 남기지 않는다 =="
setup
WTX="$ROOT/repo-ses-SESX"
mkdir -p "$WTX"; echo "이전 실행 잔재" > "$WTX/leftover.txt"   # 경로 선점
OUT="$(run start SESX 2>&1)"; rc=$?
[ "$rc" != 0 ] && ok start_fail_exit_nonzero || no start_fail_exit_nonzero "실패인데 exit=$rc"
echo "$OUT" | grep -q "worktree 생성 실패" && ok start_fail_reported || no start_fail_reported "실패를 알리지 않음"
git -C "$ROOT/repo" show-ref --verify --quiet refs/heads/session/SESX \
  && no start_fail_no_dangling_branch "잔여 브랜치 session/SESX 남음" || ok start_fail_no_dangling_branch

echo "== 경로에 도구 캐시만 남아 있으면 회수하고 진행한다 =="
setup
WTR="$ROOT/repo-ses-SESR"
mkdir -p "$WTR/.omc/observations"; echo cache > "$WTR/.omc/patterns.md"   # 다른 도구가 만든 잔재
OUT="$(run start SESR 2>&1)"; rc=$?
[ "$rc" = 0 ] && ok reclaim_exit0 || no reclaim_exit0 "회수 가능한 잔재인데 exit=$rc"
echo "$OUT" | grep -q "경로 잔재 회수" && ok reclaim_reported || no reclaim_reported "회수를 알리지 않음"
git -C "$ROOT/repo" show-ref --verify --quiet refs/heads/session/SESR \
  && ok reclaim_branch_created || no reclaim_branch_created "브랜치 미생성"

echo "== 실제 파일이 있으면 회수하지 않고 실패한다 =="
setup
WTK="$ROOT/repo-ses-SESK"
mkdir -p "$WTK"; echo "사람이 둔 파일" > "$WTK/keep.txt"
OUT="$(run start SESK 2>&1)"; rc=$?
[ "$rc" != 0 ] && ok keep_exit_nonzero || no keep_exit_nonzero "실제 파일이 있는데 exit=$rc"
[ -f "$WTK/keep.txt" ] && ok keep_file_preserved || no keep_file_preserved "사용자 파일이 삭제됨"

echo "== end 성공 시 디렉터리까지 실제로 사라진다 =="
setup
run start SESY >/dev/null 2>&1
WTY="$ROOT/repo-ses-SESY"
echo "Y작업" > "$WTY/y.txt"; git -C "$WTY" add -A; git -C "$WTY" commit -q -m "Y work"
OUT="$(run end SESY 2>&1)"
[ ! -e "$WTY" ] && ok end_dir_gone || no end_dir_gone "디렉터리 잔존: $WTY"
echo "$OUT" | grep -q "정리됨" && ok end_reports_clean || no end_reports_clean "정리 완료 보고 없음"
echo "$OUT" | grep -q "정리에 남은 것" && no end_no_false_alarm "잔여 없는데 경고" || ok end_no_false_alarm

echo "== 원격에 세션 브랜치가 없어도 실패로 보고하지 않는다 =="
setup
run start SESZ >/dev/null 2>&1
WTZ="$ROOT/repo-ses-SESZ"
echo "Z작업" > "$WTZ/z.txt"; git -C "$WTZ" add -A; git -C "$WTZ" commit -q -m "Z work"
git -C "$ROOT/repo" push -q origin session/SESZ 2>/dev/null || true
git -C "$ROOT/repo" push -q origin --delete session/SESZ 2>/dev/null || true   # 원격만 미리 제거
OUT="$(run end SESZ 2>&1)"
echo "$OUT" | grep -q "원격 브랜치 삭제 실패" && no end_no_remote_false_alarm "없는 원격 브랜치를 실패로 보고" \
  || ok end_no_remote_false_alarm

echo "== 경로에 공백이 있어도 start·end 가 정리까지 끝낸다 =="
# worktree list --porcelain 을 awk $2 로 파싱하면 경로가 첫 공백에서 잘려 end 의
# worktree remove 가 'not a working tree' 로 실패하고, 그러면 브랜치가 그 worktree 에
# 체크아웃된 채라 branch -D 도 거부된다 — 정리 3단계가 통째로 무력화된다. 위 케이스는
# 전부 mktemp 경로(공백 없음)라 이 결함을 못 잡는다. 실측: 폴더명이 'LGIT-C6-Cobot '
# 인 프로젝트에서 종료된 세션 worktree 가 무한 누적(1개당 151MB).
SPACE_SUFFIX="/dir name"
setup
run start SESW >/dev/null 2>&1
WTW="$ROOT/repo-ses-SESW"
[ -d "$WTW" ] && ok space_start_worktree || no space_start_worktree "worktree 없음: $WTW"
echo "W작업" > "$WTW/w.txt"
git -C "$WTW" add w.txt; git -C "$WTW" commit -q -m "W work"
OUT="$(run end SESW 2>&1)"
[ ! -e "$WTW" ] && ok space_end_dir_gone || no space_end_dir_gone "디렉터리 잔존: $WTW"
git -C "$ROOT/repo" show-ref --verify --quiet refs/heads/session/SESW \
  && no space_branch_deleted "브랜치 잔존" || ok space_branch_deleted
echo "$OUT" | grep -q "정리됨" && ok space_end_reports_clean || no space_end_reports_clean "정리 완료 보고 없음"
unset SPACE_SUFFIX

echo "-- 결과: PASS=$PASS FAIL=$FAIL --"
[ "$FAIL" = 0 ]
