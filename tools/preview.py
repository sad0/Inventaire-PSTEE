"""Composite the manifest's visible layers with PIL (quick check, independent of GIMP).

Usage: python tools/preview.py out.png [--show "group name" ...] [--hide "group name" ...] [--wide]
--show/--hide override the visibility of nodes whose name starts with the given text. --wide renders 1366x768.
"""
import json
import os
import sys

from PIL import Image

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


def main():
    args = sys.argv[1:]
    out = args.pop(0)
    show, hide, wide = [], [], False
    while args:
        a = args.pop(0)
        if a == "--show":
            show.append(args.pop(0))
        elif a == "--hide":
            hide.append(args.pop(0))
        elif a == "--wide":
            wide = True
    m = json.load(open(os.path.join(ROOT, "design", "build", "manifest.json"), encoding="utf-8"))
    ox = 171 if wide else 0
    img = Image.new("RGBA", (m["width"] + 2 * ox, m["height"]), (0, 0, 0, 255))

    def vis(n):
        if any(n["name"].startswith(s) for s in show):
            return True
        if any(n["name"].startswith(s) for s in hide):
            return False
        return n["visible"]

    def walk(nodes):
        for n in nodes:
            if not vis(n):
                continue
            if n["type"] == "group":
                walk(n["children"])
            elif n["type"] == "layer":
                im = Image.open(os.path.join(ROOT, n["png"])).convert("RGBA")
                if n.get("opacity", 100) != 100:
                    a = im.getchannel("A").point(lambda v: v * n["opacity"] // 100)
                    im.putalpha(a)
                tmp = Image.new("RGBA", img.size, (0, 0, 0, 0))
                tmp.paste(im, (n["x"] + ox, n["y"]))
                img.alpha_composite(tmp)

    walk(m["root"])
    img.convert("RGB").save(out)


main()
