# -*- coding: utf-8 -*-
"""
parse.py —— 合同文本提取
支持：.docx / .pdf / .txt / .md / .png / .jpg / .jpeg
输出：output/<合同名>/extract.txt + parse_meta.json
说明：扫描版 PDF 与图片无法本地 OCR 时，meta 中标记 needs_agent_ocr=True，
      由 AutoClaw（或人工）完成图片识读后补入 extract.txt。
"""
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def _read_text_file(path: Path) -> str:
    data = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def parse_docx(path: Path):
    """python-docx 逐段提取，表格按 | 分隔保留。"""
    import docx

    doc = docx.Document(str(path))
    lines = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            lines.append(text)
    for ti, table in enumerate(doc.tables, 1):
        rows = []
        for row in table.rows:
            cells = [c.text.strip().replace("\n", " ") for c in row.cells]
            rows.append("| " + " | ".join(cells) + " |")
        if rows:
            lines.append(f"[表格{ti}]")
            lines.extend(rows)
    text = "\n".join(lines)
    meta = {"type": "docx", "pages": None, "paragraphs": len(lines)}
    return text, meta


def parse_pdf(path: Path):
    """逐页提取；页带非零 /Rotate 时改用 pypdf（pdfplumber 对旋转页会输出倒序文本），
    其余用 pdfplumber；连续两页无文本判定为扫描件。"""
    warnings = []
    scanned_pages = []
    from pypdf import PdfReader

    rot = {}
    reader = PdfReader(str(path))
    total = len(reader.pages)
    for pg in reader.pages:
        rot[pg.rotation] = rot.get(pg.rotation, 0) + 1
    use_pypdf = any(k not in (0, None) for k in rot)
    if use_pypdf:
        warnings.append(f"检测到页旋转标记{rot}，改用 pypdf 提取以避免旋转页文本倒序")

    if use_pypdf:
        pages_text = [(pg.extract_text() or "").strip() for pg in reader.pages]
        scanned_pages = [i for i, t in enumerate(pages_text, 1) if len(t) < 5]
    else:
        try:
            import pdfplumber

            with pdfplumber.open(str(path)) as pdf:
                pages_text = [(page.extract_text() or "").strip() for page in pdf.pages]
                scanned_pages = [i for i, t in enumerate(pages_text, 1) if len(t) < 5]
        except Exception as exc:  # pdfplumber 失败时退回 pypdf
            warnings.append(f"pdfplumber 解析失败({exc})，改用 pypdf 重试")
            pages_text = [(pg.extract_text() or "").strip() for pg in reader.pages]
            scanned_pages = [i for i, t in enumerate(pages_text, 1) if len(t) < 5]

    text = "\n\n".join(f"[第{i}页]\n{t}" for i, t in enumerate(pages_text, 1) if t)
    if scanned_pages:
        warnings.append(f"以下页面几乎无文本层，疑似扫描件：{scanned_pages}，请用 AutoClaw 识读补全")
    meta = {"type": "pdf", "pages": total, "scanned_pages": scanned_pages, "warnings": warnings}
    return text, meta


def parse_image(path: Path):
    """本地无法 OCR，交给 AutoClaw 图像识读。"""
    meta = {
        "type": "image",
        "pages": 1,
        "needs_agent_ocr": True,
        "warnings": ["图片文件需由 AutoClaw 图像识读提取文字，结果写入 extract.txt 后重跑流水线"],
    }
    return "", meta


def parse_any(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return parse_docx(path)
    if suffix == ".pdf":
        return parse_pdf(path)
    if suffix in (".txt", ".md"):
        return _read_text_file(path), {"type": suffix.lstrip("."), "pages": None}
    if suffix in (".png", ".jpg", ".jpeg", ".webp"):
        return parse_image(path)
    raise SystemExit(f"不支持的格式：{suffix}（支持 docx/pdf/txt/md/图片）")


def main():
    ap = argparse.ArgumentParser(description="合同文本提取")
    ap.add_argument("contract", help="合同文件路径")
    ap.add_argument("--outdir", default=None, help="输出目录，默认 output/<合同名>")
    args = ap.parse_args()

    src = Path(args.contract)
    if not src.exists():
        raise SystemExit(f"文件不存在：{src}")
    outdir = Path(args.outdir) if args.outdir else Path("output") / src.stem
    outdir.mkdir(parents=True, exist_ok=True)

    text, meta = parse_any(src)
    meta.update({"source": str(src), "chars": len(text)})
    (outdir / "extract.txt").write_text(text, encoding="utf-8")
    (outdir / "parse_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[parse] 完成：{len(text)} 字 -> {outdir / 'extract.txt'}")
    for w in meta.get("warnings", []):
        print(f"[parse] 警告：{w}")


if __name__ == "__main__":
    main()
