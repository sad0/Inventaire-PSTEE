-- Debug: load the grid Lua, store backpack slot 18, refresh, print the view, take it back.
dofile('E:/Enhanced Edition/Inventaire-PTEE/mod/InventairePTEE/lua/M_PSUI.lua')
print('PSC portrait ' .. tostring(PSUI_Portrait()))
print('PSC add18 ' .. tostring(PSC_Add(PSUI_Portrait(), 18)))
PSUI_Refresh()
for i = 1, 5 do
	if PSUI_Has(i) then print('PSC view ' .. i .. ' ' .. tostring(PSUI_Icon(i)) .. ' ' .. tostring(PSUI_Name(i)) .. ' ' .. PSUI_Count(i)) end
end
print('PSC weight ' .. tostring(PSUI_Weight()))
PSUI_Take(1)
PSUI_Refresh()
print('PSC view after take ' .. tostring(PSUI_Has(1)))
