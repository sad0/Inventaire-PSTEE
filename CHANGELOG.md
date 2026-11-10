# Changelog

## v0.9

- **Bags from other mods** (Bags of Torment...), as in Party Stash: **Store all** asks first, then empties each bag into
  the stash and keeps the bag there. Collected bags are shown at the end of the All and Misc tabs. Dropping a bag on the
  grid shows a hint instead.
- **Fixed:** items that a dialogue transforms (the tankard, the teeth, the copper earring, the finger, the Unbroken Circle
  blades...) now stay in the backpack. The game does not see them in the stash, so the dialogue would fail.
- **Bags of Torment:** the sealed Pocket Singularity stays in the backpack, so its quest works.

## v0.8 (2026-11-08): first public preview

- **Stash bag:** every party member now carries a bag in the last backpack slot, as in Party Stash. This leaves 19 free
  backpack slots.
- **Quests see the stash:** quest items can now go into the stash. Dialogues and scripts still find them and can take them.
- **Exceptions:** door and container keys and the Tail stay in the backpack, with a message.
- **Dropping on the grid** now puts the item straight into the bag.
- **Merchants:** the bag can't be opened or sold from the sell list. Not tested in play yet: share your results!
- **Fixed:** dropping an item on the grid no longer earns 1 gold.

## v0.7

- **Fixed:** the stash cells no longer disappear while an item is in hand.

## v0.6

- **Drag and drop:** drag an item onto the stash grid to store it.

## v0.5

- **Quest items** stay in the backpack on Store all. The list of 143 items comes from the game's dialogues and scripts.
- **Quest tab** uses this list.

## v0.4

Checked on EEex-Torment v1.3.1-pstee2.

- **Fixed:** the stash used the wrong backpack slots.
- **Fixed:** taking a stack gave back only one unit.
- **Fixed:** items lost their identified state when taken back.
- **Fixed:** storing an item earned gold.
- **Fixed:** sort and pages did not work, and icons stayed stale after moving items.
- **Installer** now checks that EEex is installed.
