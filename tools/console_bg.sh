#!/bin/bash
# Run Lua lines in the PTEE debug console of the inactive game window (wininput MCP, background mode).
# Each line: ctrl+space (open console), end + 300 backspaces (the field keeps old text), type, enter. Output: print() lines in EEex.log.
# Usage: tools/console_bg.sh "PSC_Test()" "PSC_Slots(0)"
T="$(dirname "$0")/wininput.py"
W="${PTEE_WINDOW:-Torment}"
CLR=$(python -c "print(' '.join(['backspace']*1500))")  # ctrl+a does not select in the console field
for c in "$@"; do
  python "$T" press_keys "{\"window\":\"$W\",\"keys\":\"ctrl+space end $CLR\",\"mode\":\"background\",\"hold_ms\":2,\"delay_ms\":2}" \
              type_text "{\"window\":\"$W\",\"text\":$(python -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$c"),\"mode\":\"background\"}" \
              press_keys "{\"window\":\"$W\",\"keys\":\"enter\",\"mode\":\"background\"}" >/dev/null
  sleep 1
done
