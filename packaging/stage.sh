#!/bin/sh
# Installs CzGram's files under the root directory given as $1 (/usr/bin, /usr/lib/czgram,
# /usr/share/...). Shared by build_deb.sh and the Arch PKGBUILD so both packages match.
set -eu
ROOT=$1
cd "$(dirname "$0")/.."

install -d "$ROOT/usr/bin" "$ROOT/usr/lib/czgram/czgram" "$ROOT/usr/share/czgram" \
    "$ROOT/usr/share/applications" "$ROOT/usr/share/icons/hicolor/64x64/apps" "$ROOT/usr/share/doc/czgram"

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

install -m 644 README.md "$ROOT/usr/share/doc/czgram/README.md"
chmod 644 "$ROOT/usr/share/applications/czgram.desktop" "$ROOT/usr/share/icons/hicolor/64x64/apps/czgram.png"
