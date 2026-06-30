# git_workflow 번들 — Git 커밋·푸시 워크플로

Claude Code 에이전트가 git 작업(commit/push/merge/PR/branch) 시 따르는 **협업 절차 규칙**. solo/team 모드 판정, 커밋 규약, 다중 원격 미러, team PR·리뷰 게이트를 한 곳에서 소유한다. 판단 기준은 마크다운(`git_workflow.md`), 진입 강제는 UserPromptSubmit 훅이다.

## 설치

```bash
cd git_workflow && ./install.sh <타깃-프로젝트-루트>
```

`git_workflow.md` + `hooks/` 를 `docs/claude_guideline/git_workflow/` 로 복사, `CLAUDE.md` 에 등록 스니펫 append, 타깃 `.claude/settings.json` 에 UserPromptSubmit(reminder)·PostToolUse(track) 훅 등록(python 있을 때). **활성화 게이트**: 본 파일이 그 경로에 없으면 룰 비활성. **설치 산출물은 규칙·훅뿐** — `install.sh`·`claude.snippet.md`·`README.md` 는 복사하지 않는다.

## 모드 (solo vs team)

push·리뷰 방식이 모드에 갈리므로 작업 전 먼저 판정한다 (→ `git_workflow.md` §0). **모드는 기록된 선언이 권위** — 저장소 `README.md` 의 `git 협업 모드: solo|team` 줄이 최우선, 없으면 `CLAUDE.md` 선언, **둘 다 없으면 사용자에게 문의 후 README 에 기록**한다(자동 default 금지). 자동 감지는 *문의 시 제안 근거*일 뿐 단독 확정하지 않는다.

| 모드 | 기록 / 신호 | push 방식 |
| --- | --- | --- |
| **solo** | README/CLAUDE.md 에 `git 협업 모드: solo` | `main` 직접 commit + push (다중 원격이면 모두) |
| **team** | README/CLAUDE.md 에 `git 협업 모드: team` (제안 근거: collaborator ≥2 · CODEOWNERS · `main` 보호 · 다중 author · "팀/공유" 맥락) | `main` 직접 push 금지 → 브랜치 → PR → 리뷰 ≥1 → merge |
| **미선언** | 위 선언 없음 | **진행 전 사용자 문의 → README 기록** (solo 임의 진행 금지) |

**원격별 판정** — 미러 원격마다 collaborator 가 다르면 각 원격이 그 모드를 따른다. **관리자 단방향 미러**(예: `fito`)는 직접 push 를 문서화된 예외로 허용 가능.

## 강제 모델 — 정직 선언

- **UserPromptSubmit 훅**(`hooks/git_workflow-reminder.py`) = git 트리거(커밋/푸시/머지/PR/브랜치/rebase/stash 등) 감지 시 응답 전 SOP + **이 세션 수정 파일 목록**을 주입. CLAUDE.md '수동 포인터'를 능동 게이트로 승격해 임의 커밋/푸시 직행을 차단한다.
- **세션 격리 추적 훅**(`hooks/git_workflow-track.py`, PostToolUse) = Write/Edit/MultiEdit/NotebookEdit 시 이 세션이 수정한 파일을 `.git/git_workflow/sessions/<session_id>/touched` 에 기록 → reminder 훅이 커밋 시 그 목록을 주입해 **세션별 staging 격리**를 grounding(working tree 공유로 섞인 타 세션 변경 휩쓸기 방지). `.git` 내부 저장이라 비-커밋·자기완결(Claude Code 네이티브 session_id, OMC 비의존).
- **GitHub 정책 강제(선택)** = team 저장소의 branch protection·CODEOWNERS·PR 템플릿(→ §4). CLAUDE.md/README 규칙은 **권고**, GitHub 설정은 사람 실수까지 막는 **강제**.
- **한계(정직)** — 훅은 SOP·세션 파일 목록을 *주입*할 뿐, 커밋된 코드에서 위반을 *재도출·차단*하지 못한다(coding/debt 의 `checks/*.sh` 같은 CI 이빨 없음). 모드 자동 감지·커밋 형식은 자기보고 의존 **advisory**, staging 범위는 track 훅으로 **grounding 하되 최종 staging 은 모델 행동**(하드 차단 아님). track 훅은 Write/Edit 계열만 추적 — Bash(`mv`·codegen 등)로 만든 변경은 누락될 수 있다. python 없는 환경에선 훅 등록도 생략(강제력 0) — 규칙 텍스트만 생존한다.

## 자체 점검

```bash
# 모드 선언 확인 (team 공유 저장소 권장)
grep -E "git 협업 모드: (solo|team)" CLAUDE.md || echo "(모드 미선언 — 자동 감지)"

# 원격별 collaborator 수 (≥2 → team)
for r in $(git remote); do
  url=$(git remote get-url "$r"); slug=$(echo "$url" | sed -E 's#.*github.com[:/]([^/]+/[^/.]+)(\.git)?#\1#')
  echo "$r: $(gh api "repos/$slug/collaborators" --jq 'length' 2>/dev/null || echo '?') collaborators"
done

# 마지막 커밋 메시지 형식
git log -1 --format='%s' | grep -E "^(feat|fix|docs|refactor|style|chore|test)(\([^)]+\))?: "
```

## 변경 절차

- SSOT 는 본 번들 폴더. 규칙 변경은 사용자 승인 후 `git_workflow.md` + (필요 시) `hooks/` + `claude.snippet.md` 를 **단일 번들 VERSION 으로 동반 갱신**(부분 드리프트 금지).
- 트리거 키워드 추가/변경 시 `hooks/git_workflow-reminder.py` 의 `TRIGGERS` 와 `claude.snippet.md` 안내를 함께 맞춘다.

## 검증 (experiments/)

`install.sh` 멱등성·비파괴는 `experiments/SIL/` 에 기록(타깃 프로젝트에서 수행 후 반영). 통합 결과는 상위 `../experiments/INDEX.md` §2 로 집계.

## 파일

`git_workflow.md`(코어 규칙) · `hooks/git_workflow-reminder.py`(UserPromptSubmit 게이트+세션 주입) · `hooks/git_workflow-track.py`(PostToolUse 세션 파일 추적) · `install.sh`(멱등 설치) · `claude.snippet.md`(CLAUDE.md 등록) · `experiments/`(SIL/HIL 검증)
