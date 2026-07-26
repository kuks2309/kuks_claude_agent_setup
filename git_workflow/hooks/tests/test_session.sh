#!/usr/bin/env bash
# git_workflow-session.sh 통합 테스트 — 로컬 bare origin/fito 로 실제 worktree·병합·정리 검증.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION="$(dirname "$HERE")/git_workflow-session.sh"
PASS=0; FAIL=0
ok(){ echo "  PASS $1"; PASS=$((PASS+1)); }
no(){ echo "  FAIL $1: ${2:-}"; FAIL=$((FAIL+1)); }

setup(){
  ROOT="$(mktemp -d)"
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

echo "-- 결과: PASS=$PASS FAIL=$FAIL --"
[ "$FAIL" = 0 ]
