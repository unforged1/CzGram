#!/bin/sh
# Builds dist/czgram_<version>_all.deb. Needs dpkg-deb and python3-pil (for the icon).
set -eu
cd "$(dirname "$0")/.."
VERSION=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' czgram/__init__.py)
ROOT=$(mktemp -d)
trap 'rm -rf "$ROOT"' EXIT

install -d "$ROOT/DEBIAN"
sh packaging/stage.sh "$ROOT"

# The license text comes from LICENSE, so the package and the repository always agree.
{
    printf 'Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/\n'
    printf 'Upstream-Name: czgram\nSource: https://github.com/unforged1/CzGram\n\n'
    printf 'Files: *\nCopyright: 2026 unforged1\nLicense: MIT\n'
    # Debian's format indents the license text and marks blank lines with a dot.
    tail -n +2 LICENSE | sed -e 's/^[[:space:]]*$/./' -e 's/^/ /'
} > "$ROOT/usr/share/doc/czgram/copyright"

cat > "$ROOT/DEBIAN/control" <<EOF
Package: czgram
Version: $VERSION
Section: education
Priority: optional
Architecture: all
Depends: python3 (>= 3.9), python3-tk, python3-pil, python3-gi, gir1.2-glib-2.0, tesseract-ocr, tesseract-ocr-ces, libx11-6, x11-xserver-utils, fonts-dejavu-core
Recommends: xdg-desktop-portal
Suggests: python3-anthropic
Installed-Size: $(du -sk "$ROOT/usr" | cut -f1)
Maintainer: CzGram <noreply@example.invalid>
Description: Czech grammar lookup on the PrintScreen key
 Press PrintScreen while solving Czech exercises. CzGram finds gaps and
 questions on screen, by OCR or from the page's HTML, and shows the matching
 grammar rule in a small bar at the top of the screen, optionally explained
 by an animated mascot.
EOF

cat > "$ROOT/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
# Compiled modules start faster and use less memory on every key press.
if [ "$1" = "configure" ]; then
    python3 -m compileall -q /usr/lib/czgram >/dev/null 2>&1 || true
fi
EOF
cat > "$ROOT/DEBIAN/prerm" <<'EOF'
#!/bin/sh
set -e
find /usr/lib/czgram -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
EOF
chmod 755 "$ROOT/DEBIAN/postinst" "$ROOT/DEBIAN/prerm"

chmod 644 "$ROOT/usr/share/doc/czgram/copyright"

mkdir -p dist
dpkg-deb --root-owner-group --build "$ROOT" "dist/czgram_${VERSION}_all.deb"
