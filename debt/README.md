# debt 번들 — 부채 관리 registry

기술·이해·의도 3-부채의 **등록·추적·상환** registry. 작업 SOP(coding 등)가 부채를 *식별*하면, 여기가 *등록·추적·상환*을 소유한다.

## 설치

```bash
cd debt && ./install.sh <타깃-프로젝트-루트>
```

`debt.md` + `checks/` 를 `docs/claude_guideline/debt/` 로 복사, registry 템플릿을 `docs/debt/registry.md` 로(기존 보존), `.gitignore` 에 `.omc/` 추가, `CLAUDE.md` 등록.

## 세 부채

| 부채 | 무엇 | 식별 지점(coding) |
| --- | --- | --- |
| **기술** | shortcut·임시방편·미흡 테스트·미룬 리팩토링·`TODO` | §4 구현 · §5 검증 |
| **이해** | 시스템·코드 이해 공백, "왜 되는지 모름" | §2 사전조사 |
| **의도** | 결정 근거·의도 상실 | §3 ADR · `user_instruction` |

## 강제 (이빨)

| 이빨 | 태그 | 검사 |
| --- | --- | --- |
| `check-mapping.sh` | (메타) | `⟦CI⟧` 태그 ↔ 스크립트 1:1 정합 |
| `debt-marker.sh` | `⟦CI:debt-marker⟧` | 코드 `TODO`/`FIXME`/`HACK` 가 debt id 참조 — **맨 마커 차단**(등록 강제) |

나머지(부채 유형 판단·상환 우선순위)는 `⟦권고⟧`.

## registry 양식 (debt 가 SSOT)

`docs/debt/registry.md` — `id · 유형 · 위치 · 사유 · 식별일 · 상태 · 상환계획`. 항목 append, 해결도 기록(덮어쓰기 금지). coding 의 함수표↔code_review 처럼, **부채 등록 양식의 권위는 debt** 이고 coding 은 식별만.

## 자체 점검

```bash
cd docs/claude_guideline/debt
bash checks/check-mapping.sh        # green 이어야
bash checks/debt-marker.sh ../../..  # 프로젝트 코드 마커 점검
```

## 파일

`debt.md`(코어) · `checks/*.sh`(2) · `registry.template.md` · `install.sh` · `claude.snippet.md` · `.pre-commit-config.yaml` · `ci/debt-gates.yml`
