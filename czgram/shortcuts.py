"""Point the desktop's PrintScreen key at CzGram, and put it back afterwards.

Whatever was bound before is saved to ~/.config/czgram/shortcut-backup.json, and
`czgram --restore-shortcut` restores it.
"""
import json
import os
import shutil
import subprocess

from . import config

_MEDIA = "org.gnome.settings-daemon.plugins.media-keys"
_CUSTOM_SCHEMA = _MEDIA + ".custom-keybinding"
_CUSTOM_PATH = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/czgram/"
_SHELL = "org.gnome.shell.keybindings"
_XFCE_CH = "xfce4-keyboard-shortcuts"
_XFCE_PROP = "/commands/custom/Print"


def _backup_path():
    return os.path.join(config.config_dir(), "shortcut-backup.json")


def _run(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=10)


def desktop():
    d = (os.environ.get("XDG_CURRENT_DESKTOP") or "").lower()
    if ("gnome" in d or "unity" in d or "budgie" in d) and shutil.which("gsettings"):
        return "gnome"
    if "xfce" in d and shutil.which("xfconf-query"):
        return "xfce"
    return "other"


def _gnome_list(schema, key):
    """Parse a gsettings string array; '@as []' is how an empty one prints."""
    out = _run("gsettings", "get", schema, key).stdout.strip()
    if out.startswith("@as"):
        out = out[3:].strip()
    try:
        return json.loads(out.replace("'", '"'))
    except ValueError:
        return []


def _gnome_set(schema, key, values):
    return _run("gsettings", "set", schema, key, json.dumps(values).replace('"', "'"))


def _custom_set(key, value):
    return _run("gsettings", "set", "%s:%s" % (_CUSTOM_SCHEMA, _CUSTOM_PATH), key, value)


def is_bound():
    kind = desktop()
    if kind == "gnome":
        return _CUSTOM_PATH in _gnome_list(_MEDIA, "custom-keybindings")
    if kind == "xfce":
        out = _run("xfconf-query", "-c", _XFCE_CH, "-p", _XFCE_PROP).stdout
        return "czgram" in out
    return False


def bind(command="czgram --trigger"):
    """Returns (ok, message)."""
    kind = desktop()
    if kind == "gnome":
        return _bind_gnome(command)
    if kind == "xfce":
        return _bind_xfce(command)
    from .capture import is_wayland
    if is_wayland():
        return False, ("Add a keyboard shortcut for PrintScreen in your desktop's "
                       "settings that runs: " + command)
    return True, "PrintScreen is handled by the CzGram hotkey service"


def _save_backup(data):
    # Keep the first backup: a repeat bind must not record our own binding as "original".
    if not os.path.exists(_backup_path()):
        os.makedirs(config.config_dir(), mode=0o700, exist_ok=True)
        with open(_backup_path(), "w", encoding="utf-8") as f:
            json.dump(data, f)


def _bind_gnome(command):
    shell_keys = _gnome_list(_SHELL, "show-screenshot-ui")
    _save_backup({"desktop": "gnome", "show-screenshot-ui": shell_keys})
    # GNOME Shell consumes Print before custom shortcuts see it, so it must give it up.
    remaining = [k for k in shell_keys if k != "Print"]
    if remaining != shell_keys:
        if _gnome_set(_SHELL, "show-screenshot-ui", remaining).returncode != 0:
            return False, "could not release PrintScreen from GNOME's screenshot tool"
    paths = _gnome_list(_MEDIA, "custom-keybindings")
    if _CUSTOM_PATH not in paths:
        _gnome_set(_MEDIA, "custom-keybindings", paths + [_CUSTOM_PATH])
    _custom_set("name", "'CzGram'")
    _custom_set("command", "'%s'" % command)
    res = _custom_set("binding", "'Print'")
    if res.returncode != 0:
        return False, "could not set the shortcut: " + res.stderr.strip()
    return True, "PrintScreen now runs CzGram"


def _bind_xfce(command):
    old = _run("xfconf-query", "-c", _XFCE_CH, "-p", _XFCE_PROP)
    _save_backup({"desktop": "xfce", "print": old.stdout.strip() if old.returncode == 0 else None})
    res = _run("xfconf-query", "-c", _XFCE_CH, "-p", _XFCE_PROP, "-n", "-t", "string",
               "-s", command)
    if res.returncode != 0:
        return False, "could not set the XFCE shortcut: " + res.stderr.strip()
    return True, "PrintScreen now runs CzGram"


def restore():
    """Returns (ok, message)."""
    try:
        with open(_backup_path(), encoding="utf-8") as f:
            data = json.load(f)
    except OSError:
        return True, "nothing to restore"
    except ValueError:
        return False, "the shortcut backup is unreadable"
    if data.get("desktop") == "gnome":
        paths = [p for p in _gnome_list(_MEDIA, "custom-keybindings") if p != _CUSTOM_PATH]
        _gnome_set(_MEDIA, "custom-keybindings", paths)
        _gnome_set(_SHELL, "show-screenshot-ui", data.get("show-screenshot-ui", ["Print"]))
    elif data.get("desktop") == "xfce":
        if data.get("print"):
            _run("xfconf-query", "-c", _XFCE_CH, "-p", _XFCE_PROP, "-s", data["print"])
        else:
            _run("xfconf-query", "-c", _XFCE_CH, "-p", _XFCE_PROP, "-r")
    os.unlink(_backup_path())
    return True, "PrintScreen shortcut restored"
