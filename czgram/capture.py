"""Grab the screen and return it as an 8-bit grey PGM (bytes) for Tesseract.

X11:              XGetImage through ctypes, no helper programs.
Wayland / other:  xdg-desktop-portal Screenshot, which writes a PNG; we read it
                  and delete that file straight away so ~/Pictures doesn't fill up.
Windows:          Pillow's ImageGrab, in memory.
"""
import ctypes
import ctypes.util
import os
import subprocess
import sys


class CaptureError(Exception):
    pass


def is_wayland():
    return bool(os.environ.get("WAYLAND_DISPLAY")) or \
        os.environ.get("XDG_SESSION_TYPE") == "wayland"


def _pgm(width, height, grey):
    return b"P5\n%d %d\n255\n" % (width, height) + bytes(grey)


# ---------------------------------------------------------------- X11

class _XImage(ctypes.Structure):
    # Only the leading fields we read; XGetImage owns the allocation.
    _fields_ = [
        ("width", ctypes.c_int), ("height", ctypes.c_int),
        ("xoffset", ctypes.c_int), ("format", ctypes.c_int),
        ("data", ctypes.POINTER(ctypes.c_ubyte)),
        ("byte_order", ctypes.c_int), ("bitmap_unit", ctypes.c_int),
        ("bitmap_bit_order", ctypes.c_int), ("bitmap_pad", ctypes.c_int),
        ("depth", ctypes.c_int), ("bytes_per_line", ctypes.c_int),
        ("bits_per_pixel", ctypes.c_int),
    ]


def _capture_x11():
    name = ctypes.util.find_library("X11") or "libX11.so.6"
    x = ctypes.CDLL(name)
    x.XOpenDisplay.restype = ctypes.c_void_p
    x.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x.XDefaultRootWindow.restype = ctypes.c_ulong
    x.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    x.XDefaultScreen.argtypes = [ctypes.c_void_p]
    x.XDisplayWidth.argtypes = x.XDisplayHeight.argtypes = [ctypes.c_void_p, ctypes.c_int]
    x.XGetImage.restype = ctypes.POINTER(_XImage)
    x.XGetImage.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int,
                            ctypes.c_uint, ctypes.c_uint, ctypes.c_ulong, ctypes.c_int]
    x.XCloseDisplay.argtypes = [ctypes.c_void_p]
    x.XFree.argtypes = [ctypes.c_void_p]

    dpy = x.XOpenDisplay(None)
    if not dpy:
        raise CaptureError("cannot open X display")
    try:
        scr = x.XDefaultScreen(dpy)
        w, h = x.XDisplayWidth(dpy, scr), x.XDisplayHeight(dpy, scr)
        ZPixmap, AllPlanes = 2, 0xFFFFFFFF
        img = x.XGetImage(dpy, x.XDefaultRootWindow(dpy), 0, 0, w, h, AllPlanes, ZPixmap)
        if not img:
            raise CaptureError("XGetImage failed")
        try:
            im = img.contents
            if im.bits_per_pixel != 32:
                raise CaptureError("unsupported pixel depth %d" % im.bits_per_pixel)
            raw = ctypes.string_at(im.data, im.bytes_per_line * h)
            # Green approximates luminance; a slice avoids a per-pixel Python loop.
            stride = im.bytes_per_line // 4
            grey = raw[1::4]
            if stride != w:
                grey = b"".join(grey[y * stride:y * stride + w] for y in range(h))
            return _pgm(w, h, grey)
        finally:
            x.XFree(img)
    finally:
        x.XCloseDisplay(dpy)


# ---------------------------------------------------------------- portal

_PORTAL_HELPER = r"""
import sys, secrets
from gi.repository import Gio, GLib
bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
token = "czgram" + secrets.token_hex(6)
sender = bus.get_unique_name()[1:].replace(".", "_")
handle = "/org/freedesktop/portal/desktop/request/%s/%s" % (sender, token)
loop = GLib.MainLoop()
out = {"code": 3, "uri": ""}
def on_response(conn, snd, path, iface, sig, params):
    code, res = params.unpack()
    out["code"] = code
    out["uri"] = res.get("uri", "")
    loop.quit()
bus.signal_subscribe("org.freedesktop.portal.Desktop",
                     "org.freedesktop.portal.Request", "Response", handle, None,
                     Gio.DBusSignalFlags.NO_MATCH_RULE, on_response)
bus.call_sync("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop",
              "org.freedesktop.portal.Screenshot", "Screenshot",
              GLib.Variant("(sa{sv})", ("", {
                  "handle_token": GLib.Variant("s", token),
                  "interactive": GLib.Variant("b", False),
                  "modal": GLib.Variant("b", False)})),
              None, Gio.DBusCallFlags.NONE, 15000, None)
GLib.timeout_add_seconds(60, loop.quit)
loop.run()
print(out["code"], out["uri"])
"""


def _capture_portal():
    # A throwaway interpreter keeps GObject out of the scan process's memory.
    try:
        res = subprocess.run([sys.executable, "-c", _PORTAL_HELPER], capture_output=True,
                             text=True, timeout=75)
    except subprocess.TimeoutExpired:
        raise CaptureError("screenshot portal timed out")
    parts = res.stdout.strip().split(None, 1)
    if res.returncode != 0 or not parts:
        detail = (res.stderr.strip().splitlines() or ["no response"])[-1]
        raise CaptureError("screenshot portal failed: " + detail)
    if parts[0] != "0" or len(parts) < 2:
        raise CaptureError("screenshot was denied or cancelled")
    from urllib.parse import unquote, urlparse
    uri = urlparse(parts[1])
    path = unquote(uri.path)
    if uri.scheme != "file" or not _own_regular_file(path):
        raise CaptureError("the screenshot portal returned an unexpected file")
    try:
        return _png_to_pgm(path)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _own_regular_file(path):
    """A plain file of ours, not a link, so cleaning up can't delete anything else."""
    import stat
    try:
        st = os.lstat(path)
    except OSError:
        return False
    return stat.S_ISREG(st.st_mode) and st.st_uid == os.getuid()


def _png_to_pgm(path):
    from PIL import Image
    with Image.open(path) as im:
        g = im.convert("L")
        return _pgm(g.width, g.height, g.tobytes())


def capture():
    """Returns PGM bytes. Raises CaptureError."""
    if sys.platform == "win32":
        from . import windows
        try:
            return _pgm(*windows.capture_grey())
        except OSError as e:
            raise CaptureError("screenshot failed: %s" % e)
    if is_wayland():
        return _capture_portal()
    if os.environ.get("DISPLAY"):
        return _capture_x11()
    raise CaptureError("no display found")


def upscale_pgm(pgm):
    """Double the resolution; small UI text OCRs far better at 2x. Skipped in low-RAM mode."""
    w, h, offset = _pgm_header(pgm)
    if w * 2 > 5000:
        return pgm
    from PIL import Image
    im = Image.frombuffer("L", (w, h), pgm[offset:], "raw", "L", 0, 1)
    big = im.resize((w * 2, h * 2), Image.BICUBIC)
    return _pgm(big.width, big.height, big.tobytes())


def _pgm_header(pgm):
    fields, pos = [], 0
    while len(fields) < 4:
        end = pos
        while pgm[end] not in b" \n\t\r":
            end += 1
        fields.append(pgm[pos:end])
        pos = end + 1
    return int(fields[1]), int(fields[2]), pos
