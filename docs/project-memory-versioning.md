# Claude Code 프로젝트 메모리를 저장소와 함께 버전 관리하기

> 적용 범위: **모든 프로젝트 공통**. 특정 저장소가 아니라 어느 프로젝트에서든 따라 할 수 있는 일반 가이드.
> 위치: `~/.claude/docs/project-memory-versioning.md` (글로벌)

## 1. 이슈 (문제 정의)

Claude Code 의 per-project(프로젝트별) 메모리는 다음 경로에 **사용자 홈 중앙 저장소** 형태로 저장된다.

```
~/.claude/projects/<encoded-project-path>/memory/
```

- `<encoded-project-path>` = 프로젝트 절대경로의 슬래시(`/`)를 대시(`-`)로 치환한 키.
  - 예: `/home/amap/FITO/kkw` → `-home-amap-FITO-kkw`
- 이 디렉터리는 **프로젝트별로 분리**되어, 해당 프로젝트 세션에서만 자동 로드된다.
- 인덱스 파일 `MEMORY.md` 한 줄 + 개별 메모리 파일들로 구성된다.

### 무엇이 문제인가

| 측면 | 현재 동작 | 한계 |
|---|---|---|
| 자동 로드 | harness 가 세션 시작 시 위 경로를 컨텍스트에 주입 | ✅ 동작 |
| 저장 위치 | 사용자 홈(중앙) | 프로젝트 트리 **밖** |
| 버전 관리 | 없음 (홈은 보통 git 비추적) | 프로젝트와 함께 이력/공유 불가 |
| 팀 공유 | 안 됨(개인 전용) | 동료가 같은 메모리를 못 받음 |
| 백업/이동 | 홈에 종속 | 프로젝트만 옮기면 메모리는 따라오지 않음 |

즉 메모리는 "프로젝트별"이긴 하지만 **프로젝트와 함께 이동·버전 관리·공유되지 않는다.**

## 2. 해결 방향 (다른 프로젝트에 적용하는 워크플로)

원본은 그대로 두어 자동 로드를 유지하고, 프로젝트 저장소에 **미러(복사본)** 를 둔다.

1. **원본 작성/수정은 항상 `~/.claude/projects/<encoded>/memory/` 에서 한다.**
   - harness 자동 로드 메커니즘이 이 경로에만 작동하므로, 여기를 정본(source of truth)으로 유지.
2. **프로젝트 저장소에 미러 폴더를 만든다.** 권장 경로: `<repo>/.claude/memory/`
   - `~/.claude` 구조를 그대로 미러링해 직관적이고, 다른 프로젝트에서도 같은 관례 재사용 가능.
3. **동기화한다.** 셋 중 택1:
   - (a) 수동 복사: 변경 후 `cp` 로 미러 갱신 (가장 단순, 명시적)
   - (b) 심볼릭 링크: `<repo>/.claude/memory` → 원본 디렉터리 링크 (항상 최신, 단 절대경로 종속·OS 이식성 주의)
   - (c) 동기화 스크립트: 아래 `sync` 예시를 프로젝트 훅/`Makefile` 에 연결
4. **공유 여부를 메모리 종류로 구분한다.**
   - `project` / `reference` 타입(해당 저장소와 직접 관련): 미러·공유 적합
   - `user` / `feedback` 타입(개인 작업 지침): 공개 저장소에 올리면 개인 정보·선호 노출 위험 → 미러 제외하거나 `.gitignore` 처리 판단
5. **여러 세션 공유 작업 트리 주의.** 동시 세션이 같은 저장소를 공유하면, 미러 동기화 시 다른 세션 산출물을 휩쓸지 않도록 **이번 작업이 만진 파일만** 명시적으로 복사한다.

## 3. 재사용 스니펫

### 프로젝트 경로 → 인코딩 키
```bash
# /home/me/proj → -home-me-proj
enc() { printf '%s' "$1" | sed 's#/#-#g'; }
SRC=~/.claude/projects/$(enc "$(pwd)")/memory
```

### 원본 → 저장소 미러 동기화
```bash
# 저장소 루트에서 실행
DST=.claude/memory
mkdir -p "$DST"
# 프로젝트성/참조성만 미러하려면 파일을 명시 (개인 메모리 제외 시)
cp -av "$SRC"/. "$DST"/
# 또는 특정 파일만:  cp -av "$SRC"/MEMORY.md "$SRC"/<name>.md "$DST"/
```

### 공개 저장소에서 개인 메모리 제외 (선택)
```gitignore
# .gitignore — 개인 user/feedback 메모리는 공유 안 함
.claude/memory/verify-before-concluding.md
.claude/memory/investigate-before-asking.md
```

## 4. 대안: 프로젝트 지침은 `CLAUDE.md` / `AGENTS.md`

메모리 미러는 "개인 작업 기록을 저장소에 백업/공유"하는 용도다.
**저장소에 의도적으로 커밋해 팀과 공유할 프로젝트 지침**은 처음부터 프로젝트 루트의 `CLAUDE.md`(또는 `AGENTS.md`)에 작성하는 것이 정석이다. 이 파일은 repo 를 여는 모든 사람/세션에 적용된다.

| 목적 | 수단 |
|---|---|
| 개인 작업 메모리 + 저장소 백업/이력 | `~/.claude/.../memory/` 정본 + `<repo>/.claude/memory/` 미러 |
| 팀 공유 프로젝트 규칙·관례 | 저장소 내 `CLAUDE.md` / `AGENTS.md` (직접 커밋) |

## 5. 체크리스트 (다른 프로젝트 적용 시)

- [ ] 원본 메모리는 `~/.claude/projects/<encoded>/memory/` 에 둔다
- [ ] 저장소 루트가 git 인지 확인 (`git rev-parse --show-toplevel`)
- [ ] `<repo>/.claude/memory/` 미러 생성
- [ ] 공유할 메모리 종류 선별 (project/reference vs user/feedback)
- [ ] 개인 메모리는 `.gitignore` 또는 미러 제외
- [ ] 동시 세션 환경이면 이번 작업이 만진 파일만 복사
- [ ] 변경 시 동기화 방법(수동/심링크/스크립트) 한 가지를 정해 일관 적용
