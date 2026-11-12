#!/usr/bin/env python3
"""What an Android screen says, from `adb shell uiautomator dump`.

    python3 app/ui_text.py <ui.xml>              the texts on the screen, in order, separated by " | "
    python3 app/ui_text.py <ui.xml> <text>       "x y": the middle of the element with exactly that text (to tap it)
"""
import html
import re
import sys


def main(argv):
    if len(argv) not in (1, 2):
        sys.exit(__doc__)
    t = open(argv[0], encoding="utf-8", errors="replace").read()
    if len(argv) == 2:
        for m in re.finditer(r"<node\b[^>]*>", t):
            node = m.group(0)
            if re.search(r'\btext="%s"' % re.escape(html.escape(argv[1], quote=True)), node):
                b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', node)
                if b:
                    x1, y1, x2, y2 = map(int, b.groups())
                    print((x1 + x2) // 2, (y1 + y2) // 2)
                    return
        return
    seen = []
    for m in re.finditer(r'\b(?:text|content-desc)="([^"]+)"', t):
        s = html.unescape(m.group(1)).strip()
        if s and s not in seen:
            seen.append(s)
    print(" | ".join(seen)[:1500] or "(no text on the screen)")


if __name__ == "__main__":
    main(sys.argv[1:])
