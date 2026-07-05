#!/usr/bin/env python3
"""Stop 훅 — 답변을 마친 뒤 AI 에게 약자 병기 '검토'를 요청한다.

현행 check.py 와 결정적 차이:
  - check.py: 정규식이 위반을 '단정'하고 오답 재작성을 강제 → 오탐 시 잘못된 재작성.
  - 본 훅   : 후보 약자를 '제시'만 하고 병기 여부 판단은 AI 에게 위임 → 오탐 무해.

동작:
  1) 후보(대문자 2~6자, 화이트리스트/코드/URL/이미 병기 제외)가 없으면 종료(추가 패스 없음).
  2) 후보가 있으면 '스스로 확인해 누락이면 보완, 아니면 그대로 마쳐라' 요청 후 차단(exit 2).
화이트리스트는 정답 게이트가 아니라 '소음 감소용' — 흔한 약어를 굳이 되묻지 않기 위한 것.
무한 루프는 stop_hook_active 로 방지(검토는 최대 1패스).
"""
import json
import re
import sys

# 흔한 약어 — 되묻지 않아도 되는 토큰(소음 감소용). 필요 시 추가한다.
WHITELIST = {
    "CLAUDE", "JSON", "YAML", "YML", "README", "TODO", "FIXME",
    "HTTP", "HTTPS", "URL", "URI", "API", "CLI", "SDK", "GUI", "UI", "UX",
    "ID", "OK", "OS", "IO", "AI", "ML", "PDF", "HTML", "CSS", "XML", "CSV",
    "MD", "SSOT", "OMC", "ROS", "ROS2", "KST", "NDA", "USB", "CAN", "PWM",
    "TF", "QOS", "RAM", "CPU", "GPU", "SQL", "SSH", "GIT", "NPM", "PR",
    # 공통 추가
    "ROM", "DDR", "TCP", "UDP", "IP", "DNS", "JWT", "CI", "CD",
    # 프로젝트 / 코드 리뷰
    "RxO", "DRY", "SOP", "DDS", "SOLID", "SRP", "OCP", "LSP", "ISP", "DIP",
    # ROS2 / 로보틱스
    "REP", "IMU", "FOV", "RTOS",
    # 임베디드
    "ADC", "DAC", "I2C", "SPI", "UART", "GPIO", "DMA", "ISR", "NVIC",
    "HAL", "MCU", "WCET", "FFT", "FPU", "MPU", "RMW", "IRQ",
    # 비전
    "BGR", "RGB", "PAMI",
    # 표준 / 인증 (고유명사)
    "RFC", "IEEE", "ISO", "IEC", "JEDEC", "AEC", "MISRA", "ASIL", "AUTOSAR",
    "CERT", "NASA", "JPL", "KC", "CE", "FCC", "UL", "PTP", "PEP", "LLVM", "GPL", "PSF",
    # 고유명사·조직 (대문자 표기)
    "FITO",
    # RFC 2119 정규 키워드 (형식 리터럴 — 약자 아님)
    "MUST", "SHOULD", "MAY", "SHALL", "NOT",
    # 도구·명령 이름 (고정 명칭, OMC 와 동류)
    "CCG",
    # 프로그래밍·로그 리터럴 (대문자 영어 단어 — 약자 아님)
    "PASS", "FAIL", "NULL", "NONE", "TRUE", "FALSE", "DONE", "GREEN", "RED",
    "AND", "OR", "XOR",
}


def last_assistant_text(transcript_path):
    text = ""
    try:
        with open(transcript_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("type") != "assistant":
                    continue
                for block in obj.get("message", {}).get("content", []):
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "")  # 마지막 텍스트 블록 유지
    except FileNotFoundError:
        return ""
    return text


def find_candidates(text):
    # 코드블록 / 인라인 코드 / URL 제거 (예외 영역)
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    # 본문 어디든 확장형(약자 바로 뒤 '(')이 한 번이라도 있으면 '도입된 약자'로 간주.
    # 규칙은 "첫 등장 시 병기" — 이후 bare 사용은 위반 아님.
    introduced = set(re.findall(r"\b([A-Z]{2,6})\(", text))
    out = []
    seen = set()
    # 약자는 보통 2~6자. 문자+숫자 식별자(MD060·STM32)와 7자+ 대문자 단어
    # (CODEOWNERS·UNVERIFIED 등)는 약자 아님 — 제외.
    for m in re.finditer(r"\b([A-Z]{2,6})\b(?![0-9])", text):
        tok = m.group(1)
        if tok in WHITELIST or tok in introduced or tok in seen:
            continue
        seen.add(tok)
        out.append(tok)
    return out


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)
    if data.get("stop_hook_active"):  # 검토 루프 방지 (최대 1패스)
        sys.exit(0)
    text = last_assistant_text(data.get("transcript_path", ""))
    if not text:
        sys.exit(0)
    cands = find_candidates(text)
    if cands:
        shown = ", ".join(cands[:10])
        print(
            f"[약자 병기 점검] 다음 토큰이 '첫 등장 시' '약어(영어 단어)'로 병기됐는지 "
            f"스스로 확인하라 — 누락이면 병기를 보완하고, 이미 병기했거나 "
            f"예외(코드·파일명·URL·고유명사·형식 리터럴·흔한 약어)면 수정 없이 그대로 마쳐라: {shown}.",
            file=sys.stderr,
        )
        sys.exit(2)  # stop 차단 → Claude 가 스스로 검토·보완 후 종료
    sys.exit(0)


if __name__ == "__main__":
    main()
