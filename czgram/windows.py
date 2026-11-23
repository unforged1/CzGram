"""Windows support: screen capture, the PrintScreen hotkey, the selection, local pipes and setup.

Everything here uses the standard library (ctypes, winreg, multiprocessing.connection) plus
Pillow, which CzGram needs anyway. Each part mirrors a Linux piece:

  X11 key grab / desktop shortcut   ->  RegisterHotKey in a small daemon started at sign-in
  Unix sockets                      ->  named pipes with a random name and a key, both kept in a
                                        file in the user's private AppData folder
  XGetImage / screenshot portal     ->  Pillow's ImageGrab
  PRIMARY selection                 ->  copy with Ctrl+C (Ctrl+Insert in terminals), then put the
                                        clipboard back
"""
import ctypes
import json
import os
import subprocess
import sys
import tempfile
import time

IS_WINDOWS = os.name == "nt"
FONT = "Segoe UI"
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "CzGram hotkey"
SNIP_KEY = r"Control Panel\Keyboard"
SNIP_VALUE = "PrintScreenKeyForSnippingEnabled"
HOST_NAME = "cz.czgram.bridge"
# Where each browser looks for native-messaging hosts (HKEY_CURRENT_USER).
HOST_KEYS = {
    "chromium": (r"Software\Google\Chrome\NativeMessagingHosts",
                 r"Software\Chromium\NativeMessagingHosts",
                 r"Software\Microsoft\Edge\NativeMessagingHosts",
                 r"Software\BraveSoftware\Brave-Browser\NativeMessagingHosts"),
    "firefox": (r"Software\Mozilla\NativeMessagingHosts",),
}


# ---------------------------------------------------------------- folders

def local_dir():
    """%LOCALAPPDATA%\\czgram: per-user and private (the profile's ACL admits only its owner)."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local")
    return os.path.join(base, "czgram")


def config_base():
    return os.environ.get("APPDATA") or os.path.expanduser(r"~\AppData\Roaming")


def runtime_dir():
    path = os.path.join(local_dir(), "run")
    os.makedirs(path, exist_ok=True)
    return path


def tessdata_dir():
    return os.path.join(local_dir(), "tessdata")


# ---------------------------------------------------------------- processes

def gui_python():
    """pythonw.exe beside the running interpreter, so no console window opens."""
    folder, name = os.path.split(sys.executable)
    if name.lower() == "python.exe":
        candidate = os.path.join(folder, "pythonw.exe")
        if os.path.exists(candidate):
            return candidate
    return sys.executable


def child_flags():
    """Popen keywords for a helper process: never flash a console window."""
    return {"creationflags": CREATE_NO_WINDOW}


def spawn_detached(args, cwd):
    """Start `pythonw -m ...` on its own, the Windows form of start_new_session."""
    return subprocess.Popen([gui_python()] + list(args), cwd=cwd,
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP)


def kill_tree(pid):
    """Stop a helper and whatever it started. Windows has no SIGTERM to pass on, so a
    Claude Code lookup would otherwise outlive the bar that asked for it."""
    subprocess.run(["taskkill", "/T", "/F", "/PID", str(int(pid))], capture_output=True,
                   timeout=10, creationflags=CREATE_NO_WINDOW)


# ---------------------------------------------------------------- local pipes

def _write_private(path, data):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def serve(desc_path):
    """A pipe listener whose address and key are written to desc_path.

    Only the owner can read the file, the pipe's default access admits only the owner and
    administrators, and both ends prove they hold the key before any data is exchanged.
    """
    import secrets
    from multiprocessing.connection import Listener
    key = secrets.token_bytes(32)
    address = r"\\.\pipe\czgram-" + secrets.token_hex(16)
    listener = Listener(address, family="AF_PIPE", authkey=key)
    _write_private(desc_path, {"address": address, "key": key.hex()})
    return listener


def connect(desc_path):
    """A connection to the listener described by desc_path. Raises FileNotFoundError when it's gone."""
    from multiprocessing import AuthenticationError
    from multiprocessing.connection import Client
    with open(desc_path, encoding="utf-8") as f:
        desc = json.load(f)
    try:
        return Client(desc["address"], family="AF_PIPE", authkey=bytes.fromhex(desc["key"]))
    except (AuthenticationError, EOFError) as e:
        # Whatever answered on that pipe didn't hold the key.
        raise ConnectionError("the other end failed to authenticate: %s" % e) from None


