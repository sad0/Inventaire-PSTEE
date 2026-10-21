"""Paint the layout guide for variant H: serpentine pipes + material zones, in the PTEE (variant F) palette.

The guide is fed to SwarmUI img2img (tools/swarm.py) so the generated art follows our pipe paths and zones.
Output: design/art/h/guide_2x.png (2732x1366 = the 1366x683 area above the action bar, x2) + guide_mask.png
(white = content zones that the UI covers: grid, slots, plates).

Usage: python tools/pipes_guide.py [seed]
"""
import json
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "design", "art", "h")
L = json.load(open(os.path.join(ROOT, "design", "build", "layout.json"), encoding="utf-8"))
S = 2                       # guide scale
OX = 171                    # 1024 frame -> 1366 screen
W, H = 1366 * S, 683 * S

# PTEE palette (measured on variant F + vanilla art)
VOID = (8, 6, 4)
PLATE = (43, 40, 30)
PLATE_DARK = (25, 21, 14)
TUBES = {  # base, highlight, shadow
    "copper": ((122, 66, 38), (196, 128, 82), (40, 18, 10)),
    "rust": ((92, 44, 26), (150, 82, 52), (30, 12, 6)),
    "verdigris": ((70, 84, 70), (130, 150, 120), (22, 28, 22)),
    "iron": ((58, 54, 44), (112, 104, 86), (16, 14, 10)),
    "brass": ((120, 100, 52), (200, 176, 104), (40, 30, 12)),
}


def P(x, y):
    """1024-frame coords -> guide px."""
    return ((x + OX) * S, y * S)


def R(r):
    x, y, w, h = r
    return (x + OX) * S, y * S, (x + OX + w) * S, (y + h) * S


def catmull(pts, n=24):
    out = []
    pts = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1:i + 3]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(pts[-2])
    return out


def resample(pts, step):
    out = [pts[0]]
    for p in pts[1:]:
        q = out[-1]
        dist = math.dist(p, q)
        while dist > step:
            t = step / dist
            q = (q[0] + (p[0] - q[0]) * t, q[1] + (p[1] - q[1]) * t)
            out.append(q)
            dist = math.dist(p, q)
    out.append(pts[-1])
    return out


