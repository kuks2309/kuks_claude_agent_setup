---
applyTo: "**/*.launch.py,**/package.xml,**/CMakeLists.txt,src/**/*.cpp,src/**/*.py"
---

# ROS2 코딩 도메인 규칙 (요약 포인터)

ROS2 관련 코드를 작성/수정하기 전에 `docs/claude_guideline/coding/domains/ros2-coding.md` 를
읽는다. 특히:

- **QoS 명시** — 센서 스트림은 통상 BEST_EFFORT(SensorDataQoS). 구독이 RELIABLE 을
  요구하면 연결 자체가 안 되는 무음 실패가 난다. 발행자 QoS 를 먼저 확인하고 맞춘다.
- **sim time** — 시뮬레이터 연동 노드는 `use_sim_time` 파라미터를 명시한다. 벽시계
  스탬프 TF 를 sim-time 시스템에 섞으면 tf2 버퍼가 오염된다.
- **실기·시험 기동 규율** — 재기동 전 기존 프로세스 종료를 `ps` 로 실확인(같은 이름
  노드는 `ros2 node list` 에 겹쳐 보인다), 기동 후 토픽 발행자 수를 확인한다.
- **빌드 검증** — `colcon build --symlink-install --packages-up-to <패키지>` 성공 +
  해당 테스트 실행까지가 "완료"의 최소 조건이다.
