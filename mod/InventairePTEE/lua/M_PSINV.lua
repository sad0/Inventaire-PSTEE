-- Inventaire PTEE (Party Stash for Planescape: Torment EE), step 1: redesigned inventory page (art J).
psInvTexts = {
	Quiver = 'Quiver', ['Quick Weapons'] = 'Quick Weapons', ['Quick Items'] = 'Quick Items',
	AC = 'AC', THAC0 = 'THAC0', HP = 'HP', Damage = 'Damage', Sort = 'Sort: Auto', ['Store all'] = 'Store all',
	Help = 'Help',
}
psInvTabs = {'All', 'Weap.', 'Tatt.', 'Jewel', 'Eyes', 'Charm', 'Quest', 'Misc'}
psInvActiveTab = 1

function psInvBackground() return 'PSIVBGJ' end
function psInvText(key) return psInvTexts[key] or key end
function psInvTab(i) return psInvTabs[i] end
function psInvSelectTab(i) psInvActiveTab = i end
-- selected tab shows the "selected" frame (2)
function psInvTabFrame(i) if psInvActiveTab == i then return 2 end return 0 end

-- gauges and glass tubes: slow pulse between the normal (0) and lit (2) frames, each piece with its own phase
psInvPhase = {gauge_top = 0, gauge_left = 7, gauge_right = 13, tube_left = 3, tube_right = 9, tube_mid = 5}
function psInvPulse(name)
	local t = math.floor(Infinity_GetClockTicks() / 400) + (psInvPhase[name] or 0)
	if t % 6 == 0 then return 2 end
	return 0
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

-- detail lines come with EEex (step 2)
function psInvStatDetail(key)
	return ''
end
