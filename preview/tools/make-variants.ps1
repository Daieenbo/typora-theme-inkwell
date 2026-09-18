# 生成三套配色的小样张并横向拼接成对照图。
#
# 要点:
#   - 每栏按最终展示尺寸直接渲染, 拼接时不做任何缩放 => 文字不糊
#   - 每栏只展示一小块代表性内容 (标题 + 正文 + 行内代码 + 代码块)
#   - 深浅底色由主题 CSS 提供, 硬编码的只有字体加载与少量排版覆盖
#
# 用法: pwsh -File preview/tools/make-variants.ps1
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

$workDir = Join-Path $env:TEMP 'inkwell-variants-work'
Remove-Item $workDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $workDir | Out-Null
$profile = Join-Path $workDir 'profile'

function Url([string]$rel) {
    $abs = (Join-Path $themeDir $rel).Replace('\', '/')
    'file:///' + $abs.Replace(' ', '%20')
}

$uBody = Url 'inkwell/Cantarell-VF-fixed.otf'
$uHanM = Url 'inkwell/SourceHanSerifCN-Medium.ttf'
$uHanB = Url 'inkwell/SourceHanSerifCN-Bold.ttf'
$uMono = Url 'inkwell/JetBrainsMono-Regular.ttf'

$css = New-Object System.Collections.Generic.List[string]
$css.Add('@font-face{font-family:"PvBody";src:url("' + $uBody + '")}')
$css.Add('@font-face{font-family:"PvHan";src:url("' + $uHanM + '");font-weight:400}')
$css.Add('@font-face{font-family:"PvHan";src:url("' + $uHanB + '");font-weight:700}')
$css.Add('@font-face{font-family:"PvMono";src:url("' + $uMono + '")}')
# 小样张用紧凑排版; 背景/前景色一律交给主题 CSS
$css.Add('html,body{margin:0;background:var(--bg-color) !important}')
$css.Add('#write{margin:0 auto !important;padding:14px 16px 16px !important;max-width:100% !important;' +
         'font-size:14px !important;margin-bottom:0 !important}')
$css.Add('body,#write{font-family:"PvBody","PvHan",system-ui,sans-serif !important}')
$css.Add('h1{font-size:1.32rem !important;margin:0 0 .5rem !important;padding:0 !important;' +
         'border-bottom:0 !important;text-align:left !important;font-family:"PvHan","PvBody",serif !important}')
$css.Add('h2{font-size:1.02rem !important;margin:.1em 0 .5em !important;font-family:"PvHan","PvBody",serif !important}')
$css.Add('p{margin:0 0 .45rem !important;line-height:1.5 !important}')
$css.Add('code,tt,pre,.md-fences,.cm-s-inner,.CodeMirror,.CodeMirror-line,.CodeMirror-code,' +
         '.CodeMirror-sizer,.CodeMirror-lines,.CodeMirror-gutters,.CodeMirror-linenumber{font-family:"PvMono",monospace !important}')
$css.Add('.md-fences{padding:0 !important;margin:.25rem 0 0 !important}')
$css.Add('.md-fences .cm-s-inner.CodeMirror{margin:0 !important;padding:.5rem .6rem !important}')
$css.Add('.CodeMirror-line{min-height:0 !important;line-height:1.45 !important}')
$css.Add('.CodeMirror-lines{padding:0 !important}')
$fontCss = '<style id="preview-font-force">' + ($css -join '') + '</style>'

# 每栏只展示一小块: 标题 + 一句正文(含行内代码) + 三行代码块。
# 用数组拼接而非 here-string: 避免 here-string 在不同换行/编码下被解析成一行。
$pageParts = @(
    '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
    '<!-- THEME_CSS -->'
    '__FONT__'
    '</head><body><div id="write">'
    '<h1>Inkwell</h1>'
    '<h2>标题 Heading</h2>'
    '<p>正文与 <code>inline code</code>, <strong>粗体</strong> 与 <a href="#">链接</a>。</p>'
    '<pre class="md-fences" lang="javascript"><div class="CodeMirror cm-s-inner CodeMirror-wrap"><div class="CodeMirror-scroll"><div class="CodeMirror-sizer"><div class="CodeMirror-lines"><div class="CodeMirror-code">' +
    '<pre class="CodeMirror-line"><span role="presentation"><span class="cm-comment">// comment</span></span></pre>' +
    '<pre class="CodeMirror-line"><span role="presentation"><span class="cm-keyword">const</span> <span class="cm-variable">n</span> <span class="cm-operator">=</span> <span class="cm-number">42</span>;</span></pre>' +
    '<pre class="CodeMirror-line"><span role="presentation"><span class="cm-keyword">return</span> <span class="cm-string">"inkwell"</span>;</span></pre>' +
    '</div></div></div></div></div></pre>'
    '</div></body></html>'
)
$pageHtml = $pageParts -join "`n"

$variants = @(
    @{ css = 'inkwell.css';       file = 'v-dark.png' },
    @{ css = 'inkwell-paper.css'; file = 'v-kraft.png' },
    @{ css = 'inkwell-green.css'; file = 'v-sage.png' }
)

$panelW = 760
$panelH = 430
$scale = 2

foreach ($v in $variants) {
    $tag = $v.file.Replace('v-', '').Replace('.png', '')
    # 把主题 CSS 落成每个变体独立的外部样式表 (展开 @import, 字体路径绝对化)。
    # 不内联进 <style>: CSS 里含 '<' 字符, 内联会破坏 HTML 解析, 浏览器会显示错误页。
    $themeCss = [System.IO.File]::ReadAllText((Join-Path $themeDir $v.css), [System.Text.UTF8Encoding]::new($false))
    if ($themeCss -match '@import\s+"inkwell\.css";') {
        $baseCss = [System.IO.File]::ReadAllText((Join-Path $themeDir 'inkwell.css'), [System.Text.UTF8Encoding]::new($false))
        $themeCss = $themeCss -replace '@import\s+"inkwell\.css";', $baseCss
    }
    $themeCss = $themeCss.Replace("url('inkwell/Cantarell-VF-fixed.otf')", "url('$uBody')")
    $themeCss = $themeCss.Replace("url('inkwell/SourceHanSerifCN-Medium.ttf')", "url('$uHanM')")
    $themeCss = $themeCss.Replace("url('inkwell/SourceHanSerifCN-Bold.ttf')", "url('$uHanB')")
    $themeCss = $themeCss.Replace("url('inkwell/JetBrainsMono-Regular.ttf')", "url('$uMono')")
    $cssFile = "theme-$tag.css"
    [System.IO.File]::WriteAllText((Join-Path $workDir $cssFile), $themeCss, (New-Object System.Text.UTF8Encoding $false))
    $html = $pageHtml.Replace('<!-- THEME_CSS -->', ('<link rel="stylesheet" href="' + $cssFile + '">')).Replace('__FONT__', $fontCss)
    $page = Join-Path $workDir "panel-$tag.html"
    [System.IO.File]::WriteAllText($page, $html, (New-Object System.Text.UTF8Encoding $false))
    $out = Join-Path $workDir $v.file
    Remove-Item $out -Force -ErrorAction SilentlyContinue
    $logFile = Join-Path $workDir 'shot.log'
    Remove-Item $logFile -Force -ErrorAction SilentlyContinue
    # 直接调用 Edge: headless 浏览器需要 mojo 命名管道与进程访问权限,
    # 经 cmd/bat 间接调用时该权限更容易被沙箱拒绝。
    $argList = @(
        '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run',
        "--user-data-dir=$profile",
        "--window-size=$panelW,$panelH",
        "--force-device-scale-factor=$scale",
        '--virtual-time-budget=15000',
        "--screenshot=$out",
        "file:///$($page.Replace('\', '/'))"
    )
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        Start-Process -FilePath $edge -ArgumentList $argList -NoNewWindow -Wait `
            -RedirectStandardOutput $logFile -RedirectStandardError "$logFile.err"
    } catch {
        "  Start-Process 异常: $_"
    }
    $ErrorActionPreference = $prev
    if (-not (Test-Path $out)) {
        "  渲染失败: $($v.css)"
        if (Test-Path "$logFile.err") { Get-Content "$logFile.err" -Tail 4 | ForEach-Object { "    $_" } }
        continue
    }
    "  渲染 $($v.css) -> $(Split-Path $out -Leaf) $((Get-Item $out).Length) bytes"
}

# 横向拼接 (纯像素, 不缩放)
$py = Join-Path $toolDir 'stitch-variants.py'
& python $py $workDir (Join-Path $previewDir 'preview-variants.png') 2>&1 | Select-Object -Last 2
Write-Output 'ok'
