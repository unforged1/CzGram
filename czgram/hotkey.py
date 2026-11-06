"""X11 PrintScreen listener. Uses ctypes rather than a toolkit, so it stays small while idle.

On Wayland no app may grab keys globally; there the desktop shortcut runs
`czgram --trigger` instead (see shortcuts.py) and this daemon isn't needed.
"""
import ctypes
import ctypes.util
import select
import sys

from . import ipc

XK_Print = 0xFF61
KeyPress = 2
GrabModeAsync = 1
# Ignore NumLock (Mod2) and CapsLock (Lock) so they don't stop the grab matching.
_LOCK_COMBOS = (0, 2, 16, 18)


class _XEvent(ctypes.Union):
    _fields_ = [("type", ctypes.c_int), ("pad", ctypes.c_long * 24)]


_grab_failed = False


def _on_x_error(_dpy, _event):
    global _grab_failed
    _grab_failed = True
    return 0


_ERROR_HANDLER = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)(_on_x_error)


def run():
    x = ctypes.CDLL(ctypes.util.find_library("X11") or "libX11.so.6")
    x.XOpenDisplay.restype = ctypes.c_void_p
    x.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x.XDefaultRootWindow.restype = ctypes.c_ulong
    x.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    x.XKeysymToKeycode.restype = ctypes.c_ubyte
    x.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    x.XGrabKey.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint, ctypes.c_ulong,
                           ctypes.c_int, ctypes.c_int, ctypes.c_int]
    x.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
    x.XConnectionNumber.argtypes = [ctypes.c_void_p]
    x.XPending.argtypes = [ctypes.c_void_p]
    x.XNextEvent.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    x.XSetErrorHandler(_ERROR_HANDLER)

    dpy = x.XOpenDisplay(None)
    if not dpy:
        print("czgram: cannot open X display", file=sys.stderr)
        return 1
    root = x.XDefaultRootWindow(dpy)
    code = x.XKeysymToKeycode(dpy, XK_Print)
    for mods in _LOCK_COMBOS:
        x.XGrabKey(dpy, code, mods, root, 1, GrabModeAsync, GrabModeAsync)
    x.XSync(dpy, 0)
    if _grab_failed:
        print("czgram: PrintScreen is already taken by another program. "
              "Free it in your desktop's keyboard shortcuts or run czgram --config.",
              file=sys.stderr)
        return 2

    fd = x.XConnectionNumber(dpy)
    ev = _XEvent()
    while True:
        # Block in select so the process stays asleep between key presses.
        select.select([fd], [], [])
        while x.XPending(dpy):
            x.XNextEvent(dpy, ctypes.byref(ev))
            if ev.type == KeyPress:
                ipc.trigger()
