-- Inventaire PTEE, step 2a (John 2026-10-22): the stash core, ported from Party Stash BG (M_PSTASH.lua "Engine
-- functions" + "Store I/O"). The stash is a hidden bag store PSTASH.STO; items move with the engine's own store
-- functions (CInfGame::AddItemToStore and friends), called through tiny lua_CFunction stubs wired to one whitelisted
-- function each, prologue bytes checked first: on any other Torment.exe build the stash switches itself off.
-- Torment v3.2.2.0 addresses from the EEex-PTEE session (shared note inventaire-ptee-store-funcs.md).
-- Console test: PSC_Test() lists, PSC_Add(portrait, slot), PSC_Take(portrait, 'RESREF').

PSC = PSC or {}
local P = PSC
P.RES = 'PSTASH'

-- { address, first prologue bytes, args }
local FUNCS = {
	AddItemToStore = { 0x1402D0DD0, { 0x40, 0x55, 0x53, 0x56, 0x57, 0x41, 0x54, 0x41 }, 4 },
	-- 8 args in Torment (BG 9): BG's 8th argument is gone, Torment's 8th = BG's 9th flag (EEex-PTEE analysis):
	-- BG passes (..., 0xFFFF, 0, 1, 0), Torment (..., 0xFFFF, 0, 0). Passing 1 corrupted the heap.
	SwapItemPersonal = { 0x1402F81B0, { 0x40, 0x55, 0x53, 0x56, 0x57, 0x41, 0x54, 0x41 }, 8 },
	AddDisposableItem = { 0x1402D0DB0, { 0x48, 0x85, 0xD2, 0x74, 0x0C, 0x48, 0x81, 0xC1 }, 2 },
	DemandServerStore = { 0x1402D74D0, { 0x48, 0x89, 0x5C, 0x24, 0x10, 0x48, 0x89, 0x74 }, 3 },
	GetServerStore = { 0x1402DDE40, { 0x32, 0xC0, 0x0F, 0x1F, 0x40, 0x00, 0x66, 0x66 }, 2 },
	ReleaseServerStore = { 0x1402EB3E0, { 0x48, 0x83, 0xEC, 0x28, 0x4C, 0x8B, 0xD9, 0x32 }, 2 },
	TakeItemFromStore = { 0x1402F9A30, { 0x40, 0x55, 0x53, 0x56, 0x57, 0x41, 0x55, 0x41 }, 4 },
}
local PROBE = { 0x1402D1210, { 0x85, 0xD2, 0x0F, 0x84, 0x88, 0x00, 0x00, 0x00 } }  -- CInfGame::AddPartyGold

-- PTEE backpack = SLOT_MISC0..19 (SLOTS.IDS 15..34)
P.BACKPACK_FIRST, P.BACKPACK_LAST = 15, 34

local function bytesAt(addr, bytes)
	for i, b in ipairs(bytes) do
		if EEex_ReadU8(addr + i - 1) ~= b then return false end
	end
	return true
end

local function bytesLE(v, n)
	local out = {}
	for i = 1, n do out[i] = v % 256 v = math.floor(v / 256) end
	return table.unpack(out)
end

-- Same stub as Party Stash BG: reads nargs integers from the Lua stack, calls target (Win64), pushes the result.
local function buildStub(name, target, nargs)
	local toint, pushint = EEex_Label('Hardcoded_lua_tointegerx'), EEex_Label('Hardcoded_lua_pushinteger')
	local code = {}
	local function emit(...) for _, b in ipairs({ ... }) do code[#code + 1] = b end end
	local function slot(i) return 0x50 + 8 * (i - 1) end
	emit(0x53, 0x56, 0x57)
	emit(0x48, 0x81, 0xEC, bytesLE(0xA0, 4))
	emit(0x48, 0x89, 0xCB)
	for i = 1, nargs do
		emit(0x48, 0x89, 0xD9)
		emit(0xBA, bytesLE(i, 4))
		emit(0x45, 0x31, 0xC0)
		emit(0x48, 0xB8, bytesLE(toint, 8))
		emit(0xFF, 0xD0)
		emit(0x48, 0x89, 0x84, 0x24, bytesLE(slot(i), 4))
	end
	for k = 0, nargs - 5 do
		emit(0x48, 0x8B, 0x84, 0x24, bytesLE(slot(5 + k), 4))
		emit(0x48, 0x89, 0x44, 0x24, 0x20 + 8 * k)
	end
	local regs = { { 0x48, 0x8B, 0x8C }, { 0x48, 0x8B, 0x94 }, { 0x4C, 0x8B, 0x84 }, { 0x4C, 0x8B, 0x8C } }
	for i = 1, math.min(nargs, 4) do
		emit(regs[i][1], regs[i][2], regs[i][3], 0x24, bytesLE(slot(i), 4))
	end
	emit(0x48, 0xB8, bytesLE(target, 8))
	emit(0xFF, 0xD0)
	emit(0x48, 0x89, 0xD9)
	emit(0x48, 0x89, 0xC2)
	emit(0x48, 0xB8, bytesLE(pushint, 8))
	emit(0xFF, 0xD0)
	emit(0xB8, 1, 0, 0, 0)
	emit(0x48, 0x81, 0xC4, bytesLE(0xA0, 4))
	emit(0x5F, 0x5E, 0x5B, 0xC3)
	local addr = EEex_AllocNear(#code)
	EEex_DisableCodeProtection()
	for i, b in ipairs(code) do EEex_WriteU8(addr + i - 1, b) end
	EEex_EnableCodeProtection()
	EEex_ExposeToLua(addr, 'PSC_Eng_' .. name)
end

-- true when EEex runs and every function matches this Torment.exe build.
function PSC_Ready()
	if P.ready ~= nil then return P.ready end
	P.ready = false
	if type(EEex_ReadU8) ~= 'function' then P.why = 'EEex not running' return false end
	if not bytesAt(PROBE[1], PROBE[2]) then P.why = 'unknown Torment.exe build' return false end
	for name, f in pairs(FUNCS) do
		if not bytesAt(f[1], f[2]) then P.why = 'prologue mismatch: ' .. name return false end
	end
	for name, f in pairs(FUNCS) do
		if not _G['PSC_Eng_' .. name] then buildStub(name, f[1], f[3]) end
	end
	P.scratch = P.scratch or EEex_Malloc(64) -- [0] store resref, [16] CItem*, [24] int err, [32] item resref
	P.ready = true
	return true
end

local function resRef(res, offset)
	local buf = P.scratch + (offset or 0)
	res = string.upper(res)
	for i = 0, 7 do EEex_WriteU8(buf + i, i < #res and string.byte(res, i + 1) or 0) end
	return buf
end

-- Torment: CItemList m_items is a CItem** (EEex-PTEE note in B3AttackInfo.lua), not BG's array accessor.
local function itemPtrAt(sp, slot)
	return EEex_ReadPtr(EEex_UDToPtr(sp.m_equipment.m_items) + EEex_PtrSize * slot)
end
local function itemRes(ptr)
	local t = {}
	for i = 0, 7 do
		local b = EEex_ReadU8(ptr + 0x10 + i)  -- Torment CItem: vtable, pRes, then the resref at +0x10
		if b == 0 then break end
		t[#t + 1] = string.char(b)
	end
	return string.upper(table.concat(t))
end

local function gamePtr() return EEex_UDToPtr(EEex_EngineGlobal_CBaldurChitin.m_pObjectGame) end

-- Stash contents: { {res, count, uses, identified}, ... } in store order.
function PSC_List()
	if not PSC_Ready() then return {} end
	local game, out = gamePtr(), {}
	PSC_Eng_DemandServerStore(game, resRef(P.RES), 0)
	local ok, err = pcall(function()
		local storePtr = PSC_Eng_GetServerStore(game, resRef(P.RES))
		if storePtr == 0 then return end
		EEex_Utility_IterateCPtrList(EEex_PtrToUD(storePtr, 'CStore').m_lInventory, function(data)
			local fi = type(data) == 'number' and EEex_PtrToUD(data, 'CStoreFileItem') or data
			local ptr = type(data) == 'number' and data or EEex_UDToPtr(data)
			out[#out + 1] = { res = string.upper(fi.m_itemId:get()), count = fi.m_nInStock,
				uses = fi.m_usageCount:get(0), identified = bit32.band(EEex_ReadU32(ptr + 0x10), 1) ~= 0 }
		end)
	end)
	PSC_Eng_ReleaseServerStore(game, resRef(P.RES))
	if not ok then P.lastError = tostring(err) end
	return out
end

-- Moves the item in inventory slot `slot` of `portrait` into the stash.
function PSC_Add(portrait, slot)
	if not PSC_Ready() then return false, P.why end
	local ok, res, why = pcall(function()
		local sp = EEex_Sprite_GetInPortrait(portrait)
		if not sp then return false, 'no such portrait' end
		local itemPtr = itemPtrAt(sp, slot)
		if itemPtr == 0 then return false, 'empty slot' end
		local game, buf = gamePtr(), P.scratch
		EEex_Write32(buf + 24, -1)
		if PSC_Eng_AddItemToStore(game, resRef(P.RES), itemPtr, buf + 24) % 256 == 0 then
			return false, string.format('refused (0x%x)', EEex_ReadU32(buf + 24))
		end
		EEex_Write64(buf + 16, 0)
		PSC_Eng_SwapItemPersonal(game, portrait, buf + 16, slot, buf + 24, 0xFFFF, 0, 0)
		local out = EEex_ReadU64(buf + 16)
		if out ~= itemPtr then return false, 'in the stash but the slot kept it (duplicate!)' end
		PSC_Eng_AddDisposableItem(game, out)
		return true
	end)
	if not ok then return false, tostring(res) end
	return res, why
end

local function freeSlot(sp)
	for i = P.BACKPACK_FIRST, P.BACKPACK_LAST do if itemPtrAt(sp, i) == 0 then return i end end
end

-- Takes `itemRes` out of the stash into `portrait`'s backpack (a whole pile for stackable items).
function PSC_Take(portrait, itemRes)
	if not PSC_Ready() then return nil, P.why end
	local sp = EEex_Sprite_GetInPortrait(portrait)
	if not sp then return nil, 'no such portrait' end
	if not freeSlot(sp) then return nil, 'backpack full' end
	itemRes = string.upper(itemRes)
	local entry
	for _, e in ipairs(PSC_List()) do
		if e.res == itemRes then entry = e break end
	end
	if not entry then return nil, 'not in the stash' end
	local taken = PSC_Eng_TakeItemFromStore(gamePtr(), resRef(P.RES), resRef(itemRes, 32), 1) % 65536
	if taken == 0 then return nil, 'the stash kept it' end
	EEex_Action_ExecuteResponseStringOnAIBaseInstantly(
		string.format('CreateItem("%s",%d,0,0)', itemRes, math.max(0, entry.uses)), sp)
	return true
end

-- Console helpers (results in EEex.log): what each slot holds, add, take.
function PSC_Slots(portrait)
	local sp = EEex_Sprite_GetInPortrait(portrait or 0)
	if not sp then print('PSC no portrait') return end
	for i = 0, 38 do
		local p = itemPtrAt(sp, i)
		if p ~= 0 then print('PSC slot ' .. i .. ' ' .. itemRes(p)) end
	end
end

function PSC_AddP(portrait, slot)
	local ok, why = PSC_Add(portrait, slot)
	print('PSC add ' .. tostring(ok) .. ' ' .. tostring(why))
end

function PSC_TakeP(portrait, res)
	local ok, why = PSC_Take(portrait, res)
	print('PSC take ' .. tostring(ok) .. ' ' .. tostring(why))
end

-- Auto-test (tools/test_stash.ps1 sets [Party Stash] Autotest=1): runs once when the inventory opens,
-- stores backpack slot 16 of portrait 0, lists the stash, takes it back; everything printed to EEex.log.
function PSC_AutoTest()
	if Infinity_GetINIValue('Party Stash', 'Autotest', 0) ~= 1 then return end
	Infinity_SetINIValue('Party Stash', 'Autotest', 0)
	local ok, err = pcall(function()
		print('PSC autotest begin')
		PSC_Test()
		PSC_Slots(0)
		local sp = EEex_Sprite_GetInPortrait(0)
		local p = sp and itemPtrAt(sp, 16) or 0
		local res = p ~= 0 and itemRes(p) or nil
		print('PSC slot16 = ' .. tostring(res))
		PSC_AddP(0, 16)
		PSC_Test()
		PSC_Slots(0)
		if res then PSC_TakeP(0, res) end
		PSC_Test()
		PSC_Slots(0)
		print('PSC autotest end')
	end)
	if not ok then print('PSC autotest error ' .. tostring(err)) end
end

-- Console helper: prints readiness and the stash contents in the message log.
function PSC_Test()
	local ok = PSC_Ready()
	local lines = { 'PSC ready: ' .. tostring(ok) .. (P.why and (' (' .. P.why .. ')') or '') }
	for _, e in ipairs(PSC_List()) do
		lines[#lines + 1] = string.format('%s x%d uses %d %s', e.res, e.count, e.uses, e.identified and 'id' or '')
	end
	if P.lastError then lines[#lines + 1] = 'error: ' .. P.lastError end
	local text = table.concat(lines, '\n')
	print(text)  -- EEex.log (LPRINT)
	return text
end
