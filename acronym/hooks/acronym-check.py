#!/usr/bin/env python3
"""Stop 훅 — 직전 답변에 미병기 영어 약자가 있으면 차단·재작성 요구.

규칙: 영어 약자(대문자 2자 이상)는 첫 등장 시 '약어(영어 단어)' 형식이어야 한다.
화이트리스트·코드·URL·형식 리터럴은 예외. 무한 루프는 stop_hook_active 로 방지.
"""
import json
import re
import sys

# 약자로 보여도 병기 불필요한 토큰 (예외). 필요 시 추가한다.
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


def find_violations(text):
    # 코드블록 / 인라인 코드 / URL 제거 (예외 영역)
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    out = []
    seen = set()
    for m in re.finditer(r"\b([A-Z]{2,}[0-9]*)\b", text):
        tok = m.group(1)
        if tok in WHITELIST or tok in seen:
            continue
        if text[m.end():m.end() + 1] == "(":  # 바로 뒤 ( → 병기됨
            continue
        seen.add(tok)
        out.append(tok)
    return out


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)
    if data.get("stop_hook_active"):  # 재작성 루프 방지
        sys.exit(0)
    text = last_assistant_text(data.get("transcript_path", ""))
    if not text:
        sys.exit(0)
    viols = find_violations(text)
    if viols:
        shown = ", ".join(viols[:10])
        print(
            f"영어 약자 미병기: {shown}. '약어(영어 단어)' 형식으로 고쳐 다시 답하라 "
            f"(예외: 코드·파일명·URL·고유명사·형식 리터럴).",
            file=sys.stderr,
        )
        sys.exit(2)  # stop 차단 → Claude 가 이어서 수정
    sys.exit(0)


if __name__ == "__main__":
    main()
