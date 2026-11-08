"""Run Lua in the disposable PSTEE test copy through M_ZBRDG.lua (loadfile polling) and print the PB() lines of EEex.log.

Usage: python tools/bridge.py <file.lua | -c "lua code"> [timeout_s]   (state: bridge/next.txt; reset when the game restarts)
"""
import os
import re
import sys
import time

G = r"E:\Enhanced Edition\Environnement de test\Compat\PSTEE stash test"
B = os.path.join(G, "bridge")
LOG = os.path.join(G, "EEex.log")


def main():
    os.makedirs(B, exist_ok=True)
    if sys.argv[1] == "reset":
        for f in os.listdir(B):
            os.remove(os.path.join(B, f))
        return
    if sys.argv[1] == "-c":
        code, rest = sys.argv[2], sys.argv[3:]
    else:
        code, rest = open(sys.argv[1], encoding="utf-8").read(), sys.argv[2:]
    timeout = float(rest[0]) if rest else 30
    nums = [int(m.group(1)) for f in os.listdir(B) if (m := re.match(r"cmd_(\d+)\.lua", f))]
    n = max(nums, default=0) + 1
    start = os.path.getsize(LOG) if os.path.exists(LOG) else 0
    tmp = os.path.join(B, "tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(code)
    os.replace(tmp, os.path.join(B, f"cmd_{n}.lua"))
    end = time.time() + timeout
    while time.time() < end:
        with open(LOG, "rb") as f:
            f.seek(start)
            text = f.read().decode("utf-8", "replace")
        if f"PB --done {n}" in text:
            for line in text.splitlines():
                m = re.search(r"LPRINT: PB (.*)", line)
                if m and "--done" not in m.group(1):
                    print(m.group(1))
            return
        time.sleep(0.2)
    print("TIMEOUT: no answer from the bridge")
    sys.exit(1)


main()
