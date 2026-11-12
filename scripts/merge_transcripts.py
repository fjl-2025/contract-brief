# -*- coding: utf-8 -*-
"""
merge_transcripts.py —— 合并转录批次文件
用法：python scripts/merge_transcripts.py --transcripts <批次目录> --extract <输出 extract.txt>
把 transcripts/batch_*.txt 按 batch 序号拼接，并按页序整理为 extract.txt。
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PAGE_RE = re.compile(r"【第\s*(\d+)\s*页】")


def main():
    ap = argparse.ArgumentParser(description="合并转录批次")
    ap.add_argument("--transcripts", required=True, help="batch_*.txt 所在目录")
    ap.add_argument("--extract", required=True, help="输出 extract.txt 路径")
    args = ap.parse_args()

    tdir = Path(args.transcripts)
    pages = {}
    bad = []
    for f in sorted(tdir.glob("batch_*.txt")):
        text = f.read_text(encoding="utf-8")
        if not PAGE_RE.search(text):
            bad.append(f.name)
            continue
        # 按【第N页】切分；同页多次出现时内容追加
        parts = PAGE_RE.split(text)
        # parts: [前导, 页号, 内容, 页号, 内容...]
        for i in range(1, len(parts), 2):
            n = int(parts[i])
            body = parts[i + 1].strip()
            if body:
                pages.setdefault(n, []).append(body)
    if bad:
        raise SystemExit(
            "以下批次文件缺少【第N页】标记，需先人工检查补标："
            + ", ".join(bad)
        )
    if not pages:
        raise SystemExit("未从批次文件中解析到任何【第N页】内容")

    out = Path(args.extract)
    out.parent.mkdir(parents=True, exist_ok=True)
    chunks = []
    meta = {"pages": sorted(pages), "chars": 0}
    buf = []
    for n in sorted(pages):
        body = "\n".join(pages[n])
        chunks.append(f"[第{n}页]\n{body}")
        buf.append({"page": n, "chars": len(body)})
    full = "\n\n".join(chunks)
    out.write_text(full, encoding="utf-8")
    meta["chars"] = len(full)
    (out.parent / "transcript_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[merge] 合并 {len(pages)} 页、{len(full)} 字符 -> {out}")


if __name__ == "__main__":
    main()
