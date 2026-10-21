"""Contact sheet of BAM cycles/frames (debug)."""
import sys
from PIL import Image, ImageDraw
sys.path.insert(0, 'tools'); import ie
g = ie.Game(r'E:\Enhanced Edition\Environnement de test\Planescape Torment Enhanced Edition')
names = sys.argv[2:]; cell = 72
rows = []
for n in names:
    for ci, cy in enumerate(ie.bam(g, n) or []):
        rows.append((n, ci, cy))
W = 160 + cell * max(len(r[2]) for r in rows); H = cell * len(rows)
sheet = Image.new('RGBA', (W, H), (60, 0, 60, 255)); d = ImageDraw.Draw(sheet)
for y, (n, ci, cy) in enumerate(rows):
    d.text((4, y * cell + 30), f'{n} c{ci}', fill='white')
    for x, (im, cx, cyy) in enumerate(cy):
        t = im.copy(); t.thumbnail((cell - 4, cell - 4)); sheet.alpha_composite(t, (160 + x * cell, y * cell))
sheet.save(sys.argv[1])
