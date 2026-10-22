# Inventaire-PSTEE

Party Stash (shared infinite party stash, see `../PartyStash-EE`) brought to **Planescape: Torment EE** (v3.2.2.0).
Step 1: design mockup.

## Design file

`design/inventory_ptee.xcf` (GIMP 3.2, ~80 MB, not in git: rebuild it). Canvas = the `INVENTORY` menu frame,
**1024x768**: GIMP pointer coordinates are UI.MENU `area` coordinates. Backgrounds (1366 wide) hang off-canvas
at x = -171 (*Image > Fit Canvas to Layers* to see them).

Top-level groups:

| Group | Contents |
|---|---|
| Background | `INVBG` + hidden cut-outs of every panel (rails, ground column, gold box, discs...) |
| Inventory (vanilla INVENTORY menu) | Paperdolls (`IVP*`, one per companion), slots by category (one group per slot; frame 0 visible, other states hidden), labels/icons, sample items, text in game fonts, buttons with all states |
| Action bar | `WORLD_ACTIONBAR` + `_LEFT`, drawn over the inventory: portraits, buttons with all states |
| Party Stash mockup | **Variant E (John's pick: LeUI layout, PSTEE textures, visible)**; D (first redesign), A (rail toggle), B (stash window), C (ground column) hidden |
| Library (hidden) | Buttons, tabs, slots/placeholders, scrollbars, BAM/MOS icons, panels/popups, bars, 120 item icons, paperdolls |
| Annotations (hidden) | Box + name + size + coords for each element |

Guides: menu frame, action bar, slot rails, mockup grids.
Previews: `design/inventory_ptee_preview.png` (default visibility) and `design/preview/*.png`.

Decisions (2026-10-21): redesign like BG (D), 8 PST tabs (All, Weapons, Tattoos, Jewelry, Eyes & Teeth, Charms,
Quest, Misc), weight like BG (sum of members' allowances), keep Store all, Sort, colour hints, Sell marked.

Notes found in the vanilla UI.MENU: quiver slots ask for `SLOTARRW`, the game only has `SLOTARW`
(the engine draws nothing there; the layers are kept hidden).

## Rebuild

```powershell
tools\build_xcf.ps1
```

`tools/build_assets.py` reads the game **read-only** (KEY/BIFF, MOS v1/v2, BAM v1/v2, PVRZ, TLK via `tools/ie.py`,
UI.MENU via `tools/menu.py`), writes `design/assets/` and `design/build/manifest.json`; then GIMP batch
(`tools/gimp_build.py`) builds the .xcf and exports the previews. `tools/preview.py` composites the manifest
with Pillow alone (quick check). Game path: `GAME` in `build_assets.py`.
