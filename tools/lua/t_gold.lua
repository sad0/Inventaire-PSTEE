-- Gold before/after each stash operation, one item at a time, for the portrait 1 backpack.
local function gold() return game:GetPartyGold() end
PB('gold start', gold())
for _, slot in ipairs({ 18, 19, 20 }) do
	local g0 = gold()
	PB('add slot', slot, PSC_Add(1, slot))
	PB('  gold', g0, '->', gold())
end
