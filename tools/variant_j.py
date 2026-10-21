"""Variant J (John 2026-10-22): John's painted inventory taken as is (design/art/j/ref.png, x2 by SwarmUI img2img 0.2),
with the interactive pieces detached (buttons, bag, face, gauges, glass tubes) and the holes inpainted.

Steps (python tools/variant_j.py <step>):
  cut     -> design/art/j/parts/*.png (alpha cut-outs from ref_2x) + design/art/j/mask_2x.png
  inpaint -> design/art/j/bg_clean_2x.png (SwarmUI inpaint of the mask)
  layout  -> design/build/layout_j.json (UI geometry in INVENTORY menu coords)
Coordinates below are measured on ref.png (1579x996). Frame mapping: fx = x * K - 30, fy = y * K (K = 683/996).
"""
import base64
import json
import os
import sys
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
J = os.path.join(ROOT, "design", "art", "j")
K = 683 / 996
OXJ = -30          # image left edge in the 1024 frame (1083 px wide, centred)
API = "http://localhost:7801"

# (name, shape, box in ref px)
PARTS = [(f"tab{i + 1}", "pill", (b, 145, b + 68, 182)) for i, b in
         enumerate((758, 830, 903, 975, 1047, 1120, 1192, 1264))] + [
    ("tab_more", "round", (1349, 144, 1391, 184)),
    ("close", "round", (1497, 27, 1551, 81)),
    ("store_all", "pill", (759, 875, 943, 933)),
    ("page_prev", "round", (1401, 837, 1451, 883)),
    ("page_next", "round", (1461, 837, 1511, 883)),
    ("bag", "blob", (762, 16, 858, 110)),
    ("face", "round", (13, 6, 117, 120)),
    ("gauge_top", "round", (664, 47, 703, 89)),
    ("gauge_left", "round", (2, 244, 59, 306)),
    ("gauge_right", "round", (1519, 484, 1574, 541)),
    ("tube_left", "rect", (8, 358, 48, 482)),
    ("tube_right", "rect", (1526, 278, 1569, 412)),
    ("tube_mid", "rect", (664, 178, 701, 327)),
]
OVAL_INNER = (428, 238, 604, 488)   # baked character inside the oval: inpainted (the engine draws the paperdoll)


def shape_mask(shape, w, h, feather=1.5):
    m = Image.new("L", (w * 4, h * 4), 0)
    d = ImageDraw.Draw(m)
    if shape == "pill":
        d.rounded_rectangle((0, 0, w * 4 - 1, h * 4 - 1), radius=h * 2, fill=255)
    elif shape in ("round", "blob"):
        d.ellipse((0, 0, w * 4 - 1, h * 4 - 1), fill=255)
    else:
        d.rounded_rectangle((0, 0, w * 4 - 1, h * 4 - 1), radius=12, fill=255)
    return m.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(feather))


def cut():
    big = Image.open(os.path.join(J, "ref_2x.png")).convert("RGBA")
    os.makedirs(os.path.join(J, "parts"), exist_ok=True)
    mask = Image.new("L", big.size, 0)
    md = ImageDraw.Draw(mask)
    for name, shape, (x0, y0, x1, y1) in PARTS:
        bx = (x0 * 2, y0 * 2, x1 * 2, y1 * 2)
        part = big.crop(bx)
        part.putalpha(shape_mask(shape, part.width, part.height))
        part.save(os.path.join(J, "parts", f"{name}.png"))
        g = 6  # grow the inpaint mask a little past the cut
        if shape == "pill":
            md.rounded_rectangle((bx[0] - g, bx[1] - g, bx[2] + g, bx[3] + g), radius=(bx[3] - bx[1]) // 2 + g,
                                 fill=255)
        elif shape == "rect":
            md.rectangle((bx[0] - g, bx[1] - g, bx[2] + g, bx[3] + g), fill=255)
        else:
            md.ellipse((bx[0] - g, bx[1] - g, bx[2] + g, bx[3] + g), fill=255)
    o = OVAL_INNER
    md.ellipse((o[0] * 2, o[1] * 2, o[2] * 2, o[3] * 2), fill=255)
    mask.save(os.path.join(J, "mask_2x.png"))
    print("parts:", len(PARTS))


