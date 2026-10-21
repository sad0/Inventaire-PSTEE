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
OUT = os.path.join(ROOT, "design", "art", "h", "gen")
MODEL = "ZImage/SwarmUI_Z-Image-Turbo-FP8Mix"
PROMPTS = {
    "bg": ("dark grim steampunk industrial machine interior, Planescape Torment game UI background art, tentacular "
           "serpentine pipes coiling and twisting like snakes and tentacles, copper pipes, rusted iron pipes, "
           "verdigris green tubes, brass collars and rivets, riveted corroded dark metal plates, biomechanical, "
           "grimy, dark olive brown and rust palette, dim moody light, highly detailed painterly texture, no text"),
}
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
    with open(guide, "rb") as f:
        init = "data:image/png;base64," + base64.b64encode(f.read()).decode()
    sid = post("/API/GetNewSession", {})["session_id"]
    for c in creats.split(","):
        for sd in seeds.split(","):
            req = {"session_id": sid, "images": 1, "prompt": PROMPTS[pkey], "negativeprompt": NEG, "model": MODEL,
                   "width": 1792, "height": 896, "steps": 8, "cfgscale": 1, "seed": int(sd),
                   "initimage": init, "initimagecreativity": float(c)}
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