def tube(img, pts, r, kind, rings=True, light=(-0.6, -0.8)):
    """Shaded tube along a polyline: stacked discs from shadow to highlight, joint collars every ~22r."""
    base, hi, sh = TUBES[kind]
    pts = resample(pts, max(1.0, r / 3))
    d = ImageDraw.Draw(img)
    layers = [(1.0, sh), (0.86, base), (0.55, tuple((b + h) // 2 for b, h in zip(base, hi))), (0.22, hi)]
    for scale, col in layers:
        rr = r * scale
        off = (0, 0) if scale >= 0.86 else (light[0] * r * (1 - scale) * 0.9, light[1] * r * (1 - scale) * 0.9)
        for (x, y) in pts:
            d.ellipse((x - rr + off[0], y - rr + off[1], x + rr + off[0], y + rr + off[1]), fill=col)
    if rings:
        acc, last = 0.0, pts[0]
        for p in pts[1:]:
            acc += math.dist(p, last)
            last = p
            if acc > r * 22:
                acc = 0
                d.ellipse((p[0] - r * 1.22, p[1] - r * 1.22, p[0] + r * 1.22, p[1] + r * 1.22), fill=sh)
                d.ellipse((p[0] - r * 1.1, p[1] - r * 1.1, p[0] + r * 1.1, p[1] + r * 1.1), fill=base)
                d.ellipse((p[0] - r * 0.8, p[1] - r * 0.9, p[0] - r * 0.1, p[1] - r * 0.2), fill=hi)


def serpent(rng, a, b, wiggle, n=6):
    """Wavy path a -> b with perpendicular sine-ish offsets."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    ln = math.hypot(dx, dy) or 1
    nx, ny = -dy / ln, dx / ln
    ph = rng.uniform(0, math.tau)
    freq = rng.uniform(1.2, 2.6)
    pts = []
    for i in range(n + 1):
        t = i / n
        o = math.sin(ph + t * math.pi * freq) * wiggle * math.sin(math.pi * t) + rng.uniform(-wiggle, wiggle) * 0.25
        pts.append((ax + dx * t + nx * o, ay + dy * t + ny * o))
    return catmull(pts)


def loop_around(rng, rect, pad, wob):
    """Organic closed pipe loop around a rect (rounded, wobbly)."""
    x0, y0, x1, y1 = rect
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    pts = []
    for (x, y) in [(x0, y0), ((x0 + x1) / 2, y0), (x1, y0), (x1, (y0 + y1) / 2), (x1, y1), ((x0 + x1) / 2, y1),
                   (x0, y1), (x0, (y0 + y1) / 2), (x0, y0)]:
        pts.append((x + rng.uniform(-wob, wob), y + rng.uniform(-wob, wob)))
    return catmull(pts, 18)


def main():
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
    os.makedirs(OUT, exist_ok=True)
    img = Image.new("RGB", (W, H), VOID)
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)

    # oval centre (behind the paperdoll)
    pd = L["paperdoll"]
    cx, cy = P(pd[0] + pd[2] / 2, pd[1] + pd[3] / 2)
    rx, ry = pd[2] * 0.75 * S, pd[3] * 0.62 * S

    # 1) deep background: many thin serpentine cables radiating from behind the character to the window edges
    for i in range(46):
        ang = rng.uniform(0, math.tau)
        start = (cx + math.cos(ang) * rx * 0.9, cy + math.sin(ang) * ry * 0.9)
        far = max(W, H) * 1.2
        end = (cx + math.cos(ang) * far, cy + math.sin(ang) * far)
        end = (min(max(end[0], -40), W + 40), min(max(end[1], -40), H + 40))
        tube(img, serpent(rng, start, end, rng.uniform(40, 140) * S / 2, 7), rng.uniform(3, 7) * S / 2,
             rng.choice(["iron", "iron", "rust", "verdigris"]), rings=False)
    img = img.filter(ImageFilter.GaussianBlur(1.2))

    # 2) big tentacle pipes from the oval rim to the edges (over the cables)
    big_targets = [(-30, 120), (-30, 520), (200, -30), (W * 0.42, -30), (W * 0.62, -30), (W + 30, 90),
                   (W + 30, H * 0.55), (W + 30, H - 60), (W * 0.30, H + 30), (W * 0.75, H + 30), (-30, H - 40),
                   (W * 0.5, H + 30)]
    kinds = ["copper", "rust", "verdigris", "copper", "iron", "copper", "rust", "verdigris", "copper", "rust",
             "iron", "verdigris"]
    for (tx, ty), kind in zip(big_targets, kinds):
        ang = math.atan2(ty - cy, tx - cx)
        start = (cx + math.cos(ang) * rx * 0.85, cy + math.sin(ang) * ry * 0.85)
        tube(img, serpent(rng, start, (tx, ty), rng.uniform(80, 220) * S / 2, 9), rng.uniform(16, 26) * S / 2, kind)

    # 3) material zones: plates the UI sits on (no clean rectangles: pipes coil around them)
    d = ImageDraw.Draw(img)

    def plate(rect, pad=8, dark=False, rad=26):
        x0, y0, x1, y1 = R(rect)
        box = (x0 - pad * S, y0 - pad * S, x1 + pad * S, y1 + pad * S)
        d.rounded_rectangle(box, radius=rad * S, fill=PLATE_DARK if dark else PLATE)
        md.rounded_rectangle(box, radius=rad * S, fill=255)
        return box

    zones = []
    bp, st = L["backpack"], L["stash"]
    grid = (min(a[0] for a in bp + st), min(a[1] for a in bp), max(a[0] + a[2] for a in bp + st) -
            min(a[0] for a in bp + st), max(a[1] + a[3] for a in st) - min(a[1] for a in bp))
    zones.append(("grid", plate(grid, 10, True), "copper", 11))
    g = L["ground"]
    zones.append(("ground", plate((g[0][0], g[0][1], g[0][2], g[-1][1] + g[-1][3] - g[0][1]), 8, True, 20),
                  "verdigris", 8))
    for key, kind in (("quiver", "verdigris"), ("quick weapons", "verdigris"), ("quick items", "verdigris")):
        a = L[key]
        zones.append((key, plate((a[0][0], a[0][1], a[-1][0] + a[-1][2] - a[0][0], a[0][3]), 6, True, 18), kind, 8))
    for nm, stt in L["stats"].items():
        dd, pp = stt["disc"], stt["plate"]
        zones.append((nm, plate((dd[0], pp[1], pp[0] + pp[2] - dd[0], pp[3]), 4, False, 30), "rust", 7))
    body = list(L["body"].values())
    for a in body:
        plate(a, 6, True, 10)
    t = L["text"]
    for key in ("name", "weight"):
        zones.append((key, plate(t[key], 2, False, 16), "iron", 6))
    zones.append(("header", plate((496, 82, 448, 34), 2, False, 16), "iron", 6))
    zones.append(("title", plate(t["title"], 4, False, 18), "brass", 6))

    # 4) pipe contours coiling around each zone, then a few connectors between zones
    for name, box, kind, r in zones:
        tube(img, loop_around(rng, box, r * S * 0.9, r * S * 0.6), r * S / 2 * 1.2, kind)
    # columns: no rectangles, two long serpentine "spines" outline each column
    for (x0, x1) in ((14, 470), (480, 1012)):
        for yy in (56, 676):
            tube(img, serpent(rng, P(x0, yy), P(x1, yy), 10 * S, 6), 8 * S / 2 * 1.3, "copper")
        for xx in (x0, x1):
            tube(img, serpent(rng, P(xx, 56), P(xx, 676), 12 * S, 7), 8 * S / 2 * 1.3, "rust")

    # 5) the oval itself stays the game's frame: dark hole marker
    d.ellipse((cx - rx * 0.66, cy - ry * 0.82, cx + rx * 0.66, cy + ry * 0.82), fill=VOID)
    md.ellipse((cx - rx * 0.66, cy - ry * 0.82, cx + rx * 0.66, cy + ry * 0.82), fill=255)

    img.save(os.path.join(OUT, "guide_2x.png"))
    mask.save(os.path.join(OUT, "guide_mask.png"))
    img.resize((W // 2, H // 2), Image.LANCZOS).save(os.path.join(OUT, "guide_1x.png"))
    print("guide:", os.path.join(OUT, "guide_2x.png"))


main()
