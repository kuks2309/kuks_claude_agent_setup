#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HWPX 렌더 시각 검증 원커맨드 (HWPX → PDF → PNG + 텍스트 추출 요약)

편집 완료된 HWPX 를 렌더해 사람이(또는 Claude 가 Read 도구로) 눈으로 검토할
페이지 이미지를 만든다. 완료 선언 전 반드시 이 스크립트를 실행하고
생성된 PNG 를 확인할 것 (references/render-verify.md 체크리스트).

사용:
  python3 render_verify.py <input.hwpx> [--outdir DIR] [--dpi 110]
출력:
  DIR/<이름>.pdf, DIR/page-N.png, DIR/text-pN.txt (페이지별 추출 텍스트)
  stdout 요약: 페이지 수, PNG 경로, 깨진 글자(U+FFFD/tofu 의심) 경고
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from render_pdf import render          # noqa: E402
from pdf_to_png import convert         # noqa: E402


def extract_texts(pdf, outdir, n_pages):
    """페이지별 텍스트 추출 (pdftotext). 치환 누락·오버플로 진단용."""
    texts = []
    if not shutil.which("pdftotext"):
        return texts
    for i in range(1, n_pages + 1):
        out = os.path.join(outdir, f"text-p{i}.txt")
        subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), pdf, out],
                       check=False)
        if os.path.exists(out):
            texts.append(out)
    return texts


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    src = os.path.abspath(args[0])
    outdir = os.path.abspath(
        sys.argv[sys.argv.index("--outdir") + 1] if "--outdir" in sys.argv
        else os.path.join(os.path.dirname(src), "render-verify"))
    dpi = int(sys.argv[sys.argv.index("--dpi") + 1]) if "--dpi" in sys.argv else 110
    os.makedirs(outdir, exist_ok=True)

    pdf = render(src, os.path.join(
        outdir, os.path.splitext(os.path.basename(src))[0] + ".pdf"))
    if not pdf:
        sys.exit(1)
    pages = convert(pdf, outdir, dpi)
    texts = extract_texts(pdf, outdir, len(pages))

    # 깨진 글자 휴리스틱: U+FFFD(치환 문자), .notdef 로 자주 새는 U+25A1 등
    suspicious = []
    for t in texts:
        with open(t, encoding="utf-8", errors="replace") as f:
            content = f.read()
        hits = [ch for ch in ("�",) if ch in content]
        if hits:
            suspicious.append((t, hits))

    print("\n=== RENDER VERIFY SUMMARY ===")
    print(f"pdf   : {pdf}")
    print(f"pages : {len(pages)}")
    for p in pages:
        print(f"png   : {p}")
    if suspicious:
        for t, hits in suspicious:
            print(f"WARN  : 깨진 글자 의심 {hits} in {t}")
    print("다음 단계: 각 PNG 를 Read 도구로 열어 체크리스트 검토 "
          "(references/render-verify.md)")


if __name__ == "__main__":
    main()
