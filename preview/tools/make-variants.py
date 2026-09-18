# 用已渲染好的三张变体预览, 拼成一张并排对照图 (纯像素拼接, 不依赖 iframe)
import os
import re
import struct
import subprocess
import zlib

BASE = os.path.dirname(os.path.abspath(__file__))
THEME = os.path.dirname(BASE)
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PROFILE = os.path.join(BASE, '_work', 'profile')

MONO = {
    'a': ['01110', '10001', '11111', '10001', '10001'],
    'd': ['01110', '10001', '10001', '10001', '01110'],
    'e': ['01110', '10001', '11111', '10000', '01110'],
    'f': ['00110', '01000', '11100', '01000', '01000'],
    'g': ['01110', '10001', '01111', '00001', '01110'],
    'i': ['11111', '00100', '00100', '00100', '11111'],
    'k': ['10001', '10010', '11100', '10010', '10001'],
    'l': ['11100', '00100', '00100', '00100', '11111'],
    'n': ['10110', '11001', '10001', '10001', '10001'],
    'p': ['11110', '10001', '11110', '10000', '10000'],
    'r': ['10110', '11001', '10000', '10000', '10000'],
    's': ['01111', '10000', '01110', '00001', '11110'],
    't': ['01000', '11100', '01000', '01001', '00110'],
    'u': ['10001', '10001', '10001', '10011', '01101'],
    'w': ['10001', '10001', '10101', '10101', '01010'],
    'M': ['10001', '11011', '10101', '10001', '10001'],
    '_': ['00000', '00000', '00000', '00000', '11111'],
    '-': ['00000', '00000', '11111', '00000', '00000'],
    '|': ['00100', '00100', '00100', '00100', '00100'],
    '(': ['00110', '01000', '01000', '01000', '00110'],
    ')': ['01100', '00010', '00010', '00010', '01100'],
    ' ': ['00000', '00000', '00000', '00000', '00000'],
}

PANELS = [
    ('inkwell.css', 'inkwell  |  dark', (0x20, 0x24, 0x2b), (0xe8, 0xec, 0xf2)),
    ('inkwell-paper.css', 'inkwell-paper  |  kraft', (0xf1, 0xf1, 0xd6), (0x3b, 0x3b, 0x2c)),
    ('inkwell-green.css', 'inkwell-green  |  sage', (0xee, 0xf3, 0xe9), (0x34, 0x3b, 0x30)),
]


def url(rel):
    return 'file:///' + os.path.join(THEME, rel).replace('\\', '/').replace(' ', '%20')


# 与 render-previews.ps1 一致: 页面内用 file:// 绝对路径声明字体并强制生效
FORCE = ('<style>'
         '@font-face{font-family:"PvBody";src:url("' + url('inkwell/Cantarell-VF-fixed.otf') + '")}'
         '@font-face{font-family:"PvHan";src:url("' + url('inkwell/SourceHanSerifCN-Medium.ttf') + '");font-weight:400}'
         '@font-face{font-family:"PvHan";src:url("' + url('inkwell/SourceHanSerifCN-Bold.ttf') + '");font-weight:700}'
         '@font-face{font-family:"PvMono";src:url("' + url('inkwell/JetBrainsMono-Regular.ttf') + '")}'
         'body,#write{font-family:"PvBody","PvHan",system-ui,sans-serif !important}'
         'h1,h2,h3,h4,h5,h6{font-family:"PvHan","PvBody",serif !important}'
         'code,tt,pre,.md-fences,.cm-s-inner,.CodeMirror,.CodeMirror-line,.CodeMirror-code,'
         '.CodeMirror-sizer,.CodeMirror-lines,.CodeMirror-gutters,.CodeMirror-linenumber{'
         'font-family:"PvMono",monospace !important}'
         '</style>')

