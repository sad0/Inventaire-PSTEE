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

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

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
    return dict(layer(name, img, f"txt_{name}_{text}"[:80], area[0] + ox, area[1] + oy), kind="text")


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
LAYOUT = {}  # in-game geometry shared by variants F and G (written to design/build/layout.json for the mod)


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
    gr = group(name, kids)  # draw order: frame 0 at the bottom, other states above (hidden)
    if label_states is STATES_SLOT:
        gr["kind"] = "slot"
    elif label_states is STATES_BTN:
        gr["kind_bg"] = "button"  # engine-drawn: excluded from the flattened in-game backgrounds
    return gr


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
    return dict(layer(f"{nm} ({itm})", canvas, key, x, y), kind="item")


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

# ---- Variant F: art-direction guide (John, 2026-10-21): Variant E organisation, built only from PTEE pieces
# (WIRESBG cables, LOADBG frames, vanilla rails/frames/discs/plates), Lady of Pain (JRNLOP) as top keystone.
def nine(src, w, h, l, t, r, b, k=1.0):
    """9-slice `src` (borders l,t,r,b in src px) into w x h; borders drawn at scale k."""
    sw, sh = src.size
    L_, T_, R_, B_ = (max(1, round(v * k)) for v in (l, t, r, b))
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    xs = [(0, l, 0, L_), (l, sw - r, L_, w - R_), (sw - r, sw, w - R_, w)]
    ys = [(0, t, 0, T_), (t, sh - b, T_, h - B_), (sh - b, sh, h - B_, h)]
    for sx0, sx1, dx0, dx1 in xs:
        for sy0, sy1, dy0, dy1 in ys:
            if dx1 > dx0 and dy1 > dy0:
                out.alpha_composite(src.crop((sx0, sy0, sx1, sy1)).resize((dx1 - dx0, dy1 - dy0), Image.LANCZOS),
                                    (dx0, dy0))
    return out


wires = mos("WIRESBG").resize((1366, 768), Image.LANCZOS)
loadbg = mos("LOADBG").resize((1366, 768), Image.LANCZOS)
lb = loadbg.crop((112, 12, 1240, 762))
# replace the ladder side with the mirrored right border
right_strip = lb.crop((lb.width - 40, 0, lb.width, lb.height)).transpose(Image.FLIP_LEFT_RIGHT)
lb2 = lb.copy()
lb2.paste(Image.new("RGBA", (100, lb.height), (0, 0, 0, 0)), (0, 0))
lb2.paste(lb.crop((100, 0, 140, lb.height)).resize((60, lb.height)), (40, 0))  # stone filler over the ladder
lb2.paste(right_strip, (0, 0))
LB = lb2


def F_frame(name, rect, k=0.5):
    x, y, w, h = rect
    annotate("Party Stash F", name, rect, "mock")
    guide_box(*rect)
    return layer(name, nine(LB, w, h, 40, 66, 40, 82, k), f"Fframe_{w}x{h}_{k}", x, y)


def F_bar(name, rect):
    """Rounded rusty bar (vanilla message bar), 3-slice horizontally."""
    x, y, w, h = rect
    src = bg_piece("Message bar")
    annotate("Party Stash F", name, rect, "mock")
    return layer(name, nine(src, w, h, 30, 12, 30, 12, h / src.height), f"Fbar_{w}x{h}", x, y)


def F_slotframe(name, rect):
    """Red riveted slot frame (vanilla earring frame), 9-slice."""
    x, y, w, h = rect
    src = bg_piece("Earring frame left")
    return layer(name, nine(src, w, h, 22, 20, 22, 20, w / src.width), f"Fsf_{w}x{h}", x, y)


def F_text(name, text, rect, **kw):
    annotate("Party Stash F", name, rect, "text")
    return text_layer(name, text, rect, **kw)


def F_piece(name, piece, rect):
    x, y, w, h = rect
    annotate("Party Stash F", name, rect, "mock")
    return layer(name, bg_piece(piece).resize((w, h), Image.LANCZOS), f"Fp_{piece}_{w}x{h}", x, y)


F_items = []


def F_icon(itm, a, **kw):
    n = icon_in_slot(itm, a, **kw)
    if n:
        F_items.append(n)


def F_rail(prefix, piece, slots_prefix, rect, title):
    """A vanilla rail piece scaled into rect, slots placed on its baked cells, title above."""
    x, y, w, h = rect
    px, py, pw, ph = BG_PIECES[piece]
    sx, sy = w / pw, h / ph
    cells = [i["area"] for i in inv["items"] if i.get("slotinfo", "").split(".")[-1].startswith(slots_prefix)]
    kids = [F_piece(f"{prefix} rail ({piece})", piece, rect)]
    for n, a in enumerate(sorted(cells)):
        ca = (x + round((a[0] - px) * sx), y + round((a[1] - py) * sy), round(a[2] * sx), round(a[3] * sy))
        kids.append(bam_states(f"{prefix} slot {n}", "IVSLOT", n, ca, STATES_SLOT))
        LAYOUT.setdefault(prefix[2:], []).append(ca)
    kids.append(F_text(f"{prefix} title", title, (x, y - 22, w, 20), style="label", point=15))
    return group(prefix, kids), [k for k in kids if k.get("kind") == "slot"]


# --- frame layout (menu px). Usable area 1024x683.
LP = (10, 52, 462, 628)
RP = (478, 52, 536, 628)
F_bg = [layer("F WIRESBG (cables background, 1366x683 @ -171,0)", wires.crop((0, 0, 1366, ACTIONBAR_Y)),
              "WIRESBG_1366x683", BG_OFF, 0)]

