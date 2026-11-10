# Inventaire PSTEE

A redesigned inventory page with a shared party stash for **Planescape: Torment Enhanced Edition** (v3.2.2.0). It brings
[Party Stash](https://github.com/sad0/PartyStash-EE) from the Baldur's Gate games to Torment, with a new painted page.

**Status: preview (v0.9).** It works in play tests, but it has not been tested through a full playthrough.

## Features

- **Shared stash:** one stash for the whole party, with 8 tabs, 5 sort orders and pages.
- **Drag and drop:** drag an item onto the grid to store it, or use **Store all** for the backpack. Click a stash item to
  take it back.
- **Quests keep working:** every party member carries a stash bag in the last backpack slot, so the game sees what the
  stash holds. This leaves 19 free backpack slots.
- **Bags from other mods** (such as [Bags of Torment](https://github.com/Argent77/A7-BagsOfTorment)), as in Party Stash:
  **Store all** asks first, then empties each bag into the stash and keeps the bag there (end of the All and Misc tabs).
  Collected bags cannot be taken back.
- **New page:** details for AC, THAC0, HP and damage, including attacks per round.

## Requirements

- Planescape: Torment Enhanced Edition v3.2.2.0
- [EEex-Torment](https://github.com/sad0/EEex-Torment) v1.3.1-pstee2

The game must be started through `InfinityLoader.exe`, as EEex requires.

## Install

1. Close the game. Back up your saves if you care about them.
2. Download `InventairePSTEE-v0.9.zip` from [Releases](https://github.com/sad0/Inventaire-PSTEE/releases).
3. Extract it into the game folder, next to `Torment.exe`.
4. Run `setup-InventairePSTEE.exe`.

The cloned repository cannot be installed as it is: the mod's art is built from your game and only ships in the zip.

## Known limits

- **Items that stay in the backpack:** door and container keys, the Tail, and the items a dialogue transforms (the
  tankard, the teeth, the copper earring, Bags of Torment's sealed Pocket Singularity...). The game does not see the
  stash when it counts or transforms an item.
- **Language:** English only.
- **Uninstalling:** the stash contents and the collected bags are lost. Take out what you want to keep first.
- **Not tested yet:** selling the stash bag from a merchant's sell list, a full playthrough, a party of 6, a member joining
  mid-game, opening a door with a key from the stash, uninstalling with the bag in a save. Tried one of these? Please share
  your results on [Discord](https://discord.gg/3XzeQv7HeS) or [GitHub](https://github.com/sad0/Inventaire-PSTEE/issues)!

## Not there yet

Weight penalty, Sell Marked and translations.

## Building from source

`tools/build_mod_j.py` writes the page and the installer into `mod/`. `tools/build_quest_items.py` regenerates the quest
item list from the game's dialogues and scripts. Both have local game paths at the top of the scripts: change them first.
The other files in `tools/` and `design/` are working files from development and test tools. None of them ship in the mod.