PAGE = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<link rel="stylesheet" href="../__THEME_CSS__">""" + FORCE + """
<style>html,body{margin:0;background:var(--bg-color)}
#write{margin:0 auto;padding:16px 20px;font-size:15px;margin-bottom:0}
h1{font-size:1.5rem !important;margin:0 0 .7rem !important}
h2{font-size:1.15rem !important;margin:.5em 0 !important}</style>
</head><body><div id="write">
<h1>Inkwell</h1>
<p>同一套版式, 三种纸面。中文思源宋体, latin Cantarell。</p>
<h2>标题 Heading</h2>
<p>正文与 <code>inline code</code> 混排, <strong>粗体</strong> 与 <a href="#">链接</a>。</p>
<ul><li>列表项 <em>emphasis</em></li></ul>
<pre class="md-fences" lang="javascript"><div class="CodeMirror cm-s-inner CodeMirror-wrap"><div class="CodeMirror-scroll"><div class="CodeMirror-sizer"><div class="CodeMirror-lines"><div class="CodeMirror-code"><pre class="CodeMirror-line"><span role="presentation"><span class="cm-comment">// comment 2 modes</span></span></pre><pre class="CodeMirror-line"><span role="presentation"><span class="cm-keyword">const</span> <span class="cm-variable">n</span> <span class="cm-operator">=</span> <span class="cm-number">42</span>;</span></pre><pre class="CodeMirror-line"><span role="presentation"><span class="cm-keyword">return</span> <span class="cm-string">"inkwell"</span>;</span></pre></div></div></div></div></div></pre>
</div></body></html>"""

W, H, LABEL_H = 560, 470, 34


def read_png(path):
    data = open(path, 'rb').read()
    pos, idat = 8, b''
    while pos < len(data):
        ln = struct.unpack('>I', data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        if typ == b'IHDR':
            w, h, bitd, ctype = struct.unpack('>IIBB', data[pos + 8:pos + 18])
        elif typ == b'IDAT':
            idat += data[pos + 8:pos + 8 + ln]
        pos += 12 + ln
    raw = zlib.decompress(idat)
    ch = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
    bpp = ch * (bitd // 8)
    stride = w * bpp
    out, prev, p = bytearray(), bytearray(stride), 0
    for _ in range(h):
        ft = raw[p]; p += 1
        line = bytearray(raw[p:p + stride]); p += stride
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            x = line[i]
            if ft == 1:
                x = (x + a) & 0xFF
            elif ft == 2:
                x = (x + b) & 0xFF
            elif ft == 3:
                x = (x + (a + b) // 2) & 0xFF
            elif ft == 4:
                pp = a + b - c
                pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                x = (x + pr) & 0xFF
            line[i] = x
        out += line
        prev = line
    return w, h, bpp, out


def write_png(path, w, h, rows):
    raw = b''.join(b'\x00' + bytes(r) for r in rows)
    comp = zlib.compress(raw, 9)

    def chunk(tag, payload):
        return (struct.pack('>I', len(payload)) + tag + payload +
                struct.pack('>I', zlib.crc32(tag + payload) & 0xFFFFFFFF))

    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)))
        f.write(chunk(b'IDAT', comp))
        f.write(chunk(b'IEND', b''))


def draw_text(rows, text, x0, y0, scale, ink, total_w):
    for ch in text:
        g = MONO.get(ch)
        if g is None:
            x0 += 6 * scale
            continue
        for gy, line in enumerate(g):
            for gx, bit in enumerate(line):
                if bit == '1':
                    for dy in range(scale):
                        for dx in range(scale):
                            px, py = x0 + gx * scale + dx, y0 + gy * scale + dy
                            if 0 <= px < total_w and 0 <= py < len(rows):
                                i = px * 3
                                rows[py][i], rows[py][i + 1], rows[py][i + 2] = ink
        x0 += 6 * scale


cols = []
for theme_css, label, page_bg, ink in PANELS:
    page = os.path.join(BASE, '_v.html')
    with open(page, 'w', encoding='utf-8') as fh:
        # 用 replace 而不是 % 格式化: 字体 URL 里含 %20, 会与 % 格式化冲突
        fh.write(PAGE.replace('__THEME_CSS__', theme_css))
    shot = os.path.join(BASE, '_v.png')
    subprocess.run([EDGE, '--headless=new', '--disable-gpu', '--hide-scrollbars',
                    '--no-first-run', '--user-data-dir=' + PROFILE,
                    '--window-size=%d,%d' % (W, H), '--force-device-scale-factor=1',
                    '--virtual-time-budget=15000', '--screenshot=' + shot,
                    'file:///' + page.replace('\\', '/')], capture_output=True)
    w, h, bpp, px = read_png(shot)
    rows = [bytearray(bytes(page_bg) * w) for _ in range(LABEL_H)]
    for y in range(min(h, H)):
        bi = y * w * bpp
        row = bytearray()
        for x in range(w):
            i = bi + x * bpp
            row += bytes((px[i], px[i + 1], px[i + 2]))
        rows.append(row)
    draw_text(rows, label, 14, 11, 2, ink, w)
    cols.append(rows)
    os.remove(page)
    os.remove(shot)

out_h = min(len(c) for c in cols)
out_w = W * len(cols)
merged = [bytearray() for _ in range(out_h)]
for rows in cols:
    for y in range(out_h):
        merged[y] += rows[y]
write_png(os.path.join(BASE, 'preview-variants.png'), out_w, out_h, merged)
print('ok %dx%d' % (out_w, out_h))
