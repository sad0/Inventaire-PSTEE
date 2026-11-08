-- Identified state: flag BACKBTR as identified in the backpack, store it, take it back, check after a tick.
local sp = EEex_Sprite_GetInPortrait(0)
local base = EEex_UDToPtr(sp.m_equipment.m_items)
for _, i in ipairs(PSC.BACKPACK) do
	local a = EEex_ReadPtr(base + EEex_PtrSize * i)
	if a ~= 0 then
		local r = {}
		for k = 0, 7 do local b = EEex_ReadU8(a + 0x10 + k) if b == 0 then break end r[#r + 1] = string.char(b) end
		if table.concat(r) == 'BACKBTR' then
			PB('flags before', EEex_ReadU32(a + 0x24))
			EEex_WriteU32(a + 0x24, 1)
			PB('add', PSC_Add(0, i))
			break
		end
	end
end
for _, e in ipairs(PSC_List()) do if e.res == 'BACKBTR' then PB('in stash identified', e.identified) end end
PB('take', PSC_Take(0, 'BACKBTR'))
