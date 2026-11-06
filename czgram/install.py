"""Per-user setup applied when settings are saved: shortcut, hotkey service, browser host."""
import json
import os
import shutil
import stat
import subprocess
import sys

from . import config, shortcuts
from .extension_id import CHROMIUM_ID, FIREFOX_ID

HOST_NAME = "cz.czgram.bridge"
HERE = os.path.dirname(os.path.abspath(__file__))
_AUTOSTART = "czgram-hotkey.desktop"


def extension_dir():
    for path in (os.path.join(os.path.dirname(HERE), "extension"), "/usr/share/czgram/extension"):
        if os.path.isdir(path):
            return path
    return "/usr/share/czgram/extension"


def _command():
    """How the desktop shortcut should run us: the installed command, or this source tree."""
    exe = shutil.which("czgram")
    if exe:
        return exe + " --trigger"
    return "env PYTHONPATH=%s %s -m czgram --trigger" % (os.path.dirname(HERE), sys.executable)


def native_host_dirs():
    home = os.path.expanduser("~")
    cfg = os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    return {
        "firefox": [os.path.join(home, ".mozilla", "native-messaging-hosts")],
        "chromium": [os.path.join(cfg, d, "NativeMessagingHosts") for d in
                     ("chromium", "google-chrome", "google-chrome-beta",
                      "BraveSoftware/Brave-Browser", "microsoft-edge", "vivaldi")],
    }


def install_native_host():
    host = os.path.join(HERE, "nmhost.py")
    mode = os.stat(host).st_mode
    if not mode & stat.S_IXUSR:
        try:
            os.chmod(host, mode | stat.S_IXUSR)
        except OSError:
            pass
    base = {"name": HOST_NAME, "description": "CzGram browser connector",
            "path": host, "type": "stdio"}
    firefox = dict(base, allowed_extensions=[FIREFOX_ID])
    chromium = dict(base, allowed_origins=["chrome-extension://%s/" % CHROMIUM_ID])
    dirs = native_host_dirs()
    for kind, manifest in (("firefox", firefox), ("chromium", chromium)):
        for path in dirs[kind]:
            # Only for browsers that exist here, so we don't litter ~/.config.
            if not os.path.isdir(os.path.dirname(path)):
                continue
            os.makedirs(path, exist_ok=True)
            with open(os.path.join(path, HOST_NAME + ".json"), "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)


def _autostart_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "autostart", _AUTOSTART)


def _hotkey_daemon_needed(cfg):
    """Only X11 desktops without a shortcut we can set need a key-grabbing process."""
    from .capture import is_wayland
    return cfg["bind_printscreen"] and not is_wayland() and shortcuts.desktop() == "other"


def _manage_daemon(cfg):
    path = _autostart_path()
    if _hotkey_daemon_needed(cfg):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("[Desktop Entry]\nType=Application\nName=CzGram hotkey\n"
                    "Exec=%s\nX-GNOME-Autostart-enabled=true\nNoDisplay=true\n"
                    % _command().replace("--trigger", "--hotkey-daemon"))
        subprocess.Popen([sys.executable, "-m", "czgram", "--hotkey-daemon"],
                         cwd=os.path.dirname(HERE), start_new_session=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    elif os.path.exists(path):
        os.unlink(path)


def apply(cfg):
    """Returns [(ok, message), ...] for the settings window."""
    results = []
    try:
        install_native_host()
    except OSError as e:
        results.append((False, "Browser connector setup failed: %s." % e))
    if cfg["bind_printscreen"]:
        if shortcuts.is_bound():
            results.append((True, "PrintScreen is set."))
        else:
            ok, msg = shortcuts.bind(_command())
            results.append((ok, msg + "."))
    else:
        ok, msg = shortcuts.restore()
        results.append((ok, msg[0].upper() + msg[1:] + "." if msg != "nothing to restore" else ""))
    _manage_daemon(cfg)
    return results
