"""Minimal read-only Infinity Engine resource reader: KEY/BIFF, MOS v1/v2, BAM v1/v2, PVRZ."""
import os
import struct
import zlib

from PIL import Image

RES_TYPES = {
    0x001: "BMP", 0x3EB: "2DA", 0x3EC: "MOS", 0x3E8: "BAM", 0x3F4: "BCS", 0x3FD: "VVC",
    0x408: "MENU", 0x409: "LUA", 0x40A: "TTF", 0x40B: "PNG", 0x404: "PVRZ", 0x3F3: "CHU",
    0x3ED: "ITM", 0x3EE: "SPL", 0x3F5: "IDS", 0x3EF: "BCS", 0x3F0: "WED",
}
EXT_TO_TYPE = {v: k for k, v in RES_TYPES.items()}


class Game:
    def __init__(self, root):
        self.root = root
        self.override = os.path.join(root, "override")
        with open(os.path.join(root, "chitin.key"), "rb") as f:
            d = f.read()
        nbif, nres, obif, ores = struct.unpack_from("<4I", d, 8)
        self.bifs = []
        for i in range(nbif):
            ln, fno, fnl, loc = struct.unpack_from("<IIHH", d, obif + i * 12)
            self.bifs.append(d[fno:fno + fnl].rstrip(b"\0").decode().replace("\\", "/"))
        self.res = {}
        for i in range(nres):
            name, typ, loc = struct.unpack_from("<8sHI", d, ores + i * 14)
            name = name.rstrip(b"\0").decode("latin1").upper()
            self.res[(name, typ)] = loc
        self._bifcache = {}

    def names(self, ext):
        t = EXT_TO_TYPE[ext]
        return sorted(n for (n, ty) in self.res if ty == t)

    def _bif(self, idx):
        if idx not in self._bifcache:
            with open(os.path.join(self.root, self.bifs[idx]), "rb") as f:
                d = f.read()
            assert d[:8] == b"BIFFV1  ", self.bifs[idx]
            nfile, ntile, off = struct.unpack_from("<3I", d, 8)
            files = {}
            for i in range(nfile):
                loc, o, sz, ty = struct.unpack_from("<IIIH", d, off + i * 16)
                files[loc & 0x3FFF] = (o, sz)
            self._bifcache[idx] = (d, files)
        return self._bifcache[idx]

    def read(self, name, ext, vanilla=False):
        """Return resource bytes. vanilla=True skips the override folder."""
        name = name.upper()
        if not vanilla:
            p = os.path.join(self.override, f"{name}.{ext}")
            if os.path.exists(p):
                with open(p, "rb") as f:
                    return f.read()
        loc = self.res.get((name, EXT_TO_TYPE[ext]))
        if loc is None:
            if vanilla:
                return None
            return None
        d, files = self._bif(loc >> 20)
        o, sz = files[loc & 0x3FFF]
        return d[o:o + sz]

    def exists(self, name, ext):
        return self.read(name, ext) is not None


# ---------------------------------------------------------------- PVRZ
_pvrz_cache = {}


def pvrz(game, page):
    if page in _pvrz_cache:
        return _pvrz_cache[page]
    d = game.read(f"MOS{page:04d}", "PVRZ")
    if d is None:
        raise KeyError(f"MOS{page:04d}.PVRZ")
    raw = zlib.decompress(d[4:])
    fmt = struct.unpack_from("<Q", raw, 8)[0]
    h, w = struct.unpack_from("<II", raw, 24)
    meta = struct.unpack_from("<I", raw, 48)[0]
    data = raw[52 + meta:]
    if fmt == 7:
        img = Image.frombuffer("RGBA", (w, h), data, "bcn", 1, "")
    elif fmt == 11:
        img = Image.frombuffer("RGBA", (w, h), data, "bcn", 3, "")
    else:
        raise ValueError(f"PVRZ format {fmt}")
    img = img.copy()
    _pvrz_cache[page] = img
    return img


def pvrz_named(game, resref):
    d = game.read(resref, "PVRZ")
    raw = zlib.decompress(d[4:])
    fmt = struct.unpack_from("<Q", raw, 8)[0]
    h, w = struct.unpack_from("<II", raw, 24)
    meta = struct.unpack_from("<I", raw, 48)[0]
    data = raw[52 + meta:]
    n = {7: 1, 11: 3}[fmt]
    return Image.frombuffer("RGBA", (w, h), data, "bcn", n, "").copy()


# ---------------------------------------------------------------- MOS
def _pal_img(w, h, pix, pal, trans_green=True):
    """pal: list of (r,g,b,a); index 0 / pure green -> transparent."""
    img = Image.new("RGBA", (w, h))
    img.putdata([pal[p] for p in pix])
    return img


def _read_pal(d, off, n=256):
    pal = []
    for i in range(n):
        b, g, r, a = d[off + i * 4:off + i * 4 + 4]
        pal.append((r, g, b, 255))
    return pal


