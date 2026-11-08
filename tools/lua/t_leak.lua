-- Compare a normal shop (BARSE) with the stash: no stash item may show up in it.
local g = EEex_UDToPtr(EEex_EngineGlobal_CBaldurChitin.m_pObjectGame)
local b = PSC.scratch
local function list(name)
	for i = 0, 7 do EEex_WriteU8(b + i, i < #name and string.byte(name, i + 1) or 0) end
	PSC_Eng_DemandServerStore(g, b, 0)
	local s = PSC_Eng_GetServerStore(g, b)
	local out = {}
	if s ~= 0 then
		EEex_Utility_IterateCPtrList(EEex_PtrToUD(s, 'CStore').m_lInventory, function(d) out[#out + 1] = string.upper(d.m_itemId:get()) end)
	end
	for i = 0, 7 do EEex_WriteU8(b + i, i < #name and string.byte(name, i + 1) or 0) end
	PSC_Eng_ReleaseServerStore(g, b)
	return out
end
PB('BARSE', table.concat(list('BARSE'), ' '))
PB('PSTASH', table.concat(list('PSTASH'), ' '))
