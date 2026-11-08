"""Add the test-bridge poll label (M_ZBRDG.lua) to a test copy's UI.MENU: start menu + world action bar. Never shipped."""
import sys

p = sys.argv[1]
s = open(p, encoding="latin1", newline="").read()
lab = '\tlabel\n\t{\n\t\tarea 0 0 0 0\n\t\tenabled "PB_Poll()"\n\t}\n'
a = "\t--PC Version"
assert s.count(a) == 1
s = s.replace(a, lab + a)
i = s.index("name 'START_MAIN'")
j = s.index("\tlabel", i)
s = s[:j] + lab + s[j:]
open(p, "w", encoding="latin1", newline="").write(s)
