-- Inventaire PSTEE, step 2b (John 2026-10-22): the stash grid on the inventory page, over the core (M_PSCORE.lua).
-- 60 cells show the stash filtered by the active tab; click = take into the shown character's backpack;
-- "Store all" = every backpack item into the stash. Item data read from the ITM headers (EEex).

PSUI = PSUI or {}
local U = PSUI
U.CELLS = 60
U.view = {}       -- entries shown in the grid (filtered, sorted)
U.page = U.page or 1
U.sort = U.sort or 1
U.SORTS = { 'Auto', 'Name', 'Type', 'Price', 'Weight' }
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

-- Quest item: the game's dialogues or scripts look for it in the party (M_PSQST.lua), or it is a key (type 8).
function PSUI_IsQuest(res)
	if PSC_QUEST and PSC_QUEST[res] then return true end
	local info = PSUI_ItemInfo(res)
	return info ~= nil and info.type == 8
end

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
			idName = EEex_ReadU32(p + 0x0C), weight = EEex_ReadU32(p + 0x4C), price = EEex_ReadU32(p + 0x34) }
	end)
	U.itm[res] = ok and info or false
	return ok and info or nil
end

local function inTab(res, info, tab)
	if tab == 1 or not info then return true end
	if tab == 7 then return PSUI_IsQuest(res) end
	if tab == 8 then
		if PSUI_IsQuest(res) then return false end
		for t = 2, 6 do if TAB_TYPES[t][info.type] then return false end end
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

local function entryName(e)
	local info = PSUI_ItemInfo(e.res)
	if not info then return e.res end
	local first, second = info.unidName, info.idName
	if e.identified then first, second = info.idName, info.unidName end
	-- some PST items have only one of the two names (or an unset strref)
	for _, ref in ipairs({ first, second }) do
		if ref > 0 and ref < 0xFFFFFFFF then
			local n = Infinity_FetchString(ref)
			if n and n ~= '' then return n end
		end
	end
	return e.res
end

local function byField(f, descending)
	return function(a, b)
		local x, y = PSUI_ItemInfo(a.res), PSUI_ItemInfo(b.res)
		local vx, vy = x and x[f] or 0, y and y[f] or 0
		if vx ~= vy then
			if descending then return vx > vy end
			return vx < vy
		end
		return entryName(a) < entryName(b)
	end
end
local SORTERS = { Name = function(a, b) return entryName(a) < entryName(b) end, Type = byField('type'),
	Price = byField('price', true), Weight = byField('weight', true) }
SORTERS.Auto = SORTERS.Type

