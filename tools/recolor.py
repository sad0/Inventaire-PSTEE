"""Reinhard colour transfer (CIE Lab mean/std) of an image towards a reference palette image.

Usage: python tools/recolor.py src.png ref.png out.png [strength 0..1]
Near-black (void) pixels are ignored so the dark backgrounds do not dominate the statistics.
"""
import sys

import numpy as np
from PIL import Image

M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WHITE = np.array([0.95047, 1.0, 1.08883])


def to_lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    xyz = c @ M.T / WHITE
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def to_rgb(lab):
    fy = (lab[..., 0] + 16) / 116
    fx = fy + lab[..., 1] / 500
    fz = fy - lab[..., 2] / 200
    f = np.stack([fx, fy, fz], -1)
    xyz = np.where(f ** 3 > 0.008856, f ** 3, (f - 16 / 116) / 7.787) * WHITE
    c = xyz @ np.linalg.inv(M).T
    c = np.where(c > 0.0031308, 1.055 * np.clip(c, 0, None) ** (1 / 2.4) - 0.055, 12.92 * c)
    return np.clip(c * 255, 0, 255).astype(np.uint8)


def transfer(src_img, ref_img, k=1.0):
    s = to_lab(np.asarray(src_img.convert("RGB"), np.float64))
    r = to_lab(np.asarray(ref_img.convert("RGB"), np.float64))
    sm, rm = s[..., 0] > 6, r[..., 0] > 6
    o = s.copy()
    for c in range(3):
        ss, rs = s[..., c][sm], r[..., c][rm]
        o[..., c] = (s[..., c] - ss.mean()) / (ss.std() + 1e-6) * rs.std() + rs.mean()
    o = s + (o - s) * k
    return Image.fromarray(to_rgb(o), "RGB")


if __name__ == "__main__":
    src, ref, out = sys.argv[1:4]
    k = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
    transfer(Image.open(src), Image.open(ref), k).save(out)
