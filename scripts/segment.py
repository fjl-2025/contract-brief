# -*- coding: utf-8 -*-
"""
segment.py —— 合同条款切分
识别「第一章」章级结构、「第X条」条级条款及条款内的款项层级，
输出 clauses.json（结构化）与 outline.md（目录树）。
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CN_NUM = "一二三四五六七八九十百零"
CHAPTER_RE = re.compile(rf"第\s*[{CN_NUM}0-9]+\s*章(?:\s+(.*))?")
PART_RE = re.compile(r"第\s*[一二三四五]+\s*部分|\s*附件\s*\d+")
CLAUSE_RE = re.compile(rf"第\s*[{CN_NUM}0-9]+\s*条")
SUB_RE = re.compile(rf"^（\s*[{CN_NUM}0-9]+\s*）|^\(\s*[{CN_NUM}0-9]+\s*\)|^\d+\.\d+")
ALT_TOP_RE = re.compile(rf"^[{CN_NUM}]+\s*、|^\d+[\.、](?!\d)")


def pick_style(lines):
    """在三种体例中选出现次数最多者为顶层编号。"""
    nonempty = [ln for ln in lines if ln]
    n_clause = sum(1 for ln in nonempty if CLAUSE_RE.match(ln))
    n_alt = sum(1 for ln in nonempty if ALT_TOP_RE.match(ln))
    use_alt = n_alt > n_clause
    return use_alt, n_clause, n_alt


def split_clauses(text: str):
    """按「第X部分/附件N/第X章」分段，段内各自选占优体例切条，避免混合体例串号。"""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # 1) 先按部分/附件/章边界切段
    segments = []  # {header, lines}
    for ln in lines:
        if (CHAPTER_RE.match(ln) or PART_RE.match(ln)) and not CLAUSE_RE.match(ln) and len(ln) <= 45:
            segments.append({"header": ln, "lines": []})
        elif not segments:
            segments.append({"header": "", "lines": [ln]})
        else:
            segments[-1]["lines"].append(ln)

    chapters = []
    clauses = []
    clause_counter = 0

    def is_top(ln, use_alt):
        if not use_alt:
            return CLAUSE_RE.match(ln)
        return ALT_TOP_RE.match(ln)

    for seg in segments:
        if seg["header"]:
            chapters.append({"title": seg["header"][:40], "start_clause": len(clauses)})
        use_alt, _, _ = pick_style(seg["lines"])
        current = None
        for ln in seg["lines"]:
            if is_top(ln, use_alt):
                clause_counter += 1
                body = (CLAUSE_RE.sub("", ln, count=1) if not use_alt else ALT_TOP_RE.sub("", ln, count=1)).strip()
                m_title = re.match(r"([^。；：\n]{2,25}?)[。：：]", body + "：")
                title = m_title.group(1).strip() if m_title and len(m_title.group(1)) <= 25 else ""
                current = {
                    "no": clause_counter,
                    "marker": ln[:14],
                    "title": title,
                    "lines": [body],
                    "items": [],
                }
                clauses.append(current)
            elif current is not None:
                if SUB_RE.match(ln):
                    current["items"].append({"marker": ln[:8], "text": ln})
                else:
                    current["lines"].append(ln)
            else:
                clauses.append({"no": 0, "marker": "序言", "title": "", "lines": [ln], "items": []})
                current = clauses[-1]
    return chapters, clauses


def clause_text(c):
    return "\n".join(c["lines"]).strip()


def build_outline(clauses, chapters):
    out = ["# 合同条款目录", ""]
    ch_idx = 0
    for i, c in enumerate(clauses):
        while ch_idx < len(chapters) and chapters[ch_idx]["start_clause"] == i:
            out.append(f"## {chapters[ch_idx]['title']}")
            out.append("")
            ch_idx += 1
        head = c["marker"] if c["no"] else "序言"
        body = clause_text(c)
        if c["title"]:
            out.append(f"- **{head} {c['title']}**（{len(body)}字）")
        else:
            preview = body[:40].replace("\n", " ")
            out.append(f"- **{head}** {preview}…（{len(body)}字）" if body else f"- **{head}**（空）")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="合同条款切分")
    ap.add_argument("extract", help="extract.txt 路径")
    ap.add_argument("--outdir", default=None, help="输出目录，默认与 extract.txt 同目录")
    args = ap.parse_args()

    extract = Path(args.extract)
    outdir = Path(args.outdir) if args.outdir else extract.parent
    text = extract.read_text(encoding="utf-8")

    chapters, clauses = split_clauses(text)
    for c in clauses:
        c["text"] = clause_text(c)

    (outdir / "clauses.json").write_text(
        json.dumps({"chapters": chapters, "clauses": clauses}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (outdir / "outline.md").write_text(build_outline(clauses, chapters), encoding="utf-8")
    n_items = sum(len(c["items"]) for c in clauses)
    print(f"[segment] 条款 {len(clauses)} 条、款项 {n_items} 项、章节 {len(chapters)} 章 -> {outdir}")


if __name__ == "__main__":
    main()
