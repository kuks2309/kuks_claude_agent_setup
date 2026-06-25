# SIL / HIL 검증 계획 (마스터)

> 본 디렉터리는 `kuks_claude_skill_setup` 번들 저장소의 **검증(verification) 계획·기록의 SSOT(Single Source of Truth)**.
> 개별(단위) 검증은 각 번들 안에, 통합 검증은 본 상위 폴더에 기록하며, 모든 결과는 [INDEX.md](INDEX.md) 로 집계한다.
> 명명·기록 규약은 `kuks2309/TR_Nav_ros2_ws` 의 `experiments/` + `src/SIL/` 관례를 따른다.

---

## 1. 목적

이 저장소의 산출물은 로봇 제어 코드가 아니라 **Claude Code 용 번들**(규칙 + 검사 스크립트 + 훅 + install.sh)이다.
따라서 "동작 검증" 의 대상은 **셸/파이썬 코드의 결정성**과 **실제 Claude Code 런타임에서의 활성화·강제력**이다.

SIL(Software-in-the-Loop) / HIL(Hardware-in-the-Loop) 개념을 이 저장소에 충실하게 사상(mapping)하면:

| 개념 | 로봇(원 의미) | 본 저장소에서의 의미 |
|------|---------------|----------------------|
| **SIL** | 제어 코드를 시뮬레이터(가짜 하드웨어) 안에서 실행 | 번들 스크립트를 **격리 샌드박스**(`mktemp` 임시 디렉터리, mock `CLAUDE_HOME`, fixture 코드 표본)에서 실행. **라이브 에이전트 없음**, 100% 결정적·재현 가능. |
| **HIL** | 제어 코드를 **실제 하드웨어**(루프에 물린 장비)와 함께 실행 | 번들을 **실제 Claude Code 런타임**(진짜 `~/.claude`, `settings.json`, 훅 발화, 라이브 세션, 에이전트의 규칙 준수)에 설치해 검증. "하드웨어" = Claude Code 하네스(harness). |

- **SIL = 코드가 스스로 옳은가** (입력→출력·exit code 가 사양과 일치하는가)
- **HIL = 하네스에 물렸을 때 실제로 강제되는가** (훅이 진짜 차단하는가, 규칙이 진짜 활성화되는가)

> **SIL 수행 위치 (중요)**: 본 저장소의 SIL 검증은 번들이 실제로 설치·동작하는 **다른(타깃) 프로젝트에서 수행**하고, 그 결과를 본 저장소(`experiments/SIL/` 및 각 번들 `<bundle>/experiments/SIL/`)에 **반영(기록)**한다.
> 따라서 모든 SIL 검증 기록은 **수행 프로젝트(repo·commit)** 와 **반영 일자** 를 명시한다. (HIL 은 라이브 하네스에서 직접 수행·기록.)

---

## 2. 검증 레벨 (V-모델: 함수 단위 → 단일 프로그램 → 통합)

| 레벨 | 이름 | 대상 | 방법 | 기록 위치 |
|------|------|------|------|-----------|
| **L1** | 함수 단위(function-unit) | 스크립트 내부의 가장 작은 판정 로직 (정규식, 분기, 함수) | fixture 한 줄/한 케이스를 최소 단위에 주입해 판정 비교 | 번들 내부 (`<bundle>/experiments/SIL/`) |
| **L2** | 단일 프로그램(single-program) | 스크립트 한 개를 end-to-end 실행 (`check.sh`, `install.sh`, 훅) | fixture 디렉터리/입력 대상으로 통째 실행 → exit code·출력·부수효과 검증 | 번들 내부 (`<bundle>/experiments/SIL/` · HIL) |
| **L3** | 통합(integration) | 여러 번들이 함께 (전 번들 설치, CI 게이트 일괄, CLAUDE.md 집계, 훅 공존) | 깨끗한 타깃 프로젝트에 다수 번들 설치 후 상호작용·충돌 검증 | **상위** (`experiments/SIL/` · `experiments/HIL/`) |

> **배치 규칙 (사용자 지정)**
> - **SW 단위 검증(L1 + L2)** → 해당 번들 폴더(`<bundle>/experiments/SIL|HIL/`) 에 기록.
> - **통합 검증(L3)** → 상위 폴더(`experiments/SIL|HIL/`) 에 기록.
> - 상위 [INDEX.md](INDEX.md) 가 단위·통합 **모든 결과를 요약·인덱스**한다.

### SIL ↔ HIL ↔ 레벨 매핑