# ---------------------------------------------------------------- capture

def capture_grey():
    """(width, height, 8-bit grey bytes) of every screen. Pillow handles high-DPI displays."""
    from PIL import ImageGrab
    im = ImageGrab.grab(all_screens=True).convert("L")
    return im.width, im.height, im.tobytes()


# ---------------------------------------------------------------- selection

_CF_UNICODETEXT = 13
_GMEM_MOVEABLE = 0x0002
_VK_CONTROL, _VK_C, _VK_INSERT = 0x11, 0x43, 0x2D
_KEYEVENTF_EXTENDEDKEY, _KEYEVENTF_KEYUP = 0x0001, 0x0002
# Ctrl+C in a console stops the running program; there, Ctrl+Insert copies instead.
_CONSOLE_CLASSES = ("ConsoleWindowClass", "CASCADIA_HOSTING_WINDOW_CLASS", "mintty",
                    "VirtualConsoleClass", "PuTTY")


def _user32():
    u = ctypes.WinDLL("user32", use_last_error=True)
    u.OpenClipboard.argtypes = [ctypes.c_void_p]
    u.GetClipboardData.restype = ctypes.c_void_p
    u.GetClipboardData.argtypes = [ctypes.c_uint]
    u.SetClipboardData.restype = ctypes.c_void_p
    u.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    u.GetForegroundWindow.restype = ctypes.c_void_p
    u.GetClassNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
    u.GetClipboardSequenceNumber.restype = ctypes.c_uint32
    u.keybd_event.argtypes = [ctypes.c_ubyte, ctypes.c_ubyte, ctypes.c_uint32, ctypes.c_void_p]
    return u


def _kernel32():
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.GlobalLock.restype = ctypes.c_void_p
    k.GlobalLock.argtypes = [ctypes.c_void_p]
    k.GlobalUnlock.argtypes = [ctypes.c_void_p]
    k.GlobalAlloc.restype = ctypes.c_void_p
    k.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    k.GlobalFree.argtypes = [ctypes.c_void_p]
    return k


def _open_clipboard(u):
    for _ in range(20):  # another program may hold it for a moment
        if u.OpenClipboard(None):
            return True
        time.sleep(0.02)
    return False


def get_clipboard_text():
    """The clipboard's text, or None if it holds no text."""
    u, k = _user32(), _kernel32()
    if not _open_clipboard(u):
        return None
    try:
        handle = u.GetClipboardData(_CF_UNICODETEXT)
        if not handle:
            return None
        ptr = k.GlobalLock(handle)
        if not ptr:
            return None
        try:
            return ctypes.wstring_at(ptr)
        finally:
            k.GlobalUnlock(handle)
    finally:
        u.CloseClipboard()


def set_clipboard_text(text):
    u, k = _user32(), _kernel32()
    data = ctypes.create_unicode_buffer(text)
    size = ctypes.sizeof(data)
    if not _open_clipboard(u):
        return False
    try:
        u.EmptyClipboard()
        handle = k.GlobalAlloc(_GMEM_MOVEABLE, size)
        if not handle:
            return False
        ptr = k.GlobalLock(handle)
        ctypes.memmove(ptr, data, size)
        k.GlobalUnlock(handle)
        if not u.SetClipboardData(_CF_UNICODETEXT, handle):
            k.GlobalFree(handle)  # still ours if the clipboard didn't take it
            return False
        return True
    finally:
        u.CloseClipboard()


def _foreground_class(u):
    buf = ctypes.create_unicode_buffer(256)
    hwnd = u.GetForegroundWindow()
    if hwnd:
        u.GetClassNameW(hwnd, buf, 256)
    return buf.value


def _press_copy(u):
    console = _foreground_class(u) in _CONSOLE_CLASSES
    key, flags = (_VK_INSERT, _KEYEVENTF_EXTENDEDKEY) if console else (_VK_C, 0)
    u.keybd_event(_VK_CONTROL, 0, 0, None)
    u.keybd_event(key, 0, flags, None)
    u.keybd_event(key, 0, flags | _KEYEVENTF_KEYUP, None)
    u.keybd_event(_VK_CONTROL, 0, _KEYEVENTF_KEYUP, None)