def post(path, data):
    req = urllib.request.Request(API + path, json.dumps(data).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.load(r)


def b64(path):
    return "data:image/png;base64," + base64.b64encode(open(path, "rb").read()).decode()


def inpaint(seed=5):
    sid = post("/API/GetNewSession", {})["session_id"]
    prompt = ("dark corroded stone wall, rusted copper pipes and corroded metal, steampunk, dark, matching the "
              "surroundings, painterly, no buttons, no text")
    res = post("/API/GenerateText2Image", {
        "session_id": sid, "images": 1, "prompt": prompt, "negativeprompt": "button, purple, text, gauge, face",
        "model": "ZImage/SwarmUI_Z-Image-Turbo-FP8Mix", "width": 3152, "height": 1984, "steps": 8, "cfgscale": 1,
        "seed": seed, "initimage": b64(os.path.join(J, "ref_2x.png")), "initimagecreativity": 0.9,
        "maskimage": b64(os.path.join(J, "mask_2x.png")), "maskblur": 8})
    if "images" not in res:
        raise SystemExit(f"SwarmUI: {res}")
    data = urllib.request.urlopen(API + "/" + urllib.parse.quote(res["images"][0])).read()
    open(os.path.join(J, "bg_clean_2x.png"), "wb").write(data)
    print("inpainted -> bg_clean_2x.png")


def F(x, y):
    return round(x * K + OXJ), round(y * K)


def FB(box):
    x0, y0 = F(box[0], box[1])
    x1, y1 = F(box[2], box[3])
    return (x0, y0, x1 - x0, y1 - y0)


def layout():
    """UI geometry on John's image, in INVENTORY menu coords (same keys as layout.json)."""
    L = {"menu": {"width": 1024, "height": 768, "bg_offset": OXJ, "bg_size": [round(1579 * K), 683]}}
    L["parts"] = {name: FB(box) for name, _, box in PARTS}
    # left column: title bars at ref y 165/300/440, slots in the dark band under each bar
    def rail(n, y):
        return [(14 + i * 40, y, 36, 36) for i in range(n)]
    L["quiver"], L["quick weapons"], L["quick items"] = rail(5, 150), rail(4, 248), rail(5, 340)
    L["titles"] = {"Quiver": FB((55, 165, 335, 198)), "Quick Weapons": FB((55, 302, 335, 338)),
                   "Quick Items": FB((55, 442, 335, 478))}
    # paperdoll + 10 body slots around the oval (ref oval frame 410-625 x 220-505)
    L["paperdoll"] = FB(OVAL_INNER)
    L["body"] = {"earringright0": (256, 104, 36, 36), "earringleft0": (296, 104, 36, 36),
                 "chest0": (336, 104, 36, 36), "wrist0": (376, 104, 36, 36),
                 "hand0": (404, 158, 36, 36), "ring0": (404, 204, 36, 36), "ring1": (404, 250, 36, 36),
                 "tattoo0": (270, 350, 36, 36), "tattoo1": (310, 350, 36, 36), "tattoo2": (350, 350, 36, 36)}
    # stats: rings (discs) and plates of the 2x4 boxes
    L["stats"] = {}
    for nm, (rx, ry, px0, px1) in {"AC": (120, 690, 200, 355), "THAC0": (450, 690, 505, 700),
                                   "HP": (120, 850, 200, 355), "Damage": (450, 850, 505, 700)}.items():
        cx, cy = F(rx, ry)
        top = 615 if ry < 800 else 778
        L["stats"][nm] = {"disc": (cx - 31, cy - 31, 62, 62), "plate": FB((px0, top, px1, top + 148))}
    # right column: backpack 2x10 above the rod (ref y 330), stash 6x10 under it, ground 1x10 row at the bottom
    L["backpack"] = [(501 + c * 50, 137 + r * 43, 40, 40) for c in range(10) for r in range(2)]
    L["stash"] = [(501 + c * 50, 238 + r * 46, 40, 40) for r in range(6) for c in range(10)]
    L["ground"] = [(501 + c * 42, 540, 38, 38) for c in range(10)]
    L["ground_prev"], L["ground_next"] = L["parts"]["page_prev"], L["parts"]["page_next"]
    L["ground_page"] = (930, 548, 80, 20)
    L["text"] = {"name": FB((178, 100, 330, 135)), "class": FB((330, 100, 468, 135)),
                 "weight": FB((870, 103, 1120, 135)), "gold": (765, 624, 100, 26), "title": (0, 0, 0, 0)}
    L["buttons"] = {"close": L["parts"]["close"], "sort": FB((1150, 103, 1330, 135)),
                    "store_all": L["parts"]["store_all"],
                    "tabs": [L["parts"][f"tab{i + 1}"] for i in range(8)], "tab_names":
                        ["All", "Weap.", "Tatt.", "Jewel", "Eyes", "Charm", "Quest", "Misc"],
                    "tab_more": L["parts"]["tab_more"], "bag": L["parts"]["bag"], "face": L["parts"]["face"]}
    with open(os.path.join(ROOT, "design", "build", "layout_j.json"), "w", encoding="utf-8") as f:
        json.dump(L, f, indent=1)
    print("layout_j.json written")


if __name__ == "__main__":
    {"cut": cut, "inpaint": inpaint, "layout": layout}[sys.argv[1]]()
