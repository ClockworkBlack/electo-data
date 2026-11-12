#!/usr/bin/env python3
"""Is this screenshot the Electo page, or a blank or crashed app?

    python3 app/shot_check.py <screenshot.png>

Passes when the picture shows the page's own mark (the blue-over-red bar beside the name, in the light or the dark
colours) on a mostly plain background with text on it. Reads the PNG itself, so the build needs no image library."""
import struct
import sys
import zlib

MARK = {"light": ((0x1E, 0x5F, 0xB0), (0xC8, 0x34, 0x2D)), "dark": ((0x4F, 0x8F, 0xDF), (0xE0, 0x63, 0x5C))}


def read_png(path):
    """(width, height, rows of (r, g, b) tuples) for an 8- or 16-bit RGB or RGBA PNG without interlacing."""
    d = open(path, "rb").read()
    if d[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    pos, idat, w = 8, [], None
    while pos < len(d):
        n, kind = struct.unpack(">I4s", d[pos:pos + 8])
        body = d[pos + 8:pos + 8 + n]
        pos += 12 + n
        if kind == b"IHDR":
            w, h, depth, ctype, _, _, lace = struct.unpack(">IIBBBBB", body)
            if lace or depth not in (8, 16) or ctype not in (2, 6):
                raise ValueError("PNG kind not read here (depth %d, colour type %d, interlace %d)" % (depth, ctype, lace))
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
    if w is None:
        raise ValueError("no PNG header")
    raw = zlib.decompress(b"".join(idat))
    bpp = (3 if ctype == 2 else 4) * (depth // 8)
    stride = w * bpp
    rows, prev = [], bytearray(stride)
    for y in range(h):
        f = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        if f == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride):
                line[i] = (line[i] + (((line[i - bpp] if i >= bpp else 0) + prev[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(line)
        prev = line
    step = depth // 8          # 16-bit samples: the high byte is enough here
    return w, h, [[(r[x * bpp], r[x * bpp + step], r[x * bpp + 2 * step]) for x in range(w)] for r in rows]


def near(p, c, tol=14):
    return abs(p[0] - c[0]) <= tol and abs(p[1] - c[1]) <= tol and abs(p[2] - c[2]) <= tol


def check(path):
    w, h, px = read_png(path)
    total = w * h
    counts = {}
    for row in px[::2]:                       # every second line and column is plenty
        for p in row[::2]:
            k = (p[0] >> 3, p[1] >> 3, p[2] >> 3)
            counts[k] = counts.get(k, 0) + 1
    seen = sum(counts.values())
    top = max(counts.values()) / seen
    dark = sum(n for (r, g, b), n in counts.items() if r + g + b < 3 * 10) / seen        # text and filled buttons
    light = sum(n for (r, g, b), n in counts.items() if r + g + b > 3 * 27) / seen
    mark = {}
    for name, (blue, red) in MARK.items():
        nb = nr = 0
        for row in px[: h // 3]:              # the mark is at the top of the page
            for p in row:
                if near(p, blue):
                    nb += 1
                elif near(p, red):
                    nr += 1
        mark[name] = (nb, nr)
    need = max(30, total // 40000)            # the bar is about 9 by 22 CSS pixels
    theme = next((n for n, (nb, nr) in mark.items() if nb >= need and nr >= need), None)
    info = "%dx%d; most common shade %.0f%%; dark %.1f%%, light %.1f%%; mark pixels (blue, red): light %s, dark %s" % (
        w, h, top * 100, dark * 100, light * 100, mark["light"], mark["dark"])
    why = []
    if top > 0.97:
        why.append("one shade fills the screen (a blank page)")
    if theme is None:
        why.append("the page's mark is not at the top")
    if theme == "light" and dark < 0.004 or theme == "dark" and light < 0.004:
        why.append("no text on the page")
    return why, info


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    try:
        problems, facts = check(sys.argv[1])
    except Exception as e:  # noqa: BLE001
        sys.exit("screenshot not readable: %s" % e)
    print(("NOT the page: " + "; ".join(problems) if problems else "the page is on the screen") + " (" + facts + ")")
    sys.exit(1 if problems else 0)
