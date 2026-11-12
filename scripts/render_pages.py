# -*- coding: utf-8 -*-
"""
render_pages.py —— 扫描版 PDF 转图片
用法：python scripts/render_pages.py <合同.pdf> --outdir <页图目录> [--dpi 150]
把每页渲染为 JPEG，供 AutoClaw 图像识读转录（parse.py 标记 needs_agent_ocr 后使用）。
"""
import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# 优先用 pypdfium2（随 pdfplumber 安装），否则回退 PyMuPDF
try:
    import pypdfium2 as pdfium

    BACKEND = "pypdfium2"
except ImportError:
    import fitz

    BACKEND = "fitz"


def main():
    ap = argparse.ArgumentParser(description="PDF 页渲染为图片")
    ap.add_argument("pdf", help="PDF 文件路径")
    ap.add_argument("--outdir", required=True, help="页图输出目录")
    ap.add_argument("--dpi", type=int, default=150, help="渲染 DPI，默认 150")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    print(f"[render] 渲染后端：{BACKEND}")
    if BACKEND == "pypdfium2":
        pdf = pdfium.PdfDocument(args.pdf)
        total = len(pdf)
        for i in range(len(pdf)):
            page = pdf[i]
            bitmap = page.render(scale=args.dpi / 72)
            img = bitmap.to_pil()
            img.save(str(outdir / f"page_{i + 1:03d}.jpg"), "JPEG", quality=82)
            page.close()
            if (i + 1) % 20 == 0:
                print(f"  已渲染 {i + 1} 页…")
        pdf.close()
    else:
        doc = fitz.open(args.pdf)
        total = len(doc)
        for i, page in enumerate(doc, 1):
            pix = page.get_pixmap(dpi=args.dpi)
            pix.save(str(outdir / f"page_{i:03d}.jpg"))
            if i % 20 == 0:
                print(f"  已渲染 {i} 页…")
    size_mb = sum(f.stat().st_size for f in outdir.glob("*.jpg")) / 1024 / 1024
    print(f"[render] 共渲染 {total} 页 -> {outdir}（{size_mb:.1f} MB）")


if __name__ == "__main__":
    main()
