"""Build the in-game mod for variant J (John's painted inventory, detached animated pieces).

Writes mod/InventairePTEE/ (same tp2 as tools/build_mod.py): PSIVBGJ.MOS (2x background), PSJ*.BAM (detached pieces,
4 frames: normal / pressed / selected (hover) / disabled), menu/inventory.menu, lua/M_PSINV.lua.
The stash grid, tabs, sort and store-all are drawn but inactive until the EEex stash (step 2).
Usage: python tools/build_mod_j.py  (after tools/variant_j.py layout).
"""
import json
import os
import struct

from PIL import Image, ImageDraw, ImageEnhance

import build_mod as bm  # noqa: F401  (reuses write_mos_v1, menu helpers, TP2)

ROOT = bm.ROOT
JD = os.path.join(ROOT, "design", "art", "j")
L = json.load(open(os.path.join(ROOT, "design", "build", "layout_j.json"), encoding="utf-8"))
MOD = bm.MOD
UP = 1  # MOS/BAM V1 are drawn 1:1 by the engine (no scaling to the area): keep menu-pixel size

BAMS = {"tab1": "PSJTAB1", "tab2": "PSJTAB2", "tab3": "PSJTAB3", "tab4": "PSJTAB4", "tab5": "PSJTAB5",
        "tab6": "PSJTAB6", "tab7": "PSJTAB7", "tab8": "PSJTAB8", "close": "PSJCLOSE",
        "store_all": "PSJSTORE", "page_prev": "PSJPREV", "page_next": "PSJNEXT", "bag": "PSJBAG", "face": "PSJFACE",
}  # gauges and tubes are static art in bg_final_2x.png (John 2026-10-22: no animated pieces)


def write_bam_v1(frames, path):
    """BAM V1, one cycle, uncompressed frames, 256-colour palette with alpha (EE reads palette alpha)."""
    w, h = frames[0].size
    sheet = Image.new("RGBA", (w, h * len(frames)))
    for i, f in enumerate(frames):
        sheet.paste(f, (0, i * h))
    q = sheet.quantize(colors=255, method=Image.Quantize.FASTOCTREE)
    pal = q.getpalette("RGBA")[:255 * 4]
    pal += [0] * (255 * 4 - len(pal))
    # index 0 = transparent key (pure green, alpha 0); real colours shifted to 1..255
    px = bytes((p + 1) for p in q.tobytes())
    entries = [struct.pack("<BBBB", 0, 255, 0, 0)]
    alpha = sheet.getchannel("A").tobytes()
    px = bytes(0 if alpha[i] < 12 else px[i] for i in range(len(px)))
    for i in range(255):
        r, g, b, a = pal[i * 4:i * 4 + 4]
        if (r, g, b) == (0, 255, 0):
            g = 254
        entries.append(struct.pack("<BBBB", b, g, r, max(1, a)))
    nfr = len(frames)
    hdr_size = 24
    foff = hdr_size
    coff = foff + nfr * 12
    poff = coff + 4
    loff = poff + 1024
    doff = loff + nfr * 2
    out = bytearray(b"BAM V1  " + struct.pack("<HBBIII", nfr, 1, 0, foff, poff, loff))
    data = bytearray()
    for i in range(nfr):
        out += struct.pack("<HHhhI", w, h, 0, 0, (doff + len(data)) | 0x80000000)
        data += px[i * w * h:(i + 1) * w * h]
    out += struct.pack("<HH", nfr, 0)
    out += b"".join(entries)
    out += b"".join(struct.pack("<H", i) for i in range(nfr))
    out += data
    with open(path, "wb") as f:
        f.write(out)


def write_bam_cycles(cycles, path):
    """BAM V1 with several cycles (lists of same-size RGBA frames)."""
    frames = [f for cy in cycles for f in cy]
    w, h = frames[0].size
    sheet = Image.new("RGBA", (w, h * len(frames)))
    for i, f in enumerate(frames):
        sheet.paste(f, (0, i * h))
    q = sheet.quantize(colors=255, method=Image.Quantize.FASTOCTREE)
    pal = q.getpalette("RGBA")[:255 * 4]
    pal += [0] * (255 * 4 - len(pal))
    alpha = sheet.getchannel("A").tobytes()
    raw = q.tobytes()
    px = bytes(0 if alpha[i] < 12 else raw[i] + 1 for i in range(len(raw)))
    entries = [struct.pack("<BBBB", 0, 255, 0, 0)]
    for i in range(255):
        r, g, b, a = pal[i * 4:i * 4 + 4]
        entries.append(struct.pack("<BBBB", b, 254 if (r, g, b) == (0, 255, 0) else g, r, max(1, a)))
    nfr, ncy = len(frames), len(cycles)
    foff = 24
    coff = foff + nfr * 12
    poff = coff + ncy * 4
    loff = poff + 1024
    doff = loff + nfr * 2
    out = bytearray(b"BAM V1  " + struct.pack("<HBBIII", nfr, ncy, 0, foff, poff, loff))
    for i in range(nfr):
        out += struct.pack("<HHhhI", w, h, 0, 0, (doff + i * w * h) | 0x80000000)
    k = 0
    for cy in cycles:
        out += struct.pack("<HH", len(cy), k)
        k += len(cy)
    out += b"".join(entries) + b"".join(struct.pack("<H", i) for i in range(nfr)) + px
    with open(path, "wb") as f:
        f.write(out)


