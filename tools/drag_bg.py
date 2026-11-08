"""Mouse drag posted to the disposable test copy's window (no focus change, John's cursor stays free).

Usage: python tools/drag_bg.py x1 y1 x2 y2   (client pixels, as seen by capture_window at scale 1)
"""
import ctypes
import sys
import time

user32 = ctypes.windll.user32
user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
user32.FindWindowW.restype = ctypes.c_void_p
WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP, MK_LBUTTON = 0x200, 0x201, 0x202, 1
TITLE = "PSTEE Stash Test - v3.2.2.0"


def main():
    x1, y1, x2, y2 = map(int, sys.argv[1:5])
    h = user32.FindWindowW(None, TITLE)
    if not h:
        sys.exit("test copy window not found")

    def post(msg, wp, x, y):
        user32.PostMessageW(h, msg, wp, (y << 16) | x)
        time.sleep(0.06)

    post(WM_MOUSEMOVE, 0, x1, y1)
    time.sleep(0.2)
    post(WM_LBUTTONDOWN, MK_LBUTTON, x1, y1)
    time.sleep(0.2)
    for i in range(1, 9):
        post(WM_MOUSEMOVE, MK_LBUTTON, x1 + (x2 - x1) * i // 8, y1 + (y2 - y1) * i // 8)
    time.sleep(0.3)
    post(WM_LBUTTONUP, 0, x2, y2)
    print("dragged")


main()
