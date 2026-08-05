# tailscale — 새 PC 온보딩·접속 진단 (Self-Contained)

새 PC 를 tailnet 에 들여 **원격 작업 대상으로 쓸 수 있는 상태까지** 만드는 절차와, 이미 들인 PC 에 못 붙을 때의 판정 규칙에 대한 단일 근원(SSOT, Single Source of Truth). 본 파일 1개로 자체 완결.

## 설치 위치

- **본 파일**: `~/.claude/tailscale/tailscale.md` (전역 — 접속은 프로젝트가 아니라 머신 단위 문제)
- **온보딩·진단 스크립트**: `~/.claude/tailscale/tailscale-doctor.sh`
- 본 파일이 위 경로에 없으면 본 규칙은 활성화되지 않는다.

## 모토 — 온보딩은 절차로, 실패는 계층으로

새 PC 를 들이는 일은 **순서가 정해진 8단계**이며, 각 단계에는 끝났는지 눈으로 확인할 수 있는 판정 명령이 있다. "설치했으니 됐겠지"는 온보딩이 아니다. 반대로 이미 들인 PC 에 못 붙는 것은 절차가 아니라 **계층 판정** 문제다(§6).

**sudo 는 온보딩 중 딱 두 번만 쓴다**(설치·operator 지정). 그 뒤로는 관리자 권한 없이 운용한다(§4).

---

## 1. 새 PC 온보딩 — 8단계 (★ 순서 고정)

위에서부터 순서대로 밟는다. 각 단계는 **판정 명령의 출력을 확인한 뒤에만** 다음으로 넘어간다.

| 단계 | 무엇을 | 판정 명령 | 통과 기준 | sudo |
| --- | --- | --- | --- | --- |
| **S1** | Tailscale 설치 | `tailscale version` | 버전 문자열 출력 | 필요 |
| **S2** | 데몬 상시 기동 | `systemctl is-enabled tailscaled && systemctl is-active tailscaled` | `enabled` + `active` | 필요 |
| **S3** | tailnet 가입(인증) | `tailscale status` | 자기 주소·피어 목록 출력 (`Logged out` 아님) | 필요 |
| **S4** | **operator 지정 (sudo 졸업)** | `tailscale debug prefs \| grep -i OperatorUser` | 자기 계정명이 출력됨 | **마지막 sudo** |
| **S5** | 머신 이름 확정 | `tailscale status \| head -1` | 의도한 이름 그대로 (`-1` 접미사 없음) | 불필요 |
| **S6** | 키 만료 정책 | 관리 콘솔의 해당 노드 | 사람이 못 붙는 머신은 **만료 끔** | — |
| **S7** | SSH 수신 준비 | `systemctl is-active ssh` 또는 `tailscale debug prefs \| grep RunSSH` | `active` 또는 `RunSSH: true` | 불필요 |
| **S8** | **반대편에서 접속 검증** | 다른 PC 에서 `ssh <계정>@<이름> true` | 종료 코드 `0` | 불필요 |

**S8 을 생략하지 않는다.** 새 PC 에서 밖으로 나가는 것과 밖에서 그 PC 로 들어오는 것은 다른 경로이며, 원격 작업 대상으로 쓰려면 필요한 것은 후자다. 새 PC 앞에 앉아 확인할 수 있는 것이 아니라 **다른 PC 에서 실제로 붙어 봐야** 끝난 것이다.

S1~S3 은 §2·§3, S4 는 §4, S5~S8 은 §5 를 본다.

## 2. 설치 (S1·S2)

### Linux — Ubuntu·Debian 계열, arm64(Jetson) 포함

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

공식 설치 스크립트가 배포판·아키텍처를 판별해 apt 저장소를 등록하고 설치한다. Jetson(Orin 계열)의 JetPack 도 Ubuntu 기반이라 같은 명령을 쓴다. 패키지 설치라 이 단계는 관리자 권한이 필요하다.

저장소 등록은 `/etc/apt/sources.list.d/tailscale.list` 로 확인하고, 이후 갱신은 다음과 같다.

```bash
sudo apt update && sudo apt install --only-upgrade tailscale
```

### 데몬 상시 기동 (S2)

```bash
sudo systemctl enable --now tailscaled
```