- **L1·L2 는 거의 SIL** — 샌드박스에서 결정적으로 검증 가능 (대부분의 검사·install·훅 로직).
- **HIL 필요** — 훅이 실제 답변을 차단하는지, CLAUDE.md 등록이 실제 스킬을 활성화하는지, settings.json 병합이 라이브 세션에 반영되는지 등 **하네스가 있어야만 드러나는 행위**.
- **L3 는 SIL(설치·게이트 일괄 실행) + HIL(실 프로젝트·실 세션) 양쪽**으로 나뉜다.

---

## 3. 폴더·명명 규약

상위와 각 번들이 **동일한 구조**를 미러링한다.

```
experiments/                         ← 상위 (L3 통합 + 전체 인덱스)
├── README.md                        ← 본 문서 (마스터 계획)
├── INDEX.md                         ← 단위+통합 전체 결과 요약·인덱스
├── SIL/
│   ├── _template/README.md          ← 통합 SIL 실행 템플릿 (복사 원본)
│   └── YYYY-MM-DD_<topic>/          ← 실제 통합 SIL 검증 (실행 시 생성)
└── HIL/
    ├── _template/README.md          ← 통합 HIL 실행 템플릿
    └── YYYY-MM-DD_<topic>/

<bundle>/experiments/                ← 각 번들 (L1·L2 단위)
├── README.md                        ← 번들 검증 미니 가이드 (자기완결)
├── SIL/
│   ├── _template/README.md          ← 단위 SIL 템플릿
│   └── YYYY-MM-DD_<topic>/
└── HIL/
    ├── _template/README.md
    └── YYYY-MM-DD_<topic>/
```

**규칙**
1. **날짜별 폴더**: `YYYY-MM-DD_<topic>/` (예: `2026-06-22_debt-marker_unit/`). 한 검증 = 한 폴더.
2. **주제별 파일명**: 폴더 안 파일은 주제로 명명 (`README.md` 필수 + 필요 시 `scripts/`, `results/`, `logs/`).
   - `README.md`: 목적 · 검증 대상 · 실행 절차 · 결과 표(측정값 vs 기대값 + ✅/✗ 판정) · 분석.
3. **검증 실행 시**: `_template/` 를 `YYYY-MM-DD_<topic>/` 로 **복사**한 뒤 결과를 채운다 (TR_Nav 의 `*_template/` 관례와 동일).
4. **자기완결**: 각 번들의 `experiments/` 는 상위 문서 없이도 읽히도록 작성 (번들 self-contained 원칙).
5. **인덱스 갱신**: 검증 1건 완료 시 상위 [INDEX.md](INDEX.md) 에 한 줄 추가 (§5).

---

## 4. 번들별 검증 매트릭스

코드 보유 정도에 따라 3개 "코드 번들"(검사·훅 보유) 과 6개 "설치 번들"(install.sh 만) 로 나뉜다.
모든 번들의 install.sh 는 멱등(idempotent) 설치 프로그램이므로 **L2 단일 프로그램 검증 대상**이다.

### 4.1 코드 번들

| 번들 | L1 함수 단위 | L2 단일 프로그램 | L3 / HIL |
|------|--------------|------------------|----------|
| **acronym** | `acronym-check.py::find_violations()` — 병기 도입 인식·whitelist·코드/URL 제거·2~6자 약자·7자+ 제외; `last_assistant_text()` JSONL 파싱 | `acronym-check.py` stdin JSON → exit 0/2 (fixture transcript), `stop_hook_active` 루프방지; `install.sh` mock `CLAUDE_HOME` 멱등·settings.json merge·`--reminder-only` | **HIL**: 실 `~/.claude` 설치 후 Stop 훅이 미병기 약자 답변을 실제 차단, UserPromptSubmit 리마인더 주입 |
| **coding** | 8개 check 의 grep/sed 판정 로직 (adr-fields 필드 5종 · banned-pattern 금지패턴 · check-mapping 태그↔스크립트 1:1 · dup-signature Python/C++ 중복 · format formatter 선택 · index-fresh · memory graceful skip · tests-ran TEST_CMD/pytest) | 각 `checks/*.sh <fixture>` → exit 0/1 + 출력; `install.sh <sandbox>` 코어/도메인 복사·`.gitignore` `.omc/`·CLAUDE.md marker 멱등 | **HIL**: 실 프로젝트 pre-commit / CI 게이트(`ci/coding-gates.yml`)에서 검사 발화·차단 |
| **debt** | `check-mapping.sh` 정합; `debt-marker.sh` — `TODO(debt-42)` OK vs 맨 `TODO` 차단 정규식 | 각 `checks/*.sh <fixture>` → exit code; `install.sh <sandbox>` + registry template 배치 | **HIL**: 실 프로젝트에서 미등록 마커 차단 |

