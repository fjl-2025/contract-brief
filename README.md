# 合同要点归纳（contract-brief）

用 AutoClaw 完成「通读合同 → 归纳要点 → 输出可核对报告」的完整工作流。
本项目为 [AutoClaw 创造力挑战第六期 · 法律实践赛道](docs/challenge-requirements.md) 的参赛工程。

> **隐私原则：真实合同不入库。** 本仓库只含代码与虚构样例；真实合同放在本地 `contracts/`（已被 .gitignore 忽略），真实合同的分析结果输出到项目外的本地归档目录。发布仓库前请核对 .gitignore 与 output/ 目录。

## 项目做三件事

1. **机器解析**：文本型合同（docx/pdf/txt）自动提取条款并预提取金额、日期、违约金等线索；扫描版 PDF 走「渲染成图 → AI 图像识读逐页转录 → 按页合并」流水线；自动规避带旋转标记 PDF 的文本倒序问题；
2. **AI 归纳**：AutoClaw 通读全文，按 [summary_framework.md](prompts/summary_framework.md) 的 14 个维度归纳要点，每个要点附条款出处，金额大小写核对、风险提示讲后果、信息缺口必填；
3. **双格式报告**：生成 `要点报告.md` 与自包含 `要点报告.html`，含风险提示与信息缺口清单。

## 目录结构

```
contract-brief/
├── contracts/          # 本地放入待分析合同（已被 .gitignore 忽略，不入库）
├── output/             # 分析产物（仅虚构样例入库，真实产物本地归档）
│   └── sample_contract/    # 虚构样例的完整演示（docx 全流程）
├── scripts/
│   ├── run_pipeline.py     # 一键流水线：解析 → 切分 → 预提取 → 报告
│   ├── parse.py            # 文本提取（docx/pdf/txt/md/图片；旋转 PDF 自动换 pypdf）
│   ├── render_pages.py     # 扫描版 PDF → 逐页 JPEG（供图像识读）
│   ├── merge_transcripts.py# 按页合并转录批次 → extract.txt
│   ├── segment.py          # 条款切分（自动识别 第X条 / 一、/ 1. 混合体例）
│   ├── fields.py           # 金额、日期、违约、争议解决等线索预提取
│   └── build_report.py     # 组装要点报告（Markdown + 自包含 HTML）
├── prompts/
│   ├── summary_framework.md   # AI 归纳框架与填写规则（14 维度）
│   └── summary_template.json  # summary.json 模板
├── tests/
│   ├── make_sample.py         # 生成虚构测试合同
│   └── sample_contract.docx   # 虚构样例（北京示例科技 × 上海演示信息）
├── docs/challenge-requirements.md  # 挑战赛要求存档
├── SUBMISSION.md              # 参赛投稿指南（四要素对照 + 发布步骤）
└── README.md
```

## 快速开始

### 方式一：图形界面（推荐）

双击桌面快捷方式「contract-brief 合同要点归纳」，或双击项目根目录的 **`打开界面.bat`** → 自动打开浏览器（http://127.0.0.1:8765，仅本机可访问）：

- 拖入/选择合同文件 → 点「开始解析」→ 自动完成解析→切分→预提取→报告，页面直接可看；
- 「历史产物」列表可随时查看每份合同的报告与状态（预提取版/完整版）；
- 扫描件 PDF 会提示需回 AutoClaw 走转录流程；
- 最后一步 AI 归纳见页面「③ AI 归纳怎么做」。

### 方式二：命令行 / 拖拽

双击 **`运行合同要点归纳.bat`**（或把合同文件拖到它图标上）用控制台菜单运行。

### 方式三：命令行直接跑


```powershell
# 在项目根目录 contract-brief 下
python scripts/run_pipeline.py contracts/你的合同.docx
# 然后让 AutoClaw 按 prompts/summary_framework.md 通读合同，
# 把 output/<合同名>/summary.template.json 填好另存为 summary.json，再：
python scripts/build_report.py output/<合同名>
```

