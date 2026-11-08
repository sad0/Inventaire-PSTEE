-- Report: stash contents + backpack of every party member.
local function res(a)
	local n = {}
	for k = 0, 7 do local b = EEex_ReadU8(a + 0x10 + k) if b == 0 then break end n[#n + 1] = string.char(b) end
	return table.concat(n)
end
local ls = {}
for _, e in ipairs(PSC_List()) do ls[#ls + 1] = e.res .. 'x' .. e.count .. '/u' .. tostring(e.uses) .. (e.identified and '/id' or '') end
PB('stash[' .. #ls .. '] ' .. table.concat(ls, ' '))
for p = 0, 5 do
	local sp = EEex_Sprite_GetInPortrait(p)
	if sp then
		local t = {}
		for _, i in ipairs(PSC.BACKPACK) do
			local a = EEex_ReadPtr(EEex_UDToPtr(sp.m_equipment.m_items) + EEex_PtrSize * i)
			if a ~= 0 then t[#t + 1] = i .. '=' .. res(a) .. ':' .. EEex_ReadU16(a + 0x18) end
		end
		PB('p' .. p .. ' ' .. table.concat(t, ' '))
	end
end
