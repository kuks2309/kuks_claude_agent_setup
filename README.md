# kuks_claude_agent_setup

Claude Code 자산(규칙·훅) 설치 저장소. 각 자산은 **폴더별 자기완결 번들**이며, 폴더 안의 `install.sh` 로 **따로** 설치한다 (루트 중앙 스크립트 없음).

## 자산 목록

| 번들 | 용도 | 설치 대상 | 설치 명령 |
| --- | --- | --- | --- |
| [user_instruction/](user_instruction/recording.md) | 사용자 지시 원문 기록 (의도 부채 방지) | 프로젝트별 | `cd user_instruction && ./install.sh <타깃-프로젝트-루트>` |
| [external_reference/](external_reference/handling.md) | 외부 참조 문서(매뉴얼·datasheet·SDK·표준) 보관·인용·검증 | 프로젝트별 | `cd external_reference && ./install.sh <타깃> [도메인...]` |
| [code_review/](code_review/review.md) | "코드 리뷰" 인벤토리(목적·함수·전역·의존성) + severity 평가 | 프로젝트별 | `cd code_review && ./install.sh <타깃> [도메인...]` |
| [git_workflow/](git_workflow/git_workflow.md) | git commit/push·협업(solo/team, 다중 원격, PR 리뷰 게이트) 규칙 | 프로젝트별 | `cd git_workflow && ./install.sh <타깃>` |
| [acronym/](acronym/acronym.md) | 영어 약자 `약어(영어 단어)` 병기 + 자동 적용 훅 | 전역 (`~/.claude`) | `cd acronym && ./install.sh [--reminder-only]` |

## 설치 방식

각 번들은 자기 폴더의 `install.sh` 로 설치한다.

- **user_instruction** — 타깃 프로젝트 인자를 받아 규칙(`recording.md`)을 `docs/claude_guideline/user_instruction/` 로 복사 + 타깃 `CLAUDE.md` 에 등록 줄 append.
- **external_reference** — 코어(`handling.md`) + 선택 도메인(`domains/`)을 `docs/claude_guideline/external_reference/` 로 복사 + `CLAUDE.md` 등록. 참조 자료(PDF)는 프로젝트 루트 `references/` 에 별도 보관(docs 와 분리).
- **code_review** — 코어(`review.md`) + 선택 도메인(`domains/{ros2-review,concurrency,embedded-review}`)을 `docs/claude_guideline/code_review/` 로 복사 + `CLAUDE.md` 등록. 리뷰 산출물은 `docs/code_review/<주제>/YYYY-MM-DD.md`(날짜=버전).
- **git_workflow** — `git_workflow.md` 를 `docs/claude_guideline/git_workflow/` 로 복사 + `CLAUDE.md` 등록. solo/team 모드 명시·자동 판정, team 은 `main` 직접 push 금지(브랜치+PR+리뷰 승인).
- **acronym** — `~/.claude` 에 규칙·훅 복사 + `CLAUDE.md` 등록 + `settings.json` 훅 등록. `--reminder-only` 면 리마인더(`UserPromptSubmit`)만, 생략하면 검증(`Stop`)까지 등록.

설치는 기존 `CLAUDE.md`·`settings.json` 을 **덮어쓰지 않고 append/merge** 하며, 중복은 마커로 스킵하고 `settings.json` 은 사전 백업한다.

## 구조 규약

- 자산 = 폴더별 자기완결 번들. 한 폴더에 **규칙 + `claude.snippet.md`(CLAUDE.md 등록 포인터) + `install.sh`**.
- 규칙은 단순하게 유지하고, 분석·검증은 별도로 분리한다.
- `claude.snippet.md` 은 통파일 설치가 아니라 타깃 `CLAUDE.md` 에 붙는 등록 포인터다.

## git 워크플로 (기여 정책)

- **커밋**: `type(scope): subject` (feat·fix·docs·refactor·style·chore·test) + `Co-Authored-By` 푸터. 작업 단위별 1 커밋, 명시 staging(`git add <경로>`, `-A`/`.` 금지).
- **모드 판정**: GitHub collaborator 수로 — **solo**(`main` 직접 push) vs **team**(브랜치 → PR → 리뷰 ≥1 승인 → merge, 작성자 self-approve 금지).
- **본 저장소 원격**: `origin`(kuks2309, collaborator 1) = solo · `fito`(FitoControl, 13) = team 이나 `kuks2309` 운영 **단방향 미러**라 `main` 직접 push 예외. 푸시는 양쪽 모두.
- **team 모드**: `main` 직접 push 금지. 충돌은 로컬 rebase, 공유 브랜치 force-push 금지.
- **GitHub 강제(선택)**: team 저장소는 branch protection + `CODEOWNERS` 로 `main` 직접 push 차단(관리자 미러는 bypass 허용).
- 전체 규칙: [git_workflow/git_workflow.md](git_workflow/git_workflow.md).
