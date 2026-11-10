-- Inventaire PSTEE, step 2a (John 2026-10-22): the stash core, ported from Party Stash BG (M_PSTASH.lua "Engine
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
FUNCS.AddPartyGold = { PROBE[1], PROBE[2], 2 }

-- PSTEE backpack in the engine's item array (measured in game, SLOTS.IDS does not match): 18..33 then 44..47.
P.BACKPACK = {}
for i = 18, 33 do P.BACKPACK[#P.BACKPACK + 1] = i end
for i = 44, 46 do P.BACKPACK[#P.BACKPACK + 1] = i end
-- The last backpack slot holds the stash bag (like Party Stash BG): the engine treats it as any carried bag, so quests
-- see and take the stash's items, and an item dropped on it goes into the stash natively.
P.BAG_SLOT = 47

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

local function game_gold() return game:GetPartyGold() end

local function gamePtr() return EEex_UDToPtr(EEex_EngineGlobal_CBaldurChitin.m_pObjectGame) end

-- Contents of the stash (or of bag store `store`): { {res, count, uses, identified}, ... } in store order.
function PSC_List(store)
	if not PSC_Ready() then return {} end
	store = store or P.RES
	local game, out = gamePtr(), {}
	PSC_Eng_DemandServerStore(game, resRef(store), 0)
	local ok, err = pcall(function()
		local storePtr = PSC_Eng_GetServerStore(game, resRef(store))
		if storePtr == 0 then return end
		EEex_Utility_IterateCPtrList(EEex_PtrToUD(storePtr, 'CStore').m_lInventory, function(data)
			local fi = type(data) == 'number' and EEex_PtrToUD(data, 'CStoreFileItem') or data
			local ptr = type(data) == 'number' and data or EEex_UDToPtr(data)
			out[#out + 1] = { res = string.upper(fi.m_itemId:get()), count = fi.m_nInStock,
				uses = fi.m_usageCount:get(0), identified = bit32.band(EEex_ReadU32(ptr + 0x10), 1) ~= 0 }
		end)
	end)
	PSC_Eng_ReleaseServerStore(game, resRef(store))
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
		local gold = game_gold()
		if PSC_Eng_AddItemToStore(game, resRef(P.RES), itemPtr, buf + 24) % 256 == 0 then
			return false, string.format('refused (0x%x)', EEex_ReadU32(buf + 24))
		end
		-- AddItemToStore pays the item's sell value at the store's buy rate. The shipped store buys at 0 %, but a
		-- stash saved by v0.3 kept its 80 % rate in the save: never let the stash pay.
		local paid = game_gold() - gold
		if paid ~= 0 then PSC_Eng_AddPartyGold(game, -paid) end
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

-- Every party member carries one stash bag, in the last backpack slot.
local function setSlot(sp, i, ptr)
	EEex_Write64(EEex_UDToPtr(sp.m_equipment.m_items) + EEex_PtrSize * i, ptr)
end

local function isBag(a) return a ~= 0 and itemRes(a) == P.RES end

local function placeBag(sp)
	local at
	for i = 0, P.BAG_SLOT do
		local a = itemPtrAt(sp, i)
		if isBag(a) and i ~= P.BAG_SLOT then
			if at or isBag(itemPtrAt(sp, P.BAG_SLOT)) then  -- an extra copy
				setSlot(sp, i, 0)
				PSC_Eng_AddDisposableItem(gamePtr(), a)
			else
				at = i
			end
		end
	end
	local last = itemPtrAt(sp, P.BAG_SLOT)
	if isBag(last) then return false end
	if at then  -- the bag takes the last slot, whatever sat there takes its place
		setSlot(sp, P.BAG_SLOT, itemPtrAt(sp, at))
		setSlot(sp, at, last)
		return true
	end
	if last ~= 0 then
		for _, i in ipairs(P.BACKPACK) do
			if itemPtrAt(sp, i) == 0 then
				setSlot(sp, i, last)
				setSlot(sp, P.BAG_SLOT, 0)
				return true
			end
		end
		return false  -- backpack full: the bag comes when a slot frees up
	end
	if sp.m_pArea ~= nil then
		-- the engine puts a new item in the first free slot: it moves to the last slot next tick
		EEex_Action_ExecuteResponseStringOnAIBaseInstantly('CreateItem("' .. P.RES .. '",0,0,0)', sp)
	end
	return false
end

P.bagAt = 0
local function bagTick()
	local eng = e:GetActiveEngine()
	if eng ~= worldScreen and eng ~= inventoryScreen then return end
	if EEex_EngineGlobal_CBaldurChitin.m_pEngineInventory.m_pTempItem ~= nil then return end  -- in hand: wait for the drop
	local now = Infinity_GetClockTicks()
	if now - P.bagAt < 300 then return end
	P.bagAt = now
	local moved = false
	for p = 0, 5 do
		local sp = EEex_Sprite_GetInPortrait(p)
		if sp and placeBag(sp) then moved = true end
	end
	if next(P.pour) and P.pourLeftovers then
		P.pourLeftovers()
		moved = true
	end
	if moved and Infinity_IsMenuOnStack('INVENTORY') then pcall(Infinity_ActivateInventory) end
end

function PSC_BagTick()
	local ok, why = pcall(bagTick)
	if not ok then print('PSC bag ' .. tostring(why)) end
	return false
end

-- PSC_TICK runs PSC_BagTick every frame on the world screen, so joining members get their bag too. Same pushes as Party
-- Stash BG: never pushed outside the world screen (a pushed menu crashed character creation there).
local function pushTick()
	if Infinity_IsMenuOnStack('PSC_TICK') then return end
	if worldScreen == nil or e:GetActiveEngine() ~= worldScreen then return end
	Infinity_PushMenu('PSC_TICK')
end

if not P.pushWrapped then
	P.pushWrapped = true
	local push = Infinity_PushMenu
	Infinity_PushMenu = function(...)
		local m = ...
		local r = table.pack(push(...))
		if m ~= 'PSC_TICK' then pcall(pushTick) end
		return table.unpack(r, 1, r.n)
	end
	EEex_Sprite_AddLoadedListener(function() pcall(pushTick) end)
	EEex_GameState_AddInitializedListener(pushTick)
	EEex_Menu_AddAfterMainFileReloadedListener(pushTick)
end

-- A drop into the bag pays like a sale (1 gold at a 0 % rate): the stash never pays.
function PSC_UndoPay(goldBefore)
	local paid = game:GetPartyGold() - goldBefore
	if paid > 0 then PSC_Eng_AddPartyGold(gamePtr(), -paid) end
end

-- Resref of a CItem given as userdata.
function PSC_ItemRes(item) return itemRes(EEex_UDToPtr(item)) end

-- Resref of the item in a slot, nil when empty.
function PSC_SlotRes(portrait, slot)
	local sp = EEex_Sprite_GetInPortrait(portrait)
	if not sp then return nil end
	local a = itemPtrAt(sp, slot)
	return a ~= 0 and itemRes(a) or nil
end

local function freeSlot(sp)
	for _, i in ipairs(P.BACKPACK) do if itemPtrAt(sp, i) == 0 then return i end end
end

-- Stack size of an item (ITM +0x38).
local function stackOf(res)
	local ok, v = pcall(function() return EEex_ReadU16(EEex_UDToPtr(EEex_Resource_Demand(res, 'ITM')) + 0x38) end)
	return ok and math.max(1, v) or 1
end

-- Takes `itemRes` out of the stash into `portrait`'s backpack: a whole pile for stackable items (the store keeps
-- stacks unit by unit), up to the item's max stack; one piece for the others (charges kept).
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
	local stack = stackOf(itemRes)
	local want = stack > 1 and math.min(math.max(1, entry.count), stack) or 1
	local taken = PSC_Eng_TakeItemFromStore(gamePtr(), resRef(P.RES), resRef(itemRes, 32), want) % 65536
	if taken == 0 then return nil, 'the stash kept it' end
	local uses = stack > 1 and taken * math.max(1, entry.uses) or math.max(0, entry.uses)
	-- Queued, not instant: older EEex-PTEE builds freed the instant action with the wrong destructor (heap
	-- corruption). The item shows up on the next AI tick.
	EEex_Action_QueueResponseStringOnAIBase(string.format('CreateItem("%s",%d,0,0)', itemRes, uses), sp)
	if entry.identified then P.pendingId[#P.pendingId + 1] = { portrait = portrait, res = itemRes } end
	return true
end

-----------------
-- Bags        --
-----------------

-- Collected bags (same as Party Stash BG): a container bag put away with Store all is consumed, its contents go to
-- the stash, and it is kept as a count (global PSTB_<res>) shown in the stash, never taken back. PST has no bag of
-- its own: they come from mods (Bags of Torment...). Each collected kind is recorded in the save, string globals
-- PSTBX_1..PSTBX_<n> (count PSTBX_N) plus two integer globals PSTBX_<n>A / PSTBX_<n>B (4 letters each), the BG
-- format.
local function bagCount(res) return EEex_GameState_GetGlobalInt('PSTB_' .. res) end
local function setBagCount(res, n) EEex_GameState_SetGlobalInt('PSTB_' .. res, math.max(0, n)) end

local function packRes(res, from)
	local v = 0
	for k = from + 3, from, -1 do v = v * 256 + (string.byte(res, k) or 0) end
	return v
end
local function unpackRes(v)
	local out = {}
	for _ = 1, 4 do
		local c = v % 256
		if c > 0 then out[#out + 1] = string.char(c) end
		v = math.floor(v / 256)
	end
	return table.concat(out)
end

-- Kinds of bags collected in this save.
local function bagList()
	local out = {}
	for i = 1, EEex_GameState_GetGlobalInt('PSTBX_N') do
		local r = string.upper(EEex_GameState_GetGlobalString('PSTBX_' .. i) or '')
		if r == '' then
			r = unpackRes(EEex_GameState_GetGlobalInt('PSTBX_' .. i .. 'A')) .. unpackRes(EEex_GameState_GetGlobalInt('PSTBX_' .. i .. 'B'))
		end
		if r ~= '' then out[#out + 1] = r end
	end
	return out
end
local function recordBag(res)
	for _, r in ipairs(bagList()) do if r == res then return end end
	local n = EEex_GameState_GetGlobalInt('PSTBX_N') + 1
	EEex_GameState_SetGlobalString('PSTBX_' .. n, res)
	EEex_GameState_SetGlobalInt('PSTBX_' .. n .. 'A', packRes(res, 1))
	EEex_GameState_SetGlobalInt('PSTBX_' .. n .. 'B', packRes(res, 5))
	EEex_GameState_SetGlobalInt('PSTBX_N', n)
end

-- { {res, count}, ... } of the collected bags.
function PSC_Bags()
	local out = {}
	if not PSC_Ready() then return out end
	for _, r in ipairs(bagList()) do
		local n = bagCount(r)
		if n > 0 then out[#out + 1] = { res = r, count = n } end
	end
	return out
end

-- A container bag: an item of type 36 with its own store (a type-36 item without one holds nothing).
P.bagStore = P.bagStore or {}
function PSC_IsBag(res)
	if not res or res == P.RES then return false end
	if P.bagStore[res] == nil then
		local ok, isBag = pcall(function()
			local h = EEex_Resource_Demand(res, 'ITM')
			if not h or EEex_ReadU16(EEex_UDToPtr(h) + 0x1C) ~= 36 then return false end
			return EEex_Resource_Demand(res, 'STO') ~= nil
		end)
		P.bagStore[res] = ok and isBag == true
	end
	return P.bagStore[res]
end

-- Pours bag store `bag` into the stash through `portrait`'s backpack (one free slot is enough). Instant CreateItem, as
-- for the stash bag (safe on pstee2). Returns true once the bag store is empty; what is left waits for a free slot
-- (P.pour, retried by the tick).
P.pour = P.pour or {}
function PSC_PourBag(portrait, bag)
	local sp = EEex_Sprite_GetInPortrait(portrait)
	if not sp then return false end
	for _ = 1, 1000 do
		local e = PSC_List(bag)[1]
		if not e then P.pour[bag] = nil return true end
		if not freeSlot(sp) then break end
		local before = {}
		for _, i in ipairs(P.BACKPACK) do before[i] = itemPtrAt(sp, i) end
		local stack = stackOf(e.res)
		local want = stack > 1 and math.min(math.max(1, e.count), stack) or 1
		local taken = PSC_Eng_TakeItemFromStore(gamePtr(), resRef(bag), resRef(e.res, 32), want) % 65536
		if taken == 0 then break end
		local uses = stack > 1 and taken * math.max(1, e.uses) or math.max(0, e.uses)
		EEex_Action_ExecuteResponseStringOnAIBaseInstantly(string.format('CreateItem("%s",%d,0,0)', e.res, uses), sp)
		-- the new item: a slot that changed (none = merged into a pile already in the backpack, it stays there)
		for _, i in ipairs(P.BACKPACK) do
			local a = itemPtrAt(sp, i)
			if a ~= 0 and a ~= before[i] and itemRes(a) == e.res then
				if e.identified then EEex_WriteU32(a + 0x24, bit32.bor(EEex_ReadU32(a + 0x24), 1)) end
				PSC_Add(portrait, i)
				break
			end
		end
	end
	P.pour[bag] = true
	return false
end

-- Collects the bag in `slot` of `portrait`: the item goes, the count grows, its contents go to the stash.
function PSC_CollectBag(portrait, slot)
	if not PSC_Ready() then return false, P.why end
	local sp = EEex_Sprite_GetInPortrait(portrait)
	if not sp then return false, 'no such portrait' end
	local a = itemPtrAt(sp, slot)
	if a == 0 then return false, 'empty slot' end
	local res = itemRes(a)
	if not PSC_IsBag(res) then return false, 'not a container bag' end
	setSlot(sp, slot, 0)
	PSC_Eng_AddDisposableItem(gamePtr(), a)
	recordBag(res)
	setBagCount(res, bagCount(res) + 1)
	PSC_PourBag(portrait, res)
	return true
end

-- Contents left in a collected bag (backpack was full): poured as soon as someone has room.
local function pourLeftovers()
	for res in pairs(P.pour) do
		if bagCount(res) > 0 then
			for p = 0, 5 do
				local sp = EEex_Sprite_GetInPortrait(p)
				if sp and freeSlot(sp) then PSC_PourBag(p, res) break end
			end
		else
			P.pour[res] = nil
		end
	end
end
P.pourLeftovers = pourLeftovers

-- CreateItem makes the item unidentified when its header says so: restore the state it had in the stash once the
-- queued action has run (CItem flags at +0x24, bit 0 = identified). Called every frame by the inventory page.
P.pendingId = P.pendingId or {}
function PSC_RefreshPage() P.refreshIn = 14 end
function PSC_Tick()
	PSC_BagTick()
	if P.refreshIn then
		-- the engine rebuilds the page's item tables only on this call; twice, for queued CreateItem actions
		P.refreshIn = P.refreshIn - 1
		if P.refreshIn == 12 or P.refreshIn == 0 then pcall(Infinity_ActivateInventory) end
		if P.refreshIn <= 0 then P.refreshIn = nil end
	end
	if #P.pendingId == 0 then return false end
	local keep = {}
	for _, want in ipairs(P.pendingId) do
		local sp = EEex_Sprite_GetInPortrait(want.portrait)
		local done = sp == nil
		if sp then
			for _, i in ipairs(P.BACKPACK) do
				local a = itemPtrAt(sp, i)
				if a ~= 0 and itemRes(a) == want.res then
					local f = EEex_ReadU32(a + 0x24)
					if bit32.band(f, 1) == 0 then EEex_WriteU32(a + 0x24, bit32.bor(f, 1)) end
					done = true
					break
				end
			end
		end
		if not done then
			want.tries = (want.tries or 0) + 1
			if want.tries < 300 then keep[#keep + 1] = want end
		end
	end
	P.pendingId = keep
	return false
end

-- Console helpers (results in EEex.log): what each slot holds, add, take.
function PSC_Slots(portrait)
	local sp = EEex_Sprite_GetInPortrait(portrait or 0)
	if not sp then print('PSC no portrait') return end
	for i = 0, 47 do
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