설치 스크립트가 대개 여기까지 해 두지만 **확인은 별도로 한다.** `enable` 이 빠지면 재부팅 후 그 PC 가 tailnet 에서 사라지고, 원인을 인증 문제로 오진하기 쉽다.

### Windows

```powershell
winget install --id tailscale.tailscale
```

winget 이 없으면 공식 배포 페이지의 설치 파일을 쓴다. Windows 클라이언트는 로그인한 사용자 권한으로 동작하므로 §4(operator 지정)가 필요 없고, 트레이 아이콘에서 로그인하면 S3 까지 끝난 것과 같다.

## 3. tailnet 가입 (S3)

### 사람이 앉아 있는 PC — 브라우저 승인

```bash
sudo tailscale up
```

출력된 URL 을 브라우저에서 열어 **tailnet 소유 계정**으로 승인한다. 화면이 없는 머신이면 그 URL 을 다른 기기에서 열어도 된다.

### 헤드리스·자동 온보딩 — auth key

관리 콘솔에서 auth key 를 발급해 사용한다.

```bash
sudo tailscale up --authkey "$TS_AUTHKEY" --hostname <머신이름>
```

- 실기·서버처럼 반복 재설치가 예상되면 **재사용 가능(reusable) 키**로 발급한다.
- **auth key 를 저장소·스크립트·로그·명령 이력에 남기지 않는다.** 위처럼 환경 변수로 전달하고, 쓰고 나면 `unset TS_AUTHKEY` 한다.
- 키에는 유효기간이 있다. 온보딩 실패 원인이 키 만료인 경우가 흔하므로 발급 시각을 확인한다.

## 4. sudo 졸업 — operator 지정 (S4) ★

기본 상태에서는 상태를 **바꾸는** 명령(`up`·`down`·`set`·`ssh`·`file cp`)이 관리자 권한을 요구한다. 매번 `sudo` 를 치는 것은 번거로울 뿐 아니라, 자동화 스크립트가 비밀번호 프롬프트에서 멈추는 원인이 된다. 한 번만 operator 를 지정하면 그 계정은 이후 sudo 없이 tailscale 을 운용한다.

```bash
sudo tailscale set --operator=$USER
```

**이것이 온보딩에서 sudo 를 쓰는 마지막 명령이다.**

판정:

```bash
tailscale debug prefs | grep -i OperatorUser
```

계정명이 출력되면 설정된 것이다. **아무것도 출력되지 않으면 미설정**이다(미설정일 때는 항목 자체가 나타나지 않는다). 설정 후에는 다음이 sudo 없이 성공해야 한다.

```bash
tailscale set --hostname=<현재이름>    # 같은 값이므로 무해, 권한만 확인
```

참고로 **읽기 계열은 원래 sudo 가 필요 없다** — `tailscale status`, `tailscale ip`, `tailscale netcheck`, `tailscale debug prefs` 는 지정 전에도 그냥 된다. operator 지정이 바꾸는 것은 쓰기 계열이다.

## 5. 이름·접속 준비 (S5~S8)

여기부터는 sudo 없이 수행한다.

### 머신 이름 (S5)

Tailscale 은 기본으로 OS 호스트명을 쓰고, 같은 이름이 이미 있으면 `-1`, `-2` 를 붙인다. 이름이 흔들리면 접속 대상 지정이 매번 달라지므로 **못 박는다.**

```bash
tailscale set --hostname=<머신이름>
```

이름은 소문자·숫자·하이픈만 쓴다. MagicDNS 가 켜진 tailnet 이면 이 짧은 이름으로 바로 접속되고, 아니면 `<머신이름>.<tailnet>.ts.net` 전체 이름을 쓴다.

### 키 만료 (S6)

관리 콘솔에서 노드 키 만료를 켜 두면 일정 기간 후 재인증이 필요하다. **사람이 붙기 어려운 머신(실기·헤드리스 서버)은 만료를 끈다.** 켜 둔 채로 두면 어느 날 접속이 끊기고, 그 PC 앞에 사람이 가야만 복구된다.

### SSH 수신 (S7)

두 방식 중 하나를 고른다.

| 방식 | 준비 | 언제 |
| --- | --- | --- |
| 일반 SSH | 상대에 `sshd` 설치·기동 + 공개키 배포 | 키를 배포해 둘 수 있을 때 |
| Tailscale SSH | 상대에서 `tailscale set --ssh`, 접근 권한은 관리 콘솔 ACL | 키 배포 없이 붙어야 할 때 |

