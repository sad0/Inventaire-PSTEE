"""Build the in-game preview mod (WeiDU) from the design manifest + layout.

Step 1 (John 2026-10-22): the redesigned inventory page, functional (equipment, quick slots, backpack, ground),
with a button to swap the F (PSTEE pieces) and G (generated art) backgrounds. The stash grid/tabs/sort/store-all
are drawn but inactive until the EEex stash (step 2).

Usage: python tools/build_mod.py  (after tools/build_assets.py). Writes mod/InventairePSTEE/.
"""
import json
import os
import struct

from PIL import Image

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
BUILD = os.path.join(ROOT, "design", "build")
MOD = os.path.join(ROOT, "mod", "InventairePSTEE")
M = json.load(open(os.path.join(BUILD, "manifest.json"), encoding="utf-8"))
L = json.load(open(os.path.join(BUILD, "layout.json"), encoding="utf-8"))
VARIANTS = {"F": "Variant F", "G": "Variant G", "H": "Variant H"}
BG_W, BG_H, OX = 1366, 768, 171


# ------------------------------------------------------------------ flattened backgrounds
def engine_drawn(n):
    """Nodes the engine draws itself (slots, items, texts, buttons, the paperdoll) are left out of the art."""
    return n.get("kind") in ("slot", "item", "text") or n.get("kind_bg") == "button" or "paperdoll IVPNOA" in n["name"]


def flatten(prefix):
    root = next(n for n in M["root"] if n["name"].startswith("Party Stash mockup"))
    var = next(n for n in root["children"] if n["name"].startswith(prefix))
    img = Image.new("RGBA", (BG_W, BG_H), (0, 0, 0, 255))

    def walk(nodes):
        for n in nodes:
            if engine_drawn(n):
                continue
            if n["type"] == "group":
                walk(n["children"])
            elif n["type"] == "layer":
                im = Image.open(os.path.join(ROOT, n["png"])).convert("RGBA")
                tmp = Image.new("RGBA", img.size, (0, 0, 0, 0))
                tmp.paste(im, (n["x"] + OX, n["y"]))
                img.alpha_composite(tmp)

    walk(var["children"])
    return img.convert("RGB")


def write_mos_v1(img, path):
    """MOS V1: 64x64 tiles, one 256-colour palette per tile (BGRA), uncompressed."""
    w, h = img.size
    cols, rows = (w + 63) // 64, (h + 63) // 64
    pals, datas = [], []
    for r in range(rows):
        for c in range(cols):
            tile = img.crop((c * 64, r * 64, min(w, c * 64 + 64), min(h, r * 64 + 64)))
            q = tile.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
            pal = q.getpalette()[:255 * 3]
            pal += [0] * (255 * 3 - len(pal))
            entries = []
            for i in range(255):
                rr, gg, bb = pal[i * 3:i * 3 + 3]
                if (rr, gg, bb) == (0, 255, 0):
                    gg = 254  # pure green is the transparent key
                entries.append(struct.pack("<BBBB", bb, gg, rr, 0))
            entries.append(struct.pack("<BBBB", 0, 0, 0, 0))
            pals.append(b"".join(entries))
            datas.append(q.tobytes())
    offs, pos = [], 0
    for d in datas:
        offs.append(pos)
        pos += len(d)
    hdr = b"MOS V1  " + struct.pack("<HHHHII", w, h, cols, rows, 64, 24)
    with open(path, "wb") as f:
        f.write(hdr + b"".join(pals) + b"".join(struct.pack("<I", o) for o in offs) + b"".join(datas))


# ------------------------------------------------------------------ menu
def area(a):
    return f"area {a[0]} {a[1]} {a[2]} {a[3]}"


def slot(name, rect, bam, seq, info):
    return (f'\tslot {{name "{name}"\t{area(rect)}\tbam "{bam}"\tsequence {seq}\t'
            f'slotinfo "characters[id].equipment.{info}"\thighlight selected 1}}\n')


