# 把三张小样张横向拼接成对照图。
# 只做像素拷贝, 不缩放、不重采样 —— 避免任何模糊。
import os
import struct
import sys
import zlib

SRC_DIR = sys.argv[1]
OUT = sys.argv[2]

PANELS = ['v-dark.png', 'v-kraft.png', 'v-sage.png']
GAP = 24                      # 三栏之间的间隔 (像素)
GAP_BG = (0x2a, 0x2e, 0x36)   # 间隔用中性灰, 在深浅底之间都不刺眼


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


imgs = []
for name in PANELS:
    p = os.path.join(SRC_DIR, name)
    if not os.path.exists(p):
        raise SystemExit('missing: ' + p)
    imgs.append(read_png(p))

# 三栏宽度可能因滚动条/取整略有差异, 统一取最小值, 从左上角对齐裁切
cw = min(i[0] for i in imgs)
chh = min(i[1] for i in imgs)

out_w = cw * len(imgs) + GAP * (len(imgs) - 1)
out_h = chh
gap_row = bytes(GAP_BG) * GAP

merged = [bytearray() for _ in range(out_h)]
for idx, (w, h, bpp, px) in enumerate(imgs):
    if idx:
        for y in range(out_h):
            merged[y] += gap_row
    for y in range(out_h):
        bi = y * w * bpp
        row = bytearray()
        for x in range(cw):
            i = bi + x * bpp
            row += bytes((px[i], px[i + 1], px[i + 2]))
        merged[y] += row

write_png(OUT, out_w, out_h, merged)
print('ok %dx%d' % (out_w, out_h))
