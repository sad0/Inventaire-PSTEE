local sp = EEex_Sprite_GetInPortrait(0)
local base = EEex_UDToPtr(sp.m_equipment.m_items)
for _, i in ipairs(PSC.BACKPACK) do
	local a = EEex_ReadPtr(base + EEex_PtrSize * i)
	if a ~= 0 then
		local r = {}
		for k = 0, 7 do local b = EEex_ReadU8(a + 0x10 + k) if b == 0 then break end r[#r + 1] = string.char(b) end
		if table.concat(r) == 'BACKBTR' then PB('slot', i, 'flags after', EEex_ReadU32(a + 0x24)) end
	end
end
PB('pending', #PSC.pendingId)
