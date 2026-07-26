#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF → PNG 페이지 이미지 (렌더 시각 검증 파이프라인 2단계)

pdftoppm(poppler-utils) 우선, 없으면 pypdfium2 로 폴백.

사용:
  python3 pdf_to_png.py <input.pdf> [outdir] [--dpi 110]
출력:
  outdir/page-1.png, page-2.png, ... (경로 목록을 stdout 에 출력)
"""
import os
import shutil
import subprocess
import sys


def with_pdftoppm(pdf, outdir, dpi):
    prefix = os.path.join(outdir, "page")
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), pdf, prefix], check=True)
    return sorted(
        os.path.join(outdir, f) for f in os.listdir(outdir)
        if f.startswith("page-") and f.endswith(".png"))


def with_pdfium(pdf, outdir, dpi):
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf)
    paths = []
    for i in range(len(doc)):
        p = os.path.join(outdir, f"page-{i + 1}.png")
        doc[i].render(scale=dpi / 72).to_pil().save(p)
        paths.append(p)
    return paths


def convert(pdf, outdir=None, dpi=110):
    pdf = os.path.abspath(pdf)
    if not os.path.exists(pdf):
        sys.exit(f"ERROR: PDF 없음: {pdf}")
    outdir = outdir or os.path.dirname(pdf)
    os.makedirs(outdir, exist_ok=True)
    if shutil.which("pdftoppm"):
        pages = with_pdftoppm(pdf, outdir, dpi)
    else:
        pages = with_pdfium(pdf, outdir, dpi)
    print(f"PAGES={len(pages)}")
    for p in pages:
        print(p)
    return pages


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dpi = 110
    if "--dpi" in sys.argv:
        dpi = int(sys.argv[sys.argv.index("--dpi") + 1])
        args = [a for a in args if a != str(dpi)]
    if not args:
        sys.exit(__doc__)
    convert(args[0], args[1] if len(args) > 1 else None, dpi)
