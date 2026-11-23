"""Package names for install hints, so messages match the user's distribution."""

_NAMES = {
    # Debian/Ubuntu name: the name on each other family
    "arch": {
        "tesseract-ocr-ces": "tesseract-data-ces",
        "python3-anthropic": "python-anthropic",
    },
    "fedora": {  # Fedora, RHEL and its rebuilds (Rocky, AlmaLinux), CentOS Stream
        "tesseract-ocr-ces": "tesseract-langpack-ces",
        "python3-anthropic": "anthropic (pip install --user anthropic)",
    },
    "suse": {  # openSUSE Tumbleweed and Leap, SUSE Linux Enterprise
        "tesseract-ocr-ces": "tesseract-ocr-traineddata-czech",
        "python3-anthropic": "anthropic (pip install --user anthropic)",
    },
}


def family(path="/etc/os-release"):
    """"arch", "fedora", "suse", or "debian" (also the answer when it can't tell)."""
    try:
        with open(path, encoding="utf-8") as f:
            fields = dict(line.rstrip("\n").split("=", 1) for line in f if "=" in line)
    except OSError:
        return "debian"
    ids = set((fields.get("ID", "") + " " + fields.get("ID_LIKE", "")).replace('"', "").split())
    if "arch" in ids:
        return "arch"
    if ids & {"fedora", "rhel", "centos"}:
        return "fedora"
    if any(i == "suse" or i.startswith(("opensuse", "sles", "sled")) for i in ids):
        return "suse"
    return "debian"


def pkg(debian_name, path="/etc/os-release"):
    """The package name to suggest on this system."""
    return _NAMES.get(family(path), {}).get(debian_name, debian_name)
