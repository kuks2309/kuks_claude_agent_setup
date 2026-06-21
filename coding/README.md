# coding 번들 — 코드 작성 SOP

Claude Code 에이전트가 코드 작성 시 따르는 절차 규칙 + 기계 강제(이빨). **판단 기준은 마크다운, 강제는 `checks/*.sh`(pre-commit·CI)** 로 분리한다.

## 설치

```bash
cd coding && ./install.sh <타깃-프로젝트-루트> [도메인...|--all]
# 예) ./install.sh ~/myproj ros2-coding numeric-coding
```

코어(`coding.md`·`conventions.md`·`stack.md`) + `checks/` 를 `docs/claude_guideline/coding/` 로 복사, 선택 도메인 복사, 타깃 `.gitignore` 에 `.omc/` 추가, `CLAUDE.md` 에 등록 스니펫 append. **활성화 게이트**: 본 파일들이 그 경로에 없으면 룰 비활성.

## 강제 모델 — 정직 선언

- **`⟦CI:<id>⟧`** = `checks/<id>.sh` 가 커밋된 코드에서 재도출·차단(pre-commit·CI). **에이전트가 못 속인다.**
- **`⟦권고⟧`** = 코드 재도출 불가, 자기보고에 의존 → 정직하게 advisory.
- **green ≠ good, 미탐지 ≠ 무결.**

### 무-CI 환경 강등 (큰소리 선언)

CI·pre-commit 이 없으면 **`⟦CI⟧` 도 강제력 0** 으로 강등된다(도구가 안 돈다). 그 환경에선 규칙 텍스트만 생존하며, 인덱스 등은 **수동 재생성**(`index-fresh.sh --generate`)으로 유지한다. 이 사실을 숨기지 않는다.

## 이빨 (checks/)

| 이빨 | 태그 | 검사 |
| --- | --- | --- |
| `check-mapping.sh` | (메타) | `⟦CI⟧` 태그 ↔ 스크립트 1:1 정합(번들이 자기 강제력에 거짓말 못 함) |
| `banned-pattern.sh` | `⟦CI:banned-pattern⟧` | secret·eval·raw SQL·blocking |
| `format.sh` | `⟦CI:format⟧` | 포맷터 `--check`(clang-format/black/prettier) |
| `dup-signature.sh` | `⟦CI:dup-signature⟧` | 중복 함수 시그니처 |
| `index-fresh.sh` | `⟦CI:index-fresh⟧` | 함수 인덱스 ↔ 코드 일치 |
| `memory.sh` | `⟦CI:memory⟧` | clang-tidy 정적 + AddressSanitizer 런타임 |
| `tests-ran.sh` | `⟦CI:tests-ran⟧` | 테스트 실행·통과 |
| `adr-fields.sh` | `⟦CI:adr-fields⟧` | ADR 필수 필드 |

도구 없으면 각 이빨은 graceful 생략(강제력 0, 정직히 알림).

## 도메인 (domains/) — 트리거 조건부

`memory-coding`·`concurrency-coding`·`numeric-coding`(횡단 aspect) · `ros2-coding`·`embedded-coding`(플랫폼). 트리거 감지 시 적용, 0 발화 정상. `code_review` 의 `-review` 도메인과 **write↔review 상보**.

## 자체 점검

```bash
cd docs/claude_guideline/coding
bash checks/check-mapping.sh          # ⟦CI⟧ 정합 (green 이어야)
grep -cE '^[0-9]+\. ' coding.md       # 룰 요약 = MUST 예산 (≤7)
```

## 변경 절차

- SSOT 는 본 번들 폴더. 규칙 변경은 사용자 승인 후 4 코어 + `checks/` 를 **단일 번들 VERSION 으로 동반 갱신**(부분 드리프트 금지).
- `⟦CI:<id>⟧` 태그 추가/변경 시 `checks/<id>.sh` + `check-mapping.sh` 동반. semver + 각 파일 말미 `VERSION`.

## 파일

`coding.md`(코어) · `conventions.md` · `stack.md` · `domains/*.md`(5) · `checks/*.sh`(8) · `install.sh` · `claude.snippet.md` · `.pre-commit-config.yaml` · `ci/coding-gates.yml`
