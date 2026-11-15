"""Package names for install hints, so messages match the user's distribution."""

_NAMES = {
    # Debian/Ubuntu name: Arch name
    "tesseract-ocr-ces": "tesseract-data-ces",
    "python3-anthropic": "python-anthropic",
}


def family(path="/etc/os-release"):
    """"arch" on Arch, Manjaro, EndeavourOS and other Arch-based systems, else "debian"."""
    try:
        with open(path, encoding="utf-8") as f:
            fields = dict(line.rstrip("\n").split("=", 1) for line in f if "=" in line)
    except OSError:
        return "debian"
    ids = (fields.get("ID", "") + " " + fields.get("ID_LIKE", "")).replace('"', "").split()
    return "arch" if "arch" in ids else "debian"


def pkg(debian_name, path="/etc/os-release"):
    """The package name to suggest on this system."""
    return _NAMES.get(debian_name, debian_name) if family(path) == "arch" else debian_name
