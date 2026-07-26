#!/usr/bin/env bash
# git_workflow-safepush.sh — 공유 main 안전 push (다중 세션 push 경쟁·미러 발산 자동 해소).
#
# 여러 세션(한 창 다중 탭)이 같은 `main` 에 올릴 때 "origin 이 방금 바뀜 → 거부 → 다시" 가
# 반복되는 문제를, 사용자가 신경 안 쓰게 자동 처리한다:
#   임시 worktree 에서 origin/main 최신 위로 '이 저장소의 미푸시 커밋(패치 기준)'만 얹어 push,
#   push.lock flock 직렬화 + 재시도, origin·fito(미러) 둘 다 동기.
# **공유 워킹트리·HEAD 미접촉** → 다른 탭의 미커밋 변경/작업과 무관하게 안전.
#
# 사용: git_workflow-safepush.sh [<branch>]   (기본 main)
# self-contained: git 만. 계약: 성공 exit 0, 충돌 exit 3(수동 필요), 실패 exit 1.
set -euo pipefail

say(){ echo "safepush: $*"; }
err(){ echo "safepush: $*" >&2; }

main_repo(){
  local cdir
  cdir="$(git rev-parse --git-common-dir 2>/dev/null)" || return 1
  cdir="$(cd "$cdir" 2>/dev/null && pwd)" || return 1
  dirname "$cdir"
}

BR="${1:-main}"
REPO="$(main_repo)" || { err "git 저장소 아님"; exit 1; }
GITDIR="$(git -C "$REPO" rev-parse --absolute-git-dir)"
mkdir -p "$GITDIR/git_workflow"
exec 9>"$GITDIR/git_workflow/push.lock"
flock 9   # 동시 push 직렬화

# 미러 원격 목록 (origin 필수, fito 있으면 포함)
REMOTES=(origin)
git -C "$REPO" remote | grep -qx fito && REMOTES+=(fito)

push_all_from(){  # $1 = git dir to push from, pushes HEAD:BR to all remotes (origin 먼저)
  local from="$1" r
  git -C "$from" push origin "HEAD:$BR" -q 2>/tmp/gw_pl || return 1
  for r in "${REMOTES[@]:1}"; do
    git -C "$from" push "$r" "HEAD:$BR" -q 2>/dev/null || err "$r push 실패(미러 지연) — 나중에 동기 필요"
  done
  return 0
}

for i in 1 2 3 4 5 6; do
  git -C "$REPO" fetch origin -q 2>/dev/null || true
  # 미푸시 커밋(패치 기준): git cherry 의 '+' = origin 에 없는 것. 해시 드리프트/재적용분 자동 제외.
  mapfile -t UNPUSHED < <(git -C "$REPO" cherry "origin/$BR" "$BR" 2>/dev/null | awk '/^\+/{print $2}')
  if [ "${#UNPUSHED[@]}" -eq 0 ]; then
    # 올릴 것 없음 → 미러만 origin 에 맞춤(ff 시도)
    for r in "${REMOTES[@]:1}"; do
      git -C "$REPO" push "$r" "refs/remotes/origin/$BR:refs/heads/$BR" -q 2>/dev/null \
        && say "미러 $r 동기" || true
    done
    say "✓ origin 최신 — 올릴 커밋 없음"
    exit 0
  fi

  TMP="$(mktemp -d)/sp"
  git -C "$REPO" worktree add --detach "$TMP" "origin/$BR" -q
  cp_ok=1
  for c in "${UNPUSHED[@]}"; do
    if ! git -C "$TMP" cherry-pick "$c" -x >/tmp/gw_cp 2>&1; then
      git -C "$TMP" cherry-pick --abort 2>/dev/null || true
      cp_ok=0; break
    fi
  done
  if [ "$cp_ok" = 0 ]; then
    git -C "$REPO" worktree remove --force "$TMP" 2>/dev/null || true
    err "충돌: 이 저장소 커밋이 origin/$BR 과 같은 줄에서 겹칩니다 — 수동 병합 필요."
    exit 3
  fi
  if push_all_from "$TMP"; then
    git -C "$REPO" worktree remove --force "$TMP" 2>/dev/null || true
    say "✓ $BR push 완료 (${#UNPUSHED[@]}개 커밋, attempt $i) → ${REMOTES[*]}"
    exit 0
  fi
  git -C "$REPO" worktree remove --force "$TMP" 2>/dev/null || true
  say "• attempt $i: origin 이 그새 바뀜 — 최신 받아 재시도"
done

err "origin push 반복 실패(경쟁 과다) — 잠시 후 재시도하세요."
exit 1
