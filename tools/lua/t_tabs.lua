-- For each tab and sort mode: what the grid shows.
for t = 1, 8 do
	psInvSelectTab(t)
	local n = {}
	for i = 1, 60 do if PSUI_Has(i) then n[#n + 1] = PSUI_Name(i) end end
	PB('tab ' .. t .. ' [' .. psInvTabs[t] .. '] ' .. #n .. ': ' .. table.concat(n, ' | '))
end
psInvSelectTab(1)
for s = 1, 5 do
	local n = {}
	for i = 1, 60 do if PSUI_Has(i) then n[#n + 1] = PSUI_Name(i) end end
	PB(PSUI_SortText() .. ': ' .. table.concat(n, ' | '))
	PSUI_NextSort()
end
PB('page', PSUI_PageText(), 'weight', PSUI_Weight())