def dark_copy(res, out_name, size, k=0.45):
    """Darkened copy of a vanilla slot BAM (all cycles/frames) at `size` px (John 2026-10-22: no light grey squares)."""
    import ie
    g = ie.Game(r"E:\Enhanced Edition\Environnement de test\Planescape Torment Enhanced Edition")
    cycles = []
    for cy in ie.bam(g, res) or []:
        frs = []
        for im, _, _ in cy:
            a = im.getchannel("A").resize((size, size), Image.LANCZOS)
            rgb = ImageEnhance.Brightness(im.convert("RGB").resize((size, size), Image.LANCZOS)).enhance(k)
            f = rgb.convert("RGBA")
            f.putalpha(a)
            frs.append(f)
        if frs:
            cycles.append(frs)
    write_bam_cycles(cycles, os.path.join(MOD, "art", f"{out_name}.BAM"))


def part_frames(name, rect):
    w, h = rect[2] * UP, rect[3] * UP
    base = Image.open(os.path.join(JD, "parts", f"{name}.png")).convert("RGBA").resize((w, h), Image.LANCZOS)
    a = base.getchannel("A")
    rgb = base.convert("RGB")
    out = []
    for im in (rgb, ImageEnhance.Brightness(rgb).enhance(0.7), ImageEnhance.Brightness(rgb).enhance(1.35),
               ImageEnhance.Brightness(ImageEnhance.Color(rgb).enhance(0.15)).enhance(0.6)):
        im = im.convert("RGBA")
        im.putalpha(a)
        out.append(im)
    return out  # BAM button order: normal, pressed, selected, disabled


HI = 3840 / 1366   # 4K art for the 1366x768 background area (MOS V2 is scaled to its area by the engine)
PVRZ_BASE = 9100   # our PVRZ page numbers (vanilla PTEE uses MOS0000-MOS2011)


def write_pvrz(img, path):
    """PVRZ page: zlib(PVR3 header + DXT5 data), prefixed by the uncompressed size."""
    import io
    import zlib
    buf = io.BytesIO()
    img.convert("RGBA").save(buf, format="DDS", pixel_format="DXT5")
    dxt = buf.getvalue()[128:]
    w, h = img.size
    hdr = struct.pack("<IIQIIIIIIIII", 0x03525650, 0, 11, 0, 0, h, w, 1, 1, 1, 1, 0)
    raw = hdr + dxt
    with open(path, "wb") as f:
        f.write(struct.pack("<I", len(raw)) + zlib.compress(raw, 9))


def write_mos_v2(img, name, art, page0):
    """MOS V2 split on 1024x1024 PVRZ pages MOS<page>.PVRZ."""
    w, h = img.size
    blocks, page = [], page0
    for y in range(0, h, 1024):
        for x in range(0, w, 1024):
            tile = img.crop((x, y, min(w, x + 1024), min(h, y + 1024)))
            pg = Image.new("RGBA", (1024, 1024), (0, 0, 0, 255))
            pg.paste(tile, (0, 0))
            write_pvrz(pg, os.path.join(art, f"MOS{page:04d}.PVRZ"))
            blocks.append(struct.pack("<7I", page, 0, 0, tile.width, tile.height, x, y))
            page += 1
    with open(os.path.join(art, f"{name}.MOS"), "wb") as f:
        f.write(b"MOS V2  " + struct.pack("<IIII", w, h, len(blocks), 24) + b"".join(blocks))
    return page


def cell(d, x, y, w, h, k):
    d.rounded_rectangle((x - 2 * k, y - 2 * k, x + w + k, y + h + k), radius=5 * k, fill=(6, 5, 4, 200),
                        outline=(0, 0, 0, 230), width=max(2, round(2 * k)))
    d.line((x + 2 * k, y + h, x + w - 2 * k, y + h), fill=(140, 96, 58, 150), width=max(1, round(k)))
    d.line((x + w, y + 2 * k, x + w, y + h - 2 * k), fill=(140, 96, 58, 150), width=max(1, round(k)))


