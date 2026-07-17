# 2026-07-17 — 세션: computer_use 원격 업그레이드 로컬 적용 + 윈도우 검증분 동기

세션 기간: 2026-07-12 오후 ~ 2026-07-17 오전 KST(Korea Standard Time). 대상 자산: `computer_use/` 번들 (repo `kuks_claude_skill_setup`, remote origin + fito). 이 세션은 **커밋 생산 없음** — 원격 변경의 pull·검증·전역 설치본(`~/.claude`) 배포만 수행 (본 worklog 커밋 제외).

## 개요

원격에 올라온 computer_use 업그레이드(Windows·다중 모니터 지원)를 이 Linux PC 에 2단계로 적용했다. ① 7/12: 실행기 2종 업그레이드(`ad81821`) pull + `~/.claude` 배포 + 스모크 테스트. ② 7/17: 윈도우 컴 실기 검증 후 push 된 SKILL 문서 갱신(`4973d98`) 반영. 이 과정에서 로컬 커밋과 원격 커밋이 **같은 패치·다른 해시**로 중복되어 발산(ahead 1/behind 2)한 것을 patch-id 검증 후 rebase 로 무손실 해소했다.

## 단계별 결과

### 1단계 — 실행기 업그레이드 적용 (7/12)

- 원격 신규 커밋 `ad81821` feat(computer_use): Windows·다중 모니터 지원 보완 — `capture_screen.py`(+205: Windows 창 목록/캡처, `--mode monitors` 신규, 보조 모니터 검정화면 수정, UTF-8 stdout), `computer_action.py`(+31: per-monitor DPI(Dots Per Inch) 인식).
- 로컬 main 을 fast-forward (`7bd98f0`→`ad81821`). 타 세션 미커밋 파일(README.md 등)과 충돌 없음 확인 후 진행.
- **드리프트 검사**: `~/.claude/` 설치본 2파일이 구버전(`7bd98f0`)과 바이트 동일 확인 → 신버전 복사(실행 권한 유지).
- 검증: `py_compile` 통과, `--mode monitors` 정상(단일 모니터 1920×1080 검출), `--mode list` 창 목록 회귀 없음, `computer_action.py --help` 정상.

### 2단계 — 윈도우 검증분 확인 + 발산 해소 (7/17)

- 원격 신규 커밋 2개: `4973d98` docs(computer_use) SKILL 문서 Windows·다중 모니터 반영, `52125a9` feat(git_workflow) pre-push gate.
- **중복 커밋 발산**: `52125a9` 는 이 컴 타 세션의 로컬 커밋 `deae06b`(7/12 13:34) 와 patch-id 동일·tree diff 0 — 같은 변경이 다른 해시로 원격에 올라가 로컬이 ahead 1/behind 2 로 발산.
- 해소: `git rebase --autostash origin/main` — git 이 중복 커밋 자동 스킵(skipped previously applied), 타 세션 미커밋 README.md 는 autostash 로 보존. 결과: 로컬 main = origin/main = fito/main = `52125a9`, push 불필요.
- SKILL 문서 배포: 드리프트 검사(설치본 = `ad81821` 판 동일) 후 `computer-use`/`capture-test` SKILL.md 를 `~/.claude/skills/` 에 복사. 실행기 2종은 변경 없음(1단계 배포본이 최신).

## 산출물

- 커밋 없음(worklog 제외). 배포만: `~/.claude/capture_screen.py`, `~/.claude/computer_action.py`, `~/.claude/skills/{computer-use,capture-test}/SKILL.md` = repo `52125a9` 판과 동일.

## 다음 세션 주의

- **같은 패치·다른 해시 발산 패턴**: 공유 자산을 두 컴에서 각각 커밋하면 remote 발산이 일어난다. 해소 절차 = ① `git patch-id --stable` 로 내용 동일성 검증 ② 동일하면 `git rebase --autostash <remote>/main` (중복 자동 스킵, 미커밋분 보존). 내용이 다르면 rebase 전 수동 대조 필요.
- **`~/.claude` 배포 절차(재사용)**: fetch → ff/rebase → 설치본 vs 구버전 드리프트 검사 → 변경 파일만 복사 → 스모크 테스트(`py_compile`, `--mode monitors`, `--mode list`).
- 이 PC 는 Linux/X11 단일 모니터 — Windows·DPI 경로는 잠재 상태, Linux 경로만 실검증됨. Windows 실기 검증은 7/17 윈도우 컴에서 완료(사용자).
