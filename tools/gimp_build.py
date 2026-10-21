# Runs INSIDE GIMP 3.x (python-fu-eval batch). Builds design/inventory_ptee.xcf from design/build/manifest.json.
# Launched by tools/build_xcf.ps1; the project root comes from the INVPTEE_ROOT environment variable.
import json
import os

import gi

gi.require_version("Gimp", "3.0")
gi.require_version("Gegl", "0.4")
from gi.repository import Gegl, Gimp, Gio  # noqa: E402

ROOT = os.environ["INVPTEE_ROOT"]
RUN = Gimp.RunMode.NONINTERACTIVE
LOG = open(os.path.join(ROOT, "design", "build", "gimp_build.log"), "w", encoding="utf-8")


def log(*a):
    LOG.write(" ".join(str(x) for x in a) + "\n")
    LOG.flush()


def gfile(p):
    return Gio.File.new_for_path(p)


m = json.load(open(os.path.join(ROOT, "design", "build", "manifest.json"), encoding="utf-8"))
img = Gimp.Image.new(m["width"], m["height"], Gimp.ImageBaseType.RGB)
img.undo_disable()
_fonts = {}


def font(name):
    if name not in _fonts:
        f = Gimp.Font.get_by_name(name)
        if f is None:
            f = Gimp.context_get_font()
        _fonts[name] = f
    return _fonts[name]


stats = {"group": 0, "layer": 0, "text": 0}


def build(nodes, parent):
    # manifest lists children bottom-first: inserting each at position 0 puts the last one on top
    for n in nodes:
        t = n["type"]
        if t == "group":
            lay = Gimp.GroupLayer.new(img, n["name"])
            img.insert_layer(lay, parent, 0)
            build(n["children"], lay)
        elif t == "layer":
            lay = Gimp.file_load_layer(RUN, img, gfile(os.path.join(ROOT, n["png"])))
            lay.set_name(n["name"])
            img.insert_layer(lay, parent, 0)
            lay.set_offsets(n["x"], n["y"])
            if n.get("opacity", 100) != 100:
                lay.set_opacity(float(n["opacity"]))
        elif t == "text":
            lay = Gimp.TextLayer.new(img, n["text"], font(n["font"]), float(n["size"]), Gimp.Unit.pixel())
            img.insert_layer(lay, parent, 0)
            lay.set_name(n["name"])
            r, g, b = n["color"]
            c = Gegl.Color.new("black")
            c.set_rgba(r / 255.0, g / 255.0, b / 255.0, 1.0)
            lay.set_color(c)
            lay.set_offsets(n["x"], n["y"])
        lay.set_visible(bool(n["visible"]))
        stats[t] += 1


root_nodes = m["root"]
build(root_nodes, None)
for y in m["guides"]["h"]:
    img.add_hguide(y)
for x in m["guides"]["v"]:
    img.add_vguide(x)
img.undo_enable()
log("built", stats)

xcf = os.path.join(ROOT, "design", "inventory_ptee.xcf")
Gimp.file_save(RUN, img, gfile(xcf), None)
log("saved", xcf)

def find(name, layers=None):
    """First layer/group whose name starts with `name` (depth-first)."""
    for lay in (img.get_layers() if layers is None else layers):
        if lay.get_name().startswith(name):
            return lay
        if lay.is_group():
            hit = find(name, lay.get_children())
            if hit:
                return hit
    return None


def export(fname, show=(), hide=(), wide=False):
    """Flattened PNG of the image with some groups toggled; visibility restored afterwards."""
    saved = []
    for names, vis in ((show, True), (hide, False)):
        for nm in names:
            lay = find(nm)
            saved.append((lay, lay.get_visible()))
            lay.set_visible(vis)
    dup = img.duplicate()
    if wide:
        dup.resize(1366, 768, 171, 0)
    dup.merge_visible_layers(Gimp.MergeType.CLIP_TO_IMAGE)
    dup.flatten()
    Gimp.file_save(RUN, dup, gfile(os.path.join(ROOT, "design", "preview", fname)), None)
    dup.delete()
    for lay, vis in reversed(saved):
        lay.set_visible(vis)
    log("exported", fname)


os.makedirs(os.path.join(ROOT, "design", "preview"), exist_ok=True)
MOCK = "Party Stash mockup"
export("inventory_ptee_preview.png")  # default visibility of the .xcf
export("vanilla_1024.png", hide=[MOCK])
export("vanilla_1366.png", hide=[MOCK], wide=True)
export("stash_A_rail_toggle.png", show=["Variant A"], hide=["Variant B", "Variant C"])
export("stash_B_window.png", show=["Variant B"], hide=["Variant A", "Variant C"])
export("stash_C_ground_column.png", show=["Variant C"], hide=["Variant A", "Variant B"])
export("annotated_vanilla.png", show=["Annotations"], hide=[MOCK, "Party Stash A", "Party Stash B", "Party Stash C"])
export("annotated_stash.png", show=["Annotations", "Variant B"],
       hide=["Slots", "Text", "Labels & icons", "Buttons", "Paperdoll", "Variant A", "Variant C",
             "Party Stash A", "Party Stash C"])
LOG.close()