def background():
    """4K background (MOS V2 + PVRZ): John's art + recessed cells under every grid slot (stash, backpack, ground)."""
    bw, bh = L["menu"]["bg_size"]
    W4, H4 = 3840, 2160
    img = Image.new("RGB", (W4, H4), (0, 0, 0))
    bg = Image.open(os.path.join(JD, "bg_final_2x.png")).convert("RGB").resize((round(bw * HI), round(bh * HI)),
                                                                                 Image.LANCZOS)
    img.paste(bg, (round((171 + L["menu"]["bg_offset"]) * HI), 0))
    d = ImageDraw.Draw(img, "RGBA")
    for (x, y, w, h) in L["stash"] + L["backpack"] + L["ground"]:
        cell(d, (x + 171) * HI, y * HI, w * HI, h * HI, HI)
    img.resize((1366, 768), Image.LANCZOS).save(os.path.join(ROOT, "design", "build", "ingame_bg_J.png"))
    write_mos_v2(img, "PSIVBGJ", os.path.join(MOD, "art"), PVRZ_BASE)


def slot_bam():
    """Dark recessed slot (backpack, ground): normal, hover (copper rim), selected (purple), highlight (yellow)."""
    frames = []
    for rim in (None, (190, 120, 70, 255), (170, 90, 200, 255), (230, 200, 60, 255)):
        im = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, 39, 39), radius=5, fill=(6, 5, 4, 140))
        if rim:
            d.rounded_rectangle((0, 0, 39, 39), radius=5, outline=rim, width=2)
        frames.append(im)
    write_bam_v1(frames, os.path.join(MOD, "art", "PSJSLOT.BAM"))


MOVABLE, HANDLES = [], []
_pj = os.path.join(ROOT, "design", "placements_john.json")
PLACED = json.load(open(_pj, encoding="utf-8")) if os.path.exists(_pj) else {}


def movable(key, rect, **kw):
    """Text label John can drag in placement mode (right-click on the face); its position is saved in the ini."""
    MOVABLE.append(key)
    if key in PLACED:  # John's in-game placement (design/placements_john.json)
        rect = (PLACED[key][0], PLACED[key][1], rect[2], rect[3])
    s = bm.label(rect, **kw).replace("\tlabel\n\t{\n", f'\tlabel\n\t{{\n\t\tname "psinv_{key}"\n', 1)
    a = bm.area(rect)
    HANDLES.append(f'\tlabel\n\t{{\n\t\tname "psinvr_{key}"\n\t\tenabled "psInvEdit"\n\t\t{a}\n'
                   f'\t\trectangle 1\n\t\trectangle opacity 90\n\t}}\n')
    HANDLES.append(f'\thandle\n\t{{\n\t\tname "psinvh_{key}"\n\t\tenabled "psInvEdit"\n\t\t{a}\n'
                   f'\t\tactionDrag "psInvDrag(\'{key}\', motionX, motionY)"\n\t}}\n')
    return s


def piece(name, kind="button", action=None, text_lua=None, point=None, tooltip_lua=None, seq=0, frame_lua=None,
          font=None, action_alt=None, color_lua=None):
    r = L["parts"][name]
    s = f"\t{kind}\n\t{{\n\t\t{bm.area(r)}\n\t\tbam \"{BAMS[name]}\"\n\t\tsequence {seq}\n"
    if frame_lua:
        s += f'\t\tframe lua "{frame_lua}"\n'
    if text_lua:
        s += f'\t\ttext lua "{text_lua}"\n\t\ttext style "button"\n'
        if point:
            s += f"\t\ttext point {point}\n"
        if font:
            s += f'\t\ttext font "{font}"\n'
        if color_lua:
            s += f'\t\ttext color lua "{color_lua}"\n'
    if action_alt:
        s += f'\t\tactionAlt "{action_alt}"\n'
    if tooltip_lua:
        s += f'\t\ttooltip lua "{tooltip_lua}"\n'
    if action:
        s += f'\t\taction "{action}"\n'
    return s + "\t}\n"


