-- Inventaire PTEE (Party Stash for Planescape: Torment EE), step 1: redesigned inventory page.
-- Background art variant: 'G' (generated art) or 'F' (PTEE pieces), saved in Baldur.lua/ini.
psInvVariant = Infinity_GetINIString('Party Stash', 'Inventory Art', 'G')

function psInvBackground()
	if psInvVariant == 'F' then return 'PSIVBGF' end
	return 'PSIVBGG'
end

function psInvToggleVariant()
	if psInvVariant == 'F' then psInvVariant = 'G' else psInvVariant = 'F' end
	Infinity_SetINIValue('Party Stash', 'Inventory Art', psInvVariant)
	Infinity_SetBackground('BACKGROUND_INVENTORY')
end

function psInvVariantLabel()
	return 'Art: ' .. psInvVariant
end

psInvTexts = {
	title = 'Inventory', Quiver = 'Quiver', ['Quick Weapons'] = 'Quick Weapons', ['Quick Items'] = 'Quick Items',
	AC = 'AC', THAC0 = 'THAC0', HP = 'HP', Damage = 'Damage', Sort = 'Sort: Auto', ['Store all'] = 'Store all',
	Swap = 'Swap the inventory art (F: game pieces, G: generated art)',
}
psInvTabs = {'All', 'Weap.', 'Tatt.', 'Jewel', 'Eyes', 'Charm', 'Quest', 'Misc'}

function psInvText(key) return psInvTexts[key] or key end
function psInvTab(i) return psInvTabs[i] end

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
