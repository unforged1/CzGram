"""macOS support: screen capture, the global hotkey, the selection, and per-user paths.

Macs have no PrintScreen key, so CzGram listens for Control-Option-G, and for F13, which sits
where PrintScreen is on extended keyboards. The listener uses Carbon's RegisterEventHotKey
through ctypes: it needs no Accessibility permission and no extra Python packages.
"""
import ctypes
import ctypes.util
import os
import plistlib
import subprocess
import sys
import tempfile

IS_MAC = sys.platform == "darwin"
KEY_NAME = "⌃⌥G"
FONT = "Helvetica Neue"
AGENT_LABEL = "cz.czgram.hotkey"


def key_text(text):
    """UI text with PrintScreen swapped for the Mac shortcut, and Alt and Ctrl named as Macs label them."""
    if not IS_MAC:
        return text
    return (text.replace("PrintScreen", KEY_NAME).replace("Double-tap Alt", "Double-tap Option (⌥)")
            .replace("Double Alt ", "Double Option ").replace("Double Ctrl ", "Double Control "))


# ---------------------------------------------------------------- capture

def capture_png():
    """Screenshot of the main display as a temporary PNG path. The caller deletes it.

    Needs Screen Recording permission for the app that runs CzGram. Without it, macOS
    returns only the desktop background, so OCR finds nothing.
    """
    fd, path = tempfile.mkstemp(prefix="czgram-", suffix=".png")
    os.close(fd)
    res = subprocess.run(["/usr/sbin/screencapture", "-x", "-m", "-t", "png", path],
                         capture_output=True, text=True, timeout=30)
    if res.returncode != 0 or os.path.getsize(path) == 0:
        os.unlink(path)
        raise OSError(res.stderr.strip() or "screencapture failed; allow Screen Recording in System Settings")
    return path


# ---------------------------------------------------------------- selection

def read_selection():
    """The selected text in the front app, copied with ⌘C. Restores the clipboard afterwards.

    Sending ⌘C needs Accessibility permission for the app that runs CzGram.
    """
    def paste():
        return subprocess.run(["/usr/bin/pbpaste"], capture_output=True, timeout=5).stdout

    try:
        before = paste()
        # A marker shows whether ⌘C copied anything: with no selection the clipboard stays as it was.
        subprocess.run(["/usr/bin/pbcopy"], input=b"\0czgram\0", timeout=5)
        subprocess.run(["/usr/bin/osascript", "-e",
                        'tell application "System Events" to keystroke "c" using command down'],
                       capture_output=True, timeout=5)
        import time
        for _ in range(10):
            time.sleep(0.05)
            now = paste()
            if now != b"\0czgram\0":
                break
        else:
            now = b""
        subprocess.run(["/usr/bin/pbcopy"], input=before, timeout=5)
        return now.decode("utf-8", "replace")[:500]
    except (OSError, subprocess.SubprocessError):
        return ""


# ---------------------------------------------------------------- hotkey

_kVK_ANSI_G = 0x05
_kVK_F13 = 0x69
_controlKey, _optionKey = 0x1000, 0x0800
_HOTKEYS = ((_kVK_ANSI_G, _controlKey | _optionKey), (_kVK_F13, 0))


def _fourcc(s):
    return int.from_bytes(s.encode("ascii"), "big")


class _EventTypeSpec(ctypes.Structure):
    _fields_ = [("eventClass", ctypes.c_uint32), ("eventKind", ctypes.c_uint32)]


class _EventHotKeyID(ctypes.Structure):
    _fields_ = [("signature", ctypes.c_uint32), ("id", ctypes.c_uint32)]


_HANDLER = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)


def _carbon():
    lib = ctypes.CDLL("/System/Library/Frameworks/Carbon.framework/Carbon")
    lib.GetApplicationEventTarget.restype = ctypes.c_void_p
    lib.InstallEventHandler.argtypes = [ctypes.c_void_p, _HANDLER, ctypes.c_uint32,
                                        ctypes.POINTER(_EventTypeSpec), ctypes.c_void_p, ctypes.c_void_p]
    lib.InstallEventHandler.restype = ctypes.c_int32
    lib.RegisterEventHotKey.argtypes = [ctypes.c_uint32, ctypes.c_uint32, _EventHotKeyID,
                                        ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p)]
    lib.RegisterEventHotKey.restype = ctypes.c_int32
    lib.UnregisterEventHotKey.argtypes = [ctypes.c_void_p]
    return lib


