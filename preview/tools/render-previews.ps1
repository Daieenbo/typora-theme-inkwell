# 生成预览图
#   - 字体一律用 file:// 绝对路径在页面里显式声明, 并强制赋给正文/标题/代码元素
#   - 这样出图字体是确定的, 不依赖主题 CSS 的层叠结果
# 用法: pwsh -File preview/tools/render-previews.ps1
$ErrorActionPreference = 'Stop'

$toolDir    = Split-Path -Parent $MyInvocation.MyCommand.Path
$previewDir = Split-Path -Parent $toolDir
$themeDir   = Split-Path -Parent $previewDir

$edge = @(
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $edge) { throw '未找到 Edge / Chrome' }

$workDir = Join-Path $env:TEMP 'inkwell-preview-work'
New-Item -ItemType Directory -Force -Path $workDir | Out-Null
$profile = Join-Path $workDir 'profile'

function Url([string]$rel) {
    $abs = (Join-Path $themeDir $rel).Replace('\', '/')
    'file:///' + $abs.Replace(' ', '%20')
}

$uBody  = Url 'inkwell/Cantarell-VF-fixed.otf'
$uHanM  = Url 'inkwell/SourceHanSerifCN-Medium.ttf'
$uHanB  = Url 'inkwell/SourceHanSerifCN-Bold.ttf'
$uMono  = Url 'inkwell/JetBrainsMono-Regular.ttf'

$css = New-Object System.Collections.Generic.List[string]
$css.Add('@font-face{font-family:"PvBody";src:url("' + $uBody + '")}')
$css.Add('@font-face{font-family:"PvHan";src:url("' + $uHanM + '");font-weight:400}')
$css.Add('@font-face{font-family:"PvHan";src:url("' + $uHanB + '");font-weight:700}')
$css.Add('@font-face{font-family:"PvMono";src:url("' + $uMono + '")}')
$css.Add('body,#write{font-family:"PvBody","PvHan",system-ui,sans-serif !important}')
$css.Add('h1,h2,h3,h4,h5,h6,#write table tr th,.md-toc-content{font-family:"PvHan","PvBody",serif !important}')
$css.Add('code,tt,pre,.md-fences,.cm-s-inner,.CodeMirror,.CodeMirror-line,.CodeMirror-code,' +
         '.CodeMirror-sizer,.CodeMirror-lines,.CodeMirror-gutters,.CodeMirror-linenumber,' +
         '.md-meta,.md-comment,pre.md-meta-block,.md-lang,.md-toc,' +
         '[md-inline=link]>.md-content,[md-inline=image]>.md-meta{' +
         'font-family:"PvMono",monospace !important}')
$forceTag = '<style id="preview-font-force">' + ($css -join '') + '</style>'

function Render([string]$pageName, [string]$themeCss, [string]$outLeaf, [int]$w, [int]$h, [string]$scale) {
    $tpl = [System.IO.File]::ReadAllText((Join-Path $previewDir $pageName), [System.Text.Encoding]::UTF8)
    $patched = $tpl -replace '(?<=<link rel="stylesheet" href=")[^"]+(?=">)', "../$themeCss"
    # 强制字体样式放在主题之后, 保证优先级
    $patched = $patched -replace '</head>', ($forceTag + '</head>')

    $tmpPage = Join-Path $previewDir '_render-tmp.html'
    [System.IO.File]::WriteAllText($tmpPage, $patched, (New-Object System.Text.UTF8Encoding $false))

    $out = Join-Path $previewDir $outLeaf
    Remove-Item $out -Force -ErrorAction SilentlyContinue
    $url = 'file:///' + $tmpPage.Replace('\', '/')

    $bat = Join-Path $workDir 'render.bat'
    $logFile = Join-Path $workDir 'render.log'
    $lines = @(
        '@echo off'
        '"' + $edge + '" --headless=new --disable-gpu --hide-scrollbars --no-first-run ^'
        '  --user-data-dir="' + $profile + '" ^'
        '  --window-size=' + $w + ',' + $h + ' ^'
        '  --force-device-scale-factor=' + $scale + ' ^'
        '  --virtual-time-budget=20000 ^'
        '  --screenshot="' + $out + '" ^'
        '  "' + $url + '" > "' + $logFile + '" 2>&1'
    )
    Set-Content -Path $bat -Value $lines -Encoding ASCII
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & cmd.exe /c "`"$bat`"" | Out-Null } catch { }
    $ErrorActionPreference = $prev
    Remove-Item $tmpPage -Force -ErrorAction SilentlyContinue

    if (-not (Test-Path $out) -or (Get-Item $out).Length -lt 10000) {
        if (Test-Path $logFile) { Get-Content $logFile -Tail 8 | ForEach-Object { "    $_" } }
        throw "渲染失败或输出异常: $outLeaf"
    }
    "{0,10}  {1}" -f (Get-Item $out).Length, $outLeaf
}

Render 'preview.html'     'inkwell.css'       'preview-dark.png'  1300 2750 '1.5'
Render 'code-blocks.html' 'inkwell.css'       'code-blocks.png'   1150  900 '2'
Render 'preview.html'     'inkwell-paper.css' 'preview-kraft.png' 1250 2900 '1.3'
Render 'preview.html'     'inkwell-green.css' 'preview-sage.png'  1250 2900 '1.3'

Write-Output 'ok'
