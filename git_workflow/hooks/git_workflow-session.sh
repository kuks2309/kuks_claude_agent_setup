#!/usr/bin/env bash
# git_workflow-session.sh — 세션별 worktree 격리 + 종료 시 main 안전 병합.
#
# 다중 세션(한 창 다중 탭)이 공유 워킹트리·공유 HEAD 를 쓰면 커밋이 main 에 교차되어
# 동시 push 경쟁·미러 발산이 생긴다. 본 도구는 각 세션을 자기 worktree(별도 폴더)·
# session/<id> 브랜치로 격리하고, 종료 시 main 에 안전 병합(flock 직렬화·충돌 시 보류)한다.
#
# 사용:
#   git_workflow-session.sh start <id>   # ../<repo>-ses-<id> worktree + session/<id> 생성, 경로 출력
#   git_workflow-session.sh end   <id>   # session/<id> → main 안전 병합, 성공 시 worktree·브랜치 정리
#   git_workflow-session.sh list         # 활성 세션 worktree/브랜치
#
# self-contained: git 만 사용. 계약: 성공 exit 0. end 는 충돌 시 브랜치 보존 후 exit 3.
set -euo pipefail

say(){ echo "session: $*"; }
err(){ echo "session: $*" >&2; }

# 메인 워킹트리 경로 (공유 .git 의 common-dir 부모)
main_repo(){
  local cdir
  cdir="$(git rev-parse --git-common-dir 2>/dev/null)" || return 1
  cdir="$(cd "$cdir" 2>/dev/null && pwd)" || return 1   # 절대경로화(이식성)
  dirname "$cdir"
}

# origin/main 있으면 그것, 없으면 로컬 main 을 base 로
merge_base_ref(){
  local repo="$1"
  if git -C "$repo" show-ref --verify --quiet refs/remotes/origin/main; then
    echo "origin/main"
  else
    echo "main"
  fi
}

# 이 브랜치를 체크아웃한 worktree 경로 (없으면 빈 문자열)
worktree_of_branch(){
  git -C "$1" worktree list --porcelain | awk -v b="refs/heads/$2" '
    /^worktree /{p=$2} /^branch /{if($2==b) print p}'
}

cmd_start(){
  local id="${1:-}"; [ -n "$id" ] || { err "start <id> 필요"; exit 1; }
  local short="${id:0:8}" repo; repo="$(main_repo)" || { err "git 저장소 아님"; exit 1; }
  local branch="session/$short"
  local wt; wt="$(dirname "$repo")/$(basename "$repo")-ses-$short"

  git -C "$repo" fetch origin -q 2>/dev/null || true
  if git -C "$repo" show-ref --verify --quiet "refs/heads/$branch"; then
    err "이미 존재: $branch"; local ex; ex="$(worktree_of_branch "$repo" "$branch")"
    [ -n "$ex" ] && echo "$ex"; exit 0
  fi
  local base; base="$(merge_base_ref "$repo")"
  git -C "$repo" worktree add "$wt" -b "$branch" "$base" -q
  say "worktree 생성: $wt (branch $branch, base $base)"
  say "→ 이 폴더에서 작업하세요. 종료 시 'end $short' 로 main 병합·정리."
  echo "$wt"
}

cmd_list(){
  local repo; repo="$(main_repo)" || { err "git 저장소 아님"; exit 1; }
  git -C "$repo" worktree list | sed 's/^/  /'
  echo "  --- session 브랜치 ---"
  git -C "$repo" branch --list 'session/*' | sed 's/^/  /' || true
}

cmd_end(){
  local id="${1:-}"; [ -n "$id" ] || { err "end <id> 필요"; exit 1; }
  local short="${id:0:8}" repo; repo="$(main_repo)" || { err "git 저장소 아님"; exit 1; }
  local branch="session/$short"
  git -C "$repo" show-ref --verify --quiet "refs/heads/$branch" || { say "브랜치 없음: $branch (병합 불필요)"; exit 0; }

  local gitdir; gitdir="$(git -C "$repo" rev-parse --absolute-git-dir)"
  mkdir -p "$gitdir/git_workflow"
  exec 9>"$gitdir/git_workflow/merge.lock"
  flock 9   # 동시 종료 직렬화

  git -C "$repo" fetch origin -q 2>/dev/null || true
  git -C "$repo" push origin "$branch" -q 2>/dev/null || true   # 브랜치 백업(best-effort)

  local base; base="$(merge_base_ref "$repo")"
  local tmp; tmp="$(mktemp -d)/merge"
  git -C "$repo" worktree add --detach "$tmp" "$base" -q

  local merged=0
  if git -C "$tmp" merge --no-ff -m "merge $branch into main" "$branch" -q 2>/dev/null; then
    local ok=0 i
    for i in 1 2 3 4 5; do
      if git -C "$tmp" push origin HEAD:main -q 2>/dev/null; then ok=1; break; fi
      git -C "$repo" fetch origin -q 2>/dev/null || true
      # main 이 움직였으면 origin/main 위로 재병합
      git -C "$tmp" reset --hard origin/main -q 2>/dev/null || true
      git -C "$tmp" merge --no-ff -m "merge $branch into main" "$branch" -q 2>/dev/null || { ok=2; break; }
    done
    if [ "$ok" = 1 ]; then
      merged=1
      git -C "$tmp" push fito HEAD:main -q 2>/dev/null || err "fito push 실패(미러 지연) — 나중에 동기 필요"
    elif [ "$ok" = 2 ]; then
      err "재병합 중 충돌 — $branch 보존, 수동 병합 필요"
    else
      err "origin push 반복 실패 — $branch 보존"
    fi
  else
    git -C "$tmp" merge --abort 2>/dev/null || true
    err "CONFLICT: $branch 이 main 과 충돌 — 보존. 수동 병합 필요: git merge --no-ff $branch"
  fi

  git -C "$repo" worktree remove --force "$tmp" 2>/dev/null || true

  if [ "$merged" = 1 ]; then
    local swt; swt="$(worktree_of_branch "$repo" "$branch")"
    [ -n "$swt" ] && git -C "$repo" worktree remove --force "$swt" 2>/dev/null || true
    git -C "$repo" branch -D "$branch" -q 2>/dev/null || true
    git -C "$repo" push origin --delete "$branch" -q 2>/dev/null || true
    say "✓ $branch → main 병합·push 완료, worktree·브랜치 정리됨"
    exit 0
  fi
  exit 3   # 보류(충돌/실패) — 브랜치 보존
}

case "${1:-}" in
  start) shift; cmd_start "$@";;
  end)   shift; cmd_end "$@";;
  list)  shift; cmd_list "$@";;
  *) err "사용: git_workflow-session.sh {start|end|list} [<id>]"; exit 1;;
esac
