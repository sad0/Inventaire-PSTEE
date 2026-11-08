local function gold() return game:GetPartyGold() end
for _, r in ipairs({ 'TTAC1', 'BRORING', 'COPPER' }) do
	local g0 = gold()
	PB('take', r, PSC_Take(1, r))
	PB('  gold', g0, '->', gold())
end
