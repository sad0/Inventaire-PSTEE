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
	if key == 'HP' then return psInvHPDetail(c) end
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

-- HP block (John 2026-10-22): level-up hit die, Constitution bonus per level, "Other" = flat sum of every other
-- bonus the engine lists. PTEE has no HPCLASS/HPCONBON tables: AD&D 2e rules as in PST, hard-coded.
-- Fighter 1d10 up to level 9 then +3; thief 1d6 up to 10 then +2; mage 1d4 up to 10 then +1.
local PSINV_DIE = {[2] = {10, 9, 3}, [4] = {6, 10, 2}, [1] = {4, 10, 1}}
local function psInvSprite()
	local ok, sp = pcall(function()
		for p = 0, 5 do
			local s = EEex_Sprite_GetInPortrait(p)
			if s and s.m_id == id then return s end
		end
	end)
	if ok then return sp end
	return nil
end
local function psInvClassFromName(name)
	name = string.lower(tostring(name or ''))
	if string.find(name, 'guerr', 1, true) or string.find(name, 'fight', 1, true) then return 2 end
	if string.find(name, 'voleur', 1, true) or string.find(name, 'thief', 1, true) then return 4 end
	if string.find(name, 'mage', 1, true) then return 1 end
	return nil
end
-- Constitution HP bonus per level (AD&D 2e): +3 and above only for warriors.
local function psInvConBonus(con, warrior)
	local b = 0
	if con >= 15 then b = 1 end
	if con >= 16 then b = 2 end
	if con >= 17 then b = 3 end
	if con >= 18 then b = 4 end
	if con >= 19 then b = 5 end
	if con >= 21 then b = 6 end
	if con >= 24 then b = 7 end
	if not warrior and b > 2 then b = 2 end
	return b
end
local function psInvFr()
	local lang = string.lower(Infinity_GetINIString('Language', 'Text', '') or '')
	return string.sub(lang, 1, 2) == 'fr'
end

function psInvHPDetail(c)
	local sp = psInvSprite()
	local cls, level, con
	if sp then
		cls = psInvField(function() return sp.m_typeAI.m_Class end)
		level = psInvField(function() return EEex_Sprite_GetStat(sp, 34) end)
		con = psInvField(function() return EEex_Sprite_GetStat(sp, 41) end)
	end
	cls = PSINV_DIE[cls or 0] and cls or psInvClassFromName(c.class)
	local fr = psInvFr()
	local lines = {}
	local rule = PSINV_DIE[cls or 0]
	if rule then
		local die = '1d' .. rule[1]
		if level and level + 1 > rule[2] then die = '+' .. rule[3] end
		lines[#lines + 1] = (fr and 'Classe : ' or 'Class: ') .. die
	end
	if con then
		lines[#lines + 1] = (fr and 'Con : ' or 'Con: ') .. string.format('%+d', psInvConBonus(con, cls == 2))
	end
	-- every other bonus the engine lists (items, tattoos, dialogue choices...), constitution lines excluded
	local other, any = 0, false
	for line in string.gmatch(tostring(psInvField(function() return c.HP.details end) or ''), '[^\n]+') do
		local low = string.lower(line)
		if not string.find(low, 'constit', 1, true) then
			local n = string.match(line, '([%+%-]%d+)%s*$')
			if n then other, any = other + tonumber(n), true end
		end
	end
	if any then lines[#lines + 1] = (fr and 'Autre : ' or 'Other: ') .. string.format('%+d', other) end
	return table.concat(lines, '\n')
end

function psInvAPRLabel()
	local lang = string.lower(Infinity_GetINIString('Language', 'Text', '') or '')
	if string.sub(lang, 1, 2) == 'fr' then return 'Attaques/round : ' end
	return 'Attacks/round: '
end
