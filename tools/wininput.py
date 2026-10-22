"""Minimal stdio client for John's wininput MCP server (E:/Dev/QuestLog/bin/wininput.exe), for scripted game tests.

Usage: python tools/wininput.py <tool> '<json args>' [<tool> '<json args>' ...]
  e.g. python tools/wininput.py press_keys '{"window":"Torment","keys":"ctrl+space","mode":"background"}'
capture_window results are saved as PNG files next to --out (default: wininput_capture_<n>.png in the cwd).
"""
import base64
import json
import subprocess
import sys

EXE = r"E:/Dev/QuestLog/bin/wininput.exe"


def main():
    args = sys.argv[1:]
    out = "wininput_capture"
    if "--out" in args:
        i = args.index("--out")
        out = args[i + 1]
        del args[i:i + 2]
    p = subprocess.Popen([EXE], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

    def call(o):
        p.stdin.write(json.dumps(o) + "\n")
        p.stdin.flush()
        if "id" in o:
            return json.loads(p.stdout.readline())

    call({"jsonrpc": "2.0", "id": 0, "method": "initialize",
          "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "cli", "version": "1"}}})
    call({"jsonrpc": "2.0", "method": "notifications/initialized"})
    for n in range(0, len(args), 2):
        tool, targs = args[n], json.loads(args[n + 1])
        r = call({"jsonrpc": "2.0", "id": n + 1, "method": "tools/call", "params": {"name": tool, "arguments": targs}})
        for c in r.get("result", {}).get("content", []):
            if c.get("type") == "image":
                f = f"{out}_{n // 2}.png"
                open(f, "wb").write(base64.b64decode(c["data"]))
                print(tool, "-> image", f)
            else:
                print(tool, "->", c.get("text", c))
        if "error" in r:
            print(tool, "ERROR", r["error"])
    p.kill()


main()