def register_hotkeys(on_press):
    """Registers the hotkeys; returns (carbon, refs, handler) to keep alive. Raises OSError."""
    lib = _carbon()
    target = lib.GetApplicationEventTarget()
    spec = _EventTypeSpec(_fourcc("keyb"), 5)  # kEventClassKeyboard, kEventHotKeyPressed

    def handler(_call, _event, _data):
        on_press()
        return 0

    cb = _HANDLER(handler)
    err = lib.InstallEventHandler(target, cb, 1, ctypes.byref(spec), None, None)
    if err:
        raise OSError("InstallEventHandler failed (%d)" % err)
    refs = []
    for n, (code, mods) in enumerate(_HOTKEYS, 1):
        ref = ctypes.c_void_p()
        err = lib.RegisterEventHotKey(code, mods, _EventHotKeyID(_fourcc("czgr"), n), target, 0,
                                      ctypes.byref(ref))
        if err:
            raise OSError("RegisterEventHotKey failed (%d); another app may use %s" % (err, KEY_NAME))
        refs.append(ref)
    return lib, refs, cb


def run_hotkey_daemon():
    from . import ipc
    try:
        lib, _refs, _cb = register_hotkeys(ipc.trigger)
    except OSError as e:
        print("czgram: %s" % e, file=sys.stderr)
        return 2
    lib.RunApplicationEventLoop()
    return 0


# ---------------------------------------------------------------- per-user setup

def _support():
    return os.path.expanduser("~/Library/Application Support")


def native_host_dirs():
    s = _support()
    return {
        "firefox": [os.path.join(s, "Mozilla", "NativeMessagingHosts")],
        "chromium": [os.path.join(s, d, "NativeMessagingHosts") for d in
                     ("Google/Chrome", "Google/Chrome Beta", "Chromium", "BraveSoftware/Brave-Browser",
                      "Microsoft Edge", "Vivaldi")],
    }


def agent_path():
    return os.path.expanduser("~/Library/LaunchAgents/%s.plist" % AGENT_LABEL)


def agent_plist(argv, path_env):
    return plistlib.dumps({
        "Label": AGENT_LABEL,
        "ProgramArguments": list(argv),
        "RunAtLoad": True,
        "KeepAlive": False,
        "LimitLoadToSessionType": "Aqua",
        "EnvironmentVariables": {"PATH": path_env},
        "ProcessType": "Interactive",
    })


def _launchctl(*args):
    return subprocess.run(["/bin/launchctl"] + list(args), capture_output=True, text=True, timeout=10)


def install_agent(argv):
    """Starts the hotkey listener now and at every login."""
    path = agent_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    env_path = os.pathsep.join(dict.fromkeys(
        ["/opt/homebrew/bin", "/usr/local/bin"] + os.environ.get("PATH", "/usr/bin:/bin").split(os.pathsep)))
    with open(path, "wb") as f:
        f.write(agent_plist(argv, env_path))
    domain = "gui/%d" % os.getuid()
    _launchctl("bootout", domain + "/" + AGENT_LABEL)
    res = _launchctl("bootstrap", domain, path)
    if res.returncode != 0:
        return False, "hotkey listener didn't start: " + (res.stderr.strip() or "launchctl failed")
    return True, "%s and F13 are set" % KEY_NAME


def remove_agent():
    path = agent_path()
    if not os.path.exists(path):
        return True, "nothing to restore"
    _launchctl("bootout", "gui/%d/%s" % (os.getuid(), AGENT_LABEL))
    os.unlink(path)
    return True, "%s is free again" % KEY_NAME


def agent_installed():
    return os.path.exists(agent_path())


def open_path(path):
    subprocess.Popen(["/usr/bin/open", path])
