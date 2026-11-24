"""Settings and per-user paths. Stdlib only: imported by the tiny hotkey daemon."""
import json
import os
import stat
import tempfile

DEFAULTS = {
    "detection": "screenshot",  # "screenshot" | "html" | "manual" (the word the user selected)
    "auto_fallback": True,      # screenshot unreadable -> read page code
    "quick_mode": False,        # PrintScreen starts and stops continuous page reading
    "low_ram": False,
    "mascot": True,
    "speed_mode": False,        # blue look and instant text when the model is Opus or Fable
    "language": "en",           # explanation language: "en" | "cs"
    "use_claude": False,        # send recognised text to the chosen AI service
    "claude_backend": "code",   # "code": Claude plan | "api": Anthropic key | "custom": other provider
    "code_model": "default",    # "default" leaves the choice to the user's Claude account
    "api_key": "",              # optional; the SDK's own credentials are used if empty
    "model": "claude-opus-5-5",
    "custom_base_url": "http://localhost:3001/v1",  # FreeLLMAPI's usual local address
    "custom_api_key": "",
    "custom_model": "",
    "bind_printscreen": True,
    "bulk_key": "Alt",          # double-tapped in the browser to accept bulk mode: see BULK_KEYS
}

# Keys a double tap can confirm bulk mode with, as browsers name them, and how the bar shows them.
BULK_KEYS = {"Alt": "Alt", "Control": "Ctrl", "Shift": "Shift"}


def bulk_key(cfg):
    """The configured bulk-mode key; anything else in a hand-edited file falls back to Alt."""
    key = cfg.get("bulk_key")
    return key if key in BULK_KEYS else "Alt"


def config_dir():
    base = os.environ.get("XDG_CONFIG_HOME")
    if not base and os.name == "nt":
        from .windows import config_base
        base = config_base()
    base = base or os.path.expanduser("~/.config")
    return os.path.join(base, "czgram")


def config_path():
    return os.path.join(config_dir(), "config.json")


def exists():
    return os.path.exists(config_path())


def load():
    cfg = dict(DEFAULTS)
    try:
        with open(config_path(), encoding="utf-8") as f:
            cfg.update({k: v for k, v in json.load(f).items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    return cfg


def save(cfg):
    """Write atomically, owner-only: the file can hold an API key."""
    os.makedirs(config_dir(), mode=0o700, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=config_dir(), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp, config_path())
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def runtime_dir():
    """Private directory for the app's sockets (mode 0700)."""
    base = os.environ.get("XDG_RUNTIME_DIR")
    if not base and os.name == "nt":
        from .windows import runtime_dir as windows_runtime_dir
        return windows_runtime_dir()
    path = os.path.join(base, "czgram") if base else os.path.join(
        tempfile.gettempdir(), "czgram-%d" % os.getuid())
    os.makedirs(path, mode=0o700, exist_ok=True)
    if os.name == "nt":
        return path  # tests point XDG_RUNTIME_DIR at a private temporary folder
    st = os.lstat(path)
    if st.st_uid != os.getuid() or not stat.S_ISDIR(st.st_mode):
        raise RuntimeError("unsafe runtime directory: " + path)
    os.chmod(path, 0o700)
    return path


def ui_socket():
    """The bar's socket; on Windows, the file naming its pipe and key."""
    return os.path.join(runtime_dir(), "ui.json" if os.name == "nt" else "ui.sock")
