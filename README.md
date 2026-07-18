# kuks_claude_agent_setup

Claude Code 자산(규칙·훅) 설치 저장소. 각 자산은 **폴더별 자기완결 번들**이며, 폴더 안의 `install.sh` 로 **따로** 설치한다 (루트 중앙 스크립트 없음).

**git 협업 모드: solo** — origin(kuks2309 개인) `main` 직접 commit/push, PR 미사용. 다른 사람은 코워커(collaborator)로 등록되어 있어도 **참조(열람) 전용** — commit·PR 기여를 받지 않는다. `fito`(FitoControl) 는 관리자 단방향 미러 → `git push origin main && git push fito main` 으로 동기화([git_workflow](git_workflow/git_workflow.md) §0 미러 예외). 공동 작업 전환 시 본 줄을 `team` 으로 갱신한다.

## 자산 목록

| 번들 | 용도 | 설치 대상 | 설치 명령 |
| --- | --- | --- | --- |
| [user_instruction/](user_instruction/recording.md) | 사용자 지시 원문 기록 (의도 부채 방지) | 프로젝트별 | `cd user_instruction && ./install.sh <타깃-프로젝트-루트>` |
| [external_reference/](external_reference/handling.md) | 외부 참조 문서(매뉴얼·datasheet·SDK·표준) 보관·인용·검증 | 프로젝트별 | `cd external_reference && ./install.sh <타깃> [도메인...]` |
| [code_review/](code_review/review.md) | "코드 리뷰" 인벤토리(목적·함수·전역·의존성) + severity 평가 | 프로젝트별 | `cd code_review && ./install.sh <타깃> [도메인...]` |
| [sw_structure/](sw_structure/structure.md) | "SW 구조" 파일·클래스 연결 시각화(파일그래프+클래스+시퀀스+연결표) | 프로젝트별 | `cd sw_structure && ./install.sh <타깃>` |
| [coding/](coding/coding.md) | 코드 작성 SOP(조사→ADR→구현→검증→이중기록) + 이빨 8개(`⟦CI⟧` pre-commit·CI 강제) | 프로젝트별 | `cd coding && ./install.sh <타깃> [도메인...\|--all]` |
| [debt/](debt/debt.md) | 기술·이해·의도 3-부채 등록·추적 registry (`TODO`↔debt id 강제) | 프로젝트별 | `cd debt && ./install.sh <타깃>` |
| [issue_fix/](issue_fix/issue_fix.md) | 버그 수정·이슈 해결·빌드 실패 진단→제안→구현→검증→기록 사이클 | 프로젝트별 | `cd issue_fix && ./install.sh <타깃-프로젝트-루트>` |
| [mistake/](mistake/mistake.md) | Claude 실수·규칙위반 2-type 기록(rule-violation 우선 판정) + closure(`reflected_assets`) 강제 | 프로젝트별 | `cd mistake && ./install.sh <타깃>` |
| [git_workflow/](git_workflow/git_workflow.md) | git commit/push·협업(solo/team, 다중 원격, PR 리뷰 게이트) 규칙 | 프로젝트별 | `cd git_workflow && ./install.sh <타깃>` |
| [reverse_engineering/](reverse_engineering/principle.md) | RE 제1원칙(재구현 출력 원본 100% 동일·원본입력 양쪽구동 비트대조) + 분석 보고 원칙(존재 vs 동작 분리) | 프로젝트별 | `cd reverse_engineering && ./install.sh <타깃>` |
| [acronym/](acronym/acronym.md) | 영어 약자 `약어(영어 단어)` 병기 + 자동 적용 훅 | 전역 (`~/.claude`) | `cd acronym && ./install.sh [--reminder-only]` |
| [computer_use/](computer_use/computer_use.md) | PC 화면 읽기·분석·조작(read→analyze→act→re-read) — capture(읽기)+action(쓰기) 스킬·에이전트, 입력 후 피드백 안전 | 전역 (`~/.claude`) | `cd computer_use && ./install.sh` |

## 설치 방식

각 번들은 자기 폴더의 `install.sh` 로 설치한다.

