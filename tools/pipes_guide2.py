"""Guide v2 for variant I (John 2026-10-22): no looping cables. Long cables and bigger pipes cross the whole screen
behind everything, in the shadow (like the original INVBG); zone edges = big copper pipes running along the columns
(gauges, collars, glass tubes) + an organic corroded lattice; the stash zone is dark stone with faint Sigil spires.

Output: design/art/i/guide_1x.png (1366x683) and guide_2x.png. Usage: python tools/pipes_guide2.py [seed]
"""
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from pipes_guide import L, P, R, S, TUBES, W, H, catmull, tube  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "design", "art", "i")
VOID = (6, 4, 3)
STONE = (34, 30, 26)
STONE_DARK = (20, 17, 14)


def long_path(rng, a, b, bend, n=5):
    """Long gently bending path a -> b (no loops: offsets stay below the length)."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    ln = math.hypot(dx, dy) or 1
    nx, ny = -dy / ln, dx / ln
    ph = rng.uniform(0, math.tau)
    pts = []
    for i in range(n + 1):
        t = i / n
        o = math.sin(ph + t * math.pi * rng.uniform(0.8, 1.4)) * bend * math.sin(math.pi * t)
        pts.append((ax + dx * t + nx * o, ay + dy * t + ny * o))
    return catmull(pts, 30)


def edge_point(rng, side):
    if side == 0:
        return (-60, rng.uniform(-40, H + 40))
    if side == 1:
        return (W + 60, rng.uniform(-40, H + 40))
    if side == 2:
        return (rng.uniform(-40, W + 40), -60)
    return (rng.uniform(-40, W + 40), H + 60)


def shade(img, k):
    """Darken an image (cables in the shadow)."""
    return Image.eval(img, lambda v: int(v * k))


def blob(rng, box, amp, step=40):
    """Irregular organic outline around a box (noisy perimeter, smoothed)."""
    x0, y0, x1, y1 = box
    pts = []
    for (ax, ay, bx, by) in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
        n = max(2, int(math.hypot(bx - ax, by - ay) / (step * S)))
        for k in range(n):
            t = k / n
            pts.append((ax + (bx - ax) * t + rng.uniform(-amp, amp), ay + (by - ay) * t + rng.uniform(-amp, amp)))
    pts.append(pts[0])
    return catmull(pts, 8)


def lattice(d, rng, box, thick, col, hole):
    """Organic corroded lattice band along a box outline: rough band with round holes."""
    x0, y0, x1, y1 = box
    for (ax, ay, bx, by) in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x0, y1, x1, y1), (x0, y0, x0, y1)):
        steps = int(math.hypot(bx - ax, by - ay) / (thick * 0.35)) + 1
        for k in range(steps + 1):
            t = k / steps
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t
            r = thick * rng.uniform(0.45, 0.75)
            d.ellipse((x - r, y - r, x + r, y + r), fill=col)
        for k in range(steps // 2):
            t = rng.random()
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t
            r = thick * rng.uniform(0.15, 0.45)
            d.ellipse((x - r, y - r * rng.uniform(0.6, 1.0), x + r, y + r * rng.uniform(0.6, 1.0)), fill=hole)
        for k in range(steps // 3):  # bony knots spilling out of the band
            t = rng.random()
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t
            r = thick * rng.uniform(0.6, 1.1)
            d.ellipse((x - r, y - r, x + r, y + r), outline=col, width=max(2, int(thick * 0.25)))


def main():
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 21)
    os.makedirs(OUT, exist_ok=True)

    # 1) deep layer: many long thin cables crossing the whole screen, in the shadow
    deep = Image.new("RGB", (W, H), VOID)
    for i in range(70):
        s1 = rng.choice([0, 1, 2, 3])
        s2 = {0: 1, 1: 0, 2: 3, 3: 2}[s1] if rng.random() < 0.75 else rng.choice([0, 1, 2, 3])
        a, b = edge_point(rng, s1), edge_point(rng, s2)
        tube(deep, long_path(rng, a, b, rng.uniform(60, 260) * S / 2), rng.uniform(3, 7) * S / 2,
             rng.choice(["iron", "iron", "rust", "copper", "verdigris"]), rings=False)
    deep = shade(deep.filter(ImageFilter.GaussianBlur(1.4)), 0.6)

    # 2) mid layer: bigger pipes crossing the cables, still behind the panels, half in shadow
    mid = deep.copy()
    for i in range(18):
        s1 = rng.choice([0, 1, 2, 3])
        s2 = {0: 1, 1: 0, 2: 3, 3: 2}[s1]
        a, b = edge_point(rng, s1), edge_point(rng, s2)
        tube(mid, long_path(rng, a, b, rng.uniform(80, 300) * S / 2), rng.uniform(13, 22) * S / 2,
             rng.choice(["copper", "rust", "iron"]))
    img = Image.blend(deep, shade(mid, 0.7), 0.85)

    # 3) panels: dark stone, slightly translucent so the cables still cross the whole screen in the shadow
    cols = [(14, 54, 470, 674), (480, 54, 1012, 674)]
    stone = Image.new("RGB", (W, H), STONE)
    smask = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(smask)
    for c in cols:
        sd.polygon(blob(rng, R((c[0], c[1], c[2] - c[0], c[3] - c[1])), 16 * S), fill=200)
    img = Image.composite(stone, img, smask)
    d = ImageDraw.Draw(img)
    # stash zone: darker stone + faint spires of Sigil
    bp, st = L["backpack"], L["stash"]
    gx0, gy0 = min(a[0] for a in bp) - 10, min(a[1] for a in bp) - 10
    gx1, gy1 = max(a[0] + a[2] for a in st) + 10, max(a[1] + a[3] for a in st) + 10
    sx0, sy0, sx1, sy1 = R((gx0, gy0, gx1 - gx0, gy1 - gy0))
    d.rounded_rectangle((sx0, sy0, sx1, sy1), radius=14 * S, fill=STONE_DARK)
    for k in range(9):
        cx = rng.uniform(sx0 + 40, sx1 - 40)
        top = rng.uniform(sy0 + 40, sy1 - 200)
        wdt = rng.uniform(14, 34) * S / 2
        d.polygon([(cx, top), (cx + wdt, sy1 - 20), (cx - wdt, sy1 - 20)], fill=(28, 24, 22))
        d.ellipse((cx - wdt * 2, top + 60, cx + wdt * 2, top + 120), fill=(26, 22, 20))
    # left column: zones carved out of the stone by the lattice
    zones = []
    for key in ("quiver", "quick weapons", "quick items"):
        a = L[key]
        zones.append((a[0][0] - 12, a[0][1] - 12, a[-1][0] + a[-1][2] + 12, a[0][1] + a[0][3] + 12))
    for nm, s in L["stats"].items():
        dd, pp = s["disc"], s["plate"]
        zones.append((dd[0] - 6, pp[1] - 4, pp[0] + pp[2] + 4, pp[1] + pp[3] + 4))
    g = L["ground"]
    zones.append((g[0][0] - 10, g[0][1] - 10, g[0][0] + g[0][2] + 10, g[-1][1] + g[-1][3] + 10))
    for z in zones:
        bx = R((z[0], z[1], z[2] - z[0], z[3] - z[1]))
        d.rounded_rectangle(bx, radius=10 * S, fill=STONE_DARK)
    lat_col, hole = (88, 62, 40), (10, 7, 5)
    for z in zones + [(gx0, gy0, gx1, gy1)]:
        lattice(d, rng, R((z[0], z[1], z[2] - z[0], z[3] - z[1])), 14 * S, lat_col, hole)
    # big copper pipes along the column edges (straight runs with gentle sag, elbows at corners)
    for c in cols:
        x0, y0, x1, y1 = c
        for (a, b) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
            pa, pb = P(*a), P(*b)
            tube(img, long_path(rng, pa, pb, 18 * S, 4), 9 * S, rng.choice(["copper", "copper", "brass", "rust"]))
            for k in range(2):  # tendrils escaping the frame
                t = rng.uniform(0.15, 0.85)
                sx_, sy_ = pa[0] + (pb[0] - pa[0]) * t, pa[1] + (pb[1] - pa[1]) * t
                ang = rng.uniform(0, math.tau)
                ln_ = rng.uniform(80, 220) * S
                tube(img, long_path(rng, (sx_, sy_), (sx_ + math.cos(ang) * ln_, sy_ + math.sin(ang) * ln_),
                                    ln_ * 0.4, 4), rng.uniform(3, 6) * S, rng.choice(["copper", "rust", "verdigris"]),
                     rings=False)
    # paperdoll niche: dark hole behind the oval
    pd = L["paperdoll"]
    cx, cy = P(pd[0] + pd[2] / 2, pd[1] + pd[3] / 2)
    d.ellipse((cx - pd[2] * 0.62 * S, cy - pd[3] * 0.62 * S, cx + pd[2] * 0.62 * S, cy + pd[3] * 0.62 * S),
              fill=VOID)
    # title plate
    t = L["text"]["title"]
    d.rounded_rectangle(R((120, 8, 784, 40)), radius=14 * S, fill=STONE)
    img.save(os.path.join(OUT, "guide_2x.png"))
    img.resize((W // 2, H // 2), Image.LANCZOS).save(os.path.join(OUT, "guide_1x.png"))
    print("guide:", OUT)


if __name__ == "__main__":
    main()
