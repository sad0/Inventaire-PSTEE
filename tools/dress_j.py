"""Dress variant J's slots (John 2026-10-22): quick-slot rows = slots set on a carrying copper pipe like valves;
the 10 body slots = organic sockets pushed into the corroded lattice, ringed with copper, linked to the oval by thin
pipes. A sketch is painted into the masked areas of bg_clean_2x.png, then SwarmUI repaints only the mask.

Usage: python tools/dress_j.py [creativity] [seed]  -> design/art/j/dress_sketch_2x.png, dress_mask_2x.png,
       design/art/j/gen/dress_c<c>_s<seed>.png (pick one, copy it to bg_dressed_2x.png)
"""
import base64
import json
import math
import os
import sys
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from pipes_guide import tube  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
J = os.path.join(ROOT, "design", "art", "j")
L = json.load(open(os.path.join(ROOT, "design", "build", "layout_j.json"), encoding="utf-8"))
K = 683 / 996
OXJ = L["menu"]["bg_offset"]
API = "http://localhost:7801"
PROMPT = ("steampunk biomechanical game inventory slots: square dark recessed sockets set like valves on a thick "
          "horizontal copper pipe with brass collars and rivets; organic corroded metal sockets with copper rims grown "
          "into a bone-like rusted lattice, thin copper pipes linking them, dark, deep shadows, painterly, highly "
          "detailed, matching the surroundings, no text")
NEG = "text, letters, items, objects inside the sockets, bright colors, purple, cartoon"


def S(x, y):
    """Menu coords -> bg_clean_2x px."""
    return ((x - OXJ) / K * 2, y / K * 2)


def SR(a, pad=0):
    x0, y0 = S(a[0] - pad, a[1] - pad)
    x1, y1 = S(a[0] + a[2] + pad, a[1] + a[3] + pad)
    return x0, y0, x1, y1


def socket(d, box, rim, k):
    """Dark recessed square socket with a thick rim."""
    x0, y0, x1, y1 = box
    d.rounded_rectangle((x0 - 7 * k, y0 - 7 * k, x1 + 7 * k, y1 + 7 * k), radius=10 * k, fill=rim[2])
    d.rounded_rectangle((x0 - 5 * k, y0 - 5 * k, x1 + 5 * k, y1 + 5 * k), radius=9 * k, fill=rim[0])
    d.rounded_rectangle((x0 - 3 * k, y0 - 3 * k, x1 + 3 * k, y1 + 1 * k), radius=8 * k, fill=rim[1])
    d.rounded_rectangle((x0, y0, x1, y1), radius=6 * k, fill=(7, 6, 5))


def main():
    c = float(sys.argv[1]) if len(sys.argv) > 1 else 0.55
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 71
    base = Image.open(os.path.join(J, "bg_clean_2x.png")).convert("RGB")
    sk = base.copy()
    mask = Image.new("L", base.size, 0)
    md = ImageDraw.Draw(mask)
    k = 2 / K / 2  # sketch unit ~ 1 menu px at 2x
    copper = ((122, 66, 38), (196, 128, 82), (40, 18, 10))
    brass = ((120, 100, 52), (200, 176, 104), (40, 30, 12))
    # quick-slot rows: carrying pipe through the slot centres, sockets on it
    for key in ("quiver", "quick weapons", "quick items"):
        row = L[key]
        x0, y0, _, y1 = SR(row[0])
        x1 = SR(row[-1])[2]
        cy = (y0 + y1) / 2
        md.rounded_rectangle((x0 - 40, y0 - 22, x1 + 40, y1 + 22), radius=30, fill=255)
        tube(sk, [(x0 - 34, cy), (x1 + 34, cy)], 13 * k * 2, "copper")
        d = ImageDraw.Draw(sk)
        for a in row:
            socket(d, SR(a), brass if key == "quick weapons" else copper, k * 2)
    # body slots: organic sockets + thin pipes to the oval rim
    pd = L["paperdoll"]
    ocx, ocy = S(pd[0] + pd[2] / 2, pd[1] + pd[3] / 2)
    for nm, a in L["body"].items():
        bx = SR(a)
        cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
        ang = math.atan2(ocy - cy, ocx - cx)
        end = (cx + math.cos(ang) * 70, cy + math.sin(ang) * 70)
        md.line((cx, cy, end[0], end[1]), fill=255, width=40)
        md.ellipse((bx[0] - 30, bx[1] - 30, bx[2] + 30, bx[3] + 30), fill=255)
        tube(sk, [(cx, cy), end], 5 * k * 2, "copper", rings=False)
        d = ImageDraw.Draw(sk)
        r = (bx[2] - bx[0]) * 0.75
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(70, 52, 36))
        for t in range(9):  # lattice knots around the socket
            aa = t / 9 * math.tau
            d.ellipse((cx + math.cos(aa) * r - 9, cy + math.sin(aa) * r - 9, cx + math.cos(aa) * r + 9,
                       cy + math.sin(aa) * r + 9), fill=(10, 8, 6))
        socket(d, bx, copper, k * 2)
    mask = mask.filter(ImageFilter.GaussianBlur(6))
    sk.save(os.path.join(J, "dress_sketch_2x.png"))
    mask.save(os.path.join(J, "dress_mask_2x.png"))

    def post(path, data):
        req = urllib.request.Request(API + path, json.dumps(data).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=900) as r:
            return json.load(r)

    def b64(p):
        return "data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode()

    sid = post("/API/GetNewSession", {})["session_id"]
    res = post("/API/GenerateText2Image", {
        "session_id": sid, "images": 1, "prompt": PROMPT, "negativeprompt": NEG,
        "model": "ZImage/SwarmUI_Z-Image-Turbo-FP8Mix", "width": base.width, "height": base.height, "steps": 8,
        "cfgscale": 1, "seed": seed, "initimage": b64(os.path.join(J, "dress_sketch_2x.png")),
        "initimagecreativity": c, "maskimage": b64(os.path.join(J, "dress_mask_2x.png")), "maskblur": 6})
    os.makedirs(os.path.join(J, "gen"), exist_ok=True)
    out = os.path.join(J, "gen", f"dress_c{c}_s{seed}.png")
    open(out, "wb").write(urllib.request.urlopen(API + "/" + urllib.parse.quote(res["images"][0])).read())
    print("saved", out)


if __name__ == "__main__":
    main()
