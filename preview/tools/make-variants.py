# 由已渲染好的三张变体预览裁剪拼接出对照图。
# 直接复用 preview-dark / preview-kraft / preview-sage.png, 因此字体与主预览图
# 完全一致, 不需要再单独渲染一遍 (避免第二次渲染引入字体不确定性)。
import os
import struct
import zlib

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # preview/
THEME = os.path.dirname(BASE)

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
    '_': ['00000', '00000', '00000', '00000', '11111'],
    '-': ['00000', '00000', '11111', '00000', '00000'],
    '|': ['00100', '00100', '00100', '00100', '00100'],
    ' ': ['00000', '00000', '00000', '00000', '00000'],
}

# (源文件, 标签, 标签底色, 标签文字色)
PANELS = [
    ('preview-dark.png', 'inkwell  |  dark', (0x20, 0x24, 0x2b), (0xe8, 0xec, 0xf2)),
    ('preview-kraft.png', 'inkwell-paper  |  kraft', (0xf1, 0xf1, 0xd6), (0x3b, 0x3b, 0x2c)),
    ('preview-sage.png', 'inkwell-green  |  sage', (0xee, 0xf3, 0xe9), (0x34, 0x3b, 0x30)),
]

KEEP_W = 560          # 输出面板宽度 (统一)
KEEP_H = 640          # 输出面板高度 (统一)
LABEL_H = 34          # 顶部标签条高度
CROP_FRAC_X = 0.88    # 各源图按同比例裁剪, 保证三个面板取景一致
CROP_FRAC_Y = 0.72


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
                                rows[py][i] = ink[0]
                                rows[py][i + 1] = ink[1]
                                rows[py][i + 2] = ink[2]
        x0 += 6 * scale


cols = []
for src, label, page_bg, ink in PANELS:
    w, h, bpp, px = read_png(os.path.join(BASE, src))
    # 按同比例裁剪, 再缩放到统一尺寸 —— 三张源图分辨率不同, 固定像素裁剪会导致取景不一致
    cw = int(w * CROP_FRAC_X)
    ch = int(h * CROP_FRAC_Y)
    x_off = (w - cw) // 2
    y_off = int(h * 0.012)
    rows = [bytearray(bytes(page_bg) * KEEP_W) for _ in range(LABEL_H)]
    for oy in range(KEEP_H):
        sy = y_off + min(ch - 1, int(oy * ch / KEEP_H))
        bi = sy * w * bpp
        row = bytearray()
        for ox in range(KEEP_W):
            sx = x_off + min(cw - 1, int(ox * cw / KEEP_W))
            i = bi + sx * bpp
            row += bytes((px[i], px[i + 1], px[i + 2]))
        rows.append(row)
    draw_text(rows, label, 14, 11, 2, ink, KEEP_W)
    cols.append(rows)

out_h = min(len(c) for c in cols)
out_w = sum(len(c[0]) // 3 for c in cols)
merged = [bytearray() for _ in range(out_h)]
for rows in cols:
    for y in range(out_h):
        merged[y] += rows[y]
write_png(os.path.join(BASE, 'preview-variants.png'), out_w, out_h, merged)
print('ok %dx%d' % (out_w, out_h))
