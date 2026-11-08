-- Give test items covering PST item types (one of each plus stacks), to the selected character.
for _, r in ipairs({ 'AX', 'BOLT01', 'TTAC1', 'AMBEAR', 'EYEBALL', 'FTEETH', 'BELL', 'KEYSNTRY', 'LENS01', 'COPPER', 'BREAST1', 'BROBRA' }) do C:CreateItem(r) end
PB('gave')
