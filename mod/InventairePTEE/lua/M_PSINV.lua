-- Inventaire PTEE (Party Stash for Planescape: Torment EE), step 1: redesigned inventory page (art J).
psInvTexts = {
	Quiver = 'Quiver', ['Quick Weapons'] = 'Quick Weapons', ['Quick Items'] = 'Quick Items',
	AC = 'AC', THAC0 = 'THAC0', HP = 'HP', Damage = 'Damage', Sort = 'Sort: Auto', ['Store all'] = 'Store all',
	Help = 'Help (right-click: move the texts)',
	Edit = 'Placement mode: drag the texts, right-click the face to finish',
}
psInvTabs = {'All', 'Weap.', 'Tatt.', 'Jewel', 'Eyes', 'Charm', 'Quest', 'Misc'}
psInvActiveTab = 1

function psInvBackground() return 'PSIVBGJ' end
function psInvText(key) return psInvTexts[key] or key end
function psInvTab(i) return psInvTabs[i] end
function psInvSelectTab(i) psInvActiveTab = i end
-- selected tab shows the "selected" frame (2)
function psInvTabFrame(i) if psInvActiveTab == i then return 2 end return 0 end

-- Placement mode (John 2026-10-22): right-click on the face, drag the texts, right-click again to finish.
-- Positions are saved in the game ini, section [Party Stash], keys pos_<text>.
psInvEdit = false
psInvMovable = {'name', 'class', 'weight', 'gold', 'title_quiver', 'title_quick_weapons', 'title_quick_items', 'cap_ac', 'val_ac', 'det_ac', 'cap_thac0', 'val_thac0', 'det_thac0', 'cap_hp', 'val_hp', 'det_hp', 'cap_damage', 'val_damage', 'det_damage', 'ground_page', 'sort'}
local PARTS = {'psinv_', 'psinvh_', 'psinvr_'}
function psInvToggleEdit() psInvEdit = not psInvEdit end
local function psInvMove(key, x, y)
	for _, p in ipairs(PARTS) do Infinity_SetArea(p .. key, x, y, nil, nil) end
end
function psInvDrag(key, dx, dy)
	local x, y = Infinity_GetArea('psinv_' .. key)
	x, y = x + dx, y + dy
	psInvMove(key, x, y)
	Infinity_SetINIValue('Party Stash', 'pos_' .. key, x .. ',' .. y)
end
function psInvApplyPositions()
	for _, key in ipairs(psInvMovable) do
		local v = Infinity_GetINIString('Party Stash', 'pos_' .. key, '')
		local x, y = string.match(v or '', '(-?%d+),(-?%d+)')
		if x then psInvMove(key, tonumber(x), tonumber(y)) end
	end
end

function psInvYellow()
	return bit32.band(tonumber(fontcolors['Y'], 16), 0x00FFFFFF)
end

function psInvWeight()
	return game:GetSelectedCarried() .. ' / ' .. game:GetSelectedMaxEncumbrance() .. ' LB'
end

local function psInvField(f)
	local ok, v = pcall(f)
	if ok and v ~= nil then return v end
	return nil
end

function psInvStat(key)
	local c = characters[id]
	if key == 'AC' then return c.AC.current end
	if key == 'HP' then return c.HP.current .. '/' .. c.HP.max end
	if key == 'Damage' then return c.damage.min .. '-' .. c.damage.max end
	if key == 'THAC0' then
		return psInvField(function() return c.THAC0.current end) or psInvField(function() return c.thac0 end) or '-'
	end
	return ''
end

-- Detail lines: the engine's own breakdown when the inventory table provides it (AC/HP/THAC0/damage .details).
function psInvStatDetail(key)
	local c = characters[id]
	local f = {AC = function() return c.AC.details end, HP = function() return c.HP.details end,
		THAC0 = function() return c.THAC0.details end, Damage = function() return c.damage.details end}
	return tostring(psInvField(f[key]) or '')
end
