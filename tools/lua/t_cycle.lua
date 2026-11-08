-- Round trips driven across frames by the bridge poll: PB_Cycle stores everything, then takes one item per call.
-- Each call of this file does one full pass: store all, take all back (items appear on the next AI ticks).
T_PASS = (T_PASS or 0) + 1
PSUI_StoreAll()
local n = #PSC_List()
local taken = 0
for _, e in ipairs(PSC_List()) do
	local ok, why = PSC_Take(0, e.res)
	if ok then taken = taken + 1 else PB('take refused', e.res, why) end
	if taken >= 16 then break end
end
PB('pass', T_PASS, 'stash before', n, 'taken', taken, 'stash after', #PSC_List())