def mos(game, name):
    d = game.read(name, "MOS")
    if d is None:
        return None
    if d[:4] == b"MOSC":
        d = zlib.decompress(d[12:])
    sig = d[:8]
    if sig == b"MOS V1  ":
        w, h, cols, rows, bs, poff = struct.unpack_from("<HHHHII", d, 8)
        img = Image.new("RGBA", (w, h))
        ntiles = cols * rows
        pal_off = poff
        tiles_off = pal_off + ntiles * 1024
        data_off = tiles_off + ntiles * 4
        for r in range(rows):
            for c in range(cols):
                t = r * cols + c
                pal = _read_pal(d, pal_off + t * 1024)
                # green (0,255,0) is transparent in MOS v1
                pal = [(p[0], p[1], p[2], 0) if p[:3] == (0, 255, 0) else p for p in pal]
                to = struct.unpack_from("<I", d, tiles_off + t * 4)[0]
                tw = min(bs, w - c * bs)
                th = min(bs, h - r * bs)
                pix = d[data_off + to:data_off + to + tw * th]
                img.paste(_pal_img(tw, th, pix, pal), (c * bs, r * bs))
        return img
    if sig == b"MOS V2  ":
        w, h, nblk, boff = struct.unpack_from("<IIII", d, 8)
        img = Image.new("RGBA", (w, h))
        for i in range(nblk):
            page, sx, sy, bw, bh, dx, dy = struct.unpack_from("<7I", d, boff + i * 28)
            src = pvrz(game, page).crop((sx, sy, sx + bw, sy + bh))
            img.paste(src, (dx, dy))
        return img
    raise ValueError(f"{name}: {sig}")


# ---------------------------------------------------------------- BAM
def bam(game, name):
    """Return list of cycles, each a list of (Image, cx, cy)."""
    d = game.read(name, "BAM")
    if d is None:
        return None
    if d[:4] == b"BAMC":
        d = zlib.decompress(d[12:])
    sig = d[:8]
    if sig == b"BAM V1  ":
        nfr, ncy, ck, foff, poff, lut = struct.unpack_from("<HBBIII", d, 8)
        pal = _read_pal(d, poff)
        # BAM v1 alpha: palette alpha 0 means opaque (old style); compressed index ck transparent
        pal = list(pal)
        pal[ck] = (0, 0, 0, 0)
        # also pure green
        pal = [(p[0], p[1], p[2], 0) if p[:3] == (0, 255, 0) else p for p in pal]
        frames = []
        for i in range(nfr):
            w, h, cx, cy, fd = struct.unpack_from("<HHhhI", d, foff + i * 12)
            off = fd & 0x7FFFFFFF
            rle = not (fd & 0x80000000)
            pix = bytearray()
            p = off
            n = w * h
            if rle:
                while len(pix) < n:
                    b = d[p]; p += 1
                    if b == ck:
                        cnt = d[p] + 1; p += 1
                        pix += bytes([ck]) * cnt
                    else:
                        pix.append(b)
                pix = pix[:n]
            else:
                pix = d[p:p + n]
            frames.append((_pal_img(w, h, pix, pal) if w and h else Image.new("RGBA", (1, 1)), cx, cy))
        cyc_off = foff + nfr * 12
        cycles = []
        for c in range(ncy):
            cnt, idx = struct.unpack_from("<HH", d, cyc_off + c * 4)
            lst = []
            for k in range(cnt):
                fi = struct.unpack_from("<H", d, lut + (idx + k) * 2)[0]
                lst.append(frames[fi])
            cycles.append(lst)
        return cycles
    if sig == b"BAM V2  ":
        nfr, ncy, nblk, foff, coff, boff = struct.unpack_from("<6I", d, 8)
        blocks = [struct.unpack_from("<7I", d, boff + i * 28) for i in range(nblk)]
        frames = []
        for i in range(nfr):
            w, h, cx, cy, bstart, bcnt = struct.unpack_from("<HHhhHH", d, foff + i * 12)
            img = Image.new("RGBA", (max(w, 1), max(h, 1)))
            for b in blocks[bstart:bstart + bcnt]:
                page, sx, sy, bw, bh, dx, dy = b
                img.paste(pvrz(game, page).crop((sx, sy, sx + bw, sy + bh)), (dx, dy))
            frames.append((img, cx, cy))
        cycles = []
        for c in range(ncy):
            cnt, idx = struct.unpack_from("<HH", d, coff + c * 4)
            cycles.append(frames[idx:idx + cnt])
        return cycles
    raise ValueError(f"{name}: {sig}")


RES_TYPES.update({0x3F1: "CRE"})
EXT_TO_TYPE.update({"CRE": 0x3F1})


class Tlk:
    def __init__(self, path):
        with open(path, "rb") as f:
            self.d = f.read()
        self.count, self.soff = struct.unpack_from("<II", self.d, 10)

    def __getitem__(self, ref):
        if ref < 0 or ref >= self.count:
            return ""
        o, ln = struct.unpack_from("<II", self.d, 18 + ref * 26 + 18)
        return self.d[self.soff + o:self.soff + o + ln].decode("utf-8", "replace")


def itm_info(game, name):
    d = game.read(name, "ITM")
    if not d or d[:4] != b"ITM ":
        return None
    unid, idn = struct.unpack_from("<ii", d, 8)
    typ = struct.unpack_from("<H", d, 0x1C)[0]
    icon = d[0x3A:0x42].split(b"\0")[0].decode("latin1").upper()
    return {"res": name, "unid": unid, "name": idn, "type": typ, "icon": icon}
