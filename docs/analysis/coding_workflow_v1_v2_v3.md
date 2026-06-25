# 코딩 workflow(개발 라이프사이클 SOP) 분석 — v1 / v2 / v3

> **본 문서**: v3 저장소(`kuks_claude_skill_setup`, origin=`kuks_claude_agent_setup`) 배포본.
> 워크스페이스 기록 원본은 루트 `claude_code/docs/analysis/coding_workflow_v1_v2_v3.md`.
> 워크스페이스 전용 파일(CLAUDE.md, HANDOFF, claude_guideline/) 참조는 v3 저장소에 없으므로 텍스트로 표기.

- **분석 도구**: 병렬 Explore 에이전트 3명 (v1/v2/v3 각 1명)
- **대상**: `/home/amap/Project/claude_code/` 하위 3개 서브 프로젝트
- **SOP**(Standard Operating Procedure / 표준 운영 절차)

---

## 0. 3개 서브 프로젝트와 프로젝트 목적

| 트랙 | 폴더 | 역할 | git / remote |
|---|---|---|---|
| **v1** | kuks_claude_setup | 레거시 배포판 (git sync 대상) | origin = `kuks2309/kuks_claude_setup` |
| **v2** | kuks_claude_setup_new | SSOT(Single Source of Truth) 작성·검증 워크스페이스 | **비-git** |
| **v3** | kuks_claude_skill_setup | **이식 최종 목적지** (자기완결 번들) | origin=`kuks2309/kuks_claude_agent_setup` + fito=`FitoControl/FITO_claude_skill_install` |

**프로젝트 목적**: v1/v2 는 SSOT 정제 트랙, **v3 번들 이식이 종착점**. v1/v2 작성·sync 만으로는 작업 종료가 아니다 — v3 이식 또는 명시적 이식 follow-up 동반 의무 (워크스페이스 `claude_guideline/v3_porting_sop.md` 규정).

즉 **"v1+v2 를 문제점 보완해 v3 로 이식"** = v3 porting SOP 의 핵심 모토.

---

## 1. 공통 골격 (코딩 작업 과정)

```
지시 입력 → 요구사항 분석 → [기존 프로젝트] 코드리뷰·매뉴얼·이력 분석
         → 코드 작성 → 검증 → 기록 → 커밋/푸시
```

세 프로젝트 모두 이 흐름을 규정하지만, **어디까지 "명시적 의무"이고 어디까지 "기계 강제"인지**가 다르다. 본질은 v1부터 동일하며, v3 로 갈수록 두 축으로 진화한다:
1. **암시적 단계 → 명시화** (코드리뷰·매뉴얼·이력 분석이 독립 SOP/번들로 분리)
2. **텍스트 권고 → 기계 강제** (CI(Continuous Integration) checks 로 우회 불가)

---

## 2. v1 (kuks_claude_setup) — 9단계 선형 SOP

척추: `user_instruction_handling_sop.md` 의 9단계.

| 순서 | 단계 | 규정 파일 | 사용자 예시 매핑 |
|---|---|---|---|
| 1–2 | 지시 명확화 + 원문 기록 | user_instruction_handling_sop §2–3 | **지시 입력** ✅ |
| 3–4 | 기존 자료 5종 검색 + 적용 SSOT 룰 식별 | §4–5 | **요구 분석** ✅ |
| (3 내부) | 5종 = docs/분석·.omc/research·manual/·guideline·memory | §4 | **코드리뷰·매뉴얼·이력** ⚠️ *암시적* |
| 5 | 사전 승인 판단 (코드수정·push STOP) | §6 + coding.md | (승인 게이트) |
| 6 | 실행 (TodoWrite) + coding/tech_debt/iteration/manual 규칙 | §7 | **코드 작성** ✅ |
| 7 | 사후 검증 체크리스트 9항목 | workflow.md §종료 전 | **검증** ✅ |
| 8–9 | worklog 기록 + 1–2줄 보고 | §9–10 | **기록** ✅ |

**약점**: 코드리뷰·매뉴얼리뷰·과거이력이 "기존 자료 5종 검색"에 **암시적으로 뭉뚱그려짐**. 별도 SOP·산출물·트리거 없음. 강제 메커니즘(CI/훅) 없음.

---

## 3. v2 (kuks_claude_setup_new) — 23단계 + 강제 게이트 2개

v1 의 암시적 단계를 **독립 SOP로 분리**하고 게이트를 추가한 과도기. 핵심: `coding/README.md` 의 12단계 워크플로.

**v1 대비 새로 명시된 단계** (= 분석 단계들이 정식 단계로 승격):

| 새 단계 | 독립 SOP | 산출물 |
|---|---|---|
| **코드리뷰** (목적·함수표·전역·의존성 인벤토리) | code_review.md | docs/code_review/ |
| **매뉴얼/외부참조** (1차 source 검증, ✓/ⓦ/⚠ 등급) | external_reference_handling.md | docs/references/ |
| **SW 구조 분석** (파일그래프·클래스·시퀀스) | sw_structure.md | docs/sw_structure/ |
| **부채 등록** (기술·이해·의도 3종) | debt/ | docs/debt/ |
| **원격 동기** (모든 remote push) | remote_push_policy.md | git push |

