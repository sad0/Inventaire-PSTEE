-- Dump usage fields of the backpack (raw CItem +0x18..+0x24 and the bound fields).
local sp = EEex_Sprite_GetInPortrait(0)
for _, i in ipairs(PSC.BACKPACK) do
	local a = EEex_ReadPtr(EEex_UDToPtr(sp.m_equipment.m_items) + EEex_PtrSize * i)
	if a ~= 0 then
		local n = {}
		for k = 0, 7 do local b = EEex_ReadU8(a + 0x10 + k) if b == 0 then break end n[#n + 1] = string.char(b) end
		local u = {}
		for k = 0x18, 0x26, 2 do u[#u + 1] = EEex_ReadU16(a + k) end
		PB(i, table.concat(n), 'raw18', table.concat(u, ','))
	end
end
