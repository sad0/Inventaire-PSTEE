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
        "tab6": "PSJTAB6", "tab7": "PSJTAB7", "tab8": "PSJTAB8", "tab_more": "PSJTABM", "close": "PSJCLOSE",
        "store_all": "PSJSTORE", "page_prev": "PSJPREV", "page_next": "PSJNEXT", "bag": "PSJBAG", "face": "PSJFACE",
        "gauge_top": "PSJGTOP", "gauge_left": "PSJGLEFT", "gauge_right": "PSJGRGHT", "tube_left": "PSJTUBEL",
        "tube_right": "PSJTUBER", "tube_mid": "PSJTUBEM"}


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


def background():
    bw, bh = L["menu"]["bg_size"]
    img = Image.new("RGB", (1366 * UP, 768 * UP), (0, 0, 0))
    bg = Image.open(os.path.join(JD, "bg_clean_2x.png")).convert("RGB").resize((bw * UP, bh * UP), Image.LANCZOS)
    img.paste(bg, ((171 + L["menu"]["bg_offset"]) * UP, 0))
    # the stash grid is not engine slots yet (step 2): bake recessed cells into the background
    d = ImageDraw.Draw(img, "RGBA")
    for (x, y, w, h) in L["stash"]:
        x, y = (x + 171) * UP, y * UP
        d.rounded_rectangle((x - 2, y - 2, x + w + 1, y + h + 1), radius=5, fill=(6, 5, 4, 200),
                            outline=(0, 0, 0, 230), width=2)
        d.line((x + 2, y + h, x + w - 2, y + h), fill=(140, 96, 58, 150))
        d.line((x + w, y + 2, x + w, y + h - 2), fill=(140, 96, 58, 150))
    img.save(os.path.join(ROOT, "design", "build", "ingame_bg_J.png"))
    bm.write_mos_v1(img, os.path.join(MOD, "art", "PSIVBGJ.MOS"))


def piece(name, kind="button", action=None, text_lua=None, point=None, tooltip_lua=None, seq=0, frame_lua=None):
    r = L["parts"][name]
    s = f"\t{kind}\n\t{{\n\t\t{bm.area(r)}\n\t\tbam \"{BAMS[name]}\"\n\t\tsequence {seq}\n"
    if frame_lua:
        s += f'\t\tframe lua "{frame_lua}"\n'
    if text_lua:
        s += f'\t\ttext lua "{text_lua}"\n\t\ttext style "button"\n'
        if point:
            s += f"\t\ttext point {point}\n"
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
	"
	onClose
	"
		popSidebars()
		Infinity_SetBackground(nil)
	"
