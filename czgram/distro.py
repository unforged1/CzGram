"""Package names for install hints, so messages match the user's system."""
import sys

_NAMES = {
    # Debian/Ubuntu name: Arch name
    "tesseract-ocr-ces": "tesseract-data-ces",
    "python3-anthropic": "python-anthropic",
}


_MAC_NAMES = {
    "tesseract-ocr-ces": "tesseract-lang (Homebrew)",
    "python3-anthropic": "anthropic (pip3 install anthropic)",
}


def family(path="/etc/os-release"):
    """"macos", "arch" on Arch-based systems (Manjaro, EndeavourOS...), else "debian"."""
    if sys.platform == "darwin":
        return "macos"
    try:
        with open(path, encoding="utf-8") as f:
            fields = dict(line.rstrip("\n").split("=", 1) for line in f if "=" in line)
    except OSError:
        return "debian"
    ids = (fields.get("ID", "") + " " + fields.get("ID_LIKE", "")).replace('"', "").split()
    return "arch" if "arch" in ids else "debian"


def pkg(debian_name, path="/etc/os-release"):
    """The package name to suggest on this system."""
    kind = family(path)
    if kind == "macos":
        return _MAC_NAMES.get(debian_name, debian_name)
    return _NAMES.get(debian_name, debian_name) if kind == "arch" else debian_name
