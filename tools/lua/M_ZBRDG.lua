-- Test scaffolding, disposable game copy only (never shipped). The engine's Lua has no io/os: every ~0.3 s tries
-- dofile('bridge/cmd_<n>.lua'); when it exists it runs once and n advances. Results: PB(...) -> EEex.log, prefix "PB ".
PB_DIR = 'E:/Enhanced Edition/Environnement de test/Compat/PSTEE stash test/bridge/'
PB_N = 1
local last = 0
function PB(...)
	local t = {}
	for i = 1, select('#', ...) do t[#t + 1] = tostring((select(i, ...))) end
	print('PB ' .. table.concat(t, ' '))
end
function PB_Poll()
	local now = Infinity_GetClockTicks()
	if now - last < 300 then return false end
	last = now
	local fn = loadfile(PB_DIR .. 'cmd_' .. PB_N .. '.lua')
	if not fn then return false end
	local n = PB_N
	PB_N = PB_N + 1
	local ok, e = xpcall(fn, debug.traceback)
	if not ok then PB('RUN ERROR', e) end
	PB('--done', n)
	return false
end
