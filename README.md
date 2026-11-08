# Inventaire PSTEE

A redesigned inventory page with a shared party stash for **Planescape: Torment Enhanced Edition** (v3.2.2.0). It brings
[Party Stash](https://github.com/sad0/PartyStash-EE) from the Baldur's Gate games to Torment, with a new painted page.

**Status: preview (v0.8).** It works in play tests, but it has not been tested through a full playthrough.

## Features

- **Shared stash:** one stash for the whole party, with 8 tabs, 5 sort orders and pages.
- **Drag and drop:** drag an item onto the grid to store it, or use **Store all** for the backpack. Click a stash item to
  take it back.
- **Quests keep working:** every party member carries a stash bag in the last backpack slot, so the game sees what the
  stash holds. This leaves 19 free backpack slots.
- **New page:** details for AC, THAC0, HP and damage, including attacks per round.

## Requirements

- Planescape: Torment Enhanced Edition v3.2.2.0
- [EEex-Torment](https://github.com/sad0/EEex-Torment) v1.3.1-pstee2

The game must be started through `InfinityLoader.exe`, as EEex requires.

## Install

1. Close the game. Back up your saves if you care about them.
2. Download `InventairePSTEE-v0.8.zip` from [Releases](https://github.com/sad0/Inventaire-PSTEE/releases).
3. Extract it into the game folder, next to `Torment.exe`.
4. Run `setup-InventairePSTEE.exe`.

The cloned repository cannot be installed as it is: the mod's art is built from your game and only ships in the zip.

## Known limits

- **Items that stay in the backpack:** door and container keys, and the Tail (a dialogue counts it, and counting does not
  see the stash).
- **Merchants:** avoid clicking the stash bag's row in the sell list. The protections from Party Stash are in place, but
  this case is untested.
- **Language:** English only.
- **Not tested yet:** a party of 6, a member joining mid-game, opening a door with a key from the stash, uninstalling with
  the bag in a save.

## Not there yet

Weight penalty, Sell Marked and translations.

## Building from source

`tools/build_mod_j.py` writes the page and the installer into `mod/`. `tools/build_quest_items.py` regenerates the quest
item list from the game's dialogues and scripts. Both have local game paths at the top of the scripts: change them first.
The other files in `tools/` and `design/` are working files from development and test tools. None of them ship in the mod.
