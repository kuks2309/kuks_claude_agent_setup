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

# 훅·규칙 상속 — 새 worktree 에 공유 트리(main worktree)의 설치본을 링크한다.
#
# 왜 필요한가: worktree 는 git 이 '추적하는 파일'만 체크아웃한다. 가이드라인 설치본
# (docs/claude_guideline/**)과 훅 등록(.claude/settings.json)은 대개 미추적·gitignore
# 대상이라 새 트리에 따라오지 않는다 → 세션 격리를 강제해야 할 바로 그 작업 공간에서
# 훅이 조용히 무동작(no-op)이 된다. 실물 복사 대신 링크라 공유 트리 갱신이 즉시 반영된다.
# 추적본은 절대 덮지 않는다(브랜치가 일부 번들을 커밋해 둔 경우 그 파일이 정본).
link_shared_assets(){
  local repo="$1" wt="$2" src dst b name
  # 1) 훅 등록: 디렉토리는 실물로 두고 파일만 링크 — .gitignore 의 `.claude/` 패턴이 계속 먹도록.
  if [ -f "$repo/.claude/settings.json" ]; then
    mkdir -p "$wt/.claude"
    [ -e "$wt/.claude/settings.json" ] || \
      ln -s "$repo/.claude/settings.json" "$wt/.claude/settings.json"
  fi
  # 2) 규칙·훅 본체
  src="$repo/docs/claude_guideline"; dst="$wt/docs/claude_guideline"
  [ -d "$src" ] || return 0
  if [ ! -e "$dst" ]; then
    mkdir -p "$wt/docs"
    ln -s "$src" "$dst"
  else
    for b in "$src"/*/; do            # 일부 번들이 추적 중 → 없는 번들만 개별 링크
      [ -d "$b" ] || continue
      name="$(basename "$b")"
      [ -e "$dst/$name" ] || ln -s "${b%/}" "$dst/$name"
    done
  fi
}

# push 성공 후 공유 저장소의 **로컬 main** 을 origin/main 에 맞춘다.
#
# 왜 필요한가: 병합은 임시 detached worktree 에서 일어나 origin 으로 push 되고 그 트리는
# 폐기된다. 즉 refs/heads/main 을 갱신하는 경로가 없어, 세션이 끝날 때마다 origin 만
# 전진하고 공유 main 은 제자리에 남는다 — 발산이 누적되는 구조적 원인.
#
# 3분기: main 미체크아웃 → ref 만 갱신(작업트리 무영향) / 체크아웃+clean → fast-forward /
#        dirty → **보류하고 소리내어 경고**. 조용한 보류가 이 사태를 키웠으므로 침묵 금지.
sync_local_main(){
  local repo="$1"
  git -C "$repo" fetch origin -q 2>/dev/null || true
  git -C "$repo" show-ref --verify --quiet refs/remotes/origin/main || return 0

  # main 을 **어느 워크트리가** 물고 있는지로 판정한다. $repo 의 HEAD 만 보면 main 이
  # 링크드 워크트리에 체크아웃된 배치를 «미체크아웃»으로 오판해 update-ref 로 가고,
  # 그러면 그 워크트리는 HEAD 만 전진하고 index·파일은 옛 커밋에 남는다. 그 상태에서
  # status 는 전 차이를 «스테이지된 되돌리기»로 보여주며, 거기서 누가 커밋하면 다른
  # 세션이 병합한 것이 통째로 되돌아간다(실측: 25파일, 워킹트리 vs index 차이는 0건).
  git -C "$repo" show-ref --verify --quiet refs/heads/main || return 0  # 로컬 main 없음
  local mwt; mwt="$(worktree_of_branch "$repo" "main")"

  if [ -z "$mwt" ]; then
    # 아무 워크트리도 main 을 쓰지 않음 → ref 직접 갱신이 안전(작업트리 안 건드림).
    if git -C "$repo" merge-base --is-ancestor main origin/main 2>/dev/null; then
      if git -C "$repo" update-ref refs/heads/main origin/main 2>/dev/null; then
        say "로컬 main → origin/main 동기화(ref 갱신)"
      else
        err "⚠ 로컬 main ref 갱신 실패 — origin/main 과 벌어진 채 남습니다."
      fi
    else
      err "⚠ 로컬 main 이 origin/main 의 조상이 아님(발산) — 자동 동기화 보류."
      err "   확인: git -C \"$repo\" log --oneline origin/main..main"
    fi
    return 0
  fi

  # main 체크아웃 중(공유 트리든 링크드 워크트리든) — 그 트리에서 ff 하고
  # **git 자신의 보호에 맡긴다**. ff 가 미커밋 변경을 덮을 상황이면
  # git 이 거부하고(“Your local changes would be overwritten”), 무관하면 안전하게 전진한다.
  # dirty 이면 무조건 보류하던 판정은 과했다: 공유 트리에는 타 세션의 **미추적** 파일이
  # 상시 남아 있어(ff 로 덮일 수 없는 것들) 로컬 main 이 영영 동기화되지 못했다(실측).
  # `set -e` 주의: 실패하는 명령 치환을 대입문에 쓰면 경고를 내기 전에 스크립트가
  # 종료된다(실측: ff 거부 시 보류 경고가 조용히 사라졌다). 반드시 조건문 안에서 실행.
  local out
  if out="$(git -C "$mwt" merge --ff-only origin/main 2>&1)"; then
    say "로컬 main → origin/main 동기화(fast-forward)"
  else
    err "⚠ 로컬 main fast-forward 보류 — origin/main 과 벌어진 채 남습니다."
    err "   git: $(echo "$out" | head -2 | tr '\n' ' ')"
    err "   해소: 해당 변경을 커밋·정리 후 git -C \"$mwt\" merge --ff-only origin/main"
  fi
}

# 이 브랜치를 체크아웃한 worktree 경로 (없으면 빈 문자열)
# 경로에 공백이 있을 수 있다(실측: 저장소 폴더명이 'LGIT-C6-Cobot ' 로 끝나는 사례).
# awk $2 로 자르면 첫 공백까지만 잡혀 존재하지 않는 경로가 되고, cmd_end 의
# worktree remove 가 not a working tree 로 실패 → 브랜치도 체크아웃 중이라 삭제 거부된다.
# 따라서 'worktree ' 접두(9자) 뒤 줄 전체를 쓴다.
worktree_of_branch(){
  git -C "$1" worktree list --porcelain | awk -v b="refs/heads/$2" '
    /^worktree /{p=substr($0,10)} /^branch /{if($2==b){print p; exit}}'
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
  # 경로에 남은 잔재 회수 — worktree 로 등록돼 있지 않고 **점(.)으로 시작하는 항목만**
  # 들어 있으면 도구가 만든 캐시(예: .omc/)뿐이므로 안전하게 치운다. 이 잔재를 그대로
  # 두면 worktree 생성이 경로 선점으로 실패한다. 실제 파일이 하나라도 있으면 손대지 않는다.
  if [ -e "$wt" ] && [ -z "$(worktree_of_branch "$repo" "$branch")" ] && \
     ! git -C "$repo" worktree list --porcelain | grep -qxF "worktree $wt"; then
    if [ -d "$wt" ] && [ -z "$(find "$wt" -mindepth 1 -maxdepth 1 ! -name '.*' 2>/dev/null)" ]; then
      rm -rf "$wt" && say "경로 잔재 회수: $wt (도구 캐시만 있어 제거)"
    fi
  fi

  local base; base="$(merge_base_ref "$repo")"
  # 생성 실패 시 브랜치만 남는 경우가 있다(예: 경로에 이전 실행의 디렉터리가 잔존).
  # 그대로 두면 다음 start 가 '이미 존재'로 막히므로, 만들어진 브랜치를 되돌린다.
  local out
  if ! out="$(git -C "$repo" worktree add "$wt" -b "$branch" "$base" -q 2>&1)"; then
    err "worktree 생성 실패: $wt"
    err "   git: $(echo "$out" | head -2 | tr '\n' ' ')"
    if git -C "$repo" show-ref --verify --quiet "refs/heads/$branch" && \
       [ -z "$(worktree_of_branch "$repo" "$branch")" ] && \
       [ "$(git -C "$repo" rev-list --count "$base..$branch" 2>/dev/null || echo 1)" = "0" ]; then
      git -C "$repo" branch -D "$branch" -q 2>/dev/null && \
        err "   (커밋 없는 잔여 브랜치 $branch 되돌림)"
    fi
    [ -e "$wt" ] && err "   경로에 남은 것: $wt — 확인 후 정리하세요."
    exit 1
  fi
  link_shared_assets "$repo" "$wt"
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
  # 임시 worktree 의 admin 항목 정리 — 제거가 실패했거나 /tmp 가 먼저 비워지면
  # `git worktree list` 에 prunable 항목이 계속 쌓인다(실측: 이전 실행분 잔존).
  git -C "$repo" worktree prune 2>/dev/null || true

  if [ "$merged" = 1 ]; then
    # 정리 결과를 모아 보고한다. 각 단계의 오류를 삼키면 브랜치·디렉터리가 남아도
    # "정리됨" 이 찍혀 알 방법이 없고, 다음 `start` 가 '이미 존재'로 실패한다.
    local swt out left=""
    swt="$(worktree_of_branch "$repo" "$branch")"
    if [ -n "$swt" ]; then
      if ! out="$(git -C "$repo" worktree remove --force "$swt" 2>&1)"; then
        left="$left\n  - worktree 제거 실패: $swt — $(echo "$out" | head -1)"
      fi
    fi
    git -C "$repo" worktree prune 2>/dev/null || true
    # remove 가 성공해도 다른 도구가 그 안에 만든 파일 때문에 디렉터리가 남을 수 있다.
    if [ -n "$swt" ] && [ -d "$swt" ]; then
      left="$left\n  - 디렉터리 잔존: $swt ($(find "$swt" -mindepth 1 2>/dev/null | wc -l) 항목)"
    fi
    if ! out="$(git -C "$repo" branch -D "$branch" 2>&1)"; then
      left="$left\n  - 로컬 브랜치 삭제 실패: $branch — $(echo "$out" | head -1)"
    fi
    if git -C "$repo" ls-remote --exit-code --heads origin "$branch" >/dev/null 2>&1; then
      if ! out="$(git -C "$repo" push origin --delete "$branch" 2>&1)"; then
        left="$left\n  - 원격 브랜치 삭제 실패: origin/$branch — $(echo "$out" | head -1)"
      fi
    fi
    sync_local_main "$repo"   # origin 만 전진하고 공유 main 이 뒤처지는 발산 차단
    if [ -n "$left" ]; then
      err "⚠ 병합·push 는 완료했으나 정리에 남은 것이 있습니다:"
      printf '%b\n' "$left" >&2
      err "   방치하면 다음 'start' 가 '이미 존재'로 실패합니다 — 수동 정리 필요."
    else
      say "✓ $branch → main 병합·push 완료, worktree·브랜치 정리됨"
    fi
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