def read_selection():
    """The text selected in the front window, or "" if nothing is selected.

    Windows has no selection other programs can read, so this copies it and then puts back
    the text that was on the clipboard before.
    """
    try:
        u = _user32()
        before = get_clipboard_text()
        seq = u.GetClipboardSequenceNumber()
        _press_copy(u)
        for _ in range(30):
            time.sleep(0.02)
            if u.GetClipboardSequenceNumber() != seq:
                break
        else:
            return ""  # nothing was copied, so nothing was selected
        time.sleep(0.03)  # let the app finish writing every format
        text = get_clipboard_text() or ""
        if before is not None:
            set_clipboard_text(before)
        return text[:500]
    except OSError:
        return ""


# ---------------------------------------------------------------- hotkey

_WM_HOTKEY = 0x0312
_VK_SNAPSHOT = 0x2C
_MOD_NOREPEAT = 0x4000
_ERROR_ALREADY_EXISTS = 183


class _MSG(ctypes.Structure):
    _fields_ = [("hwnd", ctypes.c_void_p), ("message", ctypes.c_uint), ("wParam", ctypes.c_size_t),
                ("lParam", ctypes.c_ssize_t), ("time", ctypes.c_uint32), ("x", ctypes.c_long),
                ("y", ctypes.c_long), ("private", ctypes.c_uint32)]


def pid_path():
    return os.path.join(runtime_dir(), "hotkey.pid")


def run_hotkey_daemon():
    """Waits for PrintScreen and runs the trigger. Exit codes: 0 already running, 2 key taken."""
    from . import ipc
    u = _user32()
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateMutexW.restype = ctypes.c_void_p
    k.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    mutex = k.CreateMutexW(None, False, "Local\\czgram-hotkey")
    if mutex and ctypes.get_last_error() == _ERROR_ALREADY_EXISTS:
        return 0
    u.RegisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
    if not u.RegisterHotKey(None, 1, _MOD_NOREPEAT, _VK_SNAPSHOT):
        print("czgram: PrintScreen is already taken by another program, such as the Snipping Tool. "
              "Turn off 'Use the Print screen key to open screen capture' in Settings > Accessibility "
              "> Keyboard, then sign out and back in.", file=sys.stderr)
        return 2
    with open(pid_path(), "w", encoding="ascii") as f:
        f.write(str(os.getpid()))
    u.GetMessageW.argtypes = [ctypes.POINTER(_MSG), ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
    msg = _MSG()
    # GetMessage sleeps until something arrives, so the daemon uses no CPU while idle.
    while u.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        if msg.message == _WM_HOTKEY:
            ipc.trigger()
    return 0


def stop_hotkey_daemon():
    try:
        with open(pid_path(), encoding="ascii") as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        return
    # The image filter keeps a reused process number from stopping something else.
    for image in ("pythonw.exe", "python.exe"):
        subprocess.run(["taskkill", "/F", "/PID", str(pid), "/FI", "IMAGENAME eq " + image],
                       capture_output=True, timeout=10, creationflags=CREATE_NO_WINDOW)
    try:
        os.unlink(pid_path())
    except OSError:
        pass


# ---------------------------------------------------------------- per-user setup

def launcher():
    """czgram.pyw beside the package: runs CzGram without needing a working directory."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "czgram.pyw")


def daemon_command():
    return subprocess.list2cmdline([gui_python(), launcher(), "--hotkey-daemon"])


def _reg_get(root, path, name):
    import winreg
    try:
        with winreg.OpenKey(root, path) as key:
            return winreg.QueryValueEx(key, name)[0]
    except OSError:
        return None


def _reg_set(root, path, name, kind, value):
    import winreg
    with winreg.CreateKey(root, path) as key:
        winreg.SetValueEx(key, name, 0, kind, value)


def _reg_delete(root, path, name):
    import winreg
    try:
        with winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, name)
    except OSError:
        pass


def write_batch(path, line):
    """A .bat running `line`. cmd.exe reads batch files in the OEM code page, so a profile
    folder like C:\\Users\\Jiří only survives in that encoding, or in UTF-8 after chcp 65001."""
    oem = "cp%d" % ctypes.windll.kernel32.GetOEMCP()
    try:
        data = ("@echo off\r\n%s\r\n" % line).encode(oem)
    except (UnicodeEncodeError, LookupError):
        data = ("@echo off\r\nchcp 65001 >nul\r\n%s\r\n" % line).encode("utf-8")
    with open(path, "wb") as f:
        f.write(data)


def install_native_host(firefox_manifest, chromium_manifest):
    """Writes the host's manifests and a small .bat the browsers start, and registers them."""
    import winreg
    here = os.path.dirname(os.path.abspath(__file__))
    folder = os.path.join(local_dir(), "native-host")
    os.makedirs(folder, exist_ok=True)
    bat = os.path.join(folder, "czgram-bridge.bat")
    python = sys.executable if os.path.basename(sys.executable).lower() != "pythonw.exe" else \
        os.path.join(os.path.dirname(sys.executable), "python.exe")
    write_batch(bat, '"%s" -u "%s" %%*' % (python, os.path.join(here, "nmhost.py")))
    for kind, manifest in (("firefox", firefox_manifest), ("chromium", chromium_manifest)):
        path = os.path.join(folder, "%s-%s.json" % (HOST_NAME, kind))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dict(manifest, path=bat), f, indent=2)
        for key in HOST_KEYS[kind]:
            _reg_set(winreg.HKEY_CURRENT_USER, key + "\\" + HOST_NAME, "", winreg.REG_SZ, path)