def label(rect, text_lua=None, text=None, style="label", point=None, align=None, color_lua=None, font=None,
          enabled=None):
    s = "\tlabel\n\t{\n"
    if enabled:
        s += f'\t\tenabled "{enabled}"\n'
    s += f"\t\t{area(rect)}\n"
    s += f'\t\ttext lua "{text_lua}"\n' if text_lua else f'\t\ttext "{text}"\n'
    s += f'\t\ttext style "{style}"\n'
    if font:
        s += f'\t\ttext font "{font}"\n'
    if point:
        s += f"\t\ttext point {point}\n"
    if color_lua:
        s += f'\t\ttext color lua "{color_lua}"\n'
    if align:
        s += f"\t\ttext align {align}\n"
    return s + "\t}\n"


def button(rect, bam, seq=0, action=None, text_lua=None, point=None, enabled=None, tooltip_lua=None):
    s = f"\tbutton\n\t{{\n\t\t{area(rect)}\n\t\tbam \"{bam}\"\n\t\tsequence {seq}\n"
    if enabled:
        s += f'\t\tenabled "{enabled}"\n'
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
    m = []
    m.append("""
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
""")
    pd = L["paperdoll"]
    m.append(f'\tbutton\n\t{{\n\t\t{area(pd)}\n\t\tpaperdoll 1\n\t\tactiondrag "Infinity_SwapWithAppearance()"\n\t}}\n')
    t = L["text"]
    m.append(label(t["title"], text_lua="psInvText('title')", style="label_parchment", font="EXOCET", point=22))
    m.append(label(t["name"], text_lua="characters[id].name", point=15))
    m.append(label(t["class"], text_lua="characters[id].class", point=15))
    m.append(label(t["weight"], text_lua="psInvWeight()", style="normal", point=15, align="left center",
                   color_lua="getEncumbranceColor()"))
    m.append(label(t["gold"], text_lua="characters[id].gold", style="gold", point=16))
    for nm, r in L["titles"].items():
        m.append(label(r, text_lua=f"psInvText('{nm}')", point=15))
    # stats (values in the discs; detail lines need EEex, step 2)
    for nm, st in L["stats"].items():
        d = st["disc"]
        m.append(label((d[0], d[1] - 14, d[2], 14), text_lua=f"psInvText('{nm}')", style="normal", point=11,
                       align="center top", color_lua="psInvYellow()"))
        m.append(label((d[0], d[1] + 22, d[2], 40), text_lua=f"psInvStat('{nm}')", point=15))
        p = st["plate"]
        m.append(label((p[0] + 18, p[1] + 14, p[2] - 26, p[3] - 24), text_lua=f"psInvStatDetail('{nm}')",
                       style="normal", point=12, align="left top"))
    # message line (vanilla TEXT_inventoryError)
    m.append("\ttext\n\t{\n\t\tarea 640 606 150 34\n\t\ttext lua \"TEXT_inventoryError\"\n\t\ttext style normal\n"
             "\t\ttext point 12\n\t\ttext align left center\n\t}\n")
    # slots (vanilla names and slotinfo, new places)
    names = {"weapon": 1, "personal": 5, "quiver": 15}
    for i, a in enumerate(L["quick weapons"]):
        m.append(slot(f"slot_inv_{names['weapon'] + i}", a, "SLOTSWRD", i, f"weapon{i}"))
    for i, a in enumerate(L["quick items"]):
        m.append(slot(f"slot_inv_{names['personal'] + i}", a, "SLOTITM", i, f"personal{i}"))
    for i, a in enumerate(L["quiver"]):
        m.append(slot(f"slot_inv_{names['quiver'] + i}", a, "SLOTARW", i, f"quiver{i}"))
    body_ids = {"chest0": 11, "wrist0": 12, "earringleft0": 13, "earringright0": 14, "tattoo0": 21, "ring0": 22,
                "ring1": 23, "tattoo1": 24, "hand0": 25, "tattoo2": 26}
    for i, (nm, a) in enumerate(L["body"].items()):
        m.append(slot(f"slot_inv_{body_ids[nm]}", a, "IVSLOT", i % 10, nm))
    for n, a in enumerate(L["backpack"]):
        m.append(slot(f"slot_inv_{30 + n}", a, "IVSLOT", n % 10, f"group{n}"))
    for n, a in enumerate(L["ground"]):
        m.append(slot(f"slot_inv_{68 + n}", a, "IVSLOT", (n + 4) % 10, f"ground{n}"))
    # ground paging
    m.append(button(L["ground_prev"], "ARROBUTT", 0, "Infinity_OnGroundPage(-1)"))
    m.append(button(L["ground_next"], "ARROBUTT", 1, "Infinity_OnGroundPage(1)"))
    m.append(label(L["ground_page"],
                   text_lua="Infinity_GetCurrentGroundPage()+1 .. '/' .. Infinity_GetMaxGroundPage()+1", point=13))
    # stash controls: drawn, inactive until step 2
    b = L["buttons"]
    for i, r in enumerate(b["tabs"]):
        m.append(button(r, "GENBUT1", 2 if i == 0 else 0, None, f"psInvTab({i + 1})", 12))
    m.append(button(b["sort"], "STRBUTT", 0, None, "psInvText('Sort')", 13))
    m.append(button(b["store_all"], "STRBUTT", 0, None, "psInvText('Store all')", 15))
    # art swap (F <-> G) + close
    m.append(button((880, 16, 80, 26), "GENBUT1", 0, "psInvToggleVariant()", "psInvVariantLabel()", 12,
                    tooltip_lua="psInvText('Swap')"))
    m.append(button(b["close"], "XBUTT", 0, "e:GetActiveEngine():SelectEngine(worldScreen)"))
    m.append("}\n")
    return "".join(m)


