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

function psInvWhite()
	return bit32.band(tonumber(fontcolors['B'], 16), 0x00FFFFFF)
end

-- Short forms like Party Stash BG (John 2026-10-22): attribute and stat names abbreviated, quotes cut.
psInvAbbr = {
	{'Points de vie', 'PV'}, {'Hit Points', 'HP'}, {"Classe d'armure", 'CA'}, {'Armor Class', 'AC'},
	{'Armour Class', 'AC'}, {'Force', 'For'}, {'Strength', 'Str'}, {'Dext\195\169rit\195\169', 'Dex'},
	{'Dexterity', 'Dex'}, {'Constitution', 'Con'}, {'Intelligence', 'Int'}, {'Sagesse', 'Sag'}, {'Wisdom', 'Wis'},
	{'Charisme', 'Cha'}, {'Charisma', 'Cha'}, {'Comp\195\169tence', 'Comp.'}, {'Proficiency', 'Prof.'},
	{'Arme', 'Arme'}, {'Weapon', 'Weapon'},
}
-- the block's own stat name is dropped from its lines ("Adahn : +10" in the HP block, not "PV: +10")
psInvOwn = {AC = {'CA', 'AC'}, HP = {'PV', 'HP'}, THAC0 = {'TAC0', 'THAC0'}, Damage = {}}

local function psInvTrim(t)
	return (string.gsub(string.gsub(t, '^%s+', ''), '%s+$', ''))
end

function psInvShorten(key, text)
	local out = {}
	text = string.gsub(text, '"[^"]*"', '')            -- quoted dialogue lines
	text = string.gsub(text, '\226\128\156[^\226]*\226\128\157', '')  -- curly quotes
	for line in string.gmatch(text, '[^\n]+') do
		for _, a in ipairs(psInvAbbr) do line = string.gsub(line, a[1], a[2]) end
		for _, own in ipairs(psInvOwn[key] or {}) do line = string.gsub(line, '%s' .. own .. '%s*:', ' ') end
		line = string.gsub(line, '%s*:%s*:', ' :')
		line = string.gsub(line, ':%s+([%+%-]?%d)', ': %1')
		line = string.gsub(line, '%s%s+', ' ')
		line = psInvTrim(line)
		if line ~= '' and line ~= ':' then out[#out + 1] = line end
	end
	return table.concat(out, '\n')
end

-- Detail lines: the engine's own breakdown (AC/HP/THAC0/damage .details), shortened.
function psInvStatDetail(key)
	local c = characters[id]
	local f = {AC = function() return c.AC.details end, HP = function() return c.HP.details end,
		THAC0 = function() return c.THAC0.details end, Damage = function() return c.damage.details end}
	local text = psInvShorten(key, tostring(psInvField(f[key]) or ''))
	if key == 'Damage' then
		local apr = psInvAPR()
		if apr then
			text = text .. (text ~= '' and '\n' or '') .. psInvAPRLabel() .. string.format('%g', apr)
		end
	end
	return text
end

-- Attacks per round of the shown character (John 2026-10-22), like Party Stash BG: EEex stat 8 NUMBEROFATTACKS,
-- engine code 1-5 attacks, 6 = 1.5, 7 = 2.5, 8 = 3.5, 9 = 4.5. Nothing shown without EEex.
function psInvAPR()
	local ok, v = pcall(function()
		for p = 0, 5 do
			local sp = EEex_Sprite_GetInPortrait(p)
			if sp and sp.m_id == id then return EEex_Sprite_GetStat(sp, 8) end
		end
	end)
	if not ok or type(v) ~= 'number' then return nil end
	if v >= 6 then return v - 4.5 end
	return v
end

function psInvAPRLabel()
	local lang = string.lower(Infinity_GetINIString('Language', 'Text', '') or '')
	if string.sub(lang, 1, 2) == 'fr' then return 'Attaques/round : ' end
	return 'Attacks/round: '
end