"""]
    # decorative animated pieces (gauges flicker, tubes pulse): labels cycling frames 0/2
    for nm in ("gauge_top", "gauge_left", "gauge_right", "tube_left", "tube_right", "tube_mid"):
        m.append(piece(nm, "label", frame_lua=f"psInvPulse('{nm}')"))
    pd = L["paperdoll"]
    m.append(f'\tbutton\n\t{{\n\t\t{bm.area(pd)}\n\t\tpaperdoll 1\n\t\tactiondrag "Infinity_SwapWithAppearance()"\n\t}}\n')
    t = L["text"]
    m.append(bm.label(t["name"], text_lua="characters[id].name", point=14))
    m.append(bm.label(t["class"], text_lua="characters[id].class", point=14))
    m.append(bm.label(t["weight"], text_lua="psInvWeight()", style="normal", point=15, align="left center",
                      color_lua="getEncumbranceColor()"))
    m.append(bm.label(t["gold"], text_lua="characters[id].gold", style="gold", point=16))
    for nm, r in L["titles"].items():
        m.append(bm.label(r, text_lua=f"psInvText('{nm}')", point=14))
    for nm, st in L["stats"].items():
        d = st["disc"]
        m.append(bm.label((d[0], d[1] - 16, d[2], 14), text_lua=f"psInvText('{nm}')", style="normal", point=11,
                          align="center top", color_lua="psInvYellow()"))
        m.append(bm.label((d[0], d[1] + 14, d[2], 34), text_lua=f"psInvStat('{nm}')", point=15))
        p = st["plate"]
        m.append(bm.label((p[0] + 10, p[1] + 10, p[2] - 16, p[3] - 16), text_lua=f"psInvStatDetail('{nm}')",
                          style="normal", point=12, align="left top"))
    m.append("\ttext\n\t{\n\t\tarea 501 512 420 24\n\t\ttext lua \"TEXT_inventoryError\"\n\t\ttext style normal\n"
             "\t\ttext point 12\n\t\ttext align left center\n\t}\n")
    for i, a in enumerate(L["quick weapons"]):
        m.append(bm.slot(f"slot_inv_{1 + i}", a, "SLOTSWRD", i, f"weapon{i}"))
    for i, a in enumerate(L["quick items"]):
        m.append(bm.slot(f"slot_inv_{5 + i}", a, "SLOTITM", i, f"personal{i}"))
    for i, a in enumerate(L["quiver"]):
        m.append(bm.slot(f"slot_inv_{15 + i}", a, "SLOTARW", i, f"quiver{i}"))
    body_ids = {"chest0": 11, "wrist0": 12, "earringleft0": 13, "earringright0": 14, "tattoo0": 21, "ring0": 22,
                "ring1": 23, "tattoo1": 24, "hand0": 25, "tattoo2": 26}
    for i, (nm, a) in enumerate(L["body"].items()):
        m.append(bm.slot(f"slot_inv_{body_ids[nm]}", a, "IVSLOT", i % 10, nm))
    for n, a in enumerate(L["backpack"]):
        m.append(bm.slot(f"slot_inv_{30 + n}", a, "IVSLOT", n % 10, f"group{n}"))
    for n, a in enumerate(L["ground"]):
        m.append(bm.slot(f"slot_inv_{68 + n}", a, "IVSLOT", (n + 4) % 10, f"ground{n}"))
    m.append(piece("page_prev", action="Infinity_OnGroundPage(-1)"))
    m.append(piece("page_next", action="Infinity_OnGroundPage(1)"))
    m.append(bm.label(L["ground_page"],
                      text_lua="Infinity_GetCurrentGroundPage()+1 .. '/' .. Infinity_GetMaxGroundPage()+1", point=13))
    for i in range(8):
        m.append(piece(f"tab{i + 1}", text_lua=f"psInvTab({i + 1})", point=12, action=f"psInvSelectTab({i + 1})",
                       frame_lua=f"psInvTabFrame({i + 1})"))
    m.append(piece("tab_more"))
    m.append(bm.label(L["buttons"]["sort"], text_lua="psInvText('Sort')", point=14, align="right center"))
    m.append(piece("store_all", text_lua="psInvText('Store all')", point=15))
    m.append(piece("bag", tooltip_lua="psInvWeight()"))
    m.append(piece("face", action="Infinity_PushMenu('INVENTORY_HELP')", tooltip_lua="psInvText('Help')"))
    m.append(piece("close", action="e:GetActiveEngine():SelectEngine(worldScreen)"))
    m.append("}\n")
    return "".join(m)


LUA_J = r'''-- Inventaire PTEE (Party Stash for Planescape: Torment EE), step 1: redesigned inventory page (art J).
psInvTexts = {
	Quiver = 'Quiver', ['Quick Weapons'] = 'Quick Weapons', ['Quick Items'] = 'Quick Items',
	AC = 'AC', THAC0 = 'THAC0', HP = 'HP', Damage = 'Damage', Sort = 'Sort: Auto', ['Store all'] = 'Store all',
	Help = 'Help',
}
psInvTabs = {'All', 'Weap.', 'Tatt.', 'Jewel', 'Eyes', 'Charm', 'Quest', 'Misc'}
psInvActiveTab = 1

function psInvBackground() return 'PSIVBGJ' end
function psInvText(key) return psInvTexts[key] or key end
function psInvTab(i) return psInvTabs[i] end
function psInvSelectTab(i) psInvActiveTab = i end
-- selected tab shows the "selected" frame (2)
function psInvTabFrame(i) if psInvActiveTab == i then return 2 end return 0 end

-- gauges and glass tubes: slow pulse between the normal (0) and lit (2) frames, each piece with its own phase
psInvPhase = {gauge_top = 0, gauge_left = 7, gauge_right = 13, tube_left = 3, tube_right = 9, tube_mid = 5}
function psInvPulse(name)
	local t = math.floor(Infinity_GetClockTicks() / 400) + (psInvPhase[name] or 0)
	if t % 6 == 0 then return 2 end
	return 0
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

-- detail lines come with EEex (step 2)
function psInvStatDetail(key)
	return ''
end
'''


def main():
    art = os.path.join(MOD, "art")
    os.makedirs(art, exist_ok=True)
    for f in os.listdir(art):  # J replaces the F/G/H preview art
        os.remove(os.path.join(art, f))
    background()
    for nm, res in BAMS.items():
        write_bam_v1(part_frames(nm, L["parts"][nm]), os.path.join(art, f"{res}.BAM"))
    menu = build_menu()
    assert "%" not in menu and "~" not in menu
    with open(os.path.join(MOD, "menu", "inventory.menu"), "w", encoding="utf-8", newline="\n") as f:
        f.write(menu)
    with open(os.path.join(MOD, "lua", "M_PSINV.lua"), "w", encoding="utf-8", newline="\n") as f:
        f.write(LUA_J)
    tp2 = bm.TP2.replace("// The \"Art\" button swaps the two background styles (F = PTEE pieces, G = generated art).",
                         "// Art: John's painted inventory; tabs, bag, face, gauges and tubes are separate animated BAMs.")
    with open(os.path.join(MOD, "InventairePTEE.tp2"), "w", encoding="utf-8", newline="\n") as f:
        f.write(tp2)
    print("mod J written:", MOD)


if __name__ == "__main__":
    main()