LUA = r'''-- Inventaire PSTEE (Party Stash for Planescape: Torment EE), step 1: redesigned inventory page.
-- Background art variant: 'H' (tentacular pipes), 'G' (generated pieces) or 'F' (PSTEE pieces), saved in the ini.
psInvVariants = {F = 'G', G = 'H', H = 'F'}
psInvVariant = Infinity_GetINIString('Party Stash', 'Inventory Art', 'H')
if psInvVariants[psInvVariant] == nil then psInvVariant = 'H' end

function psInvBackground()
	return 'PSIVBG' .. psInvVariant
end

function psInvToggleVariant()
	psInvVariant = psInvVariants[psInvVariant]
	Infinity_SetINIValue('Party Stash', 'Inventory Art', psInvVariant)
	Infinity_SetBackground('BACKGROUND_INVENTORY')
end

function psInvVariantLabel()
	return 'Art: ' .. psInvVariant
end

psInvTexts = {
	title = 'Inventory', Quiver = 'Quiver', ['Quick Weapons'] = 'Quick Weapons', ['Quick Items'] = 'Quick Items',
	AC = 'AC', THAC0 = 'THAC0', HP = 'HP', Damage = 'Damage', Sort = 'Sort: Auto', ['Store all'] = 'Store all',
	Swap = 'Swap the inventory art (F: game pieces, G: generated pieces, H: tentacular pipes)',
}
psInvTabs = {'All', 'Weap.', 'Tatt.', 'Jewel', 'Eyes', 'Charm', 'Quest', 'Misc'}

function psInvText(key) return psInvTexts[key] or key end
function psInvTab(i) return psInvTabs[i] end

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

TP2 = r'''// Inventaire PSTEE: Party Stash inventory page for Planescape: Torment EE (step 1 preview).
BACKUP ~weidu_external/backup/InventairePSTEE~
AUTHOR ~sad0~
VERSION ~v0.3~

LANGUAGE ~English~ ~english~

// #0 Redesigned inventory page (BG Party Stash / LeUI organisation, PSTEE art). Equipment, quick slots, backpack
// and ground work; the stash grid, tabs, sort and store-all are drawn but wait for the EEex stash (step 2).
// The "Art" button swaps the two background styles (F = PSTEE pieces, G = generated art).
BEGIN ~Party Stash inventory page (preview)~ DESIGNATED 0
LABEL ~INVENTAIREPSTEE-PAGE~
REQUIRE_PREDICATE GAME_IS ~pstee~ ~Planescape: Torment EE only.~
REQUIRE_PREDICATE MOD_IS_INSTALLED ~EEex.tp2~ (ID_OF_LABEL ~EEex.tp2~ ~B3-EEex-Main~) ~Requires EEex (PSTEE build): install it first.~