Ubuntu 최소 설치본에는 `sshd` 가 없을 수 있다 — `sudo apt install openssh-server` 후 `sudo systemctl enable --now ssh`(패키지 설치라 이 경우만 예외적으로 관리자 권한).

### 반대편 접속 검증 (S8)

**다른 PC 에서** 실행한다.

```bash
ssh -o BatchMode=yes <계정>@<머신이름> true; echo "exit=$?"
```

`exit=0` 이면 온보딩 완료다. 처음 붙는 머신은 호스트 키 확인 때문에 `BatchMode` 에서 실패할 수 있으므로, 한 번은 대화형으로 붙어 `known_hosts` 에 등록한 뒤 다시 판정한다.

자주 붙을 머신은 `~/.ssh/config` 에 이름·계정·키를 등록해 두면 매번 적지 않아도 된다.

## 6. 접속이 안 될 때 — 실패 계층 (★)

이미 온보딩된 PC 에 못 붙는 경우다. 위에서부터 판정하고 **처음 실패한 계층에서 멈춰 그 조치만** 한다. 계층을 건너뛴 재시도·재부팅·재설치를 금지한다.

| 계층 | 무엇이 막혔나 | 판정 | 조치 | 종료 코드 |
| --- | --- | --- | --- | --- |
| L0 | 미설치 | `command -v tailscale` | §2 | `10` |
| L1 | 데몬 정지 | `systemctl is-active tailscaled` | S2 | `20` |
| L2 | 미인증·키 만료 | `tailscale status` 가 `Logged out`/`NeedsLogin` | §3 | `30` |
| L3 | **상대가 오프라인** | 피어 행에 `offline, last seen ...` | §7 | `40` |
| L4 | SSH 실패(피어는 온라인) | `ssh -o BatchMode=yes <이름> true` | S7·S8 | `50` |
| — | 이름을 tailnet 에서 못 찾음 | 피어 행 없음 | 이름 오타 또는 미가입 | `60` |

판정 명령이 모두 읽기 계열이라 **진단에는 sudo 가 필요 없다.** 계층과 종료 코드가 1:1 이므로 호출한 쪽이 출력 문자열을 파싱하지 않고 분기할 수 있다.

```bash
bash ~/.claude/tailscale/tailscale-doctor.sh [피어이름]
```

피어 이름을 생략하면 자기 머신 상태(L0~L2)만 본다. 처음 실패한 계층의 조치를 출력하고 그 코드로 끝난다.

## 7. 상대가 오프라인일 때 (L3) — 대기 금지

피어 행이 `offline, last seen <시각>` 이면 **접속 도구로 풀 문제가 아니다.** 설치·인증을 재점검하는 것은 낭비이며, 켜질 때까지 재시도 루프를 도는 것도 마찬가지다. 켜지는 시점을 예측할 수 없기 때문이다.

할 일은 둘 중 하나다.

1. 그 머신을 켤 수 있는 사람에게 전원 상태를 확인한다.
2. **작업을 비동기 지시로 남긴다** — 지시를 파일로 적어 저장소에 올려 두면 그 머신이 다음에 켜졌을 때 받는다. 붙어 있는 동안 끝내야 한다는 제약이 사라진다.

`last seen` 이 수 분 전이면 간헐 운용(작업 중 전원 on/off), 며칠 전이면 장기 미사용이다.

## 8. 금지 사항

- S4(operator 지정) 를 건너뛰어 이후 운용에 계속 `sudo` 를 요구하게 두는 것 — 자동화가 비밀번호 프롬프트에서 멈춘다.
- S8(반대편 접속 검증) 없이 온보딩 완료로 선언하는 것.
- 계층 판정 없이 재시도·재부팅·재설치하는 것.
- L3(상대 오프라인) 에서 켜질 때까지 대기 루프를 도는 것.
- 사람이 못 붙는 머신에 키 만료를 켜 두는 것.
- 이 문서·스크립트에 **tailnet 이름·노드 이름·`100.x` 주소·auth key 를 적는 것.** 본 번들은 외부 조직 저장소로 미러되므로 사설망 구성이 그대로 공개된다. 실제 값은 실행 시 `tailscale status` 로 얻는다.