### 4.2 설치 번들 (install.sh = L2 단일 프로그램)

공통 L2: `install.sh <sandbox>` → `docs/claude_guideline/<bundle>/` 복사 · CLAUDE.md `kuks_agent_setup:<bundle>` marker 멱등(재실행 시 중복 없음) · 비파괴.
공통 HIL: 활성화 게이트(규칙 파일 존재)로 스킬 활성 · 기록 경로 SSOT 준수.

| 번들 | 설치 대상 / 게이트 | L1·L2 특이사항 | HIL 특이사항 |
|------|-------------------|----------------|--------------|
| **code_review** | `docs/claude_guideline/code_review/` (+ domains) | 도메인 선택 복사 | 리뷰 결과 → `docs/code_review/<subject>/YYYY-MM-DD.md` 경로 준수, never-self-approve |
| **external_reference** | `docs/claude_guideline/external_reference/` (+ coding_standards.md) | `coding_standards.md` grep 태그 정합 | PDF fingerprint·인용 규칙 활성 |
| **git_workflow** | `docs/claude_guideline/git_workflow/` | 단일 파일 복사 | solo/team 모드 자동 감지 동작 |
| **issue_fix** | `docs/claude_guideline/issue_fix/` | **런타임 생성**: 첫 기록 시 `docs/issues_and_fixes/issues_and_fixes.md` (경로 변형 금지) | 이슈 기록 prepend·5필드 |
| **user_instruction** | `docs/claude_guideline/user_instruction/` | **런타임 생성**: 첫 기록 시 `docs/user_instructions/user_instructions.md` | 원문 verbatim·민감정보 마스킹 |
| **sw_structure** | `docs/claude_guideline/sw_structure/` | 단일 파일 복사 | 구조 분석 → `docs/sw_structure/<subject>/YYYY-MM-DD.md` 경로 준수 |

### 4.3 통합(L3) 시나리오 — 상위 `experiments/` 에 기록

- **INT-1 전 번들 설치**: 깨끗한 `mktemp` 프로젝트에 9개 install.sh 순차 실행 → 경로 충돌 0, CLAUDE.md 9개 marker 1회씩, `.gitignore` `.omc/` 1회.
- **INT-2 멱등 재설치**: 전 번들 2회째 실행 → 신규 변경 0 (전부 "스킵").
- **INT-3 CI 게이트 일괄**: 설치된 프로젝트에서 coding 8 check + debt 2 check 순차 → fixture 위반에 정확히 차단.
- **INT-4 훅 공존(HIL)**: acronym 훅 + 타 훅이 settings.json 에서 충돌 없이 공존, 실 세션 발화.
- **INT-5 CLAUDE.md 집계**: 다수 번들 등록 후 마커 중복·순서·렌더링 정상.

---

## 5. INDEX(인덱스) 갱신 프로토콜

검증 1건이 끝나면 상위 [INDEX.md](INDEX.md) 표에 한 줄을 추가한다 (단위·통합 공통).

| 열 | 의미 |
|----|------|
| 날짜 | `YYYY-MM-DD` |
| 레벨 | L1 / L2 / L3 |
| 모드 | SIL / HIL |
| 번들 | 대상 번들 (통합은 `*`) |
| 주제 | `<topic>` |
| 결과 | ✅ PASS / ✗ FAIL / ◐ 부분 |
| 경로 | 해당 `YYYY-MM-DD_<topic>/README.md` 상대 링크 |

> 개별 검증의 상세는 각 폴더 `README.md` 에 두고, INDEX 는 **요약 + 링크**만 유지한다 (SSOT 중복 금지).

---

## 6. 워크플로 (한 건 검증하는 법)

1. 레벨·모드 결정 (L1/L2 단위는 번들, L3 통합은 상위).
2. 해당 `SIL|HIL/_template/` 를 `YYYY-MM-DD_<topic>/` 로 복사.
3. `README.md` 의 목적·검증 대상·절차 작성 → 실행 → 결과 표(측정값 vs 기대값 + 판정) 채움.
4. 산출물(`scripts/`, `results/`, `logs/`) 보관.
5. 상위 [INDEX.md](INDEX.md) 에 한 줄 추가.
6. (선택) 실패 시 issue_fix 규칙으로 `docs/issues_and_fixes/` 기록.

---

## 7. 참조

- 명명·기록 관례: `kuks2309/TR_Nav_ros2_ws` → `experiments/` (날짜_주제_sil|hil|real + README 결과표), `src/SIL/` (SIL 시뮬레이션 코드 배치).
- 본 저장소 번들 규칙: 각 번들의 코어 `.md` (예: `coding/coding.md`, `debt/debt.md`).
