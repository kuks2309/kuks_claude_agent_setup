# GitHub Copilot 이식 가이드 (Copilot Adaptation)

> 본 저장소의 번들(규칙 자산)을 **GitHub Copilot** 환경에 적용하는 방법. 근거는 전부
> 2026-08-17 기준 공식 문서(docs.github.com · code.visualstudio.com)에서 검증했고 각 절에
> 출처를 병기한다. 설계 배경은 [docs/design-philosophy.md](../docs/design-philosophy.md) §6.

## 0. 핵심 결론 (요약)

3층 강제 모델의 층위 분리 덕에 이식은 "재작성"이 아니라 **재배치**다:

| 층 | 이식 방법 |
| --- | --- |
| L1 규칙 텍스트 (각 번들 `*.md`) | **그대로** — `.github/copilot-instructions.md`(전역 포인터) + `.github/instructions/*.instructions.md`(경로별)로 등록 |
| L2 훅 | Copilot hooks 로 이식 **가능해졌다**(2026, Claude Code 호환 포맷) — 단 적용 표면 제한(§3) 주의 |
| L3 CI 이빨 (`checks/*.sh`, pre-commit) | **무변경 이식** — git 기반이라 도구 무관. 최종 방어선 |

## 1. Copilot 커스터마이징 표면 (검증된 사실)

| 표면 | 위치 | 적용 범위 |
| --- | --- | --- |
| 저장소 전역 지침 | `.github/copilot-instructions.md` (단일 파일) | Copilot Chat + code review + cloud agent(구 coding agent) 전부 |
| 경로별 지침 | `.github/instructions/*.instructions.md` — frontmatter `applyTo:` glob (+ 선택 `excludeAgent:`) | github.com 은 cloud agent·code review, IDE 는 VS Code·Visual Studio·JetBrains 등 |
| AGENTS.md | 저장소 어디에나 복수 배치, **작업 파일 기준 nearest-wins** | cloud agent·CLI (code review 는 AGENTS.md 만) |
| CLAUDE.md | **루트 한정** 직접 읽음 | cloud agent·CLI·VS Code(설정) — 한 파일로 Claude/Copilot 양쪽 커버 가능 |
| 프롬프트 파일 | `.github/prompts/*.prompt.md` — `/이름` 호출 | **public preview, IDE 한정**(VS Code·Visual Studio·JetBrains). cloud agent 미지원 |
| hooks | `.github/hooks/*.json` (cloud agent) · `~/.copilot/hooks/`(CLI) · VS Code(Preview) | `preToolUse` allow/deny/ask + 인자 수정, 이벤트명 Claude Code 호환 |
| 에이전트 환경 준비 | `.github/workflows/copilot-setup-steps.yml` — job 이름 고정 `copilot-setup-steps` | cloud agent 작업 전 실행 |
| 조직 지침 | 조직 설정 UI 텍스트 박스 | github.com 의 Chat·code review·cloud agent 만 (IDE 미적용) |

우선순위(충돌 시): **개인 > 저장소 > 조직**. 경로별+전역은 매치 시 둘 다 사용, VS Code 의
복수 파일 병합 순서는 보장되지 않음("no specific order is guaranteed"). 단일 지침 파일은
약 1,000줄 이내 권장(강제 아님).

출처: docs.github.com `.../add-repository-instructions`, `.../custom-instructions-support`,
`.../customize-cloud-agent/customize-the-agent-environment`, `.../reference/hooks-reference`,
code.visualstudio.com `docs/agent-customization/*`.

## 2. Claude Code ↔ Copilot 대응표

| 본 저장소 자산 | Copilot 대응물 | 이식 판정 |
| --- | --- | --- |
| 타깃 CLAUDE.md 의 등록 포인터(claude.snippet.md) | `.github/copilot-instructions.md` 의 등록 줄 | 동일 패턴 — 포인터 + "규칙 파일을 먼저 읽어라" |
| 규칙 본문 `docs/claude_guideline/<번들>/*.md` | 그대로 두고 위 포인터가 참조 | 무변경 |
| `domains/`(ros2·embedded 등 선택 규칙) | `.github/instructions/<도메인>.instructions.md` + `applyTo` glob | **Copilot 쪽이 더 자연스러움** — 경로 조건부 자동 주입 |
| slash command / skill | `.github/prompts/*.prompt.md` | 부분 — IDE 한정·preview |
| SessionStart 주입 훅 | `sessionStart` hook | 가능 (CLI·cloud agent·VS Code) |
| PreToolUse 게이트 (drawio-write-gate, git 4게이트 등) | `preToolUse` hook — `{"permissionDecision": "allow\|deny\|ask"}` | 가능 — 단 §3 표면 제한 |
| PostToolUse 추적 | `postToolUse` hook | 가능 |
| `checks/*.sh` + `⟦CI:<id>⟧` + pre-commit | 무변경 | **완전 이식** |
| INSTALLED.md / install.sh | 무변경 (git 기반) | 완전 이식 |
| 산출물 기록 체계 (mistake·debt·issues·ADR) | 무변경 (파일 규약) — 지침 파일이 기록 의무를 지시 | 완전 이식 |