# title band + Lady keystone + close
F_top = [
    F_bar("F title band", (120, 8, 784, 40)),
    F_text("F title", "Inventory", (150, 8, 300, 40), style="label", point=22, font="EXOCET", color=COL["Y"],
           shadow=True),
]
lady = mos("JRNLOP")
lw = 112
lh = round(lady.height * lw / lady.width)
F_top.append(layer("F Lady of Pain keystone (JRNLOP)", lady.resize((lw, lh), Image.LANCZOS), f"lady_{lw}",
                   512 - lw // 2, 0))
annotate("Party Stash F", "F Lady of Pain keystone", (512 - lw // 2, 0, lw, lh), "mock")
F_top.append(button("F close (XBUTT)", "XBUTT", (972, 4, 46, 46)))

# left column
F_left = [F_frame("F left frame (LOADBG 9-slice)", LP)]
F_left.append(F_bar("F name/class bar", (30, 82, 300, 34)))
F_left.append(F_text("F name", "The Nameless One", (30, 82, 170, 34), style="label", point=15))
F_left.append(F_text("F class", "Fighter", (200, 82, 130, 34), style="label", point=15))
rq, _ = F_rail("F quiver", "Personal items rail", "personal", (28, 150, 228, 54), "Quiver")
rw, _ = F_rail("F quick weapons", "Weapons rail", "weapon", (28, 236, 210, 58), "Quick Weapons")
ri, _ = F_rail("F quick items", "Personal items rail", "personal", (28, 324, 228, 54), "Quick Items")
F_left += [rq, rw, ri]
for i, itm in enumerate(["BOLT01", "BOLT03"]):
    F_icon(itm, (28 + round((529 - 505 + i * 50) * 0.8), 150 + round((112 - 98) * 54 / 68), 34, 34), count=40)

# paperdoll: reduced oval + 10 red riveted frames around it
s = 0.52
ov = bg_piece("Paperdoll oval")
ovw, ovh = round(ov.width * s), round(ov.height * s)
ox, oy = 286, 178
dt = mos("IVPNOA").copy()
dt.thumbnail((round(pa[2] * s), round(pa[3] * s)), Image.LANCZOS)
F_doll = [layer("F oval frame (INVBG cut-out)", ov.resize((ovw, ovh), Image.LANCZOS), "ovalF", ox, oy),
          layer("F paperdoll IVPNOA", dt, "dollF", ox + round((pa[0] - 154) * s) + (round(pa[2] * s) - dt.width) // 2,
                oy + round((pa[1] - 78) * s) + (round(pa[3] * s) - dt.height) // 2)]
fs, sl = 50, 34          # frame size, slot size inside
off = (fs - sl) // 2
body_pos = [("earringright0", 262, 122), ("earringleft0", 314, 122), ("chest0", 366, 122), ("wrist0", 418, 122),
            ("hand0", 418, 186), ("ring0", 418, 240), ("ring1", 418, 294),
            ("tattoo0", 278, 342), ("tattoo1", 330, 342), ("tattoo2", 382, 342)]
F_body = []
for i, (nm, x, y) in enumerate(body_pos):
    F_body.append(group(f"F body {nm}", [
        F_slotframe(f"F frame {nm}", (x, y, fs, fs)),
        bam_states(f"F body slot {nm}", "IVSLOT", i, (x + off, y + off, sl, sl), STATES_SLOT),
    ]))
annotate("Party Stash F", "F body slots (10 riveted frames)", (262, 122, 206, 270), "slot")

# stats: 2x2 blocks = disc piece + plate piece
F_stats = []
for nm, val, lines, piece, bx, by in (("AC", "8", ["Base: 10", "Dex: -1", "Tattoo: -1"], "AC disc", 24, 408),
                                      ("THAC0", "17", ["Base: 18", "Prof.: -1", "Weapon: 0"], "AC disc", 244, 408),
                                      ("HP", "64/64", ["Class: 1d10", "Con: +2"], "HP disc", 24, 534),
                                      ("Damage", "1d6+1", ["Weapon: 1d6", "Str: +1"], "HP disc", 244, 534)):
    disc = (bx, by + 14, 78, 84)
    plate = (bx + 70, by, 140, 112)
    F_stats.append(group(f"F stat {nm}", [
        layer(f"F {nm} plate (message bar 9-slice)", nine(bg_piece("Message bar"), plate[2], plate[3], 30, 14, 30, 14,
                                                          0.9), f"Fplate_{plate[2]}x{plate[3]}", plate[0], plate[1]),
        F_piece(f"F {nm} disc ({piece})", piece, disc),
        F_text(f"F {nm} value", val, (disc[0], disc[1] + 22, disc[2], 40), style="label", point=15),
        F_text(f"F {nm} caption", nm, (disc[0], disc[1] - 14, disc[2], 14), style="normal", point=11,
               color=COL["Y"], halign="center", valign="top"),
        F_text(f"F {nm} detail", "\n".join(lines), (plate[0] + 18, plate[1] + 14, plate[2] - 26, plate[3] - 24),
               style="normal", point=12, color=COL["B"]),
    ]))

# right column: header, tabs, grid from the backpack rail piece, ground column, bottom bar
F_right = [F_frame("F right frame (LOADBG 9-slice)", RP)]
F_right.append(F_bar("F header bar", (496, 82, 448, 34)))
F_right.append(F_text("F stash weight", "816 / 2000 LB", (574, 82, 200, 34), style="normal", point=15,
                      color=COL["$"], halign="left", valign="center"))
F_right.append(button("F sort", "STRBUTT", (830, 85, 108, 28), "Sort: Auto", point=13))
F_right.append(tab_strip("F", 496, 122, 48, 22, TABS_SHORT, active=0, gap=1, arrows=False))
# backpack rail piece: rail part only (x 470..996 of the piece), 2 rows; stash = same rail stretched to 7 rows
rx0, ry0 = 470, 500
rail_src = invbg.crop((rx0 - BG_OFF, ry0, 996 - BG_OFF, 624))
k = 0.82
GXF, GYF = 494, 152
bp_w, bp_h = round(rail_src.width * k), round(rail_src.height * k)
F_right.append(layer("F backpack rail (vanilla piece x0.82)", rail_src.resize((bp_w, bp_h), Image.LANCZOS),
                     "Fbprail", GXF, GYF))
annotate("Party Stash F", "F backpack 2x10 (vanilla rail)", (GXF, GYF, bp_w, bp_h), "mock")
top, row = rail_src.crop((0, 0, rail_src.width, 65)), rail_src.crop((0, 65, rail_src.width, 115))
bot = rail_src.crop((0, 115, rail_src.width, rail_src.height))
st = Image.new("RGBA", (rail_src.width, 65 + 6 * 50 + bot.height))
st.paste(top, (0, 0))
for r in range(6):
    st.paste(row, (0, 65 + r * 50))
st.paste(bot, (0, 65 + 300))
SYF = GYF + bp_h + 6
st_w, st_h = round(st.width * k), round(st.height * k)
F_right.append(layer("F stash rail (vanilla rail stretched to 7 rows)", st.resize((st_w, st_h), Image.LANCZOS),
                     "Fstrail", GXF, SYF))
annotate("Party Stash F", "F stash 7x10 (vanilla rail x7)", (GXF, SYF, st_w, st_h), "mock")
cx = [round(8 * k) + c * 41 for c in range(10)]   # uniform 41 px step (same cells in variant G)
cell = round(43 * k)
LAYOUT["backpack"] = [(GXF + cx[c], GYF + round((15 + 50 * r) * k), cell, cell) for c in range(10) for r in range(2)]
LAYOUT["stash"] = [(GXF + cx[c], SYF + round((15 + 50 * r) * k), cell, cell) for r in range(7) for c in range(10)]
F_bp = [bam_states(f"F backpack slot r{r}c{c}", "SLOTITM", (r + c) % 5,
                   (GXF + cx[c], GYF + round((15 + 50 * r) * k), cell, cell), STATES_SLOT)
        for r in range(2) for c in range(10)]
F_st = [bam_states(f"F stash slot r{r}c{c}", "IVSLOT", (r + c) % 10,
                   (GXF + cx[c], SYF + round((15 + 50 * r) * k), cell, cell), STATES_SLOT)
        for r in range(7) for c in range(10)]
for i in range(64):
    mk = STASH_MARKS.get(i % len(STASH_ITEMS))
    F_icon(STASH_ITEMS[i % len(STASH_ITEMS)], (GXF + cx[i % 10], SYF + round((15 + 50 * (i // 10)) * k), cell, cell),
           tint=mk[1] if mk and mk[0] == "tint" else None, count=mk[1] if mk and mk[0] == "count" else None,
           plus=bool(mk and mk[0] == "plus"))
F_right += [group("F backpack slots", F_bp), group("F stash slots", F_st)]
# ground column: the vanilla arched ground panel, squeezed to one column
gpx, gpy = GXF + bp_w + 8, 116
gnd = bg_piece("Ground column")
F_right.append(layer("F ground column (vanilla piece, 9-slice 1 col)", nine(gnd, 58, 440, 22, 70, 22, 20, 0.6),
                     "Fground", gpx, gpy))
annotate("Party Stash F", "F ground column", (gpx, gpy, 58, 440), "mock")
LAYOUT["ground"] = [(gpx + 12, gpy + 34 + r * 40, 34, 34) for r in range(10)]
F_right.append(group("F ground slots", [bam_states(f"F ground slot {r}", "IVSLOT", r, a, STATES_SLOT)
                                        for r, a in enumerate(LAYOUT["ground"])]))
LAYOUT["ground_prev"], LAYOUT["ground_next"] = (gpx + 2, gpy + 450, 26, 26), (gpx + 30, gpy + 450, 26, 26)
LAYOUT["ground_page"] = (gpx - 4, gpy + 476, 66, 18)
F_right.append(button("F ground prev", "ARROBUTT", LAYOUT["ground_prev"], seq=0))
F_right.append(button("F ground next", "ARROBUTT", LAYOUT["ground_next"], seq=1))
F_right.append(F_text("F ground page", "1/1", LAYOUT["ground_page"], style="label", point=13))
F_right.append(button("F store all", "STRBUTT", (496, 604, 140, 40), "Store all", point=15))
F_right.append(F_piece("F gold box (vanilla piece)", "Gold box", (812, 588, 76, 70)))
F_right.append(layer("F gold coins (ICGOLD)", mos("ICGOLD").resize((60, 50), Image.LANCZOS), "icgoldF", 820, 596))
F_right.append(F_text("F party gold", "1250", (888, 606, 90, 30), style="gold", point=16))

# in-game geometry for the mod (tools/build_mod.py)
LAYOUT["body"] = {nm: (x + off, y + off, sl, sl) for nm, x, y in body_pos}
LAYOUT["paperdoll"] = (ox + round((pa[0] - 154) * s), oy + round((pa[1] - 78) * s), round(pa[2] * s), round(pa[3] * s))
LAYOUT["stats"] = {nm: {"disc": (bx, by + 14, 78, 84), "plate": (bx + 70, by, 140, 112)}
                   for nm, bx, by in (("AC", 24, 408), ("THAC0", 244, 408), ("HP", 24, 534), ("Damage", 244, 534))}
LAYOUT["text"] = {"title": (150, 8, 300, 40), "name": (30, 82, 170, 34), "class": (200, 82, 130, 34),
                  "weight": (574, 82, 200, 34), "gold": (888, 606, 90, 30)}
LAYOUT["titles"] = {"Quiver": (28, 128, 228, 20), "Quick Weapons": (28, 214, 210, 20), "Quick Items": (28, 302, 228, 20)}
LAYOUT["buttons"] = {"close": (972, 4, 46, 46), "sort": (830, 85, 108, 28), "store_all": (496, 604, 140, 40),
                     "tabs": [(496 + i * 49, 122, 48, 22) for i in range(8)], "tab_names": TABS_SHORT}
LAYOUT["menu"] = {"width": W, "height": H, "bg_offset": BG_OFF}

varF = group("Variant F - Art guide: E layout built from PTEE pieces (WIRESBG, LOADBG, rails, frames)", [
    group("F background (cables)", F_bg),
    group("F left column", F_left),
    group("F paperdoll", F_doll),
    group("F body slots", F_body),
    group("F stats blocks", F_stats),
    group("F right column", F_right),
    group("F items (sample)", F_items),
    group("F top (title, Lady keystone, close)", F_top),
], visible=True)
varE["visible"] = False

# ---- Variant G: Variant F organisation dressed with the generated art (design/art/gen, SwarmUI, no game art)
# except the Lady (JRNLOP), paperdoll, buttons and discs which stay game assets.
GEN = os.path.join(ROOT, "design", "art", "gen")


def gen(name):
    return Image.open(os.path.join(GEN, name)).convert("RGBA")


g_frame = gen("final/slot_frame_22.png").crop((50, 49, 975, 975))   # 925x925, border ~140 (+bolts)
g_panel = gen("final/panel_frame_31.png").crop((50, 49, 975, 975))
g_fill = gen("final/plate_fill_61_tile.png")
g_rail = gen("final/rail_body_71.png").crop((39, 66, 1490, 314))
g_pipes = [gen("final/pipes_41.png").crop((29, 59, 1512, 442)), gen("final/pipes_42.png").crop((29, 59, 1512, 442))]
g_cables = gen("cables_bg_51.png")


def tiled(w, h, k=0.25):
    """Tile the plate fill scaled by k over w x h."""
    t = g_fill.resize((round(g_fill.width * k), round(g_fill.height * k)), Image.LANCZOS)
    out = Image.new("RGBA", (w, h))
    for yy in range(0, h, t.height):
        for xx in range(0, w, t.width):
            out.paste(t, (xx, yy))
    return out


def G_box(name, rect, border=22, fill=True, k_fill=0.25, frame=None, dark=0):
    """Riveted frame (9-slice of the generated frame) with an optional tiled rust-plate fill."""
    x, y, w, h = rect
    fr = frame or g_panel
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if fill:
        inset = border // 2
        f = tiled(w - 2 * inset, h - 2 * inset, k_fill)
        if dark:
            f = Image.alpha_composite(f, Image.new("RGBA", f.size, (0, 0, 0, dark)))
        img.paste(f, (inset, inset))
    k = border / 150
    img.alpha_composite(nine(fr, w, h, 165, 165, 165, 165, k))
    annotate("Party Stash G", name, rect, "mock")
    return layer(name, img, f"G_{name}_{w}x{h}", x, y)


def G_text(name, text, rect, **kw):
    annotate("Party Stash G", name, rect, "text")
    return text_layer(name, text, rect, **kw)


def G_rail(name, rect):
    x, y, w, h = rect
    return layer(name, nine(g_rail, w, h, 230, 0, 230, 0, h / g_rail.height), f"G_rail_{w}x{h}", x, y)


def G_cells(prefix, x0, y0, cols, rows, cell, step, res="IVSLOT"):
    """Recessed dark cells painted on the plate + the game slot squares (hidden by default)."""
    w, h = (cols - 1) * step + cell, (rows - 1) * step + cell
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for r in range(rows):
        for c in range(cols):
            cx, cy = c * step, r * step
            d.rectangle((cx, cy, cx + cell - 1, cy + cell - 1), fill=(12, 10, 8, 200))
            d.line((cx, cy, cx + cell - 1, cy), fill=(0, 0, 0, 255), width=2)
            d.line((cx, cy, cx, cy + cell - 1), fill=(0, 0, 0, 255), width=2)
            d.line((cx, cy + cell - 1, cx + cell - 1, cy + cell - 1), fill=(150, 90, 50, 200))
            d.line((cx + cell - 1, cy, cx + cell - 1, cy + cell - 1), fill=(150, 90, 50, 200))
    slots = [bam_states(f"{prefix} slot r{r}c{c}", res, (r + c) % (10 if res == "IVSLOT" else 5),
                        (x0 + c * step, y0 + r * step, cell, cell), STATES_SLOT)
             for r in range(rows) for c in range(cols)]
    guide_box(x0, y0, w, h)
    return [layer(f"{prefix} cells (painted recesses)", img, f"Gcells_{cols}x{rows}_{cell}_{step}", x0, y0),
            group(f"{prefix} slot squares (game IVSLOT)", slots)]


G_items = []


def G_icon(itm, a, **kw):
    n = icon_in_slot(itm, a, **kw)
    if n:
        G_items.append(n)


# background: generated radiating cables, covering 1366x683
cb = g_cables.resize((1366, round(g_cables.height * 1366 / g_cables.width)), Image.LANCZOS)
cb = cb.crop((0, (cb.height - ACTIONBAR_Y) // 2, 1366, (cb.height - ACTIONBAR_Y) // 2 + ACTIONBAR_Y))
G_bg = [layer("G cables background (cables_bg_51, 1366x683 @ -171,0)", cb, "G_cables", BG_OFF, 0)]
# pipe connectors bridging the two columns (behind the frames)
p1 = g_pipes[0].resize((300, round(300 * g_pipes[0].height / g_pipes[0].width)), Image.LANCZOS)
p2 = g_pipes[1].resize((260, round(260 * g_pipes[1].height / g_pipes[1].width)), Image.LANCZOS)
# vertical pipe bundles bridging the seam between the two columns (drawn above the frames)
pv = g_pipes[1].rotate(90, expand=True)
pv = pv.resize((44, round(44 * pv.height / pv.width)), Image.LANCZOS)
G_conn = [layer("G pipes connector (seam, upper)", pv, "G_pv", 475 - pv.width // 2, 170),
          layer("G pipes connector (seam, lower)", pv.transpose(Image.FLIP_TOP_BOTTOM), "G_pv2", 475 - pv.width // 2,
                420)]

G_cols = [G_box("G left column frame", LP, 30), G_box("G right column frame", RP, 30)]

G_top = [G_box("G title band", (120, 6, 784, 44), 14, k_fill=0.15, dark=60),
         G_text("G title", "Inventory", (150, 6, 300, 44), style="label", point=22, font="EXOCET", color=COL["Y"],
                shadow=True),
         layer("G Lady of Pain keystone (JRNLOP)", lady.resize((lw, lh), Image.LANCZOS), f"lady_{lw}",
               512 - lw // 2, 0),
         button("G close (XBUTT)", "XBUTT", (972, 4, 46, 46))]

G_left = [G_box("G name/class bar", (28, 80, 304, 38), 12, k_fill=0.15, dark=80),
          G_text("G name", "The Nameless One", (30, 82, 170, 34), style="label", point=15),
          G_text("G class", "Fighter", (200, 82, 130, 34), style="label", point=15)]
for title_txt, y, n, res in (("Quiver", 150, 5, "SLOTARW"), ("Quick Weapons", 236, 4, "SLOTSWRD"),
                             ("Quick Items", 324, 5, "SLOTITM")):
    areas = LAYOUT[title_txt.lower()]
    x0_, y0_ = areas[0][0], areas[0][1]
    w_ = areas[-1][0] + areas[-1][2] - x0_
    cs_ = areas[0][2]
    kids = [G_rail(f"G {title_txt} rail (rail_body_71)", (x0_ - 20, y0_ - 8, w_ + 40, cs_ + 16)),
            G_text(f"G {title_txt} title", title_txt, (x0_ - 20, y0_ - 30, w_ + 40, 20), style="label", point=15)]
    for i, a in enumerate(areas):
        kids.append(layer(f"G {title_txt} frame {i}", g_frame.resize((cs_ + 12, cs_ + 12), Image.LANCZOS),
                          f"G_sf_{cs_ + 12}", a[0] - 6, a[1] - 6))
        kids.append(bam_states(f"G {title_txt} slot {i}", res, i % 4, a, STATES_SLOT))
    G_left.append(group(f"G {title_txt}", kids))
G_icon("BOLT01", LAYOUT["quiver"][0], count=40)
G_icon("BOLT03", LAYOUT["quiver"][1], count=40)
G_icon("ADDAGGER", LAYOUT["quick weapons"][0])
G_icon("EYEBALL", LAYOUT["quick items"][0])

G_doll = [layer("G oval frame (game)", ov.resize((ovw, ovh), Image.LANCZOS), "ovalF", ox, oy),
          dict(F_doll[1], name="G paperdoll IVPNOA")]
G_body = []
for i, (nm, x, y) in enumerate(body_pos):
    G_body.append(group(f"G body {nm}", [
        layer(f"G frame {nm} (slot_frame_22)", g_frame.resize((fs, fs), Image.LANCZOS), f"G_sf_{fs}", x, y),
        bam_states(f"G body slot {nm}", "IVSLOT", i, (x + off, y + off, sl, sl), STATES_SLOT),
    ]))
G_icon("AMBEAR", (262 + off, 122 + off, sl, sl))
G_icon("BRORING", (418 + off, 240 + off, sl, sl))
G_icon("TTAC1", (278 + off, 342 + off, sl, sl))

G_stats = []
for nm, val, lines, piece, bx, by in (("AC", "8", ["Base: 10", "Dex: -1", "Tattoo: -1"], "AC disc", 24, 408),
                                      ("THAC0", "17", ["Base: 18", "Prof.: -1", "Weapon: 0"], "AC disc", 244, 408),
                                      ("HP", "64/64", ["Class: 1d10", "Con: +2"], "HP disc", 24, 534),
                                      ("Damage", "1d6+1", ["Weapon: 1d6", "Str: +1"], "HP disc", 244, 534)):
    disc = (bx, by + 14, 78, 84)
    plate = (bx + 70, by, 140, 112)
    G_stats.append(group(f"G stat {nm}", [
        G_box(f"G {nm} plate", plate, 14, k_fill=0.18, dark=70),
        layer(f"G {nm} disc ({piece}, game)", bg_piece(piece).resize((disc[2], disc[3]), Image.LANCZOS),
              f"Fp_{piece}_{disc[2]}x{disc[3]}", disc[0], disc[1]),
        G_text(f"G {nm} value", val, (disc[0], disc[1] + 22, disc[2], 40), style="label", point=15),
        G_text(f"G {nm} caption", nm, (disc[0], disc[1] - 14, disc[2], 14), style="normal", point=11,
               color=COL["Y"], halign="center", valign="top"),
        G_text(f"G {nm} detail", "\n".join(lines), (plate[0] + 18, plate[1] + 14, plate[2] - 26, plate[3] - 24),
               style="normal", point=12, color=COL["B"]),
    ]))

cellG, stepG = cell, 41
GXG, GYG = LAYOUT["backpack"][0][0], LAYOUT["backpack"][0][1]
gwG = 9 * stepG + cellG
SYG = LAYOUT["stash"][0][1]
G_right = [
    G_box("G header bar", (496, 80, 448, 38), 12, k_fill=0.15, dark=80),
    G_text("G stash weight", "816 / 2000 LB", (574, 82, 200, 34), style="normal", point=15, color=COL["$"],
           halign="left", valign="center"),
    button("G sort", "STRBUTT", (830, 85, 108, 28), "Sort: Auto", point=13),
    tab_strip("G", 496, 124, 48, 22, TABS_SHORT, active=0, gap=1, arrows=False),
    G_box("G backpack well", (GXG - 12, GYG - 12, gwG + 24, 2 * stepG - stepG + cellG + 24), 18, k_fill=0.2,
          dark=40, frame=g_frame),
    *G_cells("G backpack", GXG, GYG, 10, 2, cellG, stepG, res="SLOTITM"),
    G_box("G stash well", (GXG - 12, SYG - 12, gwG + 24, 6 * stepG + cellG + 24), 18, k_fill=0.2, dark=60,
          frame=g_frame),
    *G_cells("G stash", GXG, SYG, 10, 7, cellG, stepG),
    G_box("G ground column", (gpx, gpy, 58, 448), 16, k_fill=0.2, dark=60, frame=g_frame),
    *G_cells("G ground", LAYOUT["ground"][0][0], LAYOUT["ground"][0][1], 1, 10, 34, 40),
    button("G ground prev", "ARROBUTT", LAYOUT["ground_prev"], seq=0),
    button("G ground next", "ARROBUTT", LAYOUT["ground_next"], seq=1),
    layer("G ground pickup hand (ICPICKUP)", mos("ICPICKUP").resize((14, 26), Image.LANCZOS), "pickupG", gpx + 22, gpy + 6),
    button("G store all", "STRBUTT", (496, 604, 140, 40), "Store all", point=15),
    G_box("G gold box", (800, 592, 196, 52), 12, k_fill=0.15, dark=80),
    layer("G gold coins (ICGOLD)", mos("ICGOLD").resize((52, 44), Image.LANCZOS), "icgoldG", 812, 596),
    G_text("G party gold", "1250", (870, 602, 110, 30), style="gold", point=16),
]
for i in range(5):
    G_icon(["COPPER", "BREAST1", "KEYSNTRY", "LENS04", "CLUB"][i], (GXG + i * stepG, GYG, cellG, cellG),
           count=(3, 2, None, None, None)[i])
for i in range(64):
    mk = STASH_MARKS.get(i % len(STASH_ITEMS))
    G_icon(STASH_ITEMS[i % len(STASH_ITEMS)], (GXG + (i % 10) * stepG, SYG + (i // 10) * stepG, cellG, cellG),
           tint=mk[1] if mk and mk[0] == "tint" else None, count=mk[1] if mk and mk[0] == "count" else None,
           plus=bool(mk and mk[0] == "plus"))
G_icon("CLUB2", LAYOUT["ground"][0])

varG = group("Variant G - Generated art (SwarmUI) on the F organisation", [
    group("G background (generated cables)", G_bg),
    group("G column frames (generated frame + rust plate)", G_cols),
    group("G pipe connectors (generated)", G_conn),
    group("G left column", G_left),
    group("G paperdoll", G_doll),
    group("G body slots", G_body),
    group("G stats blocks", G_stats),
    group("G right column", G_right),
    group("G items (sample)", G_items),
    group("G top (title, Lady keystone, close)", G_top),
], visible=True)
varF["visible"] = False

# ---- Variant H (John 2026-10-22): F palette, tentacular pipes invading the whole background, zones delimited by
# pipes and materials. Background = SwarmUI img2img of tools/pipes_guide.py (creativity 0.45, seed 12), colour
# matched to variant F (tools/recolor.py, 85 %). UI pieces on top use the same LAYOUT as F/G.
h_bg = Image.open(os.path.join(ROOT, "design", "art", "h", "bg_h.png")).convert("RGBA").resize((1366, ACTIONBAR_Y),
                                                                                               Image.LANCZOS)


def ellipse_cut(img, inset=2, feather=1.5):
    """Clean elliptical cut-out (no square corners)."""
    m = Image.new("L", (img.width * 4, img.height * 4), 0)
    ImageDraw.Draw(m).ellipse((inset * 4, inset * 4, (img.width - inset) * 4, (img.height - inset) * 4), fill=255)
    m = m.resize(img.size, Image.LANCZOS).filter(ImageFilter.GaussianBlur(feather))
    out = img.copy()
    out.putalpha(ImageChops.multiply(out.getchannel("A"), m))
    return out


def H_cells(prefix, areas, res="IVSLOT"):
    """Recessed dark cells at the slot areas (the engine draws slot squares/items over them)."""
    kids = []
    for i, a in enumerate(areas):
        x, y, w, h = a
        c = Image.new("RGBA", (w + 4, h + 4), (0, 0, 0, 0))
        d = ImageDraw.Draw(c)
        d.rounded_rectangle((0, 0, w + 3, h + 3), radius=4, fill=(8, 7, 5, 235), outline=(0, 0, 0, 255), width=2)
        d.line((3, h + 2, w + 2, h + 2), fill=(120, 84, 52, 170))
        d.line((w + 2, 3, w + 2, h + 2), fill=(120, 84, 52, 170))
        kids.append(layer(f"{prefix} cell {i}", c, f"Hcell_{w}x{h}", x - 2, y - 2))
        kids.append(bam_states(f"{prefix} slot {i}", res, i % (10 if res == "IVSLOT" else 4), a, STATES_SLOT))
    return group(prefix, kids)


H_items = []


def H_icon(itm, a, **kw):
    n = icon_in_slot(itm, a, **kw)
    if n:
        H_items.append(n)


ov_cut = ellipse_cut(ov.resize((ovw, ovh), Image.LANCZOS))
H_doll = [layer("H oval frame (game, clean elliptical cut)", ov_cut, "ovalH", ox, oy),
          dict(F_doll[1], name="H paperdoll IVPNOA")]
H_left = [H_cells("H quiver", LAYOUT["quiver"], "SLOTARW"), H_cells("H quick weapons", LAYOUT["quick weapons"], "SLOTSWRD"),
          H_cells("H quick items", LAYOUT["quick items"], "SLOTITM"),
          H_cells("H body slots", list(LAYOUT["body"].values()))]
for t_, r_ in LAYOUT["titles"].items():
    H_left.append(text_layer(f"H {t_} title", t_, r_, style="label", point=15))
H_left += [text_layer("H name", "The Nameless One", LAYOUT["text"]["name"], style="label", point=15),
           text_layer("H class", "Fighter", LAYOUT["text"]["class"], style="label", point=15)]
H_stats = []
for nm, stt in LAYOUT["stats"].items():
    dd, pp = stt["disc"], stt["plate"]
    piece = "AC disc" if nm in ("AC", "THAC0") else "HP disc"
    H_stats.append(group(f"H stat {nm}", [
        layer(f"H {nm} disc ({piece}, elliptical cut)", ellipse_cut(bg_piece(piece).resize((dd[2], dd[3]), Image.LANCZOS)),
              f"Hdisc_{piece}", dd[0], dd[1]),
        text_layer(f"H {nm} value", {"AC": "8", "THAC0": "17", "HP": "64/64", "Damage": "1d6+1"}[nm],
                   (dd[0], dd[1] + 22, dd[2], 40), style="label", point=15),
        text_layer(f"H {nm} caption", nm, (dd[0], dd[1] - 14, dd[2], 14), style="normal", point=11, color=COL["Y"],
                   halign="center", valign="top"),
    ]))
H_right = [
    H_cells("H backpack", LAYOUT["backpack"], "SLOTITM"),
    H_cells("H stash", LAYOUT["stash"]),
    H_cells("H ground", LAYOUT["ground"]),
    text_layer("H stash weight", "816 / 2000 LB", LAYOUT["text"]["weight"], style="normal", point=15, color=COL["$"],
               halign="left", valign="center"),
    button("H sort", "STRBUTT", LAYOUT["buttons"]["sort"], "Sort: Auto", point=13),
    tab_strip("H", 496, 122, 48, 22, TABS_SHORT, active=0, gap=1, arrows=False),
    button("H ground prev", "ARROBUTT", LAYOUT["ground_prev"], seq=0),
    button("H ground next", "ARROBUTT", LAYOUT["ground_next"], seq=1),
    button("H store all", "STRBUTT", LAYOUT["buttons"]["store_all"], "Store all", point=15),
    layer("H gold coins (ICGOLD)", mos("ICGOLD").resize((52, 44), Image.LANCZOS), "icgoldG", 812, 596),
    text_layer("H party gold", "1250", LAYOUT["text"]["gold"], style="gold", point=16),
]
for i, itm in enumerate(["COPPER", "BREAST1", "KEYSNTRY", "LENS04", "CLUB"]):
    H_icon(itm, LAYOUT["backpack"][i * 2], count=(3, 2, None, None, None)[i])
for i in range(64):
    mk = STASH_MARKS.get(i % len(STASH_ITEMS))
    H_icon(STASH_ITEMS[i % len(STASH_ITEMS)], LAYOUT["stash"][i], tint=mk[1] if mk and mk[0] == "tint" else None,
           count=mk[1] if mk and mk[0] == "count" else None, plus=bool(mk and mk[0] == "plus"))
varH = group("Variant H - Tentacular pipes (SwarmUI img2img of the pipes guide, F palette)", [
    layer("H background (generated from guide, recoloured to F)", h_bg, "H_bg", BG_OFF, 0),
    group("H left column", H_left),
    group("H paperdoll", H_doll),
    group("H stats", H_stats),
    group("H right column", H_right),
    group("H items (sample)", H_items),
    group("H top", [
        text_layer("H title", "Inventory", LAYOUT["text"]["title"], style="label", point=22, font="EXOCET",
                   color=COL["Y"], shadow=True),
        layer("H Lady of Pain keystone (JRNLOP)", lady.resize((lw, lh), Image.LANCZOS), f"lady_{lw}", 512 - lw // 2, 0),
        button("H close (XBUTT)", "XBUTT", LAYOUT["buttons"]["close"]),
    ]),
], visible=True)
varG["visible"] = False

# ---- Variant J (John 2026-10-22): John's painted inventory as is (x2 SwarmUI, pieces detached + inpainted),
# geometry in design/build/layout_j.json (tools/variant_j.py). Detached pieces get hover/pressed/disabled states.
LJ = json.load(open(os.path.join(BUILD, "layout_j.json"), encoding="utf-8"))
JD = os.path.join(ROOT, "design", "art", "j")
j_bg = Image.open(os.path.join(JD, "bg_clean_2x.png")).convert("RGBA").resize(tuple(LJ["menu"]["bg_size"]),
                                                                              Image.LANCZOS)


def part_states(name, rect, label_states=STATES_BTN, visible=True):
    """Detached piece + generated states (normal, hover = brighter, pressed = darker, disabled = grey)."""
    x, y, w, h = rect
    base = Image.open(os.path.join(JD, "parts", f"{name}.png")).convert("RGBA").resize((w, h), Image.LANCZOS)
    a = base.getchannel("A")
    rgb = base.convert("RGB")
    states = [rgb, ImageEnhance.Brightness(rgb).enhance(1.35), ImageEnhance.Brightness(rgb).enhance(0.7),
              ImageEnhance.Brightness(ImageEnhance.Color(rgb).enhance(0.15)).enhance(0.6)]
    kids = []
    for i, (st, im) in enumerate(zip(["normal", "hover", "pressed", "disabled"], states)):
        im = im.convert("RGBA")
        im.putalpha(a)
        kids.append(layer(f"{name} - {st}", im, f"J_{name}_{st}_{w}x{h}", x, y, visible=visible and i == 0))
    gr = group(f"J {name} (detached, 4 states)", kids)
    gr["kind_bg"] = "button"  # engine-drawn in the mod (BAM)
    return gr


def J_cells(prefix, areas, res="IVSLOT"):
    kids = []
    for i, a in enumerate(areas):
        x, y, w, h = a
        c = Image.new("RGBA", (w + 4, h + 4), (0, 0, 0, 0))
        d = ImageDraw.Draw(c)
        d.rounded_rectangle((0, 0, w + 3, h + 3), radius=5, fill=(6, 5, 4, 200), outline=(0, 0, 0, 230), width=2)
        d.line((4, h + 2, w, h + 2), fill=(140, 96, 58, 150))
        d.line((w + 2, 4, w + 2, h), fill=(140, 96, 58, 150))
        kids.append(layer(f"{prefix} cell {i}", c, f"Jcell_{w}x{h}", x - 2, y - 2))
        ncyc = len([c for c in bam(res) if c])
        kids.append(bam_states(f"{prefix} slot {i}", res, i % ncyc, a, STATES_SLOT))
    return group(prefix, kids)


J_items = []


def J_icon(itm, a, **kw):
    n = icon_in_slot(itm, a, **kw)
    if n:
        J_items.append(n)


pdJ = LJ["paperdoll"]
dollJ = mos("IVPNOA").copy()
dollJ.thumbnail((pdJ[2], pdJ[3]), Image.LANCZOS)
J_left = [J_cells("J quiver", LJ["quiver"], "SLOTARW"), J_cells("J quick weapons", LJ["quick weapons"], "SLOTSWRD"),
          J_cells("J quick items", LJ["quick items"], "SLOTITM"), J_cells("J body slots", list(LJ["body"].values()))]
for t_, r_ in LJ["titles"].items():
    J_left.append(text_layer(f"J {t_} title", t_, r_, style="label", point=14))
J_left += [text_layer("J name", "The Nameless One", LJ["text"]["name"], style="label", point=14),
           text_layer("J class", "Fighter", LJ["text"]["class"], style="label", point=14)]
J_stats = []
for nm, stt in LJ["stats"].items():
    dd, pp = stt["disc"], stt["plate"]
    J_stats.append(group(f"J stat {nm}", [
        text_layer(f"J {nm} value", {"AC": "8", "THAC0": "17", "HP": "64/64", "Damage": "1d6+1"}[nm],
                   (dd[0], dd[1] + 14, dd[2], 34), style="label", point=15),
        text_layer(f"J {nm} caption", nm, (dd[0], dd[1] - 16, dd[2], 14), style="normal", point=11, color=COL["Y"],
                   halign="center", valign="top"),
        text_layer(f"J {nm} detail", {"AC": "Base: 10\nDex: -1", "THAC0": "Base: 18\nProf.: -1",
                                      "HP": "Class: 1d10\nCon: +2", "Damage": "Weapon: 1d6\nStr: +1"}[nm],
                   (pp[0] + 10, pp[1] + 10, pp[2] - 16, pp[3] - 16), style="normal", point=12, color=COL["B"]),
    ]))
J_right = [J_cells("J backpack", LJ["backpack"], "SLOTITM"), J_cells("J stash", LJ["stash"]),
           J_cells("J ground", LJ["ground"]),
           text_layer("J stash weight", "816 / 2000 LB", LJ["text"]["weight"], style="normal", point=15, color=COL["$"],
                      halign="left", valign="center"),
           text_layer("J sort", "Sort: Auto", LJ["buttons"]["sort"], style="label", point=14, halign="right"),
           text_layer("J party gold", "1250", LJ["text"]["gold"], style="gold", point=16),
           text_layer("J ground page", "1/1", LJ["ground_page"], style="label", point=13)]
for i, nm in enumerate(LJ["buttons"]["tab_names"]):
    J_right.append(text_layer(f"J tab caption {nm}", nm, LJ["buttons"]["tabs"][i], style="button", point=12,
                              color=COL["Y"] if i == 0 else None))
J_right.append(text_layer("J store all caption", "Store all", LJ["buttons"]["store_all"], style="button", point=15))
for i, itm in enumerate(["COPPER", "BREAST1", "KEYSNTRY", "LENS04", "CLUB"]):
    J_icon(itm, LJ["backpack"][i * 2], count=(3, 2, None, None, None)[i])
for i in range(55):
    mk = STASH_MARKS.get(i % len(STASH_ITEMS))
    J_icon(STASH_ITEMS[i % len(STASH_ITEMS)], LJ["stash"][i], tint=mk[1] if mk and mk[0] == "tint" else None,
           count=mk[1] if mk and mk[0] == "count" else None, plus=bool(mk and mk[0] == "plus"))
J_icon("CLUB2", LJ["ground"][0])
J_parts = [part_states(nm, LJ["parts"][nm]) for nm in LJ["parts"]]
varJ = group("Variant J - John's painted inventory, pieces detached (SwarmUI x2 + inpaint)", [
    layer("J background (bg_clean_2x, 1083x683 @ -30,0)", j_bg, "J_bg", LJ["menu"]["bg_offset"], 0),
    group("J paperdoll", [layer("J paperdoll IVPNOA", dollJ, "dollJ", pdJ[0] + (pdJ[2] - dollJ.width) // 2,
                                pdJ[1] + (pdJ[3] - dollJ.height) // 2)]),
    group("J detached pieces (buttons, bag, face, gauges, tubes)", J_parts),
    group("J left column", J_left),
    group("J stats", J_stats),
    group("J right column", J_right),
    group("J items (sample)", J_items),
], visible=True)
varH["visible"] = False

mockups = group("Party Stash mockup (PTEE style)", [varC, varB, varA, varD, varE, varF, varG, varH, varJ])

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
for r in (LP, RP):
    guide_box(*r)
root = [background, vanilla, actionbar, mockups, library, annotations]


def hide_kinds(nodes, kinds=("text", "item", "slot")):
    """John (2026-10-21): show the bare panels by default; items, slot squares and texts stay as hidden layers."""
    for n in nodes:
        if n.get("kind") in kinds:
            n["visible"] = False
        if n["type"] == "group" and not n["name"].startswith("Library"):
            hide_kinds(n["children"], kinds)


hide_kinds(root)
manifest = {"width": W, "height": H, "root": root,
            "guides": {"h": sorted(v for v in GUIDES["h"] if 0 <= v <= H),
                       "v": sorted(v for v in GUIDES["v"] if 0 <= v <= W)}}
with open(os.path.join(BUILD, "layout.json"), "w", encoding="utf-8") as f:
    json.dump(LAYOUT, f, indent=1)
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
