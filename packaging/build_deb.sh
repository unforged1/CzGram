#!/bin/sh
# Builds dist/czgram_<version>_all.deb. Needs dpkg-deb and python3-pil (for the icon).
set -eu
cd "$(dirname "$0")/.."
VERSION=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' czgram/__init__.py)
ROOT=$(mktemp -d)
trap 'rm -rf "$ROOT"' EXIT

install -d "$ROOT/DEBIAN" "$ROOT/usr/bin" "$ROOT/usr/lib/czgram/czgram" \
    "$ROOT/usr/share/czgram" "$ROOT/usr/share/applications" \
    "$ROOT/usr/share/icons/hicolor/64x64/apps" "$ROOT/usr/share/doc/czgram"

install -m 644 czgram/*.py "$ROOT/usr/lib/czgram/czgram/"
chmod 755 "$ROOT/usr/lib/czgram/czgram/nmhost.py"
cp -r extension "$ROOT/usr/share/czgram/extension"
find "$ROOT/usr/share/czgram" -type f -exec chmod 644 {} +
find "$ROOT/usr/share/czgram" -type d -exec chmod 755 {} +

cat > "$ROOT/usr/bin/czgram" <<'EOF'
#!/bin/sh
# Runs the installed copy, whatever folder it's started in: with -m, Python looks in the current
# folder first, so a czgram package or a json.py there would run instead.
exec /usr/bin/python3 -c 'import sys; sys.path[:] = ["/usr/lib/czgram"] + [p for p in sys.path if p not in ("", ".")]; from czgram.__main__ import main; sys.exit(main(sys.argv[1:]))' "$@"
EOF
chmod 755 "$ROOT/usr/bin/czgram"

cat > "$ROOT/usr/share/applications/czgram.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=CzGram
Comment=Look up Czech grammar for what's on screen with PrintScreen
Exec=czgram
Icon=czgram
Terminal=false
Categories=Education;Languages;
EOF

python3 - "$ROOT/usr/share/icons/hicolor/64x64/apps/czgram.png" <<'EOF'
import sys
from PIL import Image, ImageDraw
im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
cell, body, shade, dark = 4, "#D97757", "#B95F42", "#1F1E1D"
def rect(x, y, w, h, c):
    d.rectangle((x * cell + 2, y * cell + 4, (x + w) * cell + 1, (y + h) * cell + 3), fill=c)
rect(3, 3, 9, 6, body); rect(1, 5, 2, 2, body); rect(12, 5, 2, 2, body)
for x in (4, 6, 8, 10):
    rect(x, 9, 1, 2, shade)
rect(5, 4, 1, 2, dark); rect(9, 4, 1, 2, dark)
im.save(sys.argv[1])
EOF

cp README.md "$ROOT/usr/share/doc/czgram/README.md"
chmod 644 "$ROOT/usr/share/doc/czgram/README.md"
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

chmod 644 "$ROOT/usr/share/applications/czgram.desktop" \
    "$ROOT/usr/share/icons/hicolor/64x64/apps/czgram.png" \
    "$ROOT/usr/share/doc/czgram/copyright"

mkdir -p dist
dpkg-deb --root-owner-group --build "$ROOT" "dist/czgram_${VERSION}_all.deb"
