-- Fill the backpack, then map UI group/personal/quiver/weapon keys to engine slots through the item pointers' resrefs.
for _, r in ipairs({ 'BMACE', 'HAMMER', 'ANNAHDAG', 'BACKBTR', 'ADDAGGER', 'TTAC2', 'ANTAT', 'BRORING' }) do C:CreateItem(r) end
PB('gave8')