def build_menu():
    m = ["""
menu
{
	name 'INVENTORY'
	align center center
	ignoreEsc
	size 1024 768
	greyscale lua "characters[id].HP.current <= 0"
	interactable lua "characters[id].HP.current > 0"
	onOpen
	"
		Infinity_ActivateInventory()
		pushSidebars()
		doubleClickEventScheduled = nil
		Infinity_SetBackground('BACKGROUND_INVENTORY')
		psInvApplyPositions()
		if PSC_AutoTest then PSC_AutoTest() end
		if PSUI_Refresh then PSUI_Refresh() end
	"
	onClose
	"
		popSidebars()
		Infinity_SetBackground(nil)
	"
"""]
    pd = L["paperdoll"]
    m.append(f'\tbutton\n\t{{\n\t\t{bm.area(pd)}\n\t\tpaperdoll 1\n\t\tactiondrag "Infinity_SwapWithAppearance()"\n\t}}\n')
    t = L["text"]
    m.append(movable("name", t["name"], text_lua="characters[id].name", point=13, font="EXOCET",
                     color_lua="psInvYellow()"))
    m.append(movable("class", t["class"], text_lua="characters[id].class", point=13, font="EXOCET",
                     color_lua="psInvYellow()"))
    m.append(movable("weight", t["weight"], text_lua="psInvWeight()", style="normal", point=15, align="left center",
                     color_lua="psInvWeightColor()"))
    m.append(movable("gold", t["gold"], text_lua="game:GetPartyGold()", style="gold", point=16,
                     color_lua="psInvYellow()"))
    for nm, r in L["titles"].items():
        m.append(movable("title_" + nm.lower().replace(" ", "_"), r, text_lua=f"psInvText('{nm}')", point=13,
                         font="EXOCET", color_lua="psInvYellow()"))
    for nm, st in L["stats"].items():
        d = st["disc"]
        k = nm.lower()
        m.append(movable(f"cap_{k}", (d[0] - 10, d[1] - 24, d[2] + 20, 16), text_lua=f"psInvText('{nm}')",
                         style="normal", point=11, align="center center", color_lua="psInvYellow()", font="EXOCET"))
        m.append(movable(f"val_{k}", d, text_lua=f"psInvStat('{nm}')", point=15, align="center center",
                         color_lua="psInvWhite()"))
        p = st["plate"]
        m.append(movable(f"det_{k}", (p[0] + 10, p[1] + 10, p[2] - 16, p[3] - 16),
                         text_lua=f"psInvStatDetail('{nm}')", style="normal", point=10, align="left top",
                         color_lua="psInvYellow()"))
    m.append("\ttext\n\t{\n\t\tarea 501 512 420 24\n\t\ttext lua \"psInvMessage()\"\n\t\ttext style normal\n"
             "\t\ttext point 12\n\t\ttext align left center\n\t}\n")
    for i, a in enumerate(L["quick weapons"]):
        m.append(bm.slot(f"slot_inv_{1 + i}", a, "PSJSWRD", i, f"weapon{i}"))
    for i, a in enumerate(L["quick items"]):
        m.append(bm.slot(f"slot_inv_{5 + i}", a, "PSJITM", i, f"personal{i}"))
    for i, a in enumerate(L["quiver"]):
        m.append(bm.slot(f"slot_inv_{15 + i}", a, "PSJARW", i, f"quiver{i}"))
    body_ids = {"chest0": 11, "wrist0": 12, "earringleft0": 13, "earringright0": 14, "tattoo0": 21, "ring0": 22,
                "ring1": 23, "tattoo1": 24, "hand0": 25, "tattoo2": 26}
    for i, (nm, a) in enumerate(L["body"].items()):
        m.append(bm.slot(f"slot_inv_{body_ids[nm]}", a, "PSJIVSL", i % 10, nm))
    for n, a in enumerate(L["backpack"]):
        m.append(bm.slot(f"slot_inv_{30 + n}", a, "PSJSLOT", 0, f"group{n}"))
    for n, a in enumerate(L["ground"]):
        m.append(bm.slot(f"slot_inv_{68 + n}", a, "PSJSLOT", 0, f"ground{n}"))
    m.append(piece("page_prev", action="Infinity_OnGroundPage(-1)"))
    m.append(piece("page_next", action="Infinity_OnGroundPage(1)"))
    m.append(movable("ground_page", L["ground_page"],
                     text_lua="Infinity_GetCurrentGroundPage()+1 .. '/' .. Infinity_GetMaxGroundPage()+1", point=13,
                     color_lua="psInvYellow()"))
    for i in range(8):
        m.append(piece(f"tab{i + 1}", text_lua=f"psInvTab({i + 1})", point=12, action=f"psInvSelectTab({i + 1})",
                       frame_lua=f"psInvTabFrame({i + 1})", font="EXOCET", color_lua="psInvYellow()"))
    m.append(movable("sort", L["buttons"]["sort"], text_lua="psInvText('Sort')", point=14, align="right center",
                     color_lua="psInvYellow()"))
    m.append(piece("store_all", text_lua="psInvText('Store all')", point=15, color_lua="psInvYellow()",
                   action="PSUI_StoreAll()"))
    # stash grid (step 2b): icon + count + click-to-take button per cell
    for i, (x, y, w, h) in enumerate(L["stash"], start=1):
        m.append(f'\tlabel\n\t{{\n\t\tenabled "PSUI_Has({i})"\n\t\tarea {x + 2} {y + 2} {w - 4} {h - 4}\n'
                 f'\t\ticon lua "PSUI_Icon({i})"\n\t}}\n')
        m.append(f'\tlabel\n\t{{\n\t\tenabled "PSUI_Has({i})"\n\t\tarea {x} {y + h - 16} {w - 3} 15\n'
                 f'\t\ttext lua "PSUI_Count({i})"\n\t\ttext style "normal"\n\t\ttext point 10\n'
                 f'\t\ttext align right bottom\n\t}}\n')
        m.append(f'\tbutton\n\t{{\n\t\tenabled "PSUI_Has({i})"\n\t\tarea {x} {y} {w} {h}\n'
                 f'\t\ttooltip lua "PSUI_Name({i})"\n\t\taction "PSUI_Take({i})"\n\t}}\n')
    m.append(piece("bag", tooltip_lua="psInvWeight()"))
    m.append(piece("face", action="Infinity_PushMenu('INVENTORY_HELP')", tooltip_lua="psInvText('Help')",
                   action_alt="psInvToggleEdit()"))
    # placement mode banner + drag handles (drawn last, on top)
    m.append(bm.label((300, 4, 420, 20), text_lua="psInvText('Edit')", style="normal", point=12,
                      align="center center", enabled="psInvEdit", color_lua="psInvYellow()"))
    m += HANDLES
    m.append(piece("close", action="e:GetActiveEngine():SelectEngine(worldScreen)"))
    m.append("}\n")
    return "".join(m)


