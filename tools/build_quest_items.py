"""List PSTEE quest items: items the game's dialogues and scripts look for in, or take from, the party.

Scans DLG (triggers and actions are plain text) and BCS (function ids + quoted strings) of the vanilla game, read-only.
Writes mod/InventairePSTEE/lua/M_PSQST.lua. Same rule as Party Stash BG (dialogues and scripts decide), run at build time.
PSC_QUEST: the Quest tab. PSC_KEEP: those looked for in a way not checked to see into the stash bag: they stay on the party.
Checked on the test copy with a carried bag: PartyHasItem and HasItem see the stash; TakePartyItem, TakePartyItemNum and
DestroyPartyItem take from it; NumItemsPartyGT does not see it.

Usage: python tools/build_quest_items.py [--show]
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
import ie  # noqa: E402

GAME = r"E:\Enhanced Edition\Environnement de test\Planescape Torment Enhanced Edition"
OUT = os.path.join(os.path.dirname(__file__), "..", "mod", "InventairePSTEE", "lua", "M_PSQST.lua")
ie.EXT_TO_TYPE.update({"DLG": 0x3F3, "BCS": 0x3EF, "IDS": 0x3F0, "ITM": 0x3ED, "STO": 0x3F6, "ARE": 0x3F2})
# Functions meaning "the party has it / gives it up". Dialogue HasItem is about the speaker's party too.
PARTY_FUNCS = ("PartyHasItem", "PartyHasItemIdentified", "NumItemsParty", "NumItemsPartyGT", "NumItemsPartyLT",
               "TakePartyItem", "TakePartyItemNum", "TakePartyItemAll", "DestroyPartyItem", "DestroyPartyItemNum",
               "TakeItemListParty", "TransformPartyItem", "TransformPartyItemAll", "TransformItem", "TransformItemAll")
DLG_FUNCS = PARTY_FUNCS + ("HasItem", "HasItemEquiped", "HasItemEquipedReal", "NumItems", "NumItemsGT", "NumItemsLT")
BAG_OK = ("partyhasitem", "hasitem", "takepartyitem", "takepartyitemnum", "destroypartyitem")  # checked to work through the carried stash bag
EXTRA_KEEP = ("A7#BAG3",)
DLG_RE = re.compile(r'\b(%s)\s*\(\s*"([^"]{1,8})"' % "|".join(DLG_FUNCS), re.I)
DLG_REPLACE_RE = re.compile(r'\bTakeItemReplace\s*\(\s*"[^"]*"\s*,\s*"([^"]{1,8})"', re.I)


def key(res):
    """Lua table key: a resref like A7#BAG3 is not a Lua name."""
    return res if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", res) else '["%s"]' % res


def ids(g, name):
    """{name lower: value} of an IDS file (function names up to the parenthesis)."""
    out = {}
    for line in g.read(name, "IDS").decode("latin1").splitlines():
        m = re.match(r"\s*(0x[0-9a-fA-F]+|\d+)\s+(\w+)", line)
        if m:
            out[m.group(2).lower()] = int(m.group(1), 0)
    return out


def main():
    g = ie.Game(GAME)
    items = set(g.names("ITM"))
    found = {}
    keep = set()

    def add(res, where, sees_bag=False):
        res = res.upper()
        if res in items:
            found.setdefault(res, set()).add(where)
            if not sees_bag:
                keep.add(res)

    for n in g.names("DLG"):
        t = (g.read(n, "DLG") or b"").decode("latin1")
        for m in DLG_RE.finditer(t):
            add(m.group(2), n, m.group(1).lower() in BAG_OK)
        for m in DLG_REPLACE_RE.finditer(t):
            add(m.group(1), n)
    # BCS: "TR\n<id> ... "str" "str" OB" for triggers, "AC\n<id>" + objects + ... "str" for actions
    tr, ac = ids(g, "TRIGGER"), ids(g, "ACTION")
    want_tr = {tr[f.lower()] for f in PARTY_FUNCS if f.lower() in tr}
    want_ac = {ac[f.lower()] for f in PARTY_FUNCS if f.lower() in ac}
    ok_tr = {tr[f] for f in BAG_OK if f in tr}
    ok_ac = {ac[f] for f in BAG_OK if f in ac}
    tr_re = re.compile(r'TR\s+(\d+)[^"]*"([^"]*)"')
    ac_re = re.compile(r'AC\s+(\d+)(.*?)AC', re.S)
    for n in g.names("BCS"):
        t = (g.read(n, "BCS") or b"").decode("latin1")
        for m in tr_re.finditer(t):
            if int(m.group(1)) in want_tr and m.group(2):
                add(m.group(2), n, int(m.group(1)) in ok_tr)
        for m in ac_re.finditer(t):
            if int(m.group(1)) in want_ac:
                for s in re.findall(r'"([^"]+)"', m.group(2)):
                    add(s, n, int(m.group(1)) in ok_ac)
    # Keys of doors and containers: not checked to work from the bag, whatever their item type.
    for n in g.names("ARE"):
        d = g.read(n, "ARE") or b""
        if len(d) < 0xAC:
            continue
        conts_off, conts = struct.unpack_from("<IH", d, 0x70)
        doors, doors_off = struct.unpack_from("<II", d, 0xA4)
        spots = [(doors_off + 200 * i + 0x70) for i in range(doors)]
        spots += [(conts_off + 192 * i + 0x78) for i in range(conts)]
        for at in spots:
            if at + 8 <= len(d):
                res = d[at:at + 8].split(b"\0")[0].decode("latin1").strip()
                if res:
                    add(res, n)
    # Other mods' items (installed after this list is built): Bags of Torment's sealed Pocket Singularity
    # (TransformPartyItem in its dialogues; checked not to see into the stash bag).
    for res in EXTRA_KEEP:
        found.setdefault(res, set()).add("crossmod")
        keep.add(res)
    found.pop("COPPER", None)  # coins become gold, never a quest item
    keep.discard("COPPER")
    if "--show" in sys.argv:
        tlk = ie.Tlk(os.path.join(GAME, "lang", "en_US", "dialog.tlk"))
        for r in sorted(found):
            i = ie.itm_info(g, r)
            print(r, i["type"], tlk[i["name"]] or tlk[i["unid"]], sorted(found[r])[:3])
    print(len(found), "quest items,", len(keep), "must stay on the party:", sorted(keep))
    keep_body = ",\n".join("\t" + ", ".join(f"{key(r)} = true" for r in sorted(keep)[k:k + 8])
                           for k in range(0, len(keep), 8))
    body = ",\n".join("\t" + ", ".join(f"{key(r)} = true" for r in sorted(found)[k:k + 8])
                      for k in range(0, len(found), 8))
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("-- Generated by tools/build_quest_items.py: items the game's dialogues and scripts look for in,\n"
                "-- or take from, the party (Quest tab).\n"
                "PSC_QUEST = {\n" + body + ",\n}\n"
                "-- Looked for in a way not checked to see into the stash bag: they stay on the party.\n"
                "PSC_KEEP = {\n" + keep_body + ",\n}\n")


main()
