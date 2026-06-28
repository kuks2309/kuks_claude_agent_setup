# reverse_engineering — RE 제1원칙 (원본 100% 동일) + 분석 보고 원칙

리버스 엔지니어링(reverse engineering) 산출물의 최상위 원칙 번들. 다른 모든 RE·검증 작업이 본 원칙에 종속된다.

## 무엇

- **제1원칙(§0~§5)**: 재구현(reimplementation) 출력은 원본과 **100% 동일**해야 한다. "비슷함"·"근사"는 실패. 동일성은 추정이 아니라 **원본 입력으로 원본·재구현 양쪽 구동 후 비트 대조**(≤1e-9)로 증명. 우리 코드로 입력 생성 금지(자기참조), 정·역 양방향 검증.
- **분석 보고 원칙(§6)**: 분석 단계의 정직성 게이트. 모든 주장을 `[존재]`(심볼/클래스가 바이너리에 있음 — nm/disasm) vs `[동작]`(런타임 라이브 경로에서 실행 — 호출 도달성 + 배포자산 `.smap`/`robot.model`/`rbk.plugin` 대조)으로 라벨 분리. 동작 주장은 배포 자산 대조 전 "확정/CONFIRMED" 금지. 죽은 코드(멤버가 ctor/dtor만 참조) 체크 의무.

## 설치

```bash
cd reverse_engineering && ./install.sh <타깃-프로젝트-루트>
```

`principle.md` 를 `<타깃>/docs/claude_guideline/reverse_engineering/` 로 복사하고, 등록 포인터(`claude.snippet.md`)를 타깃 `CLAUDE.md` 에 append(중복 시 스킵). **활성화 게이트**: `docs/claude_guideline/reverse_engineering/principle.md` 가 있어야 룰 활성.

## 근거

§6 은 거짓 보고 사고(2026-06-28, [issue #1](https://github.com/kuks2309/kuks_claude_agent_setup/issues/1))에서 도출 — 코드 "존재"를 런타임 "동작"으로 비약한 분석 보고를 차단한다.
