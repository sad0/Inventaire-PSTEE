-- Map UI equipment keys to items, and engine slots 0..40 to items.
PB('id', id, 'char', characters and characters[id] and characters[id].name)
local c = characters[id]
local keys = {}
for k, v in pairs(c.equipment) do keys[#keys + 1] = k end
table.sort(keys)
for _, k in ipairs(keys) do
	local v = c.equipment[k]
	local r = v and v.item and v.item.res
	PB('ui', k, tostring(r), 'empty', tostring(v and v.empty), 'ph', tostring(v and v.placeholder))
end
local sp = EEex_Sprite_GetInPortrait(0)
for i = 0, 45 do
	local a = EEex_ReadPtr(EEex_UDToPtr(sp.m_equipment.m_items) + EEex_PtrSize * i)
	if a ~= 0 then
		local n = {}
		for k = 0, 7 do local b = EEex_ReadU8(a + 0x10 + k) if b == 0 then break end n[#n + 1] = string.char(b) end
		PB('slot', i, table.concat(n))
	end
end