LUA_J = r'''-- Inventaire PTEE (Party Stash for Planescape: Torment EE), step 1: redesigned inventory page (art J).
psInvTexts = {
	Quiver = 'Quiver', ['Quick Weapons'] = 'Quick Weapons', ['Quick Items'] = 'Quick Items',
	AC = 'AC', THAC0 = 'THAC0', HP = 'HP', Damage = 'Damage', Sort = 'Sort: Auto', ['Store all'] = 'Store all',
	Help = 'Help (right-click: move the texts)',
	Edit = 'Placement mode: drag the texts, right-click the face to finish',
}
psInvTabs = {'All', 'Weap.', 'Tatt.', 'Jewel', 'Eyes', 'Charm', 'Quest', 'Misc'}
psInvActiveTab = 1

function psInvBackground() return 'PSIVBGJ' end
function psInvText(key) return psInvTexts[key] or key end
function psInvTab(i) return psInvTabs[i] end
function psInvSelectTab(i) psInvActiveTab = i if PSUI_Refresh then PSUI_Refresh() end end
-- selected tab shows the "selected" frame (2)
function psInvTabFrame(i) if psInvActiveTab == i then return 2 end return 0 end

-- Placement mode (John 2026-10-22): right-click on the face, drag the texts, right-click again to finish.
-- Positions are saved in the game ini, section [Party Stash], keys pos_<text>.
psInvEdit = false
psInvMovable = {@MOVABLE@}
local PARTS = {'psinv_', 'psinvh_', 'psinvr_'}
function psInvToggleEdit() psInvEdit = not psInvEdit end
local function psInvMove(key, x, y)
	for _, p in ipairs(PARTS) do Infinity_SetArea(p .. key, x, y, nil, nil) end
end
function psInvDrag(key, dx, dy)
	local x, y = Infinity_GetArea('psinv_' .. key)
	x, y = x + dx, y + dy
	psInvMove(key, x, y)
	Infinity_SetINIValue('Party Stash', 'pos_' .. key, x .. ',' .. y)
end
function psInvApplyPositions()
	for _, key in ipairs(psInvMovable) do
		local v = Infinity_GetINIString('Party Stash', 'pos_' .. key, '')
		local x, y = string.match(v or '', '(-?%d+),(-?%d+)')
		if x then psInvMove(key, tonumber(x), tonumber(y)) end
	end
end

function psInvYellow()
	return bit32.band(tonumber(fontcolors['Y'], 16), 0x00FFFFFF)
end

function psInvWeight()
	return game:GetSelectedCarried() .. ' / ' .. game:GetSelectedMaxEncumbrance() .. ' LB'
end

local function psInvField(f)
	local ok, v = pcall(f)
	if ok and v ~= nil then return v end
	return nil
end

function psInvStat(key)
	local c = characters[id]
	if key == 'AC' then return c.AC.current end
	if key == 'HP' then return c.HP.current .. '/' .. c.HP.max end
	if key == 'Damage' then return c.damage.min .. '-' .. c.damage.max end
	if key == 'THAC0' then
		return psInvField(function() return c.THAC0.current end) or psInvField(function() return c.thac0 end) or '-'
	end
	return ''
end

-- weight: yellow like the game's texts, the engine's warning colours past 80 % / 100 % of the limit
function psInvWeightColor()
	local c = getEncumbranceColor()
	if c == bit32.band(tonumber(fontcolors['B'], 16), 0x00FFFFFF) then return psInvYellow() end
	return c
end

function psInvMessage()
	local t = tostring(TEXT_inventoryError or '')
	if string.find(string.lower(t), 'pause', 1, true) then return '' end
	return t
end

function psInvWhite()
	return bit32.band(tonumber(fontcolors['B'], 16), 0x00FFFFFF)
end

-- Short forms like Party Stash BG (John 2026-10-22): attribute and stat names abbreviated, quotes cut.
psInvAbbr = {
	{'Points de vie', 'PV'}, {'Hit Points', 'HP'}, {"Classe d'armure", 'CA'}, {'Armor Class', 'AC'},
	{'Armour Class', 'AC'}, {'Force', 'For'}, {'Strength', 'Str'}, {'Dext\195\169rit\195\169', 'Dex'},
	{'Dexterity', 'Dex'}, {'Constitution', 'Con'}, {'Intelligence', 'Int'}, {'Sagesse', 'Sag'}, {'Wisdom', 'Wis'},
	{'Charisme', 'Cha'}, {'Charisma', 'Cha'}, {'Comp\195\169tence', 'Comp.'}, {'Proficiency', 'Prof.'},
	{'Arme', 'Arme'}, {'Weapon', 'Weapon'},
}
-- the block's own stat name is dropped from its lines ("Adahn : +10" in the HP block, not "PV: +10")
psInvOwn = {AC = {'CA', 'AC'}, HP = {'PV', 'HP'}, THAC0 = {'TAC0', 'THAC0'}, Damage = {}}

local function psInvTrim(t)
	return (string.gsub(string.gsub(t, '^%s+', ''), '%s+$', ''))
end

function psInvShorten(key, text)
	local out = {}
	local n = #text
	for cut = math.floor(n / 2) - 2, math.floor(n / 2) + 2 do
		if cut > 0 and string.sub(text, 1, cut) == string.sub(text, cut + 1, cut * 2) and cut * 2 >= n - 1 then
			text = string.sub(text, 1, cut)
			break
		end
	end
	text = string.gsub(text, '"[^"]*"', '')            -- quoted dialogue lines
	text = string.gsub(text, '\226\128\156[^\226]*\226\128\157', '')  -- curly quotes
	for line in string.gmatch(text, '[^\n]+') do
		for _, a in ipairs(psInvAbbr) do line = string.gsub(line, a[1], a[2]) end
		for _, own in ipairs(psInvOwn[key] or {}) do line = string.gsub(line, '%s' .. own .. '%s*:', ' ') end
		line = string.gsub(line, '%s*:%s*:', ' :')
		line = string.gsub(line, ':%s+([%+%-]?%d)', ': %1')
		line = string.gsub(line, '%s%s+', ' ')
		line = string.gsub(line, '%+%-', '-')                -- engine prints "+-1"
		line = psInvTrim(line)
		-- the engine sometimes repeats a line glued to itself ("TAC0 de base : 18TAC0 de base : 18")
		local half = math.floor(#line / 2)
		if #line % 2 == 0 and half > 0 and string.sub(line, 1, half) == string.sub(line, half + 1) then
			line = string.sub(line, 1, half)
		end
		local seen = false
		for _, o in ipairs(out) do if o == line then seen = true end end
		if line ~= '' and line ~= ':' and not seen then out[#out + 1] = line end
	end
	return table.concat(out, '\n')
end

-- Item lines grouped by equipment slot, like Party Stash BG (John 2026-10-22): "Tattoo: -3" instead of each
-- tattoo's full name. Names come from the equipped items; same-slot values are added up.
psInvSlotLabels = {
	{'tattoo0', 'Tatouage', 'Tattoo'}, {'tattoo1', 'Tatouage', 'Tattoo'}, {'tattoo2', 'Tatouage', 'Tattoo'},
	{'earringleft0', 'Oreille', 'Ear'}, {'earringright0', 'Oreille', 'Ear'}, {'ring0', 'Anneau', 'Ring'},
	{'ring1', 'Anneau', 'Ring'}, {'chest0', 'Torse', 'Chest'}, {'wrist0', 'Poignet', 'Wrist'},
	{'hand0', 'Main', 'Hand'}, {'weapon0', 'Arme', 'Weapon'}, {'weapon1', 'Arme', 'Weapon'},
	{'weapon2', 'Arme', 'Weapon'}, {'weapon3', 'Arme', 'Weapon'},
}
local function psInvEquippedNames()
	local out, fr = {}, psInvFr()
	local eq = characters[id] and characters[id].equipment
	if not eq then return out end
	for _, l in ipairs(psInvSlotLabels) do
		local slot = eq[l[1]]
		local nm = slot and slot.item and slot.item.name
		if nm and nm ~= '' and (slot.empty == nil or slot.empty == 0) then
			out[#out + 1] = {nm, fr and l[2] or l[3]}
		end
	end
	table.sort(out, function(a, b) return #a[1] > #b[1] end)
	return out
end
-- PTEE's AC breakdown also lists AC items carried in the backpack, then a "Bonus" line that cancels them
-- (John 2026-10-22: "my character has none of that"). Keep the base line and the equipped items only (grouped by
-- slot), and show what is left as "Other" = current AC - base - equipped items.
function psInvGroupBySlot(text)
	local names = psInvEquippedNames()
	local order, sum, base = {}, {}, nil
	local equipped = 0
	for line in string.gmatch(text, '[^\n]+') do
		local v = string.match(line, '([%+%-]?%d+)%s*$')
		local label
		for _, n in ipairs(names) do
			if string.sub(line, 1, #n[1]) == n[1] then label = n[2] break end
		end
		if v and not base and (string.match(line, '^CA%s*:') or string.match(line, '^AC%s*:')) then
			base = tonumber(v)
		elseif label and v then
			if not sum[label] then order[#order + 1] = label sum[label] = 0 end
			sum[label] = sum[label] + tonumber(v)
			equipped = equipped + tonumber(v)
		end
	end
	local out = {}
	if base then out[#out + 1] = (psInvFr() and 'Base : ' or 'Base: ') .. base end
	for _, label in ipairs(order) do out[#out + 1] = label .. ' : ' .. string.format('%+d', sum[label]) end
	local cur = tonumber(psInvField(function() return characters[id].AC.current end) or '')
	if base and cur then
		local rest = cur - base - equipped
		if rest ~= 0 then out[#out + 1] = (psInvFr() and 'Autre : ' or 'Other: ') .. string.format('%+d', rest) end
	end
	return table.concat(out, '\n')
end

-- Detail lines: the engine's own breakdown (AC/HP/THAC0/damage .details), shortened.
function psInvStatDetail(key)
	local c = characters[id]
	local f = {AC = function() return c.AC.details end, HP = function() return c.HP.details end,
		THAC0 = function() return c.THAC0.details end, Damage = function() return c.damage.details end}
	if key == 'HP' then return psInvHPDetail(c) end
	local text = psInvShorten(key, tostring(psInvField(f[key]) or ''))
	if key == 'AC' then text = psInvGroupBySlot(text) end
	if key == 'Damage' then
		local out = {}
		for line in string.gmatch(text, '[^\n]+') do
			for _, n in ipairs(psInvEquippedNames()) do
				if string.sub(line, 1, #n[1]) == n[1] then line = n[2] .. string.sub(line, #n[1] + 1) break end
			end
			out[#out + 1] = line
		end
		text = table.concat(out, '\n')
	end
	if key == 'Damage' then
		local apr = psInvAPR()
		if apr then
			text = text .. (text ~= '' and '\n' or '') .. psInvAPRLabel() .. string.format('%g', apr)
		end
	end
	return text
end

-- Attacks per round of the shown character (John 2026-10-22), like Party Stash BG: EEex stat 8 NUMBEROFATTACKS,
-- engine code 1-5 attacks, 6 = 1.5, 7 = 2.5, 8 = 3.5, 9 = 4.5. Nothing shown without EEex.
function psInvAPR()
	local ok, v = pcall(function()
		for p = 0, 5 do
			local sp = EEex_Sprite_GetInPortrait(p)
			if sp and sp.m_id == id then return EEex_Sprite_GetStat(sp, 8) end
		end
	end)
	if not ok or type(v) ~= 'number' then return nil end
	if v >= 6 then return v - 4.5 end
	return v
end

-- HP block (John 2026-10-22): level-up hit die, Constitution bonus per level, "Other" = flat sum of every other
-- bonus the engine lists. PTEE has no HPCLASS/HPCONBON tables: AD&D 2e rules as in PST, hard-coded.
-- Fighter 1d10 up to level 9 then +3; thief 1d6 up to 10 then +2; mage 1d4 up to 10 then +1.
local PSINV_DIE = {[2] = {10, 9, 3}, [4] = {6, 10, 2}, [1] = {4, 10, 1}}
local function psInvSprite()
	local ok, sp = pcall(function()
		for p = 0, 5 do
			local s = EEex_Sprite_GetInPortrait(p)
			if s and s.m_id == id then return s end
		end
	end)
	if ok then return sp end
	return nil
end
local function psInvClassFromName(name)
	name = string.lower(tostring(name or ''))
	if string.find(name, 'guerr', 1, true) or string.find(name, 'fight', 1, true) then return 2 end
	if string.find(name, 'voleur', 1, true) or string.find(name, 'thief', 1, true) then return 4 end
	if string.find(name, 'mage', 1, true) then return 1 end
	return nil
end
-- Constitution HP bonus per level (AD&D 2e): +3 and above only for warriors.
local function psInvConBonus(con, warrior)
	local b = 0
	if con >= 15 then b = 1 end
	if con >= 16 then b = 2 end
	if con >= 17 then b = 3 end
	if con >= 18 then b = 4 end
	if con >= 19 then b = 5 end
	if con >= 21 then b = 6 end
	if con >= 24 then b = 7 end
	if not warrior and b > 2 then b = 2 end
	return b
end
function psInvFr()
	local lang = string.lower(Infinity_GetINIString('Language', 'Text', '') or '')
	return string.sub(lang, 1, 2) == 'fr'
end

function psInvHPDetail(c)
	local sp = psInvSprite()
	local cls, level, con
	if sp then
		cls = psInvField(function() return sp.m_typeAI.m_Class end)
		level = psInvField(function() return EEex_Sprite_GetStat(sp, 34) end)
		con = psInvField(function() return EEex_Sprite_GetStat(sp, 41) end)
	end
	cls = PSINV_DIE[cls or 0] and cls or psInvClassFromName(c.class)
	local fr = psInvFr()
	local lines = {}
	local rule = PSINV_DIE[cls or 0]
	if rule then
		local die = '1d' .. rule[1]
		if level and level + 1 > rule[2] then die = '+' .. rule[3] end
		lines[#lines + 1] = (fr and 'Classe : ' or 'Class: ') .. die
	end
	if con then
		lines[#lines + 1] = (fr and 'Con : ' or 'Con: ') .. string.format('%+d', psInvConBonus(con, cls == 2))
	end
	-- every other bonus the engine lists (items, tattoos, dialogue choices...), constitution lines excluded
	local other, any = 0, false
	for line in string.gmatch(tostring(psInvField(function() return c.HP.details end) or ''), '[^\n]+') do
		local low = string.lower(line)
		if not string.find(low, 'constit', 1, true) then
			local n = string.match(line, '([%+%-]%d+)%s*$')
			if n then other, any = other + tonumber(n), true end
		end
	end
	if any then lines[#lines + 1] = (fr and 'Autre : ' or 'Other: ') .. string.format('%+d', other) end
	return table.concat(lines, '\n')
end

function psInvAPRLabel()
	local lang = string.lower(Infinity_GetINIString('Language', 'Text', '') or '')
	if string.sub(lang, 1, 2) == 'fr' then return 'Attaques/round : ' end
	return 'Attacks/round: '
end
'''