COPY ~InventairePSTEE/art~ ~override~
COPY ~InventairePSTEE/lua/M_PSINV.lua~ ~override~
COPY ~InventairePSTEE/lua/M_PSCORE.lua~ ~override~   // step 2a: stash core (EEex), console-tested
COPY ~InventairePSTEE/lua/M_PSUI.lua~ ~override~     // step 2b: stash grid on the inventory page

// The stash store (step 2a): a hidden bag store (type 5) built from a vanilla STORV1.1 store, no stock, buys every
// item type, practically unlimited capacity.
COPY_EXISTING ~BARSE.STO~ ~override/PSTASH.STO~
	WRITE_LONG  0x08 5
	WRITE_LONG  0x18 0            // buy rate 0 %: AddItemToStore pays the sell value at this rate
	WRITE_SHORT 0x22 65000
	WRITE_LONG  0x38 0            // no starting stock
	SET list_off = SOURCE_SIZE
	WRITE_LONG  0x2c list_off
	WRITE_LONG  0x30 80           // PST item types go up to 77 (74 eyes, 75 earrings, 76 teeth, 77 charms)
	INSERT_BYTES list_off (80 * 4)
	SET n = 0
	FOR (t = 0; t < 81; ++t) BEGIN
		PATCH_IF (t != 36) BEGIN
			WRITE_LONG (list_off + n * 4) t
			SET n += 1
		END
	END
BUT_ONLY

// read the menu text through a scratch copy (copying onto the mod's own file makes WeiDU restore an old copy on
// uninstall)
COPY ~InventairePSTEE/menu/inventory.menu~ ~weidu_external/InventairePSTEE/inventory.menu~
	READ_ASCII 0 psinv_menu (SOURCE_SIZE)

COPY_EXISTING ~UI.MENU~ ~override~
	PATCH_FOR_EACH anchor IN ~name 'INVENTORY'~ ~mosaic 'INVBG'~ BEGIN
		PATCH_IF (INDEX_BUFFER (EXACT_MATCH ~%anchor%~) < 0) BEGIN
			PATCH_FAIL ~UI.MENU: %anchor% not found (another inventory mod?)~
		END
	END
	REPLACE_TEXTUALLY EXACT_MATCH ~name 'INVENTORY'~ ~name 'INVENTORY_VANILLA'~
	REPLACE_TEXTUALLY EXACT_MATCH ~mosaic 'INVBG'~ ~mosaic lua "psInvBackground()"~
	SET len = BUFFER_LENGTH
	INSERT_BYTES len (STRING_LENGTH ~%psinv_menu%~)
	WRITE_ASCIIE len ~%psinv_menu%~
'''


def main():
    for d in ("art", "lua", "menu"):
        os.makedirs(os.path.join(MOD, d), exist_ok=True)
    for k, prefix in VARIANTS.items():
        img = flatten(prefix)
        img.save(os.path.join(BUILD, f"ingame_bg_{k}.png"))
        write_mos_v1(img, os.path.join(MOD, "art", f"PSIVBG{k}.MOS"))
    menu = build_menu()
    assert "%" not in menu and "~" not in menu, "menu text must stay WeiDU-safe"
    with open(os.path.join(MOD, "menu", "inventory.menu"), "w", encoding="utf-8", newline="\n") as f:
        f.write(menu)
    with open(os.path.join(MOD, "lua", "M_PSINV.lua"), "w", encoding="utf-8", newline="\n") as f:
        f.write(LUA)
    with open(os.path.join(MOD, "InventairePSTEE.tp2"), "w", encoding="utf-8", newline="\n") as f:
        f.write(TP2)
    print("mod written:", MOD)


if __name__ == "__main__":
    main()