def remove_native_host():
    import winreg
    for keys in HOST_KEYS.values():
        for key in keys:
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key + "\\" + HOST_NAME)
            except OSError:
                pass


def snipping_tool_owns_printscreen():
    import winreg
    return _reg_get(winreg.HKEY_CURRENT_USER, SNIP_KEY, SNIP_VALUE) != 0


def is_bound():
    import winreg
    return _reg_get(winreg.HKEY_CURRENT_USER, RUN_KEY, RUN_VALUE) is not None \
        and not snipping_tool_owns_printscreen()


def bind_printscreen(save_backup):
    """Frees PrintScreen from the Snipping Tool, starts the hotkey daemon now and at every sign-in.

    save_backup(data) records what to restore. Returns (ok, message).
    """
    import winreg
    old = _reg_get(winreg.HKEY_CURRENT_USER, SNIP_KEY, SNIP_VALUE)
    save_backup({"desktop": "windows", "snipping": old})
    changed = old != 0
    if changed:
        _reg_set(winreg.HKEY_CURRENT_USER, SNIP_KEY, SNIP_VALUE, winreg.REG_DWORD, 0)
    _reg_set(winreg.HKEY_CURRENT_USER, RUN_KEY, RUN_VALUE, winreg.REG_SZ, daemon_command())
    proc = spawn_detached([launcher(), "--hotkey-daemon"], os.path.dirname(launcher()))
    try:
        code = proc.wait(timeout=1.5)
    except subprocess.TimeoutExpired:
        return True, "PrintScreen now runs CzGram"
    if code == 2:
        return False, ("PrintScreen is still taken by the Snipping Tool. Sign out and back in, "
                       "and it will run CzGram")
    return True, "PrintScreen now runs CzGram"


def restore_printscreen(data):
    """Undoes bind_printscreen from its backup."""
    import winreg
    _reg_delete(winreg.HKEY_CURRENT_USER, RUN_KEY, RUN_VALUE)
    stop_hotkey_daemon()
    old = data.get("snipping")
    if old is None:
        _reg_delete(winreg.HKEY_CURRENT_USER, SNIP_KEY, SNIP_VALUE)
    else:
        _reg_set(winreg.HKEY_CURRENT_USER, SNIP_KEY, SNIP_VALUE, winreg.REG_DWORD, int(old))


# ---------------------------------------------------------------- Tesseract

def tesseract(found):
    """(exe or None, extra arguments). The installer from UB Mannheim doesn't add itself to PATH,
    and CzGram keeps its own copy of the Czech data so no administrator rights are needed."""
    exe = found
    if not exe:
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
                     os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")):
            path = os.path.join(base or "", "Tesseract-OCR", "tesseract.exe")
            if base and os.path.exists(path):
                exe = path
                break
    data = tessdata_dir()
    extra = ["--tessdata-dir", data] if os.path.exists(os.path.join(data, "ces.traineddata")) else []
    return exe, extra
