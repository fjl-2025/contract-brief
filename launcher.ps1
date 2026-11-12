param([string]$ContractPath = "")
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[错误] 未检测到 Python，请先安装 Python 3.10+ 并勾选 Add to PATH。" -ForegroundColor Red
    Read-Host "回车退出" | Out-Null
    exit 1
}

function Invoke-Pipeline([string]$file) {
    Write-Host ""
    Write-Host "收到合同文件: $(Split-Path -Leaf $file)"
    Write-Host ""
    & python "scripts\run_pipeline.py" $file
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "机器解析完成。产物见 output\ 文件夹。" -ForegroundColor Green
        Write-Host "下一步：回到 AutoClaw 对话，把 output\ 下的合同目录发给它，"
        Write-Host "按 prompts\summary_framework.md 通读归纳并生成完整报告。"
        Start-Process explorer.exe (Join-Path $root "output")
    } else {
        Write-Host ""
        Write-Host "解析失败，请检查文件格式是否为 docx/pdf/txt/md/图片。" -ForegroundColor Yellow
    }
}

if ($ContractPath -ne "") {
    Invoke-Pipeline $ContractPath | Out-Null
    Read-Host "完成，回车关闭" | Out-Null
    exit 0
}

while ($true) {
    Clear-Host
    Write-Host "=================================================="
    Write-Host "   合同要点归纳  contract-brief"
    Write-Host "=================================================="
    Write-Host "   项目目录: $root"
    Write-Host "--------------------------------------------------"
    Write-Host "   [1] 分析合同（输入或拖入文件路径）"
    Write-Host "   [2] 一键安装/更新依赖（首次使用先选 2）"
    Write-Host "   [3] 打开项目文件夹"
    Write-Host "   [4] 打开使用说明 README.md"
    Write-Host "   [0] 退出"
    Write-Host "--------------------------------------------------"
    $c = Read-Host "请输入数字后回车"
    switch ($c) {
        "1" { $f = Read-Host "请输入/拖入合同文件路径"; if ($f) { $f = $f.Trim('"'); Invoke-Pipeline $f | Out-Null; Read-Host "回车返回菜单" | Out-Null } }
        "2" { & python -m pip install python-docx pdfplumber pypdf pymupdf; Read-Host "依赖处理完成，回车返回" | Out-Null }
        "3" { Start-Process explorer.exe $root }
        "4" { Start-Process notepad.exe (Join-Path $root "README.md") }
        "0" { exit 0 }
    }
}
