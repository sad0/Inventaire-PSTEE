-- Debug: dump the PSTASH store object and try to iterate its inventory (run with dofile from the console).
local g = EEex_UDToPtr(EEex_EngineGlobal_CBaldurChitin.m_pObjectGame)
local b = PSC.scratch
for i = 0, 7 do EEex_WriteU8(b + i, string.byte('PSTASH\0\0', i + 1)) end
PSC_Eng_DemandServerStore(g, b, 0)
local s = PSC_Eng_GetServerStore(g, b)
local t = {}
for i = 0, 0x10f, 8 do t[#t + 1] = tostring(EEex_ReadPtr(s + i)) end
print('PSC storeraw ' .. table.concat(t, ' '))
local ok, e = pcall(function()
	local u = EEex_PtrToUD(s, 'CStore')
	print('PSC list ' .. tostring(u.m_lInventory))
	EEex_Utility_IterateCPtrList(u.m_lInventory, function(d) print('PSC it ' .. tostring(d)) end)
end)
print('PSC iter ' .. tostring(ok) .. ' ' .. tostring(e))
PSC_Eng_ReleaseServerStore(g, b)
