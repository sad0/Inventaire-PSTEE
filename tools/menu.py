"""Tiny parser for Infinity Engine EE .menu files (menus and their items, Lua blocks skipped)."""
import re

ITEM_KINDS = {"label", "button", "slot", "text", "list", "edit", "handle", "map", "progressbar",
              "slider", "template", "listbox"}


def tokenize(src):
    toks = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c.isspace():
            i += 1
        elif src.startswith("--", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
        elif c == "`":
            j = src.find("`", i + 1)
            toks.append(("lua", src[i + 1:j]))
            i = j + 1
        elif c in "\"'":
            j = src.find(c, i + 1)
            toks.append(("str", src[i + 1:j]))
            i = j + 1
        elif c in "{}":
            toks.append((c, c))
            i += 1
        else:
            m = re.compile(r"[^\s{}\"'`]+").match(src, i)
            toks.append(("word", m.group(0)))
            i = m.end()
    return toks


def _block(toks, i):
    """Parse a {...} block starting after '{'. Returns (list of (key, [values] | block), i)."""
    out = []
    while toks[i][0] != "}":
        kind, val = toks[i]
        if kind == "word" and toks[i + 1][0] == "{":
            sub, i = _block(toks, i + 2)
            out.append((val.lower(), sub))
            continue
        # key followed by values on the same logical line: we cannot see newlines, so take values
        # until the next known keyword is impossible; instead collect raw tokens and interpret later
        out.append((None, (kind, val)))
        i += 1
    return out, i + 1


def parse(src):
    toks = tokenize(src)
    menus = []
    i = 0
    while i < len(toks):
        if toks[i] == ("word", "menu") and toks[i + 1][0] == "{":
            body, i = _block(toks, i + 2)
            menus.append(_menu(body))
        else:
            i += 1
    return menus


# Properties and how many value tokens they take (rest are flags or text sub-properties)
PROPS = {
    "name": 1, "area": 4, "bam": 1, "mosaic": 1, "sequence": 1, "frame": 1, "text": 1, "enabled": 1,
    "size": 2, "align": 2, "offset": 2, "icon": 1, "tooltip": 1, "action": 1, "scrollbar": 1,
    "slotinfo": 1, "rectangle": 1, "opacity": 1, "pad": 4, "rowheight": 1, "table": 1, "var": 1,
    "fill": 1, "glow": 1, "highlight": 1, "flash": 1, "paperdoll": 1, "actiondrag": 1, "onopen": 1,
    "onclose": 1, "greyscale": 1, "interactable": 1, "width": 1, "count": 1, "on": 1, "clickable": 1,
    "actionalt": 1, "actiondbl": 1, "actionenter": 1, "actionexit": 1, "actionupdate": 1, "pulse": 1,
    "usealpha": 1, "maxlines": 1, "progressbar": 1, "toggle": 1, "radio": 1, "rectangleopacity": 1,
}
SUB = {"style", "color", "align", "point", "font", "shadow", "highlight", "upper", "lua", "useontop",
       "selected"}


def _props(body):
    """Interpret a flat token list into a dict (best effort)."""
    props = {}
    toks = [t for k, t in body if k is None]
    j = 0
    while j < len(toks):
        kind, val = toks[j]
        key = val.lower() if kind == "word" else None
        if key == "text" and j + 1 < len(toks) and toks[j + 1][0] == "word" and toks[j + 1][1].lower() in SUB:
            sub = toks[j + 1][1].lower()
            if sub == "lua":
                props["text_lua"] = toks[j + 2][1]; j += 3; continue
            if sub == "color" and toks[j + 2] == ("word", "lua"):
                props["text_color"] = ("lua", toks[j + 3][1]); j += 4; continue
            if sub == "align":
                props["text_align"] = (toks[j + 2][1], toks[j + 3][1]); j += 4; continue
            props["text_" + sub] = toks[j + 2][1]; j += 3; continue
        if key in ("bam", "mosaic", "icon", "enabled", "sequence", "frame", "tooltip") and j + 1 < len(toks) \
                and toks[j + 1] == ("word", "lua"):
            props[key + "_lua"] = toks[j + 2][1]; j += 3; continue
        if key in PROPS:
            n = PROPS[key]
            vals = [t[1] for t in toks[j + 1:j + 1 + n]]
            props[key] = vals if n > 1 else (vals[0] if vals else None)
            j += 1 + n
            continue
        props.setdefault("_flags", []).append(val)
        j += 1
    if "area" in props:
        try:
            props["area"] = [int(v) for v in props["area"]]
        except ValueError:
            pass
    return props


def _menu(body):
    m = _props(body)
    m["items"] = []
    for k, v in body:
        if k in ITEM_KINDS:
            it = _props(v)
            it["kind"] = k
            # nested columns (list) keep raw
            it["children"] = [(ck, _props(cv)) for ck, cv in v if ck]
            m["items"].append(it)
    return m
