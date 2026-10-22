-- Debug: raw bytes and bound fields of each stash item (run with dofile from the console).
local g = EEex_UDToPtr(EEex_EngineGlobal_CBaldurChitin.m_pObjectGame)
local b = PSC.scratch
for i = 0, 7 do EEex_WriteU8(b + i, string.byte('PSTASH\0\0', i + 1)) end
PSC_Eng_DemandServerStore(g, b, 0)
local s = PSC_Eng_GetServerStore(g, b)
EEex_Utility_IterateCPtrList(EEex_PtrToUD(s, 'CStore').m_lInventory, function(d)
	local ok, e = pcall(function()
		local p = type(d) == 'number' and d or EEex_UDToPtr(d)
		local t = {}
		for i = 0, 0x57 do t[#t + 1] = string.format('%02x', EEex_ReadU8(p + i)) end
		print('PSC itemraw ' .. table.concat(t, ' '))
		print('PSC itemtype ' .. type(d) .. ' ' .. tostring(d))
		print('PSC itemId ' .. tostring(d.m_itemId))
		print('PSC itemId get ' .. tostring(d.m_itemId:get()))
		print('PSC stock ' .. tostring(d.m_nInStock) .. ' uses ' .. tostring(d.m_usageCount))
	end)
	print('PSC item ok ' .. tostring(ok) .. ' ' .. tostring(e))
end)
PSC_Eng_ReleaseServerStore(g, b)
