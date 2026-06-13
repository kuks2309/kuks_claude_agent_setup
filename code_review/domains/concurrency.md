# 코드 리뷰 — 동시성 Add-on (Code Review — Concurrency / Threading / async)

> 코어 [review.md](../review.md) 의 도메인 sub-file. **관점: 동시성 코드 리뷰** — 동기화 객체·공유 상태·실행 컨텍스트 인벤토리/평가.

**트리거**: `threading`, `asyncio`, `std::thread`, `std::mutex`, `MutuallyExclusiveCallbackGroup`, `ReentrantCallbackGroup`, multi-callback ROS 노드, `@asynccontextmanager`, `await`, `async def`.

## 1. 인벤토리 추가 표

**B-1. 동기화 객체** — 컬럼: `객체`, `종류(Mutex/Lock/Event/Semaphore/Atomic/Condvar)`, `보호 자원`, `획득 위치`, `해제 위치`

**B-2. 공유 상태** — 컬럼: `변수`, `읽기 위치`, `쓰기 위치`, `보호 객체`(보호 없으면 `"비보호"`)

**B-3. 실행 컨텍스트** — 컬럼: `이름`, `종류(thread/task/coroutine/callback group/executor)`, `우선순위·executor`, `생성 위치`

## 2. 평가 추가 카테고리 (인라인 태그)

- `[race]` — 공유 변수 비보호 쓰기, race condition 후보
- `[deadlock]` — 다중 lock 획득 순서 일관성, 순환 의존
- `[timing]` — 콜백 차단성, 시간 budget, jitter 원인
- `[reentrant]` — 재진입 가능 콜백에서 비-reentrant 호출

## 3. 자체 점검 grep

```bash
TARGET=docs/code_review/<주제>.md

# 동기화 객체 / 공유 상태 표 헤더
grep -E "^\| 객체 .*종류.*보호 자원|^\| 변수 .*읽기 위치.*쓰기 위치" $TARGET

# 동시성 평가 태그 등장
grep -oE "\[(race|deadlock|timing|reentrant)\]" $TARGET | sort -u

# 비보호 공유 상태 표기
grep -E "비보호" $TARGET
```

## 4. 다른 도메인과의 의존/충돌

- **ros2-review 와 상보** — multi-threaded executor·콜백 그룹 평가는 본 도메인의 race/deadlock 과 함께 적용.
- **embedded-review 와 상보** — ISR↔Task 공유 자원은 본 도메인의 동기화 객체 표 + embedded 의 `[prio]`/`[volatile]` 와 cross-reference.
