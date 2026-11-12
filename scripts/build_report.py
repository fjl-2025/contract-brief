# -*- coding: utf-8 -*-
"""
build_report.py —— 组装合同要点报告
输入：output/<合同名>/ 下的 parse_meta.json / clauses.json / fields.json / summary.json
输出：要点报告.md 与 要点报告.html（自包含，可直接发送或发布）
summary.json 由 AutoClaw 依据 prompts/summary_framework.md 填写；
若尚未填写，本脚本仅输出「预提取要素版」报告并在开头标注状态。
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DIM_ORDER = [
    "basic",
    "parties",
    "subject",
    "payment",
    "term",
    "obligations",
    "acceptance",
    "ip_confidential",
    "breach",
    "termination",
    "dispute",
    "others",
    "risks",
    "gaps",
]
DIM_LABELS = {
    "basic": "合同基本信息",
    "parties": "合同主体",
    "subject": "标的与范围",
    "payment": "价款与支付",
    "term": "履行期限与地点",
    "obligations": "双方主要义务",
    "acceptance": "交付与验收",
    "ip_confidential": "知识产权与保密",
    "breach": "违约责任",
    "termination": "变更、解除与终止",
    "dispute": "争议解决",
    "others": "其他重要条款",
    "risks": "风险提示",
    "gaps": "信息缺口（待人工确认）",
}

HTML_CSS = """
:root { --ink:#1f2430; --muted:#6b7280; --line:#e5e7eb; --brand:#4f46e5; --bg:#f8f9fb; --warn:#b45309; --ok:#047857; }
* { box-sizing: border-box; }
body { font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif; color: var(--ink); margin: 0; background: var(--bg); }
.wrap { max-width: 860px; margin: 0 auto; padding: 40px 24px 80px; background: #fff; }
h1 { font-size: 26px; border-bottom: 3px solid var(--brand); padding-bottom: 12px; }
h2 { font-size: 19px; margin-top: 36px; padding-left: 10px; border-left: 4px solid var(--brand); }
h3 { font-size: 16px; }
table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 14px; }
th, td { border: 1px solid var(--line); padding: 8px 10px; text-align: left; vertical-align: top; }
th { background: #eef2ff; color: #3730a3; }
.meta { color: var(--muted); font-size: 13px; line-height: 1.8; }
.tag { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 12px; margin-right: 6px; }
.tag-warn { background: #fef3c7; color: var(--warn); }
.tag-ok { background: #d1fae5; color: var(--ok); }
blockquote { margin: 6px 0; padding: 6px 12px; border-left: 3px solid var(--line); color: var(--muted); font-size: 13px; background: #fafafa; }
.footer { margin-top: 48px; padding-top: 16px; border-top: 1px dashed var(--line); color: var(--muted); font-size: 12px; }
ul { padding-left: 22px; } li { margin: 4px 0; line-height: 1.7; }
code { background: #f3f4f6; padding: 1px 5px; border-radius: 4px; font-size: 13px; }
"""


def esc(s):
    return (
        str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def md_points(section):
    lines = []
    for p in section.get("points", []):
        lines.append(f"- {p}")
    for ev in section.get("evidence", []):
        lines.append(f"  - 依据：{ev.get('clause','')} 「{ev.get('quote','')}」")
    return "\n".join(lines)


def html_section(key, section):
    pts = "".join(f"<li>{esc(p)}</li>" for p in section.get("points", []))
    evs = "".join(
        f"<blockquote>{esc(ev.get('clause',''))}「{esc(ev.get('quote',''))}」</blockquote>"
        for ev in section.get("evidence", [])
    )
    return f"<h2>{esc(DIM_LABELS[key])}</h2><ul>{pts}</ul>{evs}"


def build_fields_tables(fields):
    rows_md = []
    rows_html = []
    for dim, items in fields.items():
        if not items:
            continue

        def show(i):
            if "value" in i:
                return f"{i['value']}（{i['clause']}）"
            return f"{i.get('role','')}：{i.get('name','')}（{i['clause']}）"

        values = "; ".join(show(i) for i in items[:8])
        more = f" 等共{len(items)}处" if len(items) > 8 else ""
        rows_md.append(f"| {dim} | {values}{more} |")
        cells = "".join(f"<td>{esc(show(i))}</td>" for i in items[:8])
        rows_html.append(f"<tr><td>{esc(dim)}</td><td>{cells}{esc('等共%d处' % len(items)) if len(items)>8 else ''}</td></tr>")
    md = (
        "| 维度 | 提取线索 |\n| --- | --- |\n" + "\n".join(rows_md)
        if rows_md
        else "（无预提取结果）"
    )
    html = (
        "<table><tr><th>维度</th><th>提取线索（最多展示8处）</th></tr>"
        + "".join(rows_html)
        + "</table>"
        if rows_html
        else "<p>（无预提取结果）</p>"
    )
    return md, html


def main():
    ap = argparse.ArgumentParser(description="组装要点报告")
    ap.add_argument("outdir", help="流水线输出目录")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    meta = json.loads((outdir / "parse_meta.json").read_text(encoding="utf-8"))
    fields = json.loads((outdir / "fields.json").read_text(encoding="utf-8"))
    clauses = json.loads((outdir / "clauses.json").read_text(encoding="utf-8"))["clauses"]
    summary_path = outdir / "summary.json"
    has_summary = summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if has_summary else {}

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    def _basic_title():
        b = summary.get("basic", {})
        if b.get("title"):
            return b["title"]
        for p in b.get("points", []):
            if isinstance(p, str) and p.startswith("合同名称"):
                return p.split("：", 1)[-1].split("（")[0].strip()
        return Path(meta["source"]).stem

    title = _basic_title()

    # ---------- Markdown ----------
    md = [
        f"# 合同要点报告：{title}",
        "",
        f"> 生成时间：{now}｜来源：{meta['source']}｜全文 {meta.get('chars', 0)} 字"
        + (f"｜共 {meta.get('pages')} 页" if meta.get("pages") else ""),
        "",
    ]
    if not has_summary:
        md.insert(1, "**[状态：预提取版]** summary.json 尚未由 AutoClaw 填写，本报告仅含正则预提取线索，非完整要点归纳。")
        md.insert(2, "")
    if has_summary:
        md.append("## 一、合同基本信息")
        md.append(md_points(summary.get("basic", {})) or "（未填写）")
        md.append("")
        md.append("## 二、核心要点（按维度）")
        for key in DIM_ORDER[1:-2]:
            sec = summary.get(key)
            if not sec:
                continue
            md.append(f"### {DIM_LABELS[key]}")
            md.append(md_points(sec))
            md.append("")
        md.append("## 三、风险提示")
        md.append(md_points(summary.get("risks", {})) or "（未填写）")
        md.append("")
        md.append("## 四、信息缺口（待人工确认）")
        md.append(md_points(summary.get("gaps", {})) or "（未填写）")
        md.append("")
    md.append("## " + ("五" if has_summary else "一") + "、正则预提取线索（供核对）")
    md.append(build_fields_tables(fields)[0])
    md.append("")
    md.append("## 条款目录")
    md.append(f"共 {len(clauses)} 条（详见 outline.md）")
    md.append("")
    md.append("---")
    md.append("*本报告由 AutoClaw 流水线生成，要点为 AI 归纳结果；签署或对外使用前，请逐条核对合同原文。*")
    (outdir / "要点报告.md").write_text("\n".join(md), encoding="utf-8")

    # ---------- HTML ----------
    body = [f"<h1>{esc(title)}</h1>"]
    body.append(
        f"<p class='meta'>生成时间：{now}｜来源：{esc(meta['source'])}｜全文 {meta.get('chars',0)} 字</p>"
    )
    if not has_summary:
        body.append("<p><span class='tag tag-warn'>预提取版</span> summary.json 尚未填写，以下仅含正则线索。</p>")
    else:
        body.append("<p><span class='tag tag-ok'>完整版</span> 含 AI 归纳要点，签署前请人工核对原文。</p>")
        body.append(html_section("basic", summary.get("basic", {})))
        for key in DIM_ORDER[1:-2]:
            sec = summary.get(key)
            if sec:
                body.append(html_section(key, sec))
        body.append(html_section("risks", summary.get("risks", {})))
        body.append(html_section("gaps", summary.get("gaps", {})))
    fmd, fhtml = build_fields_tables(fields)
    body.append(f"<h2>正则预提取线索</h2>{fhtml}")
    body.append(f"<p>条款目录：共 {len(clauses)} 条（见 outline.md）。</p>")
    body.append(
        "<p class='footer'>本报告由 AutoClaw 流水线生成，要点为 AI 归纳结果；签署或对外使用前，请逐条核对合同原文。</p>"
    )
    html = (
        "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{esc(title)} · 合同要点报告</title><style>{HTML_CSS}</style></head>"
        f"<body><div class='wrap'>{''.join(body)}</div></body></html>"
    )
    (outdir / "要点报告.html").write_text(html, encoding="utf-8")
    print(f"[report] 已生成：{outdir / '要点报告.md'} 与 {outdir / '要点报告.html'}（{'完整版' if has_summary else '预提取版'}）")


if __name__ == "__main__":
    main()