function PSUI_Pages() return math.max(1, math.ceil(#U.view / U.CELLS)) end
function PSUI_PageText() return U.page .. '/' .. PSUI_Pages() end
function PSUI_PageTurn(d) U.page = math.max(1, math.min(PSUI_Pages(), U.page + d)) end

-- Rebuilds the grid view (called when the page opens, after each action and on tab or sort change).
function PSUI_Refresh()
	U.view = {}
	if not PSC_Ready or not PSC_Ready() then return end
	local tab = psInvActiveTab or 1
	for _, e in ipairs(PSC_List()) do
		if inTab(e.res, PSUI_ItemInfo(e.res), tab) then U.view[#U.view + 1] = e end
	end
	table.sort(U.view, SORTERS[U.SORTS[U.sort]])
	if U.page > PSUI_Pages() then U.page = PSUI_Pages() end
end

function PSUI_NextSort()
	U.sort = U.sort % #U.SORTS + 1
	PSUI_Refresh()
end
function PSUI_SortText() return 'Sort: ' .. U.SORTS[U.sort] end

local function cell(i) return U.view[(U.page - 1) * U.CELLS + i] end

function PSUI_Icon(i)
	local e = cell(i)
	local info = e and PSUI_ItemInfo(e.res)
	return info and info.icon or ''
end

function PSUI_Count(i)
	local e = cell(i)
	if e and e.count > 1 then return tostring(e.count) end
	return ''
end

function PSUI_Name(i)
	local e = cell(i)
	return e and entryName(e) or nil
end

function PSUI_Has(i) return cell(i) ~= nil end

function PSUI_Take(i)
	local e = cell(i)
	if not e then return end
	local ok, why = PSC_Take(PSUI_Portrait(), e.res)
	if not ok then print('PSC take failed ' .. tostring(why)) end
	PSUI_Refresh()
	PSC_RefreshPage()
end

-- Must stay on the party: the game would not see it in the bag (M_PSQST.lua: counted, worn...), or it is a key.
function PSUI_Keep(res)
	if PSC_KEEP and PSC_KEEP[res] then return true end
	local info = PSUI_ItemInfo(res)
	return info ~= nil and info.type == 8
end

function PSUI_StoreAll()
	local portrait = PSUI_Portrait()
	local kept = 0
	for _, slot in ipairs(PSC.BACKPACK) do
		local res = PSC_SlotRes(portrait, slot)
		if res and PSUI_Keep(res) then
			kept = kept + 1
		elseif res then
			local ok, why = PSC_Add(portrait, slot)
			if not ok then print('PSC store slot ' .. slot .. ' ' .. tostring(why)) end
		end
	end
	TEXT_inventoryError = kept > 0 and (kept .. (kept > 1 and ' items must stay' or ' item must stay') .. ' in the backpack') or ''
	PSUI_Refresh()
	PSC_RefreshPage()
end

-- Drag and drop onto the stash grid (same as Party Stash BG): menu buttons get no clicks while an item is in hand, so
-- while one is held a real slot widget bound to the bag slot (group 19) covers the grid, and the game drops the item
-- into the bag itself. Slot widgets ignore "enabled", so it stays at size 0 until needed. Infinity_SetArea would find the
-- vanilla menu's widget of the same name: walk this menu's items instead (the size-0 slot).
local drop = { held = false, slotInfo = {}, item = nil }

local function holding()
	local inv = EEex_EngineGlobal_CBaldurChitin.m_pEngineInventory
	return inv ~= nil and inv.m_pTempItem ~= nil
end
PSUI_Holding = holding

local function placeOverlay(on)
	if not on then
		if drop.item then
			local a = drop.item.area
			a.x, a.y, a.w, a.h = 0, 0, 0, 0
			drop.item = nil
		end
		return
	end
	local menu = EEex_Menu_Find('INVENTORY')
	local item = menu and menu.items
	while item ~= nil do
		if item.type == 9 and item.area.w == 0 and item.area.h == 0 then
			local a = item.area
			a.x, a.y, a.w, a.h = PSUI_GRID[1], PSUI_GRID[2], PSUI_GRID[3], PSUI_GRID[4]
			drop.item = item
			return
		end
		item = item.next
	end
end

-- What the overlay shows: no icon, no placeholder. One table, refilled in place.
function PSUI_DropSlot(n)
	local real = characters and characters[id] and characters[id].equipment['group' .. n]
	local t = drop.slotInfo
	for k in pairs(t) do t[k] = nil end
	for k, v in pairs(real or {}) do t[k] = v end
	t.empty, t.tooltip, t.highlight, t.placeholder = 0, '', 0, ''
	t.item = { count = 0, usages = 0, icon = '', tint = '', name = '', identified = 1 }
	return t
end

-- Called every frame by the inventory page.
function PSUI_DropTick()
	local now = holding()
	if now then drop.gold = game:GetPartyGold() end
	if now and not drop.held then
		local res = PSC_ItemRes(EEex_EngineGlobal_CBaldurChitin.m_pEngineInventory.m_pTempItem)
		local keep = PSUI_Keep(res)
		if keep then TEXT_inventoryError = 'This item must stay in the backpack' end
		placeOverlay(not keep and res ~= PSC.RES)
	elseif drop.held and not now then
		placeOverlay(false)
		PSC_UndoPay(drop.gold)
		PSUI_Refresh()
		PSC_RefreshPage()
		drop.recheck = Infinity_GetClockTicks() + 300  -- the engine may store the item a frame later
	elseif drop.recheck and Infinity_GetClockTicks() >= drop.recheck then
		drop.recheck = nil
		PSC_UndoPay(drop.gold)
		PSUI_Refresh()
	end
	drop.held = now
	return false
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

function PSUI_WeightText() return 'Stash: ' .. PSUI_Weight() .. ' LB' end