**강제 게이트 2개** (미통과 시 진행 차단):
- `§1.3 함수 중복 검사` — 코드 작성 **전** 3단계 모듈 검색 안 하면 차단
- `§7 종료 체크리스트` — A(기술)/B(이해)/C(의도)/D(위반) 4부문, 거짓 ✅ 금지

**약점**: flat `.md` 와 폴더 번들 혼재로 "어느 파일 읽나" 불명확. 게이트가 여전히 **텍스트 규칙**(기계 강제 아님). 도메인 감지 시점 모호.

---

## 4. v3 (kuks_claude_skill_setup) — 5단계 + 3계층 강제

분석 단계들이 **번들 + 기계 강제(CI)** 로 굳은 최종 형태. 핵심 차별점: **강제 수준의 3계층화**.

**라이프사이클 ↔ 번들 매핑**:

| 순서 | 단계 | 담당 번들 | 강제 수준 |
|---|---|---|---|
| 0 | 약자 병기 (공통) | acronym | **⟦Hook⟧** (Stop 훅 차단) |
| 1 | 지시 원문 기록 | user_instruction | ⟦응답 전 의무⟧ |
| 2* | **[기존]** 코드리뷰 + 매뉴얼 + 구조 | code_review · external_reference · sw_structure | ⟦응답 전 의무⟧ |
| 3 | 코드 작성 | coding | ⟦의무⟧ + **⟦CI⟧** + ⟦권고⟧ |
| 3-1 | 부채 등록 | debt | **⟦CI:debt-marker⟧** |
| 4* | **[버그 시]** 이슈 수정 사이클 | issue_fix | ⟦응답 전 의무⟧ |
| 5 | 커밋·푸시 (solo/team 자동판정) | git_workflow | ⟦의무⟧ |

**강제 3계층** (v3 의 핵심 발명):
- **⟦CI:<id>⟧ 기계 강제** — `checks/*.sh` 가 코드에서 결정론적 재도출, pre-commit/CI 차단. 에이전트 자기보고로 **우회 불가**. (coding 8개 + debt 1개)
- **⟦응답 전 의무⟧** — 응답 시작 전 BLOCKING (claude.snippet.md 명시)
- **⟦권고⟧** — 자동검사 불가, 정직성 의존

**현황**: 아키텍처 완성, `experiments/` SIL(Software-in-the-Loop)/HIL(Hardware-in-the-Loop) 검증은 대부분 ⏳ 계획됨.

---

## 5. 같은 단계의 진화 (핵심 비교)

| 단계 | v1 | v2 | v3 |
|---|---|---|---|
| **지시 입력** | §2–3 텍스트 기록 | user_instruction_recording | user_instruction 번들 ⟦의무⟧ |
| **요구 분석** | "5종 검색"에 뭉뚱 | 범위 명확 + 14트리거 | 입구 분류(trivial/Full) |
| **코드리뷰** *(기존)* | ⚠️ 암시적 | code_review.md SOP | code_review 번들 ⟦의무⟧ |
| **매뉴얼 리뷰** *(기존)* | ⚠️ manual.md 수동 | external_reference + 검증등급 | external_reference 번들 ⟦의무⟧ |
| **과거이력 분석** *(기존)* | ⚠️ "동일영역 실수" 모호 | code_review 에 포함 | issue_fix 과거검색 + sw_structure |
| **코드 작성** | coding.md 텍스트 | 12단계 + 게이트(텍스트) | coding + **⟦CI⟧ 8 checks** |
| **검증** | 체크리스트 9항목(수동) | 종료 체크리스트(텍스트 게이트) | **⟦CI⟧ 기계 재도출** + never-self-approve |
| **기록** | worklog(수동) | 인덱스 CI 권장 | 함수표·ADR·registry **⟦CI:index-fresh⟧** |
| **커밋/푸시** | github.md | remote_push_policy | git_workflow solo/team 자동판정 |

**한 문장 요약**:
> **v1** = 코딩 절차를 *읽고 따르는* 9단계 텍스트 SOP (분석 단계 암시적)
> → **v2** = 분석 단계를 *독립 SOP로 분리* + 텍스트 게이트 2개 (23단계)
> → **v3** = 같은 절차를 *번들 + 기계 강제(CI)* 로 굳혀 **우회 불가능**하게 만든 형태

---

## 6. commit/push 위치 정책

| 트랙 | 폴더 | git / remote | commit·push 규칙 |
|---|---|---|---|
| **v2** | kuks_claude_setup_new | 비-git | commit/push **없음** (작성처) |
| **v1** | kuks_claude_setup | origin = `kuks2309/kuks_claude_setup` | `docs/<topic>` 브랜치 commit + **origin push** |
| **v3** | kuks_claude_skill_setup | origin=`kuks_claude_agent_setup` + fito=`FITO_claude_skill_install` | **dual-remote 양쪽 push** + SHA(Secure Hash Algorithm) 검증 |

- 루트 `claude_code/` 는 **트랙이 아닌 비-git 작업공간**.
- remote push policy: `git remote -v` 필수(폴더명 ≠ repo명 — `kuks_claude_skill_setup` ≠ `kuks_claude_agent_setup`), 등록된 모든 remote 에 push, push 후 SHA 일치 검증.
