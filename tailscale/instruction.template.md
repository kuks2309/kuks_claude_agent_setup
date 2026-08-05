---
id: YYYY-MM-DD-NNN
target: <새 PC 의 식별자>
kind: 실행
status: 대기
created: YYYY-MM-DD
done_when: "S1·S2·S3·S4·S5·S7·S8 판정 7개가 전부 통과하고 그 출력을 회신 + S6(키 만료, 콘솔·사람 작업)의 처리 여부를 명시 회신. S8 은 반드시 다른 PC 에서 실행한 결과일 것."
evidence: []
---

## 지시 원문

이 PC 를 tailnet 에 온보딩하라. 아래 S1~S8 을 **순서대로** 수행하고, 각 단계의 판정 명령 출력을 §수행 기록에 그대로 붙여라. 판정 명령의 출력을 확인하기 전에 다음 단계로 넘어가지 마라.

`<...>` 로 표시된 값은 발신 측이 지정한다. 지정되지 않았으면 **추측하지 말고 보류로 전환**하라(§보류 규칙).

### S1. 설치 — sudo 필요

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

판정: `tailscale version` → 버전 문자열이 출력될 것.

Windows 면 `winget install --id tailscale.tailscale` 를 쓰고, S4 는 건너뛴다(Windows 클라이언트는 로그인 사용자 권한으로 동작).

### S2. 데몬 상시 기동 — sudo 필요

```bash
sudo systemctl enable --now tailscaled
```

판정: `systemctl is-enabled tailscaled && systemctl is-active tailscaled` → `enabled` 와 `active` 가 모두 출력될 것.

`enable` 이 빠지면 재부팅 후 이 PC 가 tailnet 에서 사라진다. 반드시 두 값을 모두 확인한다.

### S3. tailnet 가입 — sudo 필요, **사람 필요**

```bash
sudo tailscale up --hostname <머신이름>
```

출력되는 URL 을 사람이 브라우저에서 열어 tailnet 소유 계정으로 승인해야 한다. **URL 을 회신하고 승인을 기다리는 동안 보류로 전환하라.**

auth key 를 발급받은 경우는 사람 없이 가능하다.

```bash
sudo tailscale up --auth-key=file:<키파일경로> --hostname <머신이름>
shred -u <키파일경로>
```

판정: `tailscale status` → 자기 주소와 피어 목록이 출력되고 `Logged out` 이 아닐 것.

**auth key 를 이 파일·로그·셸 이력에 적지 마라.** 키를 명령줄에 직접 넣으면 `ps` 로 다른 사용자에게 보이므로 반드시 `file:<경로>` 형식을 쓰고, 쓴 뒤 파일을 지운다. 플래그는 `--auth-key` 다(`--authkey` 아님).

### S4. operator 지정 (sudo 졸업) — 이것이 마지막 sudo

```bash
sudo tailscale set --operator=$USER
```

판정: `tailscale debug prefs | grep -i OperatorUser` → 계정명이 출력될 것. **아무것도 출력되지 않으면 미설정이다**(미설정일 때는 항목 자체가 나타나지 않는다).

이후 단계는 sudo 없이 수행한다. 이 단계를 건너뛰면 이후 자동화가 비밀번호 프롬프트에서 멈춘다.

### S5. 머신 이름 확정 — sudo 불필요

```bash
tailscale set --hostname=<머신이름>
```

판정: `tailscale status | head -1` → 지정한 이름이 그대로일 것. `-1`, `-2` 접미사가 붙었으면 이름이 이미 쓰이고 있는 것이므로 **보류로 전환하고 회신**하라(임의로 다른 이름을 쓰지 마라).

이름은 소문자·숫자·하이픈만 쓴다.

### S6. 키 만료 정책 — **사람 필요(관리 콘솔)**

이 PC 가 사람이 상주하지 않는 머신(실기·헤드리스 서버)이면 관리 콘솔에서 이 노드의 **키 만료를 꺼야** 한다. 명령으로 할 수 없다.

판정: 콘솔에서 만료가 꺼졌다는 사람의 확인 회신.

이 단계는 접속에 즉시 영향을 주지 않으므로, 미완료 상태로 S7~S8 을 먼저 진행해도 된다. 다만 **미완료 사실을 회신에 명시**하라.

### S7. SSH 수신 준비 — sudo 불필요(단 sshd 설치는 예외)

둘 중 발신 측이 지정한 방식으로 한다. 지정이 없으면 보류로 전환하고 어느 쪽인지 물어라.

**일반 SSH** — 상대가 공개키를 배포해 둔 경우:

```bash
sudo apt install -y openssh-server        # 없을 때만
sudo systemctl enable --now ssh
```

판정: `systemctl is-active ssh` → `active`.

**Tailscale SSH** — 키 배포 없이:

```bash
tailscale set --ssh
```

판정: `tailscale debug prefs | grep RunSSH` → `"RunSSH": true` 가 출력될 것.

### S8. 반대편 접속 검증 — **다른 PC 에서 실행**

```bash
ssh -o BatchMode=yes <계정>@<머신이름> true; echo "exit=$?"
```

판정: `exit=0`.

**이 PC 에서 실행한 결과는 판정으로 인정되지 않는다.** 나가는 경로와 들어오는 경로는 다르며, 원격 작업 대상으로 쓰려면 필요한 것은 후자다. 이 PC 에서 실행할 수 없으면 **보류로 전환하고 발신 측에 S8 수행을 요청**하라.

처음 붙는 경우 호스트 키 확인 때문에 `BatchMode` 가 실패할 수 있다. 한 번 대화형으로 붙어 `known_hosts` 에 등록한 뒤 다시 판정한다.

---

## 배경

이 PC 를 원격 작업 대상으로 쓰기 위한 최초 1회 절차다. 온보딩이 끝나면 이후 작업 지시는 이 채널로 전달된다.

## 보류 규칙 (이 지시 한정)

다음 경우 **작업을 중단하지 말고 `status: 보류` 로 바꾼 뒤 `blocked_reason` 과 `resume_when` 을 적고 회신**한다.

| 상황 | `resume_when` 에 적을 것 |
| --- | --- |
| S3 브라우저 승인 대기 | "발신 측이 URL 승인 완료를 회신" |
| S5 이름 충돌 | "발신 측이 사용할 이름을 재지정" |
| S6 콘솔 작업 대기 | "발신 측이 키 만료 해제를 회신" |
| S7 방식 미지정 | "발신 측이 일반 SSH / Tailscale SSH 중 하나를 지정" |
| S8 다른 PC 접근 불가 | "발신 측이 S8 을 대신 수행하고 결과를 회신" |

**추측으로 진행하지 않는다.** 위 표에 없는 막힘도 같은 방식으로 보류 전환한다.

## 수행 기록

(각 단계의 판정 명령과 그 출력을 그대로 붙인다. 요약하지 않는다.)
