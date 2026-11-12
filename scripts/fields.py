# -*- coding: utf-8 -*-
"""
fields.py —— 关键要素预提取（正则层）
在切分后的条款里定位：当事人、金额、日期、期限、比例、争议解决、
违约责任、解除终止、保密、知识产权、不可抗力等线索，
输出 fields.json，供 AutoClaw 归纳要点时逐条核对，避免漏项。
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

MONEY = re.compile(
    r"[（(]?[一二三四五六七八九十百千万零]+[）)]?元整|[￥¥$€]\s*[\d,，]+(?:\.\d+)?|[\d,，]+(?:\.\d+)?\s*(?:元|万元|万元整|人民币)"
)
UPPER_MONEY = re.compile(r"[零一二三四五六七八九十百千万]+元整")
DATE = re.compile(r"\d{4}\s*年\s*\d{1,2}\s*月(?:\s*\d{1,2}\s*日)?|\d{4}[-/]\d{1,2}[-/]\d{1,2}")
TERM = re.compile(r"\d+\s*(?:个)?(?:年|月|个月|日|天|个工作日|工作日|小时)")
PERCENT = re.compile(r"\d+(?:\.\d+)?\s*%|百分之[零一二三四五六七八九十点]+")
DISPUTE = re.compile(r"仲裁|诉讼|人民法院|仲裁委员会|管辖|争议解决")
PENALTY = re.compile(r"违约金|赔偿|罚息|滞纳金|定金|保证金|损失")
TERMINATE = re.compile(r"解除|终止|退出")
CONFIDENTIAL = re.compile(r"保密|秘密|披露")
IP = re.compile(r"知识产权|著作权|专利|商标|商业秘密|许可")
FORCE = re.compile(r"不可抗力")
PARTY = re.compile(
    r"(甲方|乙方|丙方|丁方)(?:\s*[（(]([^）)]{1,15})[）)])?\s*[：:]\s*([^\n。；，]{2,60})"
)
NOTICE = re.compile(r"通知|送达|联系方式")


def clip(text: str, start: int, end: int, radius: int = 28) -> str:
    s = max(0, start - radius)
    e = min(len(text), end + radius)
    frag = text[s:e].replace("\n", " ")
    return ("…" if s > 0 else "") + frag + ("…" if e < len(text) else "")


def scan(pattern, text, limit=12):
    out = []
    for m in pattern.finditer(text):
        out.append({"start": m.start(), "value": m.group(0).strip(), "context": clip(text, m.start(), m.end())})
        if len(out) >= limit:
            break
    return out


def clause_body(c):
    """条款正文 + 款项（（一）/1.1 等）一并纳入扫描范围。"""
    parts = [c["text"]]
    parts += [i["text"] for i in c.get("items", [])]
    return "\n".join(p for p in parts if p)


def main():
    ap = argparse.ArgumentParser(description="关键要素预提取")
    ap.add_argument("outdir", help="流水线输出目录（含 clauses.json）")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    data = json.loads((outdir / "clauses.json").read_text(encoding="utf-8"))
    clauses = data["clauses"]

    dims = {
        "金额与价款": [MONEY, UPPER_MONEY],
        "日期": [DATE],
        "期限": [TERM],
        "比例": [PERCENT],
        "争议解决": [DISPUTE],
        "违约责任": [PENALTY],
        "解除与终止": [TERMINATE],
        "保密": [CONFIDENTIAL],
        "知识产权": [IP],
        "不可抗力": [FORCE],
        "通知与送达": [NOTICE],
    }

    fields = {}
    for name, patterns in dims.items():
        hits = []
        for c in clauses:
            tag = f"第{c['no']}条" if c["no"] else "序言"
            body = clause_body(c)
            date_spans = [(m.start(), m.end()) for m in DATE.finditer(body)]
            for p in patterns:
                for m in p.finditer(body):
                    # 期限维度：剔除落在完整日期（如 2026年7月15日）内部的碎片
                    if name == "期限" and any(s <= m.start() < e for s, e in date_spans):
                        continue
                    hits.append(
                        {
                            "clause": tag,
                            "value": m.group(0).strip(),
                            "context": clip(body, m.start(), m.end()),
                        }
                    )
        # 去重：同条款同值只留一处
        seen = set()
        uniq = []
        for h in hits:
            key = (h["clause"], h["value"])
            if key not in seen:
                seen.add(key)
                uniq.append(h)
        fields[name] = uniq[:30]

    parties = []
    seen = set()
    for c in clauses:
        tag = f"第{c['no']}条" if c["no"] else "序言"
        body = clause_body(c)
        for m in PARTY.finditer(body):
            name = (m.group(3) or "").strip()
            if not name or (m.group(1), name) in seen:
                continue
            seen.add((m.group(1), name))
            parties.append(
                {
                    "clause": tag,
                    "role": m.group(1),
                    "qualifier": (m.group(2) or "").strip(),
                    "name": name,
                }
            )
    fields["当事人"] = parties[:12]

    total = sum(len(v) for v in fields.values())
    (outdir / "fields.json").write_text(
        json.dumps(fields, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[fields] 预提取 {total} 条线索，覆盖 {len(fields)} 个维度 -> {outdir / 'fields.json'}")


if __name__ == "__main__":
    main()