- **user_instruction** — 타깃 프로젝트 인자를 받아 규칙(`recording.md`)을 `docs/claude_guideline/user_instruction/` 로 복사 + 타깃 `CLAUDE.md` 에 등록 줄 append.
- **external_reference** — 코어(`handling.md`) + 선택 도메인(`domains/`)을 `docs/claude_guideline/external_reference/` 로 복사 + `CLAUDE.md` 등록. 참조 자료(PDF)는 프로젝트 루트 `references/` 에 별도 보관(docs 와 분리).
- **code_review** — 코어(`review.md`) + 선택 도메인(`domains/{ros2-review,concurrency,embedded-review}`)을 `docs/claude_guideline/code_review/` 로 복사 + `CLAUDE.md` 등록. 리뷰 산출물은 `docs/code_review/<주제>/YYYY-MM-DD.md`(날짜=버전).
- **sw_structure** — 코어(`structure.md`)를 `docs/claude_guideline/sw_structure/` 로 복사 + `CLAUDE.md` 등록. 파일 의존 그래프 + 클래스 다이어그램 + 시퀀스 다이어그램 + 연결 관계표 + 구조 관찰(순환·고립). 결함·품질 평가는 `code_review` 소관(본 번들은 연결 시각화만). 산출물 `docs/sw_structure/<주제>/YYYY-MM-DD.md`(날짜=버전).
- **coding** — 코어(`coding.md`·`conventions.md`·`stack.md`) + 선택 도메인(`domains/{ros2-coding,embedded-coding,numeric-coding,concurrency-coding,memory-coding}`) + 이빨(`checks/*.sh`)을 `docs/claude_guideline/coding/` 로 복사 + `CLAUDE.md` 등록 + `.gitignore` 에 `.omc/` 추가. 강제는 `⟦CI:<id>⟧`↔`checks/<id>.sh`(pre-commit·CI), 그 외 `⟦권고⟧`. 코드 양식(함수표·전역변수표) 권위는 `code_review`.
- **debt** — `debt.md` + 이빨(`checks/*.sh`)을 `docs/claude_guideline/debt/` 로 복사 + registry 템플릿을 `docs/debt/registry.md` 로(기존 보존) + `CLAUDE.md` 등록. 코드 `TODO`/`FIXME`/`HACK` 은 debt id 참조(맨 마커 차단). coding 이 식별, debt 가 등록 권위.
- **issue_fix** — `issue_fix.md` 를 `docs/claude_guideline/issue_fix/` 로 복사 + `CLAUDE.md` 등록. 진단→제안(승인)→구현→검증→기록 사이클. 기록은 `docs/issues_and_fixes/issues_and_fixes.md`(첫 기록 시 런타임 생성, 승인 불요), SSOT 정규 식별자 강제(변종 `issues_fixes/`·`requirements.md` 금지).
- **mistake** — 코어(`mistake.md`) + 훅(`hooks/mistake-inject.py`, SessionStart 에 INDEX 요약·open entry 주입) + 이빨(`checks/entry-lint.sh`)을 `docs/claude_guideline/mistake/` 로 복사 + entry 폴더 `docs/claude-mistake/` 생성(비파괴) + `CLAUDE.md` 등록. 사건 entry 는 `docs/claude-mistake/YYYY-MM-DD-NNN.md`(1사건 1파일, `type: mistake|rule-violation` 2-type, 카테고리 10종, rule-violation 우선 판정). closure 는 `reflected_assets` 1+ · TBD 금지 · open 7일 시한, 형식 위반은 entry-lint 가 검출(pre-commit·CI 연결 가능).
- **git_workflow** — `git_workflow.md` 를 `docs/claude_guideline/git_workflow/` 로 복사 + `CLAUDE.md` 등록. solo/team 모드 명시·자동 판정, team 은 `main` 직접 push 금지(브랜치+PR+리뷰 승인).
- **reverse_engineering** — `principle.md` 를 `docs/claude_guideline/reverse_engineering/` 로 복사 + `CLAUDE.md` 등록. RE 제1원칙(재구현 출력 = 원본 100% 동일, 원본 입력으로 원본·재구현 양쪽 구동 후 비트 대조 ≤1e-9; 우리 코드로 입력 생성 금지·정역 양방향) + §6 분석 보고 원칙(`[존재]`(nm/disasm) vs `[동작]`(호출 도달성+배포자산 `.smap`/`robot.model`/`rbk.plugin` 대조) 라벨 분리, 동작 주장은 대조 전 "확정" 금지, 죽은 코드 체크). 추정·환각 금지.
- **acronym** — `~/.claude` 에 규칙·훅 복사 + `CLAUDE.md` 등록 + `settings.json` 훅 등록. `--reminder-only` 면 리마인더(`UserPromptSubmit`)만, 생략하면 검증(`Stop`)까지 등록.
- **computer_use** — `~/.claude` 에 `capture_screen.py`·`computer_action.py` + skills(`capture-test`·`computer-use`) + agent(`computer-operator`) 복사 + `CLAUDE.md` 등록(marker 멱등). 전역 설치라 모든 프로젝트에서 동작. 훅 없음(사용자 호출형 도구). `--check`(preflight)·`--no-deps`(격리 테스트) 지원. 실입력 실행기 Linux=xdotool/Windows=pyautogui, Wayland 미지원. 검증은 `experiments/SIL`(pytest, 마우스 미동작)·`HIL`(실기).

설치는 기존 `CLAUDE.md`·`settings.json` 을 **덮어쓰지 않고 append/merge** 하며, 중복은 마커로 스킵하고 `settings.json` 은 사전 백업한다.

## 업데이트 (설치본 갱신)

설치본 갱신 = **install.sh 재실행**. 전 번들 멱등이라 재실행이 안전하다(규칙·훅 파일은 덮어쓰기, `CLAUDE.md`·`settings.json` 은 마커/멱등 등록으로 중복 방지).

1. 번들 저장소 최신화: `git pull`
2. 낡음 점검: 각 설치 타깃에 대해 `cd <번들> && ./install.sh <타깃> --status` (전역 번들은 `./install.sh --status`)
   - 판정 3종: **최신**(exit 0) / **재설치 권장**(exit 1, 기록 커밋 이후 변경 파일 목록 출력) / **기록 없음**(exit 2, 구판 설치 — 재설치하면 기록 생성)
3. 재설치 권장이면 기록된 인자 그대로 재실행: 인자는 타깃의 `docs/claude_guideline/INSTALLED.md` (전역 번들은 `~/.claude/INSTALLED.md`) 의 **인자** 열 참조
4. 다른 PC(윈도우 포함)도 같은 절차 — `git pull` → `--status` → 재설치

동작 원리: 각 `install.sh` 가 설치 성공 시 `INSTALLED.md` 에 자기 행(번들·설치 커밋·날짜·인자)을 기록하고, `--status` 는 그 기록과 저장소 HEAD·설치본 파일 내용을 대조해 판정한다. 로컬에서 설치본을 직접 수정한 경우(드리프트)도 `설치본 ≠ 저장소` 로 검출된다.

주의: `claude.snippet.md` 가 변경된 번들은 재설치해도 마커 중복방지 때문에 `CLAUDE.md` 등록 블록이 갱신되지 않는다 — `--status` 가 이 경우를 경고하며, 타깃 `CLAUDE.md` 의 기존 등록 블록을 수동으로 교체한다.

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
