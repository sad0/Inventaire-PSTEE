"""Minimal minidump reader: exception, faulting module+offset, registers, Torment/loader return addresses on the stack.

Usage: python tools/dmp.py <file.dmp>
"""
import struct
import sys


def main():
    d = open(sys.argv[1], 'rb').read()
    n, rva = struct.unpack_from('<II', d, 8)
    streams = {}
    for i in range(n):
        t, size, r = struct.unpack_from('<III', d, rva + i * 12)
        streams[t] = (r, size)
    r, _ = streams[6]
    code, flags, rec, addr, np_ = struct.unpack_from('<IIQQI', d, r + 8)
    params = struct.unpack_from('<15Q', d, r + 8 + 32)
    print('code %08x addr %x params %s' % (code, addr, [hex(p) for p in params[:np_]]))
    mods = []
    mr, _ = streams[4]
    cnt = struct.unpack_from('<I', d, mr)[0]
    for i in range(cnt):
        base, size = struct.unpack_from('<QI', d, mr + 4 + i * 108)
        namerva = struct.unpack_from('<I', d, mr + 4 + i * 108 + 20)[0]
        ln = struct.unpack_from('<I', d, namerva)[0]
        name = d[namerva + 4:namerva + 4 + ln].decode('utf-16-le')
        mods.append((base, size, name.replace('/', '\\').split('\\')[-1]))

    def where(a):
        for b, s, nm in mods:
            if b <= a < b + s:
                return '%s+%x' % (nm, a - b)
        return None

    print('fault at', where(addr))
    ctx_size, ctx_rva = struct.unpack_from('<II', d, r + 8 + 152)
    ctx = d[ctx_rva:ctx_rva + ctx_size]
    regs = ['rax', 'rcx', 'rdx', 'rbx', 'rsp', 'rbp', 'rsi', 'rdi', 'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15']
    vals = struct.unpack_from('<16Q', ctx, 0x78)
    for nm, v in zip(regs, vals):
        print(nm, hex(v), where(v) or '')
    rip = struct.unpack_from('<Q', ctx, 0xF8)[0]
    rsp = vals[4]
    print('rip', hex(rip), where(rip))
    ranges = []
    if 5 in streams:
        r5, _ = streams[5]
        c5 = struct.unpack_from('<I', d, r5)[0]
        for i in range(c5):
            st, sz, rv = struct.unpack_from('<QII', d, r5 + 4 + i * 16)
            ranges.append((st, sz, rv))
    if 9 in streams:
        r9, _ = streams[9]
        c9, base_rva = struct.unpack_from('<QQ', d, r9)
        off = base_rva
        for i in range(c9):
            st, sz = struct.unpack_from('<QQ', d, r9 + 16 + i * 16)
            ranges.append((st, sz, off))
            off += sz
    for st, sz, rv in ranges:
        if st <= rsp < st + sz:
            o = rsp - st
            for k in range(0, min(sz - o, 0x1000), 8):
                v = struct.unpack_from('<Q', d, rv + o + k)[0]
                w = where(v)
                if w and any(m in w for m in ('Torment', 'InfinityLoader', 'Lua')):
                    print('stack +%x' % k, w)
            break


main()
