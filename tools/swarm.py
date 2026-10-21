"""SwarmUI client: img2img the variant H guide (or text2img) with Z-Image Turbo, save results in design/art/h/gen/.

Usage: python tools/swarm.py guide.png out_prefix creativity[,creativity...] seeds[,seeds...] [prompt-key]
Local SwarmUI at http://localhost:7801 (never start a second instance). Z-Image Turbo: steps 8, cfg 1 (no Flux:
non-commercial licence).
"""
import base64
import json
import os
import sys
import urllib.parse
import urllib.request

API = "http://localhost:7801"
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.environ.get("SWARM_OUT") or os.path.join(ROOT, "design", "art", "h", "gen")
MODEL = "ZImage/SwarmUI_Z-Image-Turbo-FP8Mix"
PROMPTS = {
    "bg": ("dark grim steampunk industrial machine interior, Planescape Torment game UI background art, tentacular "
           "serpentine pipes coiling and twisting like snakes and tentacles, copper pipes, rusted iron pipes, "
           "verdigris green tubes, brass collars and rivets, riveted corroded dark metal plates, biomechanical, "
           "grimy, dark olive brown and rust palette, dim moody light, highly detailed painterly texture, no text"),
    "bg2": ("dark grim steampunk biomechanical machine interior, Planescape Torment game UI background, long dark "
            "cables and thick copper pipes crossing each other in the shadows behind everything, panels of dark "
            "corroded stone framed by an organic corroded rusted metal lattice full of holes like bone or coral, "
            "thick copper pipes with brass collars, pressure gauges and glass tubes running along the panel edges, "
            "faint silhouettes of gothic spires of Sigil in the dark stone, warm copper and deep brown palette, very "
            "dark, deep shadows, painterly, highly detailed, no text"),
    "bg3": ("dark grim biomechanical steampunk machine interior, Planescape Torment game UI background, organic and "
            "tentacular, long dark cables and thick copper pipes crossing each other in deep shadow behind everything, "
            "panels of dark corroded stone with irregular organic edges, framed by a bone-like corroded rusted metal "
            "lattice full of holes like coral and vertebrae, wavy copper pipes with brass collars, pressure gauges and "
            "glass tubes along the edges, thin pipe tendrils escaping the frames, faint gothic spires of Sigil in the "
            "dark stone, warm copper and deep brown palette, very dark, deep shadows, painterly, no text"),
    "btn_pill": ("single horizontal pill-shaped game button, deep purple glass inset in a riveted aged copper bezel, "
                 "steampunk, Planescape Torment UI asset, centered, isolated on a plain pure black background"),
    "btn_round": ("single round game button, purple glass dome set in a riveted brass and copper ring bezel, "
                  "steampunk UI asset, centered, isolated on a plain pure black background"),
    "btn_wide": ("single wide rectangular game button with rounded ends, deep purple glass panel framed by riveted "
                 "corroded copper and brass, steampunk UI asset, centered, isolated on a plain pure black background"),
    "disc_gauge": ("single round brass pressure gauge ring frame, empty very dark glass centre without needle or "
                   "numbers, rivets, steampunk UI frame, centered, isolated on a plain pure black background"),
    "disc_port": ("single round riveted copper porthole frame, organic corroded edges, empty very dark centre, "
                  "steampunk UI frame, centered, isolated on a plain pure black background"),
}
WORN = (", worn and grimy: scratched tarnished dull dark purple glass, oxidized corroded copper with verdigris and rust "
        "stains, dark, low key light, aged game asset")
for _k in ("btn_pill", "btn_round", "btn_wide", "disc_port"):
    PROMPTS[_k + "_worn"] = PROMPTS[_k].replace(", centered", WORN + ", centered")
NEG = ("text, letters, watermark, logo, bright colors, saturated blue, cartoon, flat vector, people, faces, "
       "snake scales, reptile, scaly hoses")


def post(path, data):
    req = urllib.request.Request(API + path, json.dumps(data).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def main():
    guide, prefix, creats, seeds = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    pkey = sys.argv[5] if len(sys.argv) > 5 else "bg"
    os.makedirs(OUT, exist_ok=True)
    init = None
    if guide != "-":  # "-" = text2img (no init image)
        with open(guide, "rb") as f:
            init = "data:image/png;base64," + base64.b64encode(f.read()).decode()
    sid = post("/API/GetNewSession", {})["session_id"]
    for c in creats.split(","):
        for sd in seeds.split(","):
            req = {"session_id": sid, "images": 1, "prompt": PROMPTS[pkey], "negativeprompt": NEG, "model": MODEL,
                   "width": 1792, "height": 896, "steps": 8, "cfgscale": 1, "seed": int(sd)}
            if init:
                req.update(initimage=init, initimagecreativity=float(c))
            else:
                req.update(width=1024, height=1024)
            res = post("/API/GenerateText2Image", req)
            if "images" not in res:
                print("error", res)
                continue
            for p in res["images"]:
                with urllib.request.urlopen(API + "/" + urllib.parse.quote(p)) as r:
                    data = r.read()
                out = os.path.join(OUT, f"{prefix}_c{c}_s{sd}.png")
                with open(out, "wb") as f:
                    f.write(data)
                print("saved", out)


main()
