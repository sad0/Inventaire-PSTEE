local sp = EEex_Sprite_GetInPortrait(0)
local byslot = {}
for i = 0, 45 do
	local a = EEex_ReadPtr(EEex_UDToPtr(sp.m_equipment.m_items) + EEex_PtrSize * i)
	if a ~= 0 then
		local n = {}
		for k = 0, 7 do local b = EEex_ReadU8(a + 0x10 + k) if b == 0 then break end n[#n + 1] = string.char(b) end
		byslot[#byslot + 1] = i .. '=' .. table.concat(n)
	end
end
PB('slots', table.concat(byslot, ' '))
local c = characters[id]
local g = {}
for i = 0, 19 do local v = c.equipment['group' .. i] g[#g + 1] = i .. '=' .. tostring(v and v.item and v.item.res) end
PB('groups', table.concat(g, ' '))
