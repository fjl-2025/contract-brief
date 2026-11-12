# -*- coding: utf-8 -*-
"""
server.py —— 合同要点归纳 本地网页界面
启动：python scripts/server.py   （自动打开浏览器 http://127.0.0.1:8765）
功能：上传/选择合同 → 一键解析切分预提取 → 在线查看报告与产物；
      仅监听本机 127.0.0.1，无外部网络依赖（AI 归纳步骤仍回 AutoClaw 完成）。
"""
import io
import json
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "output")
CONTRACT_DIR = os.path.join(ROOT, "contracts")
PORT = 8765

sys.stdout.reconfigure(encoding="utf-8")

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
}

PAGE = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>合同要点归纳 · contract-brief</title>
<style>
:root{--ink:#1f2430;--muted:#6b7280;--line:#e5e7eb;--brand:#4f46e5;--bg:#f8f9fb;--ok:#047857;--warn:#b45309}
*{box-sizing:border-box}body{font-family:"Microsoft YaHei","PingFang SC",sans-serif;margin:0;background:var(--bg);color:var(--ink)}
.wrap{max-width:880px;margin:0 auto;padding:32px 20px 80px}
h1{font-size:24px;border-bottom:3px solid var(--brand);padding-bottom:10px}
h1 small{font-size:13px;color:var(--muted);font-weight:400;margin-left:10px}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:20px;margin-top:20px;box-shadow:0 1px 3px rgba(0,0,0,.04)}
.card h2{font-size:16px;margin:0 0 14px}
#drop{border:2px dashed #c7d2fe;border-radius:10px;padding:28px;text-align:center;color:var(--muted);cursor:pointer;transition:.15s}
#drop.over{background:#eef2ff;border-color:var(--brand)}
#drop b{color:var(--brand)}
button{background:var(--brand);color:#fff;border:0;border-radius:8px;padding:9px 18px;font-size:14px;cursor:pointer}
button:disabled{background:#c7d2fe;cursor:not-allowed}
button.ghost{background:#eef2ff;color:var(--brand)}
button.small{padding:5px 12px;font-size:13px}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:14px}
#console{display:none;background:#0f172a;color:#e2e8f0;font-family:Consolas,monospace;font-size:12px;border-radius:8px;padding:12px;margin-top:14px;white-space:pre-wrap;max-height:220px;overflow:auto}
.res{margin-top:14px;display:none;border-top:1px dashed var(--line);padding-top:14px}
.tag{display:inline-block;padding:2px 10px;border-radius:10px;font-size:12px}
.tag-ok{background:#d1fae5;color:var(--ok)}.tag-warn{background:#fef3c7;color:var(--warn)}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{border-bottom:1px solid var(--line);padding:9px 8px;text-align:left;vertical-align:top}
th{color:#3730a3;background:#eef2ff;font-weight:600}
a{color:var(--brand);text-decoration:none}a:hover{text-decoration:underline}
.tip{background:#fffbeb;border:1px solid #fde68a;color:#92400e;border-radius:8px;padding:10px 14px;font-size:13px;margin-top:12px;display:none;line-height:1.7}
.muted{color:var(--muted);font-size:12px}
.steps{font-size:13px;color:var(--muted);line-height:1.9;margin:0;padding-left:18px}
</style></head><body><div class="wrap">
<h1>合同要点归纳<small>contract-brief · 本地运行，数据不出本机</small></h1>

<div class="card">
  <h2>① 分析一份合同</h2>
  <div id="drop">把合同文件拖到这里，或 <b>点击选择</b><br><span class="muted">支持 docx / pdf（有文本层）/ txt / md；扫描版 PDF 会提示需回 AutoClaw 转录</span></div>
  <input id="file" type="file" hidden accept=".docx,.pdf,.txt,.md,.png,.jpg,.jpeg">
  <div class="row">
    <button id="go" disabled>开始解析</button>
    <span id="fname" class="muted"></span>
  </div>
  <div id="console"></div>
  <div id="res" class="res"></div>
  <div id="scanTip" class="tip"><b>检测到扫描件：</b>该 PDF 无文本层，机器无法直接解析。请把原文件发给 AutoClaw（对话里拖入），说明「按 contract-brief 扫描件流程转录归纳」，由 AI 渲染逐页识读后合并生成 extract.txt，再回到本界面查看报告。</div>
</div>

<div class="card">
  <h2>② 历史产物 <button class="ghost small" onclick="loadOutputs()">刷新</button></h2>
  <div id="outs">加载中…</div>
  <p class="muted" style="margin-bottom:0">「预提取版」= 机器解析完成，待 AI 归纳；「完整版」= 已含 AI 要点（含风险提示与信息缺口）。</p>
</div>

<div class="card">
  <h2>③ AI 归纳怎么做（最后一步）</h2>
  <ol class="steps">
    <li>解析完成后，在 AutoClaw 对话里说明：<code>按 D:\\tools2\\contract-brief\\prompts\\summary_framework.md 的框架，通读 output\\&lt;合同名&gt;\\extract.txt 归纳要点并填写 summary.json</code>；</li>
    <li>AI 填完 summary.json 后，运行 <code>python scripts/build_report.py output/&lt;合同名&gt;</code>（或让我执行），本页刷新后状态即变为「完整版」。</li>
  </ol>
</div>
</div>
<script>
let file = null;
const drop = document.getElementById('drop'), fi = document.getElementById('file');
drop.onclick = () => fi.click();
fi.onchange = () => pick(fi.files[0]);
drop.ondragover = e => { e.preventDefault(); drop.classList.add('over'); };
drop.ondragleave = () => drop.classList.remove('over');
drop.ondrop = e => { e.preventDefault(); drop.classList.remove('over'); pick(e.dataTransfer.files[0]); };
function pick(f){ if(!f) return; file = f; document.getElementById('fname').textContent = f.name + '（' + (f.size/1024).toFixed(0) + ' KB）'; document.getElementById('go').disabled = false; }
document.getElementById('go').onclick = async () => {
  if(!file) return;
  const go = document.getElementById('go'); go.disabled = true; go.textContent = '解析中…';
  const con = document.getElementById('console'); con.style.display = 'block'; con.textContent = '运行中…';
  try {
    const r = await fetch('/api/analyze?name=' + encodeURIComponent(file.name), {method:'POST', body: await file.arrayBuffer()});
    const j = await r.json();
    con.textContent = j.console || '(无输出)';
    show(j);
  } catch(e) { con.textContent = '请求失败：' + e; }
  go.disabled = false; go.textContent = '开始解析';
  loadOutputs();
};
function show(j){
  const res = document.getElementById('res');
  document.getElementById('scanTip').style.display = j.scanned ? 'block' : 'none';
  let h = '';
  if(j.ok){
    h += '<p><span class="tag tag-ok">解析完成</span> 输出目录：<code>output/' + j.outdir + '</code></p>';
    if(j.report) h += '<p><a href="' + j.report + '" target="_blank"><button>查看要点报告</button></a> <button class="ghost" onclick="openDir(\\'' + j.outdir + '\\')">打开文件夹</button></p>';
  } else {
    h += '<p><span class="tag tag-warn">解析失败</span> ' + (j.error||'') + '</p>';
  }
  if(j.warnings && j.warnings.length) h += '<p class="muted">警告：' + j.warnings.join('；') + '</p>';
  res.innerHTML = h; res.style.display = 'block';
}
function openDir(d){ fetch('/api/open', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({dir:d})}); }
async function loadOutputs(){
  const el = document.getElementById('outs');
  const j = await (await fetch('/api/outputs')).json();
  if(!j.items.length){ el.innerHTML = '<p class="muted">暂无产物。先分析一份合同，或运行 tests 样例。</p>'; return; }
  let h = '<table><tr><th>合同</th><th>状态</th><th>时间</th><th>操作</th></tr>';
  for(const it of j.items){
    h += '<tr><td>' + it.name + '</td><td>' + (it.full ? '<span class="tag tag-ok">完整版</span>' : '<span class="tag tag-warn">预提取版</span>') + (it.scanned ? ' <span class="tag tag-warn">扫描件</span>' : '') + '</td><td class="muted">' + it.time + '</td><td>' +
         (it.report ? '<a href="' + it.report + '" target="_blank">查看报告</a> · ' : '') +
         '<a href="#" onclick="openDir(\\'' + it.name + '\\');return false;">打开文件夹</a></td></tr>';
  }
  el.innerHTML = h + '</table>';
}
loadOutputs();
</script></body></html>"""


def safe_name(name: str) -> str:
    name = os.path.basename(name.replace("\\", "/")).strip()
    name = re.sub(r'[<>:"|?*\x00-\x1f]', "_", name)
    return name or "contract"


def run_pipeline(path: str, outdir: str):
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "run_pipeline.py"), path, "--outdir", outdir],
        capture_output=True, text=True, encoding="utf-8", cwd=ROOT, timeout=300,
    )
    out = (r.stdout or "") + (("\n[stderr] " + r.stderr) if r.stderr.strip() else "")
    return r.returncode, out.strip()


def list_outputs():
    items = []
    if not os.path.isdir(OUT_DIR):
        return items
    for name in sorted(os.listdir(OUT_DIR)):
        d = os.path.join(OUT_DIR, name)
        if not os.path.isdir(d):
            continue
        report = os.path.join(d, "要点报告.html")
        summary = os.path.join(d, "summary.json")
        meta_p = os.path.join(d, "parse_meta.json")
        scanned = False
        if os.path.exists(meta_p):
            try:
                meta = json.loads(io.open(meta_p, encoding="utf-8").read())
                scanned = bool(meta.get("needs_agent_ocr")) or bool(meta.get("scanned_pages")) or meta.get("type") == "pdf-scanned"
            except Exception:
                pass
        items.append({
            "name": name,
            "full": os.path.exists(summary),
            "scanned": scanned,
            "report": f"/output/{name}/要点报告.html" if os.path.exists(report) else "",
            "time": time.strftime("%m-%d %H:%M", time.localtime(os.path.getmtime(d))),
        })
    items.reverse()
    return items


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        elif u.path == "/api/outputs":
            self._json({"items": list_outputs()})
        elif u.path.startswith("/output/"):
            rel = unquote(u.path[len("/output/"):])
            full = os.path.realpath(os.path.join(OUT_DIR, rel))
            if not full.startswith(os.path.realpath(OUT_DIR)) or not os.path.isfile(full):
                self._json({"error": "not found"}, 404)
                return
            ext = os.path.splitext(full)[1].lower()
            with open(full, "rb") as f:
                self._send(200, f.read(), CONTENT_TYPES.get(ext, "application/octet-stream"))
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/analyze":
            qs = parse_qs(u.query)
            name = safe_name(unquote(qs.get("name", ["contract.docx"])[0]))
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > 200 * 1024 * 1024:
                self._json({"ok": False, "error": "文件为空或超过 200MB 上限"}, 400)
                return
            data = self.rfile.read(length)
            os.makedirs(CONTRACT_DIR, exist_ok=True)
            ts = time.strftime("%Y%m%d%H%M%S")
            saved = os.path.join(CONTRACT_DIR, f"{ts}_{name}")
            with open(saved, "wb") as f:
                f.write(data)
            stem = re.sub(rf"{re.escape(ts)}_", "", os.path.splitext(name)[0])
            outdir = os.path.join(OUT_DIR, stem)
            n = 2
            base = outdir
            while os.path.exists(outdir):
                outdir = f"{base}-{n}"
                n += 1
            code, console = run_pipeline(saved, outdir)
            rel_out = os.path.relpath(outdir, OUT_DIR)
            resp = {
                "ok": code == 0,
                "outdir": rel_out,
                "console": console[-4000:],
                "report": f"/output/{rel_out}/要点报告.html" if code == 0 else "",
                "warnings": [],
            }
            meta_p = os.path.join(outdir, "parse_meta.json")
            if os.path.exists(meta_p):
                try:
                    meta = json.loads(io.open(meta_p, encoding="utf-8").read())
                    resp["warnings"] = meta.get("warnings", [])
                    resp["scanned"] = bool(meta.get("needs_agent_ocr")) or bool(meta.get("scanned_pages"))
                except Exception:
                    pass
            self._json(resp)
        elif u.path == "/api/open":
            try:
                ln = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(ln) or b"{}")
                d = os.path.realpath(os.path.join(OUT_DIR, body.get("dir", "")))
                if d.startswith(os.path.realpath(OUT_DIR)) and os.path.isdir(d):
                    os.startfile(d)
                self._json({"ok": True})
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, 500)
        else:
            self._json({"error": "not found"}, 404)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    threading.Timer(0.8, webbrowser.open, [f"http://127.0.0.1:{PORT}"]).start()
    print(f"[server] 合同要点归纳界面已启动：http://127.0.0.1:{PORT}（仅本机可访问，Ctrl+C 退出）")
    server.serve_forever()


if __name__ == "__main__":
    main()