### 附：扫描版 PDF（无文本层）流程

```powershell
python scripts/parse.py contracts/扫描合同.pdf --outdir output/扫描合同      # 会标记 needs_agent_ocr
python scripts/render_pages.py contracts/扫描合同.pdf --outdir output/扫描合同/pages --dpi 160
# 由 AutoClaw 分批图像识读逐页转录为 transcripts/batch_*.txt（每页一行【第N页】标记），
# 再按页合并并继续切分：
python scripts/merge_transcripts.py --transcripts output/扫描合同/transcripts --extract output/扫描合同/extract.txt
python scripts/segment.py output/扫描合同/extract.txt --outdir output/扫描合同
python scripts/fields.py output/扫描合同
# 最后填 summary.json → build_report.py（同场景 A 第 2 步）
```

### 产物（`output/<合同名>/`）

| 文件 | 说明 |
| --- | --- |
| extract.txt | 合同全文纯文本 |
| clauses.json / outline.md | 条款结构与目录 |
| fields.json | 正则预提取线索（人工抽查核对用） |
| summary.json | AI 归纳要点（含条款出处） |
| **要点报告.md / 要点报告.html** | 最终交付物 |

依赖：`pip install python-docx pdfplumber pypdf pymupdf`（缺哪个装哪个；扫描件渲染用 pymupdf 或随 pdfplumber 附带的 pypdfium2）。

## 隐私与合规

- 真实合同文件只放本地 `contracts/`，`.gitignore` 已忽略；**发布仓库前务必确认未混入**。
- 真实合同的分析结果（extract/clauses/fields/summary/报告）输出后移入项目外归档目录（本项目约定：`../真实合同分析归档-勿上传/`）。
- 对外展示一律使用 `tests/sample_contract.docx`（虚构主体：北京示例科技有限公司 × 上海演示信息技术有限公司）或自行脱敏的材料。
- 截图发布前检查：文件名、当事人、金额、信用代码、印章。

## 参赛对照（作品内容要求四要素）

| 挑战赛要求 | 本项目的对应产物 |
| --- | --- |
| ① 任务背景 | 本 README + `docs/challenge-requirements.md`：合同要点人工归纳慢、漏项、难核对，报告用于签约决策与法务初筛 |
| ② 使用过程 | `run_pipeline.py` 机器解析步骤 + AutoClaw 按 `summary_framework.md` 通读归纳的对话记录（截图留存） |
| ③ 实际成果 | `要点报告.md` / `要点报告.html`（发布时附关键截图与本仓库链接） |
| ④ 使用经验 | 见 [SUBMISSION.md](SUBMISSION.md) 的经验清单；发布时补上人工核对中发现的问题 |

## 使用经验（投稿时可直接引用并补充）

- **人工核对点**：AI 归纳的金额、日期必须回原文复核（大小写一致性、违约金比例）；`fields.json` 的正则线索就是人工抽查清单。
- **可借鉴的方法**：先机器切分再通读；要点引用条款号；14 维度框架防漏项；「信息缺口」单列交接人工；扫描件先渲染再分批转录，进度可控。
- **待改进**：扫描件转录仍需逐页图像识读（耗时与积分成本）；复杂表格还原建议对照原件；OCR 文本层质量差时会误切条款，需人工抽检 outline.md。

## 投稿清单（法律实践赛道）

- [ ] 关注官方账号：小红书「智谱AutoClaw」/ 微信公众号「AutoGLM」/ X @AutoClawAIer
- [ ] 在社媒发布原创案例（小红书文末带 #AutoClaw #智谱AutoClaw），内容覆盖四要素
- [ ] 提交投稿表：手机号、赛道（法律实践）、平台、账号名、社媒链接、作品链接（本仓库/报告链接）
- [ ] 注意：每人每平台每赛道限 1 篇；活动期 2026.11.4—11.20

## 声明

报告要点为 AI 归纳结果，仅供内部参考；签署或对外使用前请逐条核对合同原文。
