"""Extract PTEE inventory art and write a layer manifest for the GIMP builder.

Canvas = the INVENTORY menu frame (1024x768): GIMP pointer coordinates == UI.MENU 'area' coordinates.
Hi-res game art is scaled to each item's area, like the engine does.

Usage: python tools/build_assets.py   (reads the game read-only, writes design/assets + design/build)
"""
import io
import re
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import ie  # noqa: E402
import menu as menuparser  # noqa: E402

GAME = r"E:\Enhanced Edition\Environnement de test\Planescape Torment Enhanced Edition"
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(ROOT, "design", "assets")
PNG = os.path.join(ASSETS, "png")
BUILD = os.path.join(ROOT, "design", "build")
W, H = 1024, 768
BG_OFF = -171            # 1366-wide backgrounds are centred on the 1024 frame
LIB_SCALE = 1366 / 3840  # 4K art -> 1366x768 screen
ACTIONBAR_Y = 768 - 85

g = ie.Game(GAME)
tlk = ie.Tlk(os.path.join(GAME, "lang", "en_US", "dialog.tlk"))
UI = menuparser.parse(g.read("UI", "MENU", vanilla=True).decode("latin1"))
MENUS = {m.get("name"): m for m in UI}

os.makedirs(PNG, exist_ok=True)
os.makedirs(BUILD, exist_ok=True)
os.makedirs(os.path.join(ASSETS, "fonts"), exist_ok=True)

# ------------------------------------------------------------------ fonts & colours
FONTS = {}
for f in ("BOOKMANI", "EXOCET"):
    p = os.path.join(ASSETS, "fonts", f + ".ttf")
    if not os.path.exists(p):
        with open(p, "wb") as fh:
            fh.write(g.read(f, "TTF"))
    FONTS[f] = p


def abgr(s):
    v = int(s, 16)
    return (v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF)


COL = {"B": abgr("FFdef6f8"), "Y": abgr("FF01cde5"), "$": abgr("FF82E6FF"), "R": abgr("FF0000FF"),
       "G": abgr("FF00FF00"), "N": abgr("FFFDFBFD"), "P": abgr("FFa67da7"), "5": (0, 0, 0)}
STYLES = {  # from BGEE.lua 'styles'
    "normal": ("Y", 14, "left", "top"), "label": ("B", 20, "center", "center"),
    "label_parchment": ("Y", 20, "center", "center"), "gold": ("$", 14, "center", "center"),
    "button": ("B", 18, "center", "center"), "title": ("Y", 22, "center", "center"),
    "list": ("Y", 14, "left", "center"),
}

# ------------------------------------------------------------------ png cache
_saved = {}


def save(img, key):
    key = re.sub(r"[^A-Za-z0-9_.+-]", "_", key)
    if key not in _saved:
        p = os.path.join(PNG, key + ".png")
        img.save(p)
        _saved[key] = os.path.relpath(p, ROOT).replace("\\", "/")
    return _saved[key]


_bamc, _mosc = {}, {}


def bam(name):
    name = name.upper()
    if name not in _bamc:
        _bamc[name] = ie.bam(g, name)
    return _bamc[name]


def mos(name):
    name = name.upper()
    if name not in _mosc:
        _mosc[name] = ie.mos(g, name)
    return _mosc[name]


def bam_frame(name, cyc=0, fr=0, size=None):
    cycles = bam(name)
    if not cycles or cyc >= len(cycles) or fr >= len(cycles[cyc]):
        return None
    im = cycles[cyc][fr][0]
    if size:
        im = im.resize(size, Image.LANCZOS)
    return im


# ------------------------------------------------------------------ manifest nodes
def group(name, children=None, visible=True):
    return {"type": "group", "name": name, "visible": visible, "children": children or []}


def layer(name, img, key, x, y, visible=True, opacity=100):
    return {"type": "layer", "name": name, "png": save(img, key), "x": int(x), "y": int(y),
            "visible": visible, "opacity": opacity, "w": img.width, "h": img.height}


def textnode(name, text, x, y, size=11, color=(255, 255, 0), visible=True, font="Sans-serif Bold"):
    return {"type": "text", "name": name, "text": text, "x": int(x), "y": int(y), "size": size,
            "color": list(color), "visible": visible, "font": font}


def render_text(text, area, style="label", color=None, point=None, font="BOOKMANI", halign=None, valign=None,
                shadow=False):
    col, pt, ha, va = STYLES.get(style, STYLES["label"])
    col = color or COL[col]
    pt = point or pt
    ha = halign or ha
    va = valign or va
    w, h = area[2], area[3]
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONTS[font], pt)
    l, t, r, b = d.textbbox((0, 0), text, font=f)
    tw, th = r - l, b - t
    x = {"left": 0, "center": (w - tw) // 2, "right": w - tw}[ha] - l
    y = {"top": 0, "center": (h - th) // 2, "bottom": h - th}[va] - t
    if shadow:
        d.text((x + 1, y + 1), text, font=f, fill=(0, 0, 0, 255))
    d.text((x, y), text, font=f, fill=tuple(col) + (255,))
    return img


def text_layer(name, text, area, ox=0, oy=0, **kw):
    img = render_text(text, area, **kw)
    return layer(name, img, f"txt_{name}_{text}"[:80], area[0] + ox, area[1] + oy)


# ------------------------------------------------------------------ annotations
ANN_COL = {"slot": (0, 220, 255), "button": (255, 160, 0), "label": (120, 255, 120), "text": (255, 90, 200),
           "mock": (255, 60, 60), "bg": (200, 200, 200)}


def outline(w, h, col, fill_alpha=28):
    img = Image.new("RGBA", (max(w, 1), max(h, 1)), col + (fill_alpha,))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, w - 1, h - 1), outline=col + (255,))
    return img


ANNOT = {}  # section -> list of nodes


def annotate(section, name, area, kind, ox=0, oy=0, short=None):
    x, y, w, h = area
    col = ANN_COL.get(kind, (255, 255, 255))
    ANNOT.setdefault(section, []).append(group(f"{name} [{w}x{h} @{x},{y}]", [
        layer(f"box {name}", outline(w, h, col), f"box_{w}x{h}_{kind}", x + ox, y + oy),
        textnode(f"label {name}", f"{short}\n{w}x{h}" if short else f"{name}\n{w}x{h} @{x},{y}", x + ox + 2,
                 y + oy + 1, 8, col),
    ]))


GUIDES = {"h": set(), "v": set()}


def guide_box(x, y, w, h):
    GUIDES["v"].update([x, x + w])
    GUIDES["h"].update([y, y + h])


# ------------------------------------------------------------------ helpers for menu items
STATES_BTN = ["normal", "pressed", "selected", "disabled"]
STATES_SLOT = ["normal", "hover", "selected", "highlight"]


def bam_states(name, bamres, seq, area, label_states, first_visible=True, ox=0, oy=0, fr0=0):
    """Group with one layer per frame of a BAM cycle, frame fr0 visible, others hidden."""
    x, y, w, h = area
    cycles = bam(bamres)
    kids = []
    if not cycles or seq >= len(cycles):
        return None
    for fi, (im, cx, cy) in enumerate(cycles[seq]):
        st = label_states[fi] if fi < len(label_states) else f"frame{fi}"
        sc = im.resize((w, h), Image.LANCZOS)
        kids.append(layer(f"{name} - {st} ({bamres} c{seq} f{fi})", sc, f"{bamres}_c{seq}_f{fi}_{w}x{h}",
                          x + ox, y + oy, visible=(first_visible and fi == fr0)))
    return group(name, kids)  # draw order: frame 0 at the bottom, other states above (hidden)


# ------------------------------------------------------------------ item icons
def item_icon(itm):
    info = ie.itm_info(g, itm)
    if not info:
        return None, None
    cyc = bam(info["icon"])
    if not cyc:
        return None, None
    return cyc[0][0][0], tlk[info["name"]] or tlk[info["unid"]] or itm