## 3. 한계 — 정직하게

1. **github.com 상의 Copilot Chat·code review 에는 hook 이 없다.** hook 은 CLI·cloud
   agent·VS Code 의 에이전트 실행에만 걸린다. 따라서 code review 표면에서의 강제는
   여전히 **branch protection + required checks(CI)** 가 담당한다 — 본 저장소의 "강제는
   CI 만 진짜" 원칙이 그대로 유효한 영역.
2. **프롬프트 파일은 preview 이고 IDE 한정** — cloud agent 는 `/이름` 프롬프트를 쓰지
   못한다. 반복 워크플로는 지침 파일 또는 AGENTS.md 로 내린다.
3. **경로별 지침은 github.com Chat 에는 미적용** — 전역(copilot-instructions.md)에 핵심
   원칙을, 경로별에 도메인 세칙을 배치하는 2단 구성이 안전하다.
4. **하위 디렉터리 CLAUDE.md 는 Copilot 이 읽지 않는다**(루트만). 하위 배치가 필요하면
   `AGENTS.md`(nearest-wins)로 미러한다.
5. 구 "coding guidelines"(Enterprise 설정 UI) 기능은 2025-09 완전 폐기 — 지침 파일
   체계로 일원화됐다. 옛 문서·블로그를 따라가지 말 것.

## 4. 번들별 이식 레시피

| 번들 | 이식 형태 |
| --- | --- |
| user_instruction | 훅 의존(자동 기록) — cloud agent/CLI 는 `userPromptSubmitted` hook 으로 재현, github.com Chat 은 불가(한계 명시) |
| external_reference / issue_fix / mistake / debt / reverse_engineering | 전역 지침에 등록 줄 + 규칙 파일 참조 (L1 그대로) · entry-lint 등 checks 는 CI 로 |
| code_review / sw_structure | 전역 지침 등록 + **Copilot code review 용**으로 핵심 severity·인벤토리 규칙을 `.github/instructions/` 에 요약(head 브랜치에서 읽힘) |
| coding (+domains) | 코어는 전역 지침, 도메인은 `applyTo` 경로별 지침 (예: `**/*.launch.py,**/package.xml` → ros2) |
| drawio | `applyTo: "**/*.drawio"` 지침 + `preToolUse`/`postToolUse` hook(편집 시 린트) + pre-commit `⟦CI:drawio-lint⟧` 은 무변경 |
| git_workflow | 규칙은 전역 지침, 게이트류는 hook 이식 + **branch protection**(§4 GitHub 정책 강제 절이 이미 Copilot 시대의 정답) |
| session_workflow | Claude Code 세션 모델 전제 — cloud agent 에는 세션 레지스트리 개념이 없어 **이식 제외**(작업 단위가 PR 로 격리되므로 필요성도 낮음) |
| computer_use / acronym | 전역 도구·훅 — CLI 환경이면 `~/.copilot/` 계층으로, 그 외 이식 보류 |

## 5. 시작 템플릿

`templates/` 에 즉시 복사 가능한 시작점을 제공한다:

- `templates/copilot-instructions.md` — 저장소 전역 지침 (핵심 원칙 + 번들 등록 포인터)
- `templates/instructions/drawio.instructions.md` — 경로별 지침 예시 (drawio 2단 검증)
- `templates/instructions/ros2-coding.instructions.md` — 도메인 규칙 경로별 배치 예시
- `templates/hooks/pretooluse-lint-gate.json` — preToolUse 게이트 예시 (형식은
  docs.github.com/copilot/reference/hooks-reference 를 정본으로 재확인할 것)

적용 절차:

```bash
# 타깃 저장소에서
mkdir -p .github/instructions .github/hooks
cp <본 저장소>/copilot/templates/copilot-instructions.md .github/copilot-instructions.md
cp <본 저장소>/copilot/templates/instructions/*.instructions.md .github/instructions/
cp <본 저장소>/copilot/templates/hooks/*.json .github/hooks/
# 규칙 본문(번들)은 기존 install.sh 로 docs/claude_guideline/ 에 설치 — Copilot 도 같은 파일을 읽는다
```

## 6. 검증 방법

- **Chat/agent**: 지침 위반을 유도하는 요청을 던져 응답이 규칙 파일을 참조하는지 확인
  (응답의 reference 목록에 지침 파일이 떠야 한다).
- **code review**: 규칙 위반이 있는 PR 을 만들어 Copilot 리뷰가 지적하는지 확인 —
  지침은 head 브랜치에서 읽히므로 PR 브랜치에 지침 파일이 있어야 한다.
- **hooks**: `copilot-setup-steps.yml` 처럼 파일을 건드리는 PR + 수동 실행으로 사전 검증.
- **CI**: 기존 checks/*.sh 가 pre-commit·Actions 에서 그대로 도는지 — 이건 Copilot 과
  무관하게 이미 검증돼 있다.

---

**VERSION**: 1.0.0 (최초 작성 — 2026-08-17 공식 문서 검증 기반)
