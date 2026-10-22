-- Inventaire PSTEE, step 2b (John 2026-10-22): the stash grid on the inventory page, over the core (M_PSCORE.lua).
-- 60 cells show the stash filtered by the active tab; click = take into the shown character's backpack;
-- "Store all" = every backpack item into the stash. Item data read from the ITM headers (EEex).

PSUI = PSUI or {}
local U = PSUI
U.CELLS = 60
U.view = {}       -- entries shown in the grid (filtered)
U.itm = U.itm or {}

-- Tabs (psInvTabs order): All, Weapons, Tattoos, Jewelry, Eyes & Teeth, Charms, Quest, Misc. PST item types (ITM 0x1C).
local TAB_TYPES = {
	[2] = { [16] = true, [17] = true, [19] = true, [21] = true, [25] = true, [27] = true, [28] = true, [31] = true,
		[35] = true, [57] = true },
	[3] = { [39] = true },
	[4] = { [10] = true, [75] = true },
	[5] = { [74] = true, [76] = true, [40] = true },
	[6] = { [77] = true, [73] = true },
	[7] = { [8] = true },
}

local function readRes(p)
	local t = {}
	for i = 0, 7 do
		local b = EEex_ReadU8(p + i)
		if b == 0 then break end
		t[#t + 1] = string.char(b)
	end
	return string.upper(table.concat(t))
end

-- { type, icon, name strref (identified / not), weight }
function PSUI_ItemInfo(res)
	local c = U.itm[res]
	if c ~= nil then return c or nil end
	local ok, info = pcall(function()
		local h = EEex_Resource_Demand(res, 'ITM')
		if not h then return nil end
		local p = EEex_UDToPtr(h)
		return { type = EEex_ReadU16(p + 0x1C), icon = readRes(p + 0x3A), unidName = EEex_ReadU32(p + 0x08),
			idName = EEex_ReadU32(p + 0x0C), weight = EEex_ReadU32(p + 0x4C) }
	end)
	U.itm[res] = ok and info or false
	return ok and info or nil
end

local function inTab(info, tab)
	if tab == 1 or not info then return true end
	if tab == 8 then
		for t = 2, 7 do if TAB_TYPES[t][info.type] then return false end end
		return true
	end
	return TAB_TYPES[tab][info.type] == true
end

-- portrait index of the character shown in the inventory (global `id`)
function PSUI_Portrait()
	for p = 0, 5 do
		local sp = EEex_Sprite_GetInPortrait(p)
		if sp and sp.m_id == id then return p end
	end
	return 0
end

-- Rebuilds the grid view (called when the page opens, after each action and on tab change).
function PSUI_Refresh()
	U.view = {}
	if not PSC_Ready or not PSC_Ready() then return end
	local tab = psInvActiveTab or 1
	for _, e in ipairs(PSC_List()) do
		if inTab(PSUI_ItemInfo(e.res), tab) then U.view[#U.view + 1] = e end
	end
end

function PSUI_Icon(i)
	local e = U.view[i]
	local info = e and PSUI_ItemInfo(e.res)
	return info and info.icon or ''
end

function PSUI_Count(i)
	local e = U.view[i]
	if e and e.count > 1 then return tostring(e.count) end
	return ''
end

function PSUI_Name(i)
	local e = U.view[i]
	if not e then return nil end
	local info = PSUI_ItemInfo(e.res)
	if not info then return e.res end
	local ref = (e.identified and info.idName > 0) and info.idName or info.unidName
	return Infinity_FetchString(ref)
end

function PSUI_Has(i) return U.view[i] ~= nil end

function PSUI_Take(i)
	local e = U.view[i]
	if not e then return end
	local ok, why = PSC_Take(PSUI_Portrait(), e.res)
	if not ok then print('PSC take failed ' .. tostring(why)) end
	PSUI_Refresh()
end

function PSUI_StoreAll()
	local portrait = PSUI_Portrait()
	for slot = PSC.BACKPACK_FIRST, PSC.BACKPACK_LAST do
		local ok, why = PSC_Add(portrait, slot)
		if not ok and why ~= 'empty slot' then print('PSC store slot ' .. slot .. ' ' .. tostring(why)) end
	end
	PSUI_Refresh()
end

-- Stash weight in LB (sum of item weights x count), for the header.
function PSUI_Weight()
	local w = 0
	if not PSC_Ready or not PSC_Ready() then return 0 end
	for _, e in ipairs(PSC_List()) do
		local info = PSUI_ItemInfo(e.res)
		if info then w = w + info.weight * math.max(1, e.count) end
	end
	return w
end