def icon_in_slot(itm, area, tint=None, count=None, plus=False):
    im, nm = item_icon(itm)
    if im is None:
        return None
    x, y, w, h = area
    t = im.copy()
    t.thumbnail((w - 4, h - 4), Image.LANCZOS)
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if tint:
        canvas.paste(Image.new("RGBA", (w, h), tint + (90,)), (0, 0))
    canvas.alpha_composite(t, ((w - t.width) // 2, (h - t.height) // 2))
    d = ImageDraw.Draw(canvas)
    if count:
        f = ImageFont.truetype(FONTS["BOOKMANI"], 12)
        s = str(count)
        l, tp, r, b = d.textbbox((0, 0), s, font=f)
        d.text((w - (r - l) - 3 + 1, h - (b - tp) - 4 + 1), s, font=f, fill=(0, 0, 0, 255))
        d.text((w - (r - l) - 3, h - (b - tp) - 4), s, font=f, fill=(255, 255, 255, 255))
    if plus:
        f = ImageFont.truetype(FONTS["BOOKMANI"], 16)
        d.text((w - 12, -2), "+", font=f, fill=(0, 0, 0, 255))
        d.text((w - 13, -3), "+", font=f, fill=(255, 255, 255, 255))
    key = f"icon_{itm}_{w}x{h}_{tint}_{count}_{plus}"
    return layer(f"{nm} ({itm})", canvas, key, x, y)


# ================================================================== 1. BACKGROUND
inv = MENUS["INVENTORY"]
invbg = mos("INVBG").resize((1366, 768), Image.LANCZOS)
BG_PIECES = {  # cut-outs of INVBG in frame coordinates (x, y, w, h)
    "Paperdoll oval": (154, 78, 245, 314),
    "Personal items rail": (505, 98, 285, 68),
    "Quiver rail": (497, 220, 312, 72),
    "Weapons rail": (484, 340, 262, 72),
    "Message bar": (427, 437, 404, 58),
    "Backpack rail + weight panel": (386, 500, 610, 124),
    "Ground column": (839, 128, 152, 364),
    "Gold box": (857, 16, 118, 110),
    "Name/class plate": (139, 492, 228, 108),
    "AC disc": (0, 450, 76, 82),
    "HP disc": (51, 526, 90, 96),
    "Earring frame left": (100, 34, 92, 86),
    "Ring frame (pipe socket)": (63, 214, 90, 86),
}
pieces = []
for nm, (x, y, w, h) in BG_PIECES.items():
    crop = invbg.crop((x - BG_OFF, y, x - BG_OFF + w, y + h))
    pieces.append(layer(f"BG piece - {nm}", crop, f"bgpiece_{nm}", x, y, visible=False))
    annotate("Background pieces", nm, (x, y, w, h), "bg")
background = group("Background", [
    layer("INVBG (BACKGROUND_INVENTORY, 1366x768 @ -171,0)", invbg, "INVBG_1366", BG_OFF, 0),
    group("INVBG pieces (cut-outs, for reuse)", pieces, visible=False),
])
GUIDES["v"].update([0, 1024])
GUIDES["h"].update([0, 768])

# ================================================================== 2. VANILLA INVENTORY
slot_groups = {"Weapons": [], "Personal items (quick items)": [], "Quiver": [], "Equipment (body)": [],
               "Backpack": [], "Ground": []}
SLOT_CAT = [("weapon", "Weapons"), ("personal", "Personal items (quick items)"), ("quiver", "Quiver"),
            ("group", "Backpack"), ("ground", "Ground")]
labels, buttons, texts = [], [], []
slot_boxes = {}
paperdoll = None
for it in inv["items"]:
    k = it["kind"]
    a = it.get("area")
    if k == "slot":
        info = it["slotinfo"].split(".")[-1]
        cat = next((c for p, c in SLOT_CAT if info.startswith(p)), "Equipment (body)")
        res = it["bam"].upper()
        seq = int(it.get("sequence", 0))
        nm = f"{it['name']} ({info})"
        if bam(res) is None:
            # vanilla bug: UI.MENU asks for SLOTARRW, the game only has SLOTARW -> engine draws nothing
            gr = bam_states(nm + " - MISSING " + res + ", SLOTARW shown", "SLOTARW", seq, a, STATES_SLOT,
                            first_visible=False)
        else:
            gr = bam_states(nm, res, seq, a, STATES_SLOT)
        slot_groups[cat].append(gr)
        annotate("Slots", f"{it['name']} {info} {res} s{seq}", a, "slot", short=info)
        slot_boxes.setdefault(cat, []).append(a)
    elif k == "button" and it.get("paperdoll"):
        paperdoll = it
        annotate("Paperdoll", "paperdoll (drag to swap appearance)", a, "button")
    elif k == "button":
        res = it["bam"].upper()
        seq = int(it.get("sequence", 0))
        nm = {"XBUTT": "Close (back to world)", "ARROBUTT": "Ground page " + ("prev" if seq == 0 else "next")}[res]
        buttons.append(bam_states(nm, res, seq, a, STATES_BTN))
        annotate("Buttons", f"{nm} {res} s{seq}", a, "button")
    elif k == "label" and ("bam" in it or "mosaic" in it):
        if "bam" in it:
            img = bam_frame(it["bam"], 0, 0, (a[2], a[3]))
            nm = "Encumbrance bag (" + it["bam"].upper() + ")"
        else:
            img = mos(it["mosaic"]).resize((a[2], a[3]), Image.LANCZOS)
            nm = {"ICHPMAN": "HP figure", "ICGOLD": "Gold pile", "ICPICKUP": "Ground pickup hand"}[
                it["mosaic"].upper()] + f" ({it['mosaic'].upper()})"
        labels.append(layer(nm, img, f"lbl_{nm}", a[0], a[1]))
        annotate("Labels & icons", nm, a, "label")

for cat, boxes in slot_boxes.items():
    x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
    guide_box(x0, y0, max(b[0] + b[2] for b in boxes) - x0, max(b[1] + b[3] for b in boxes) - y0)

# clean base (background + empty slot frames): source for "cover" patches that hide vanilla content in mockups
clean = Image.new("RGBA", (W, H), (0, 0, 0, 255))
clean.alpha_composite(invbg.crop((-BG_OFF, 0, -BG_OFF + W, H)))
for it in inv["items"]:
    if it["kind"] == "slot" and bam(it["bam"]):
        a = it["area"]
        clean.alpha_composite(bam_frame(it["bam"], int(it.get("sequence", 0)), 0, (a[2], a[3])), (a[0], a[1]))


def cover(name, area):
    x, y, w, h = area
    return layer(f"cover - {name}", clean.crop((x, y, x + w, y + h)), f"cover_{x}_{y}_{w}x{h}", x, y)


# text items with sample values
SAMPLE = {
    "game:GetSelectedCarried() .. 'LB'": ("Carried weight", "34LB"),
    "game:GetSelectedMaxEncumbrance() .. 'LB'": ("Max weight", "170LB"),
    "characters[id].name": ("Character name", "The Nameless One"),
    "Infinity_GetCurrentGroundPage()+1 .. '/' .. Infinity_GetMaxGroundPage()+1": ("Ground page", "1/1"),
    "characters[id].gold": ("Gold", "1250"),
    "characters[id].class": ("Class", "Fighter"),
    "characters[id].AC.current": ("AC value", "8"),
    "characters[id].HP.current": ("HP current", "64"),
    "characters[id].HP.max": ("HP max", "64"),
    "TEXT_inventoryError": ("Message line (TEXT_inventoryError)", ""),
}
for it in inv["items"]:
    if it["kind"] not in ("label", "text"):
        continue
    if "text_lua" not in it and "text" not in it:
        continue
    a = it["area"]
    if "text_lua" in it:
        nm, val = SAMPLE[it["text_lua"]]
    else:
        nm, val = "AC label", tlk[106644]
    style = it.get("text_style", "label")
    col = None
    if it.get("text_color"):
        col = COL["B"]
    al = it.get("text_align") or it.get("align") or (None, None)
    pt = int(it["text_point"]) if "text_point" in it else None
    font = it.get("text_font", "BOOKMANI").upper()
    if val:
        texts.append(text_layer(f"{nm} [{style}]", val, a, style=style, color=col, point=pt, font=font,
                                halign=al[0], valign=al[1], shadow=bool(it.get("text_shadow"))))
    annotate("Text", f"{nm} ({style})", a, "text")

# paperdoll mosaics (IVP*): appearance shown in the oval
PAPERDOLLS = [("IVPNOA", "Nameless One (default)"), ("IVPNOC", "Nameless One C"), ("IVPNOD", "Nameless One D"),
              ("IVPNOF", "Nameless One F"), ("IVPNOH", "Nameless One H"), ("IVPNOM", "Nameless One M"),
              ("IVPNOS", "Nameless One S"), ("IVPNOZ", "Nameless One Z"), ("IVPMRT", "Morte"),
              ("IVPANN", "Annah"), ("IVPDKK", "Dak'kon"), ("IVPFFG", "Fall-from-Grace"), ("IVPIGY", "Ignus"),
              ("IVPNDM", "Nordom"), ("IVPVHA", "Vhailor")]
pa = paperdoll["area"]
dolls = []
for res, nm in PAPERDOLLS:
    im = mos(res)
    if im is None:
        continue
    # keep aspect, fit in the paperdoll area, centred
    t = im.copy()
    t.thumbnail((pa[2], pa[3]), Image.LANCZOS)
    dolls.append(layer(f"Paperdoll - {nm} ({res})", t, f"doll_{res}", pa[0] + (pa[2] - t.width) // 2,
                       pa[1] + (pa[3] - t.height) // 2, visible=(res == "IVPNOA")))
dolls.reverse()

# sample items (what a real save shows)
def slot_area(name):
    return next(i["area"] for i in inv["items"] if i.get("name") == name)


SAMPLE_ITEMS = [("slot_inv_1", "ADDAGGER", None), ("slot_inv_5", "EYEBALL", None),
                ("slot_inv_6", "BROBRA", None), ("slot_inv_21", "TTAC1", None), ("slot_inv_22", "BRORING", None),
                ("slot_inv_13", "AMBEAR", None), ("slot_inv_30", "COPPER", 3), ("slot_inv_32", "BREAST1", 2),
                ("slot_inv_34", "KEYSNTRY", None), ("slot_inv_31", "LENS04", None), ("slot_inv_68", "CLUB", None)]
sample_items = []
for sl, itm, cnt in SAMPLE_ITEMS:
    n = icon_in_slot(itm, slot_area(sl), count=cnt)
    if n:
        n["name"] = f"{sl}: {n['name']}"
        sample_items.append(n)

vanilla = group("Inventory (vanilla INVENTORY menu)", [
    group("Paperdoll (IVP* mosaics)", dolls),
    group("Slots", [group(k, v) for k, v in slot_groups.items()]),
    group("Labels & icons", labels),
    group("Sample items (example save)", sample_items),
    group("Text (sample values, game fonts)", texts),
    group("Buttons", buttons),
])

# ================================================================== 3. ACTION BAR (WORLD_ACTIONBAR overlay)
ab = []
ab.append(layer("ACTBG", mos("ACTBG").resize((1024, 85), Image.LANCZOS), "ACTBG", 0, ACTIONBAR_Y))
wing = mos("MAINWING").resize((1371, 85), Image.LANCZOS)
ab.append(layer("MAINWING left", wing, "MAINWING", -1371, ACTIONBAR_Y))
ab.append(layer("MAINWING right", wing, "MAINWING", 1024, ACTIONBAR_Y))
SEQ_DEFAULTS = {"getFormationSequence()": 14, "getLockScrollButtonSequence()": 4, "getAIButtonSequence()": 6,
                "getCombatLogSequence()": 12, "getQuickLootSequence()": 13, "getTimeSequence()": 0}
PARTY = {0: "AMPNM1", 1: "AMPMRT"}
ab_items = []
for it in MENUS["WORLD_ACTIONBAR_LEFT"]["items"]:
    a = it.get("area")
    if not a:
        continue
    flags = it.get("_flags", [])
    if "mosaic_lua" in it:  # portrait backgrounds
        n = int(it["mosaic_lua"].split("(")[1].rstrip(")"))
        res = "PRTRTBG" if n in PARTY else ("PRTRTNO0", "PRTRTNO1", "PRTRTNO0", "PRTRTNO1", "PRTRTNO1",
                                             "PRTRTNO0")[n]
        ab_items.append(layer(f"Portrait {n} background ({res})", mos(res).resize((a[2], a[3]), Image.LANCZOS),
                              f"{res}_{a[2]}", a[0], ACTIONBAR_Y + a[1]))
        continue
    if "portrait" in flags:
        n = int(flags[flags.index("portrait") + 1])
        if n in PARTY:
            ab_items.append(layer(f"Portrait {n} ({PARTY[n]})", bam_frame(PARTY[n], 0, 0, (a[2], a[3])),
                                  f"{PARTY[n]}_{a[2]}", a[0], ACTIONBAR_Y + a[1]))
        continue
    if "healthbar" in flags:
        n = int(flags[flags.index("healthbar") + 1])
        if n in PARTY:
            hb = Image.new("RGBA", (a[2], a[3]), (0, 0, 0, 0))
            ImageDraw.Draw(hb).rectangle((2, 5, a[2] - 3, a[3] - 6), fill=(150, 20, 20, 255))
            ab_items.append(layer(f"Portrait {n} health bar (engine-drawn, placeholder)", hb, "healthbar",
                                  a[0], ACTIONBAR_Y + a[1]))
        continue
    res = it.get("bam")
    if not res or res.upper() == "LVLBUTT":
        continue
    seq = int(it["sequence"]) if "sequence" in it else SEQ_DEFAULTS.get(it.get("sequence_lua"), 0)
    tip = it.get("tooltip") or it.get("tooltip_lua") or res
    gr = bam_states(f"{tip.replace('_TOOLTIP', '').title()} ({res.upper()} s{seq})", res, seq,
                    (a[0], ACTIONBAR_Y + a[1], a[2], a[3]), STATES_BTN)
    if gr:
        ab_items.append(gr)
actionbar = group("Action bar (WORLD_ACTIONBAR, drawn over the inventory)", ab + ab_items)
guide_box(0, ACTIONBAR_Y, 1024, 85)

# ================================================================== 4. PARTY STASH MOCKUPS
STASH_ITEMS = ["AX", "BMACE", "CLUB2", "HAMMER", "ANNAHDAG", "BACKBTR", "BOLT01", "TTAC2", "ANTAT", "BRORING",
               "AMBEAR", "ANEAR2", "GOLBRA", "EYEKAL", "FTEETH", "LENS01", "BREAST2", "BREAST3", "AGSCROLL",
               "ACID", "ADDRTEAR", "DBOX", "KEYSTRRM", "BELL", "EMBCHRM", "DUSTROBE", "AVEST", "SHAMAN", "AXQUAL",
               "EPUNCH", "BOLT03", "TTACCURA", "ADRING", "EYEGLAS1", "COPPER"]
STASH_MARKS = {1: ("tint", (200, 30, 30)), 6: ("count", 40), 9: ("plus", None), 14: ("tint", (40, 70, 220)),
               18: ("count", 3), 23: ("plus", None), 30: ("count", 12)}
TABS = ["All", "Weapons", "Tattoos", "Jewelry", "Eyes & Teeth", "Charms", "Quest", "Misc"]
TABS_SHORT = ["All", "Weap.", "Tatt.", "Jewel", "Eyes", "Charm", "Quest", "Misc"]
COPPER_COL = (230, 190, 120)


def stash_grid(prefix, x0, y0, cols, rows, cell, step, start=0, slotres="IVSLOT"):
    slots, items = [], []
    k = start
    for r in range(rows):
        for c in range(cols):
            a = (x0 + c * step, y0 + r * step, cell, cell)
            seq = (r * cols + c) % 10
            slots.append(bam_states(f"{prefix} slot r{r}c{c}", slotres, seq, a, STATES_SLOT))
            itm = STASH_ITEMS[k % len(STASH_ITEMS)]
            mk = STASH_MARKS.get(k)
            n = icon_in_slot(itm, a, tint=mk[1] if mk and mk[0] == "tint" else None,
                             count=mk[1] if mk and mk[0] == "count" else None, plus=bool(mk and mk[0] == "plus"))
            if n:
                items.append(n)
            k += 1
    guide_box(x0, y0, (cols - 1) * step + cell, (rows - 1) * step + cell)
    return group(f"{prefix} grid slots ({cols}x{rows}, {cell}px, step {step})", slots), \
        group(f"{prefix} stash items (sample)", items)


def button(name, res, area, text=None, seq=0, style="button", point=None, selected=False, color=None):
    gr = bam_states(name, res, seq, area, STATES_BTN, fr0=2 if selected else 0)
    if text:
        gr["children"].append(text_layer(f"{name} caption", text, area, style=style, point=point, color=color))
    return gr


def dim_layer(name, area, alpha=150):
    return layer(name, Image.new("RGBA", (area[2], area[3]), (0, 0, 0, alpha)), f"dim_{area[2]}x{area[3]}_{alpha}",
                 area[0], area[1])


def tab_strip(prefix, x, y, w, h, tabs, active=0, gap=2, arrows=True):
    kids = []
    if arrows:
        kids.append(button(f"{prefix} tabs scroll left", "ARROBUTT", (x, y + (h - 24) // 2, 24, 24), seq=0))
        x += 26
    for i, t in enumerate(tabs):
        a = (x + i * (w + gap), y, w, h)
        kids.append(button(f"{prefix} tab {t}", "GENBUT1", a, t, style="button", point=12, selected=(i == active),
                           color=COL["Y"] if i == active else None))
    if arrows:
        kids.append(button(f"{prefix} tabs scroll right", "ARROBUTT",
                           (x + len(tabs) * (w + gap), y + (h - 24) // 2, 24, 24), seq=1))
    guide_box(x, y, len(tabs) * (w + gap) - gap, h)
    return group(f"{prefix} category tabs", kids)


# ---- Variant A: backpack rail toggles to the stash (in-place)
A = "A"
rail = [i["area"] for i in inv["items"] if i.get("name", "").startswith("slot_inv_") and 30 <= int(
    i["name"].split("_")[-1]) <= 49]
ra_items = []
order = sorted(rail, key=lambda a: (a[0], a[1]))
for k, a in enumerate(order):
    mk = STASH_MARKS.get(k + 3)
    n = icon_in_slot(STASH_ITEMS[(k + 3) % len(STASH_ITEMS)], a, tint=mk[1] if mk and mk[0] == "tint" else None,
                     count=mk[1] if mk and mk[0] == "count" else None, plus=bool(mk and mk[0] == "plus"))
    if n:
        ra_items.append(n)
bagA = (403, 536, 47, 50)
glow = Image.new("RGBA", (bagA[2] + 10, bagA[3] + 10), (0, 0, 0, 0))
ImageDraw.Draw(glow).ellipse((0, 0, glow.width - 1, glow.height - 1), outline=(255, 210, 90, 255), width=2)
varA = group("Variant A - Backpack rail toggles Backpack <-> Stash (in place)", [
    group("A covers (hide vanilla content under the mockup)", [
        cover("carried weight", (400, 514, 53, 20)), cover("max weight", (400, 590, 53, 21)),
        cover("backpack rail items", (476, 513, 498, 98)),
    ]),
    tab_strip("A", 430, 452, 50, 26, TABS_SHORT[:7], active=0),
    group("A weight bag = stash toggle button", [
        layer("A bag glow (selected state: stash shown)", glow, "glowA", bagA[0] - 5, bagA[1] - 5),
        text_layer("A stash weight (replaces carried)", "816LB", (400, 514, 53, 20), style="normal",
                   color=COL["B"], halign="left", valign="center"),
        text_layer("A party limit (sum of members)", "2000LB", (400, 590, 53, 21), style="normal", color=COL["B"],
                   halign="right", valign="center"),
    ]),
    group("A rail shows stash items (20 per page)", ra_items),
    group("A page scroll", [
        button("A page up", "ARROBUTT", (978, 515, 29, 28), seq=2),
        text_layer("A page label", "2/9", (974, 543, 40, 20), style="label", point=14),
        button("A page down", "ARROBUTT", (978, 566, 29, 28), seq=3),
    ]),
    group("A actions", [
        button("A sort button", "STRBUTT", (478, 614, 96, 34), "Sort: Auto", point=13),
        button("A store all button", "STRBUTT", (580, 614, 96, 34), "Store all", point=13),
    ]),
], visible=False)
for nm, a in [("A tabs", (430, 452, 420, 26)), ("A page up", (978, 515, 29, 28)), ("A page down", (978, 566, 29, 28)),
              ("A sort", (478, 614, 96, 34)), ("A store all", (580, 614, 96, 34)), ("A bag toggle", bagA)]:
    annotate("Party Stash A", nm, a, "mock")

# ---- Variant B: stash window (POPUP1 style) over the upper half
bx, by, bw, bh = 150, 16, 600, 464
sB = bw / 750
popup = mos("POPUP1").resize((bw, bh), Image.LANCZOS)
gx, gy = bx + int(290 * sB), by + int(176 * sB)
slotsB, itemsB = stash_grid("B", gx, gy, 7, 5, 43, 47)
wheel_c = (bx + int(184 * sB), by + int(180 * sB))
bagB = (wheel_c[0] - 30, wheel_c[1] - 32, 60, 64)
varB = group("Variant B - Stash window (POPUP1 style) over paperdoll/equipment", [
    dim_layer("B dim inventory behind", (0, 0, 1024, ACTIONBAR_Y), 110),
    layer("B panel POPUP1 (scaled 0.8)", popup, "popup1_B", bx, by),
    layer("B bag in the wheel (CONTBACK)", bam_frame("CONTBACK", 0, 0, (bagB[2], bagB[3])), "contback_B", bagB[0],
          bagB[1]),
    text_layer("B title", "Party Stash", (bx + int(284 * sB), by + int(79 * sB), int(266 * sB), int(42 * sB)),
               style="label"),
    text_layer("B weight", "816 / 2000 LB", (bx + int(30 * sB), by + int(300 * sB), int(300 * sB), 24),
               style="label", point=16, color=COL["B"]),
    text_layer("B sort label", "Sort: Auto", (bx + int(30 * sB), by + int(330 * sB), int(300 * sB), 24),
               style="label", point=16, color=COL["Y"]),
    tab_strip("B", gx - 2, by + int(136 * sB), 46, 24, TABS_SHORT[:7], active=0, gap=1, arrows=False),
    slotsB, itemsB,
    group("B scrollbar (CGSCRL1)", [
        layer("B scroll up", bam_frame("CGSCRL1", 0, 0, (24, 27)), "cgscrl_up", gx + 7 * 47 + 4, gy),
        layer("B scroll trough", bam_frame("CGSCRL1", 0, 5, (8, 170)), "cgscrl_trough", gx + 7 * 47 + 12, gy + 28),
        layer("B scroll knob", bam_frame("CGSCRL1", 0, 4, (24, 19)), "cgscrl_knob", gx + 7 * 47 + 4, gy + 60),
        layer("B scroll down", bam_frame("CGSCRL1", 0, 2, (24, 27)), "cgscrl_dn", gx + 7 * 47 + 4, gy + 4 * 47 + 16),
    ]),
    button("B store all", "NORMBUTT", (bx + int(277 * sB), by + int(497 * sB), int(138 * sB), int(56 * sB)),
           "Store all", point=15),
    button("B sort", "NORMBUTT", (bx + int(427 * sB), by + int(497 * sB), int(138 * sB), int(56 * sB)), "Sort",
           point=15),
    button("B done", "NORMBUTT", (bx + int(577 * sB), by + int(497 * sB), int(138 * sB), int(56 * sB)),
           tlk[1403], point=15),
], visible=False)
guide_box(bx, by, bw, bh)
annotate("Party Stash B", "B panel POPUP1", (bx, by, bw, bh), "mock")
annotate("Party Stash B", "B grid 7x5", (gx, gy, 6 * 47 + 43, 4 * 47 + 43), "mock")

# ---- Variant C: ground column switches Ground <-> Stash, category buttons on the right edge
ground = sorted([i["area"] for i in inv["items"] if i.get("name", "").startswith("slot_inv_") and 68 <= int(
    i["name"].split("_")[-1]) <= 77], key=lambda a: (a[0], a[1]))
itemsC = []
for k, a in enumerate(ground):
    mk = STASH_MARKS.get(k)
    n = icon_in_slot(STASH_ITEMS[k], a, tint=mk[1] if mk and mk[0] == "tint" else None,
                     count=mk[1] if mk and mk[0] == "count" else None, plus=bool(mk and mk[0] == "plus"))
    if n:
        itemsC.append(n)
CAT_ICONS = ["AX", "TTAC1", "BRORING", "EYEBALL", "BREAST1", "KEYSNTRY", "DBOX"]
catsC = []
for i, itm in enumerate(CAT_ICONS):
    a = (981, 140 + i * 44, 38, 38)
    catsC.append(button(f"C category {TABS[i + 1] if i + 1 < len(TABS) else 'Misc'}", "QUICKSLT", a, seq=0))
    ic = icon_in_slot(itm, (a[0] + 3, a[1] + 3, 32, 32))
    if ic:
        catsC.append(ic)
varC = group("Variant C - Ground column switches Ground <-> Stash", [
    group("C covers (hide vanilla content under the mockup)", [
        cover("ground items", (866, 195, 98, 250)), cover("ground page label", (890, 453, 48, 24)),
    ]),
    group("C mode tabs", [
        button("C tab Ground", "GENBUT1", (858, 122, 56, 24), "Ground", point=13),
        button("C tab Stash", "GENBUT1", (917, 122, 56, 24), "Stash", point=13, selected=True, color=COL["Y"]),
    ]),
    group("C column shows stash items", itemsC),
    text_layer("C page label (stash pages)", "3/24", (890, 453, 48, 24), style="label"),
    group("C category buttons (QUICKSLT + item icon)", catsC),
    text_layer("C stash weight (limit on hover)", "816LB", (976, 455, 48, 22), style="normal", point=11, color=COL["B"],
               halign="center", valign="center"),
    button("C store all", "STRBUTT", (858, 616, 116, 34), "Store all", point=13),
], visible=False)
annotate("Party Stash C", "C mode tabs", (858, 122, 115, 24), "mock")
annotate("Party Stash C", "C categories", (981, 140, 38, 7 * 44), "mock")


# ---- Variant D: full redesign inspired by Party Stash BG (John's pick, 2026-10-21)
def bg_piece(name):
    x, y, w, h = BG_PIECES[name]
    return invbg.crop((x - BG_OFF, y, x - BG_OFF + w, y + h))


POPUP1_HI = mos("POPUP1")
STONE = POPUP1_HI.crop([round(v * POPUP1_HI.width / 750) for v in (300, 146, 700, 470)])


def panel(w, h, b=20):
    """PTEE-looking panel: rusty 9-slice border from the message bar, stone fill from POPUP1."""
    src = bg_piece("Message bar")
    sw, sh = src.size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(STONE.resize((w - 2 * b + 8, h - 2 * b + 8), Image.LANCZOS), (b - 4, b - 4))
    bh = min(b, sh // 2)
    parts = [  # (src box, dst box)
        ((0, 0, b, bh), (0, 0, b, b)), ((sw - b, 0, sw, bh), (w - b, 0, w, b)),
        ((0, sh - bh, b, sh), (0, h - b, b, h)), ((sw - b, sh - bh, sw, sh), (w - b, h - b, w, h)),
        ((b, 0, sw - b, bh), (b, 0, w - b, b)), ((b, sh - bh, sw - b, sh), (b, h - b, w - b, h)),
        ((0, bh, b, sh - bh), (0, b, b, h - b)), ((sw - b, bh, sw, sh - bh), (w - b, b, w, h - b)),
    ]
    for (sx0, sy0, sx1, sy1), (dx0, dy0, dx1, dy1) in parts:
        if dx1 > dx0 and dy1 > dy0 and sx1 > sx0 and sy1 > sy0:
            piece = src.crop((sx0, sy0, sx1, sy1)).resize((dx1 - dx0, dy1 - dy0), Image.LANCZOS)
            out.alpha_composite(piece, (dx0, dy0))
    return out


def panel_layer(name, area, b=20):
    x, y, w, h = area
    annotate(f"Party Stash {name[0]}", name, area, "mock")
    guide_box(*area)
    return layer(name, panel(w, h, b), f"panel_{w}x{h}_{b}", x, y)


# backdrop: hides the vanilla right half, keeps INVBG pipes faintly visible
bd = Image.new("RGBA", (W, H), (0, 0, 0, 0))
dark = Image.alpha_composite(invbg.crop((-BG_OFF, 0, -BG_OFF + W, H)), Image.new("RGBA", (W, H), (0, 0, 0, 200)))
mask = Image.new("L", (W, H), 0)
md = ImageDraw.Draw(mask)
md.rectangle((478, 0, W, ACTIONBAR_Y), fill=255)
md.rectangle((432, 430, 478, ACTIONBAR_Y), fill=255)
md.rectangle((380, 495, 478, ACTIONBAR_Y), fill=255)
md.rectangle((130, 600, 380, ACTIONBAR_Y), fill=255)
bd.paste(dark, (0, 0), mask)

CELL, STEP = 43, 46
GX, GY = 486, 146                      # backpack rows
SY = GY + 2 * STEP + 8                 # stash rows start (after a separator)
SROWS = 7
GW = 9 * STEP + CELL                   # 10 columns
gridD = []
for r in range(2):                     # backpack: 2 x 10 = the 20 PST backpack slots
    for c in range(10):
        a = (GX + c * STEP, GY + r * STEP, CELL, CELL)
        gridD.append(bam_states(f"D backpack slot r{r}c{c}", "SLOTITM", (r * 10 + c) % 5, a, STATES_SLOT))
stashD = []
for r in range(SROWS):
    for c in range(10):
        a = (GX + c * STEP, SY + r * STEP, CELL, CELL)
        stashD.append(bam_states(f"D stash slot r{r}c{c}", "IVSLOT", (r * 10 + c) % 10, a, STATES_SLOT))
guide_box(GX, GY, GW, 2 * STEP - 3)
guide_box(GX, SY, GW, (SROWS - 1) * STEP + CELL)
itemsD = []
for i, itm in enumerate(["COPPER", "BREAST1", "KEYSNTRY", "LENS04", "CLUB"]):
    n = icon_in_slot(itm, (GX + (i % 10) * STEP, GY, CELL, CELL), count=(3, 2, None, None, None)[i])
    if n:
        itemsD.append(n)
for i in range(SROWS * 10 - 9):
    mk = STASH_MARKS.get(i % len(STASH_ITEMS))
    a = (GX + (i % 10) * STEP, SY + (i // 10) * STEP, CELL, CELL)
    n = icon_in_slot(STASH_ITEMS[i % len(STASH_ITEMS)], a, tint=mk[1] if mk and mk[0] == "tint" else None,
                     count=mk[1] if mk and mk[0] == "count" else None, plus=bool(mk and mk[0] == "plus"))
    if n:
        itemsD.append(n)
sep = Image.new("RGBA", (GW, 3), (150, 90, 50, 255))
ImageDraw.Draw(sep).line((0, 1, GW, 1), fill=(210, 140, 80, 255))

# ground column (1 x 6) on the far right
groundD = []
for r in range(6):
    a = (968, GY + r * STEP, CELL, CELL)
    groundD.append(bam_states(f"D ground slot {r}", "IVSLOT", (r + 4) % 10, a, STATES_SLOT))
giD = icon_in_slot("CLUB2", (968, GY, CELL, CELL))


def rail(prefix, x, y, n, res, cell=40, step=43, title=None):
    """Quick-slot rail: panel frame + slots (+ optional title above)."""
    kids = [panel_layer(f"{prefix} rail frame", (x - 8, y - 8, (n - 1) * step + cell + 16, cell + 16), 12)]
    for i in range(n):
        kids.append(bam_states(f"{prefix} slot {i}", res, i % 4, (x + i * step, y, cell, cell), STATES_SLOT))
    if title:
        kids.append(text_layer(f"{prefix} title", title, (x - 8, y - 28, (n - 1) * step + cell + 16, 18),
                               style="label", point=14))
    return group(prefix, kids)


qx, qy = 494, 38
varD = group("Variant D - Redesign inspired by Party Stash BG (big grid)", [
    layer("D backdrop (hides vanilla right half, INVBG darkened)", bd, "D_backdrop", 0, 0),
    group("D quick slots (moved)", [
        rail("D quiver", qx, qy, 5, "SLOTARW", title="Quiver"),
        rail("D quick items", qx + 5 * 43 + 30, qy, 5, "SLOTITM", title="Quick items"),
        rail("D quick weapons", 150, 628, 4, "SLOTSWRD"),
    ]),
    group("D header (stash weight, sort)", [
        panel_layer("D header bar", (478, 86, 482, 32), 12),
        layer("D bag (CONTBACK)", bam_frame("CONTBACK", 0, 0, (26, 28)), "contback_D", 488, 88),
        text_layer("D stash weight", "816 / 2000 LB", (522, 87, 200, 30), style="normal", point=15,
                   color=COL["$"], halign="left", valign="center"),
        button("D sort button", "STRBUTT", (836, 88, 116, 28), "Sort: Auto", point=13),
    ]),
    tab_strip("D", 478, 117, 59, 22, TABS_SHORT, active=0, gap=1, arrows=False),
    group("D grid (backpack 2x10 + stash 7x10)", [
        panel_layer("D grid frame", (GX - 10, GY - 6, GW + 20 + 18, SY + (SROWS - 1) * STEP + CELL - GY + 14), 14),
        group("D backpack slots (SLOTITM)", gridD),
        layer("D backpack / stash separator", sep, "sepD", GX, GY + 2 * STEP + 1),
        group("D stash slots (IVSLOT)", stashD),
        group("D items (sample, marks: red/blue/+ /count)", itemsD),
        group("D grid scrollbar (CGSCRL1)", [
            layer("D scroll up", bam_frame("CGSCRL1", 0, 0, (14, 16)), "cgscrl_upD", GX + GW + 2, SY),
            layer("D scroll trough", bam_frame("CGSCRL1", 0, 5, (6, 270)), "cgscrl_troughD", GX + GW + 6, SY + 18),
            layer("D scroll knob", bam_frame("CGSCRL1", 0, 4, (14, 12)), "cgscrl_knobD", GX + GW + 2, SY + 40),
            layer("D scroll down", bam_frame("CGSCRL1", 0, 2, (14, 16)), "cgscrl_dnD", GX + GW + 2,
                  SY + (SROWS - 1) * STEP + CELL - 16),
        ]),
    ]),
    group("D ground column", [
        panel_layer("D ground frame", (962, GY - 30, 56, 6 * STEP + 70), 12),
        layer("D ground pickup hand (ICPICKUP)", mos("ICPICKUP").resize((12, 24), Image.LANCZOS), "pickupD", 984,
              GY - 27),
        group("D ground slots", groundD),
        giD if giD else group("D ground item", []),
        button("D ground page", "ARROBUTT", (976, GY + 6 * STEP, 26, 24), seq=2),
        text_layer("D ground page label", "1/1", (962, GY + 6 * STEP + 22, 56, 18), style="label", point=13),
    ]),
    button("D close (XBUTT, same as vanilla)", "XBUTT", (974, 12, 50, 50)),
    group("D bottom bar", [
        button("D store all", "STRBUTT", (486, 586, 130, 40), "Store all", point=15),
        layer("D gold pile (ICGOLD)", mos("ICGOLD").resize((52, 44), Image.LANCZOS), "icgoldD", 812, 584),
        text_layer("D party gold", "1250", (868, 594, 90, 24), style="gold", point=16),
    ]),
], visible=True)
annotate("Party Stash D", "D grid backpack 2x10", (GX, GY, GW, 2 * STEP - 3), "mock")
annotate("Party Stash D", "D grid stash 7x10", (GX, SY, GW, (SROWS - 1) * STEP + CELL), "mock")


# ---- Variant E: LeUI layout (Party Stash BG2 look on LeUI), PTEE textures (John's pick, 2026-10-21)
# Positions are measured on docs/leui_bg2.png (1458x927) and mapped to the 1024x683 area above the action bar.
LS, LY = 1024 / 1458, 16


def L(x, y, w=0, h=0):
    """LeUI screenshot rect -> frame rect."""
    return (round(x * LS), round(y * LS) + LY, round(w * LS), round(h * LS))


def E_panel(name, rect, b=14):
    return panel_layer(name.replace("D ", "E "), rect, b)


def E_text(name, text, rect, **kw):
    annotate("Party Stash E", name, rect, "text")
    return text_layer(name, text, rect, **kw)


def E_slots(prefix, x, y, n, res, cell, step, seq0=0, vertical=False):
    out = []
    for i in range(n):
        a = (x, y + i * step, cell, cell) if vertical else (x + i * step, y, cell, cell)
        out.append(bam_states(f"{prefix} slot {i}", res, (seq0 + i) % (4 if res != "IVSLOT" else 10), a,
                              STATES_SLOT))
    annotate("Party Stash E", prefix, (x, y, (cell if vertical else (n - 1) * step + cell),
                                       ((n - 1) * step + cell if vertical else cell)), "slot")
    return group(prefix, out)


E_items = []


def E_icon(itm, a, **kw):
    n = icon_in_slot(itm, a, **kw)
    if n:
        E_items.append(n)


# backdrop over the whole usable area
bdE = Image.alpha_composite(invbg.crop((-BG_OFF, 0, -BG_OFF + W, ACTIONBAR_Y)),
                            Image.new("RGBA", (W, ACTIONBAR_Y), (0, 0, 0, 215)))

# --- title + left column
title = L(20, 12, 1418, 52)
left = L(30, 68, 645, 815)
right = L(690, 68, 745, 815)
name_row = L(140, 75, 530, 40)
cs, st = 36, 39                                   # left column slot size / step (5 quiver slots must fit)
qx, qy0 = L(60, 0)[0], L(0, 182)[1]
E_left = [
    E_panel("E left panel", left, 16),
    E_panel("E name/class bar", name_row, 10),
    E_text("E name", "The Nameless One", (name_row[0], name_row[1], name_row[2] // 2, name_row[3]), style="label",
           point=16),
    E_text("E class", "Fighter", (name_row[0] + name_row[2] // 2, name_row[1], name_row[2] // 2, name_row[3]),
           style="label", point=16),
]
# section headers + quick slots (PST: quiver 5, quick weapons 4, quick items 5)
for title_txt, hy, n, res, items in (("Quiver", 130, 5, "SLOTARW", ["BOLT01", "BOLT03"]),
                                     ("Quick Weapons", 264, 4, "SLOTSWRD", ["ADDAGGER"]),
                                     ("Quick Items", 398, 5, "SLOTITM", ["EYEBALL", "BROBRA"])):
    hb = L(40, hy, 270, 40)
    E_left.append(E_panel(f"E {title_txt} header", hb, 10))
    E_left.append(E_text(f"E {title_txt} title", title_txt, hb, style="label", point=16))
    sy = hb[1] + hb[3] + 6
    E_left.append(E_slots(f"E {title_txt}", qx, sy, n, res, cs, st))
    for i, itm in enumerate(items):
        E_icon(itm, (qx + i * st, sy, cs, cs), count=40 if itm.startswith("BOLT") else None)

# --- paperdoll: PTEE oval reduced, body slots around it like LeUI
s = 0.56
ox, oy = L(372, 196)[0] + 4, L(0, 196)[1]
ov = bg_piece("Paperdoll oval")
ovw, ovh = round(ov.width * s), round(ov.height * s)
pa = paperdoll["area"]
doll = mos("IVPNOA")
dt = doll.copy()
dt.thumbnail((round(pa[2] * s), round(pa[3] * s)), Image.LANCZOS)
dx = ox + round((pa[0] - 154) * s) + (round(pa[2] * s) - dt.width) // 2
dy = oy + round((pa[1] - 78) * s) + (round(pa[3] * s) - dt.height) // 2
E_doll = group("E paperdoll (PTEE oval reduced x0.56)", [
    layer("E oval frame (INVBG cut-out)", ov.resize((ovw, ovh), Image.LANCZOS), "ovalE", ox, oy),
    layer("E paperdoll IVPNOA", dt, "dollE", dx, dy),
])
annotate("Party Stash E", "E paperdoll oval", (ox, oy, ovw, ovh), "mock")
guide_box(ox, oy, ovw, ovh)
es, est = 40, 44
top_y = L(0, 130)[1]
body = []
body_names = [("earringright0", "AMBEAR"), ("earringleft0", None), ("chest0", None), ("wrist0", "GOLBRA")]
tx0 = L(320, 0)[0]
for i, (nm, itm) in enumerate(body_names):
    a = (tx0 + i * est, top_y, es, es)
    body.append(bam_states(f"E body {nm}", "IVSLOT", i, a, STATES_SLOT))
    if itm:
        E_icon(itm, a)
side_x = ox + ovw + 8
for i, (nm, itm) in enumerate([("hand0", None), ("ring0", "BRORING"), ("ring1", None)]):
    a = (side_x, top_y + (i + 1) * (est + 14) + 6, es, es) if i else (side_x, top_y, es, es)
    body.append(bam_states(f"E body {nm}", "IVSLOT", 4 + i, a, STATES_SLOT))
    if itm:
        E_icon(itm, a)
bot_y = oy + ovh + 6
for i, (nm, itm) in enumerate([("tattoo0", "TTAC1"), ("tattoo1", None), ("tattoo2", None)]):
    a = (ox + (ovw - (3 * est - 4)) // 2 + i * est, bot_y, es, es)
    body.append(bam_states(f"E body {nm}", "IVSLOT", 7 + i, a, STATES_SLOT))
    if itm:
        E_icon(itm, a)
annotate("Party Stash E", "E body slots (10, PST)", (tx0, top_y, side_x + es - tx0, bot_y + es - top_y), "slot")

# --- stats: 2x2 blocks (icon disc + big value | detail lines)
STATS = [("AC", "8", ["Base: 10", "Dex: -1", "Tattoo: -1"], "ICAC", 548, 45),
         ("THAC0", "17", ["Base: 18", "Str: +0", "Prof.: -1", "Weapon: 0"], "ICAC", 548, 355),
         ("HP", "64/64", ["Class: 1d10", "Con: +2"], "ICHPBG", 715, 45),
         ("Damage", "1d6+1", ["Weapon: 1d6", "Str: +1", "Prof.: +0"], "ICHPBG", 715, 355)]
E_stats = []
for nm, val, lines, disc, yy, xx in STATS:
    box = L(xx, yy, 125, 160)
    det = L(xx + 130, yy, 175, 160)
    d = min(box[2], box[3]) - 26
    kids = [E_panel(f"E {nm} icon box", box, 10), E_panel(f"E {nm} detail box", det, 10),
            layer(f"E {nm} disc ({disc})", mos(disc).resize((d, d), Image.LANCZOS), f"disc_{disc}_{d}",
                  box[0] + (box[2] - d) // 2, box[1] + (box[3] - d) // 2),
            E_text(f"E {nm} value", val, box, style="label", point=15),
            E_text(f"E {nm} caption", nm, (box[0], box[1] + 4, box[2], 16), style="normal", point=11,
                   color=COL["Y"], halign="center", valign="top"),
            E_text(f"E {nm} detail", "\n".join(lines), (det[0] + 8, det[1] + 8, det[2] - 12, det[3] - 12),
                   style="normal", point=13, color=COL["B"])]
    E_stats.append(group(f"E stat {nm}", kids))

# --- right panel: header, tabs, grid (backpack 2x10 + stash 7x10), ground column, bottom bar
gxE, gyE = L(705, 0)[0], L(0, 175)[1]
ce, se = 39, 42
E_grid_bp = [bam_states(f"E backpack slot r{r}c{c}", "SLOTITM", (r * 10 + c) % 5,
                        (gxE + c * se, gyE + r * se, ce, ce), STATES_SLOT) for r in range(2) for c in range(10)]
syE = gyE + 2 * se + 8
E_grid_st = [bam_states(f"E stash slot r{r}c{c}", "IVSLOT", (r * 10 + c) % 10,
                        (gxE + c * se, syE + r * se, ce, ce), STATES_SLOT) for r in range(7) for c in range(10)]
gwE = 9 * se + ce
for i, itm in enumerate(["COPPER", "BREAST1", "KEYSNTRY", "LENS04"]):
    E_icon(itm, (gxE + i * se, gyE, ce, ce), count=(3, 2, None, None)[i])
for i in range(61):
    mk = STASH_MARKS.get(i % len(STASH_ITEMS))
    E_icon(STASH_ITEMS[i % len(STASH_ITEMS)], (gxE + (i % 10) * se, syE + (i // 10) * se, ce, ce),
           tint=mk[1] if mk and mk[0] == "tint" else None, count=mk[1] if mk and mk[0] == "count" else None,
           plus=bool(mk and mk[0] == "plus"))
guide_box(gxE, gyE, gwE, 2 * se - 3)
guide_box(gxE, syE, gwE, 6 * se + ce)
annotate("Party Stash E", "E backpack 2x10", (gxE, gyE, gwE, 2 * se - 3), "mock")
annotate("Party Stash E", "E stash 7x10", (gxE, syE, gwE, 6 * se + ce), "mock")
sepE = Image.new("RGBA", (gwE, 3), (150, 90, 50, 255))
ImageDraw.Draw(sepE).line((0, 1, gwE, 1), fill=(210, 140, 80, 255))
hdr = L(705, 70, 560, 42)
gnd_hdr = L(1280, 70, 105, 42)
gxG = gxE + gwE + 14
E_ground = [bam_states(f"E ground slot {r}", "IVSLOT", (r + 4) % 10, (gxG, gyE + r * se, ce, ce), STATES_SLOT)
            for r in range(10) if gyE + r * se + ce <= L(0, 770)[1]]
E_icon("CLUB2", (gxG, gyE, ce, ce))
annotate("Party Stash E", f"E ground column 1x{len(E_ground)}", (gxG, gyE, ce, (len(E_ground) - 1) * se + ce), "slot")
E_right = [
    E_panel("E right panel", right, 16),
    E_panel("E header bar", hdr, 10),
    layer("E big bag (CONTBACK, overlaps title like LeUI)", bam_frame("CONTBACK", 0, 0, (50, 54)), "contbackE",
          L(722, 0)[0], L(0, 12)[1]),
    E_text("E stash weight", "816 / 2000 LB", (hdr[0] + 64, hdr[1], 200, hdr[3]), style="normal", point=15,
           color=COL["$"], halign="left", valign="center"),
    E_text("E sort", "Sort: Auto", (hdr[0] + hdr[2] - 130, hdr[1], 120, hdr[3]), style="label", point=15,
           halign="right"),
    E_panel("E ground header", gnd_hdr, 10),
    E_text("E ground title", "Ground 1/1", gnd_hdr, style="label", point=13),
    tab_strip("E", gxE - 2, L(0, 122)[1], 47, 24, TABS_SHORT[:8], active=0, gap=1, arrows=False),
    button("E tabs more", "ARROBUTT", (gxE + 8 * 48 + 2, L(0, 122)[1], 24, 24), seq=1),
    group("E backpack slots (SLOTITM)", E_grid_bp),
    layer("E backpack / stash separator", sepE, "sepE", gxE, gyE + 2 * se + 2),
    group("E stash slots (IVSLOT)", E_grid_st),
    group("E ground slots", E_ground),
    button("E ground prev", "ARROBUTT", L(1292, 790, 40, 40), seq=0),
    button("E ground next", "ARROBUTT", L(1350, 790, 40, 40), seq=1),
    button("E store all", "STRBUTT", L(708, 826, 180, 50), "Store all", point=15),
    layer("E gold pile (ICGOLD)", mos("ICGOLD").resize((56, 40), Image.LANCZOS), "icgoldE", L(990, 0)[0],
          L(0, 826)[1]),
    E_panel("E gold box", L(1092, 832, 135, 40), 8),
    E_text("E party gold", "1250", L(1092, 832, 135, 40), style="gold", point=16),
]
varE = group("Variant E - LeUI layout with PTEE textures (John's pick)", [
    layer("E backdrop (INVBG darkened)", bdE, "E_backdrop", 0, 0),
    E_panel("E title bar", title, 14),
    E_text("E title", "Inventory", (title[0], title[1], title[2] - 260, title[3]), style="label", point=24,
           font="EXOCET", color=COL["Y"], shadow=True),
    group("E left column (name, quick slots)", E_left),
    group("E body slots", body),
    E_doll,
    group("E stats blocks (bottom left)", E_stats),
    group("E right column (stash)", E_right),
    group("E items (sample)", E_items),
    button("E close (XBUTT)", "XBUTT", (982, 14, 38, 38)),
], visible=True)
varD["visible"] = False

mockups = group("Party Stash mockup (PTEE style)", [varC, varB, varA, varD, varE])

# ================================================================== 5. LIBRARY
usage = {}
for m in UI:
    for it in m["items"]:
        a = it.get("area")
        if not isinstance(a, list) or len(a) != 4 or a[2] <= 0 or a[3] <= 0:
            continue
        for kk in ("bam", "mosaic"):
            if kk in it:
                usage.setdefault(it[kk].upper(), (a[2], a[3]))

LIB = {
    "Buttons": ["NORMBUTT", "WIDEBUTT", "STRBUTT", "SHRTBUTT", "GENBUT1", "ARROBUTT", "XBUTT", "CHECKBUT", "CGPLUS",
                "CGMINUS", "JRNBUTT", "JRNDONE", "MAPBUTT", "OPTBUTT", "CIRCBUTT", "RADWEDGE", "TACTBUTT",
                "PAUSBUTT", "LVLBUTT", "QLOOTARW", "SIDEHNDL", "STRCHOOS", "STARTBUT", "CBUTT", "REFCONF",
                "SKLPLUS", "SKLMINUS"],
    "Tabs": ["TAB0", "TAB1", "TAB2", "TAB3", "TAB4", "TAB5", "TAB6", "TAB7", "TAB8"],
    "Slots & placeholders": ["IVSLOT", "SLOTSWRD", "SLOTITM", "SLOTARW", "SLOTWEAP", "QUICKSLT", "IVIARW", "IVISWRD",
                             "IVISHLD", "IVISCRL", "IVQIITM", "IVQIWEAP", "IVQIARRW", "IVPIBOW", "IVPICHST",
                             "IVPIEARL", "IVPIEARR", "IVPIEYER", "IVPIHNDL", "IVPIHNDR", "IVPILENS", "IVPIRING",
                             "IVPITATT", "IVPITETH", "IVPIWRST"],
    "Scrollbars & sliders": ["CGSCRL1", "SLDRSTAR"],
    "Icons (BAM)": ["CONTBACK", "IVENCM", "IVKISS"],
}
LIB_MOS = {
    "Panels & popups": ["POPUP1", "POPUP2", "POPUP4", "POPUP5", "POPUP6", "POPUP7", "OPTPOP1", "OPTPOP2", "LVLBG",
                        "STRROW", "JRNLOP", "VERPLATE", "SLIDERBG"],
    "Bars & frames": ["CONBG", "ACTBG", "PRTRTBG", "PRTRTNO0", "PRTRTNO1", "PRTRTTOP"],
    "Icons (MOS)": ["ICGOLD", "ICGOLDF", "ICPURSE", "ICPICKUP", "ICHPMAN", "ICHPBG", "ICAC", "ICMAGE", "ICPRIEST"],
}


class Packer:
    def __init__(self):
        self.x, self.y, self.row = 4, 4, 0

    def place(self, w, h):
        if self.x + w > W - 4:
            self.x, self.y, self.row = 4, self.y + self.row + 4, 0
        if self.y + h > H:
            self.x, self.y, self.row = 4, 4, 0  # wrap: overlap is fine, library groups are hidden
        p = (self.x, self.y)
        self.x += w + 4
        self.row = max(self.row, h)
        return p


lib_groups = []
for sect, names in LIB.items():
    pk = Packer()
    kids = []
    for res in names:
        cycles = bam(res)
        if not cycles:
            continue
        f0 = next((cy[0][0] for cy in cycles if cy), None)
        if f0 is None:
            continue
        if res in usage:
            uw, uh = usage[res]
            sx, sy = uw / f0.width, uh / f0.height
        else:
            sx = sy = LIB_SCALE if f0.width > 100 else 1.0
        cyc_groups = []
        for ci, cy in enumerate(cycles):
            frs = []
            for fi, (im, cx, cyy) in enumerate(cy):
                w2, h2 = max(1, round(im.width * sx)), max(1, round(im.height * sy))
                px, py = pk.place(w2, h2)
                st = STATES_BTN[fi] if fi < 4 and sect not in ("Slots & placeholders",) else f"f{fi}"
                frs.append(layer(f"{res} c{ci} f{fi} {st}", im.resize((w2, h2), Image.LANCZOS),
                                 f"lib_{res}_c{ci}_f{fi}_{w2}x{h2}", px, py, visible=True))
            if frs:
                cyc_groups.append(group(f"{res} cycle {ci}", frs))
        kids.append(group(f"{res} ({len(cycles)} cycles)", cyc_groups, visible=True))
    lib_groups.append(group(sect, kids, visible=False))
for sect, names in LIB_MOS.items():
    pk = Packer()
    kids = []
    for res in names:
        im = mos(res)
        if im is None:
            continue
        if res in usage:
            w2, h2 = usage[res]
            if w2 > 1024:
                w2, h2 = round(im.width * LIB_SCALE), round(im.height * LIB_SCALE)
        else:
            w2, h2 = round(im.width * LIB_SCALE), round(im.height * LIB_SCALE)
        px, py = pk.place(w2, h2)
        kids.append(layer(f"{res} ({w2}x{h2})", im.resize((w2, h2), Image.LANCZOS), f"libm_{res}_{w2}x{h2}", px,
                           py))
    lib_groups.append(group(sect, kids, visible=False))
# item icon sampler
pk = Packer()
icons = []
seen = set()
for n in g.names("ITM"):
    info = ie.itm_info(g, n)
    if not info or info["icon"] in seen or not info["name"] or info["name"] < 0:
        continue
    cyc = bam(info["icon"])
    if not cyc or not cyc[0]:
        continue
    seen.add(info["icon"])
    im = cyc[0][0][0]
    px, py = pk.place(im.width, im.height)
    icons.append(layer(f"{info['icon']} - {tlk[info['name']][:40]} ({n})", im, f"itemicon_{info['icon']}", px, py))
    if len(icons) >= 120:
        break
lib_groups.append(group("Item icons (sample of 120)", icons, visible=False))
lib_groups.append(group("Paperdolls (IVP*)", [dict(d, visible=True) for d in dolls], visible=False))
library = group("Library (hidden - reusable PTEE art)", lib_groups, visible=False)

# ================================================================== 6. ANNOTATIONS
annotations = group("Annotations (element names, sizes, coords)", [
    group(sect, nodes, visible=not sect.startswith("Background")) for sect, nodes in ANNOT.items()
], visible=False)

# keep only the main guides (too many guides hide the art): frame, action bar, variant E panels
GUIDES = {"h": {0, 768, ACTIONBAR_Y}, "v": {0, 1024}}
for r in (title, left, right):
    guide_box(*r)
root = [background, vanilla, actionbar, mockups, library, annotations]
manifest = {"width": W, "height": H, "root": root,
            "guides": {"h": sorted(v for v in GUIDES["h"] if 0 <= v <= H),
                       "v": sorted(v for v in GUIDES["v"] if 0 <= v <= W)}}
with open(os.path.join(BUILD, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=1, ensure_ascii=False)


def count(nodes):
    n = 0
    for x in nodes:
        n += 1
        if x["type"] == "group":
            n += count(x["children"])
    return n


print("nodes:", count(root), "pngs:", len(_saved), "guides:", len(manifest["guides"]["h"]),
      len(manifest["guides"]["v"]))
