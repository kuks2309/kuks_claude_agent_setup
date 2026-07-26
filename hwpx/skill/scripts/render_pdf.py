#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HWPX → PDF 렌더 (Linux: LibreOffice + H2Orestart 확장)

렌더 시각 검증 파이프라인의 1단계. 편집한 HWPX 를 LibreOffice 로 열어 PDF 로 저장한다.
Windows + 한컴오피스 환경에서는 이 스크립트 대신 pyhwpx 경로를 사용한다
(references/render-verify.md 부록 참조).

soffice 탐색 순서:
  1. 환경변수 HWPX_SOFFICE
  2. ~/.local/opt/libreoffice/opt/libreoffice*/program/soffice (포터블 설치)
  3. PATH 의 soffice (H2Orestart 가 그 LO 에 설치되어 있어야 함)

전제: H2Orestart 확장이 프로필에 설치되어 있어야 한다 (scripts/setup_env.sh).

사용:
  python3 render_pdf.py <input.hwpx> [output.pdf]
  (output 생략 시 입력과 같은 경로에 .pdf)
"""
import glob
import os
import shutil
import subprocess
import sys

PROFILE_DIR = os.path.expanduser("~/.local/opt/libreoffice/profile")
PROFILE_URI = "file://" + PROFILE_DIR


def find_soffice():
    env = os.environ.get("HWPX_SOFFICE")
    if env and os.path.exists(env):
        return env
    portable = sorted(glob.glob(os.path.expanduser(
        "~/.local/opt/libreoffice/opt/libreoffice*/program/soffice")))
    if portable:
        return portable[-1]
    system = shutil.which("soffice")
    if system:
        return system
    sys.exit("ERROR: soffice 를 찾지 못했다. scripts/setup_env.sh 를 먼저 실행할 것.")


def render(src, pdf=None, timeout=180):
    src = os.path.abspath(src)
    if not os.path.exists(src):
        sys.exit(f"ERROR: 입력 파일 없음: {src}")
    outdir = os.path.dirname(os.path.abspath(pdf)) if pdf else os.path.dirname(src)
    expected = os.path.join(outdir, os.path.splitext(os.path.basename(src))[0] + ".pdf")
    if os.path.exists(expected):
        os.remove(expected)

    soffice = find_soffice()
    cmd = [soffice, f"-env:UserInstallation={PROFILE_URI}",
           "--headless", "--norestore",
           "--convert-to", "pdf", "--outdir", outdir, src]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    ok = os.path.exists(expected) and os.path.getsize(expected) > 0
    if ok and pdf and os.path.abspath(pdf) != expected:
        shutil.move(expected, pdf)
        expected = os.path.abspath(pdf)
    if not ok:
        # 실패 시에만 LO 출력을 노출 (성공 시 H2Orestart 의 무해한 java 로그가 섞임)
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        print("RENDER_FAILED path=", expected)
        return None
    print("RENDER_DONE size=", os.path.getsize(expected), "path=", expected)
    return expected


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    result = render(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    sys.exit(0 if result else 1)