def main():
    art = os.path.join(MOD, "art")
    os.makedirs(art, exist_ok=True)
    for f in os.listdir(art):  # J replaces the F/G/H preview art
        os.remove(os.path.join(art, f))
    background()
    slot_bam()
    q = L["quiver"][0][2]
    b = list(L["body"].values())[0][2]
    for res, out_name, size in (("SLOTSWRD", "PSJSWRD", q), ("SLOTITM", "PSJITM", q), ("SLOTARW", "PSJARW", q),
                                ("IVSLOT", "PSJIVSL", b)):
        dark_copy(res, out_name, size)
    # body slot silhouettes (engine placeholders, inventory only): darkened in place
    for res in ("IVPIEYER", "IVPIEARL", "IVPIEARR", "IVPICHST", "IVPIWRST", "IVPIHNDL", "IVPIHNDR", "IVPIRING",
                "IVPITATT", "IVPILENS", "IVPITETH", "IVPIBOW"):
        dark_copy(res, res, b, 0.55)
    # quick-slot silhouettes are engine placeholders too (sword, potion, arrow)
    for res in ("IVQIWEAP", "IVQIITM", "IVQIARRW", "IVIARW", "IVISWRD", "IVISHLD", "IVISCRL", "SLOTWEAP"):
        dark_copy(res, res, q, 0.45)
    for nm, res in BAMS.items():
        write_bam_v1(part_frames(nm, L["parts"][nm]), os.path.join(art, f"{res}.BAM"))
    menu = build_menu()
    assert "%" not in menu and "~" not in menu
    with open(os.path.join(MOD, "menu", "inventory.menu"), "w", encoding="utf-8", newline="\n") as f:
        f.write(menu)
    with open(os.path.join(MOD, "lua", "M_PSINV.lua"), "w", encoding="utf-8", newline="\n") as f:
        f.write(LUA_J.replace("@MOVABLE@", ", ".join("'" + k + "'" for k in MOVABLE)))
    tp2 = bm.TP2.replace("// The \"Art\" button swaps the two background styles (F = PTEE pieces, G = generated art).",
                         "// Art: John's painted inventory; tabs, bag, face, gauges and tubes are separate animated BAMs.")
    with open(os.path.join(MOD, "InventairePTEE.tp2"), "w", encoding="utf-8", newline="\n") as f:
        f.write(tp2)
    print("mod J written:", MOD)


if __name__ == "__main__":
    main()
