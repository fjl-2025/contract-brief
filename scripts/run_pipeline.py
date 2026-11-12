# -*- coding: utf-8 -*-
"""
run_pipeline.py —— 一键流水线
用法：python scripts/run_pipeline.py <合同文件路径>
步骤：parse（提取全文）→ segment（条款切分）→ fields（要素预提取）
      → 生成 summary.template.json（待 AutoClaw 按框架填写）
完成后按提示让 AutoClaw 通读合同并填写 summary.json，再生成最终报告。
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).parent


def run(script, *args):
    r = subprocess.run([sys.executable, str(HERE / script), *[str(a) for a in args]],
                       capture_output=True, text=True, encoding="utf-8")
    out = (r.stdout or "").strip()
    if out:
        print(out)
    if r.returncode != 0:
        print((r.stderr or "").strip(), file=sys.stderr)
        raise SystemExit(f"{script} 执行失败")


def main():
    ap = argparse.ArgumentParser(description="合同要点归纳流水线")
    ap.add_argument("contract", help="合同文件路径（docx/pdf/txt/md/图片）")
    ap.add_argument("--outdir", default=None, help="输出目录，默认 output/<合同名>")
    args = ap.parse_args()

    src = Path(args.contract)
    if not src.exists():
        raise SystemExit(f"文件不存在：{src}")
    outdir = Path(args.outdir) if args.outdir else Path("output") / src.stem
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"== 合同要点归纳流水线 ==\n输入：{src}\n输出：{outdir}\n")
    run("parse.py", src, "--outdir", outdir)
    run("segment.py", outdir / "extract.txt", "--outdir", outdir)
    run("fields.py", outdir)

    # 生成待填写的 summary 模板
    tpl_path = HERE.parent / "prompts" / "summary_template.json"
    if tpl_path.exists():
        shutil.copy(tpl_path, outdir / "summary.template.json")
        print(f"[template] 已生成待填模板 -> {outdir / 'summary.template.json'}")

    # 预提取版报告（可先睹为快）
    run("build_report.py", outdir)

    print(
        "\n下一步（由 AutoClaw 完成）：\n"
        f"  1. 通读 {outdir / 'extract.txt'} 与 {outdir / 'clauses.json'}；\n"
        "  2. 按 prompts/summary_framework.md 的框架填写 summary.json（以 summary.template.json 为底）；\n"
        f"  3. 运行 python scripts/build_report.py {outdir} 生成完整版要点报告。"
    )


if __name__ == "__main__":
    main()
