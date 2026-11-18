#!/bin/bash
# Installs CzGram for the current user on macOS (Apple silicon or Intel). Needs Homebrew.
# Usage: bash packaging/macos/install.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

if ! command -v brew >/dev/null; then
    echo "CzGram needs Homebrew. Install it from https://brew.sh, then run this again." >&2
    exit 1
fi
BREW=$(brew --prefix)
echo "==> Installing Python, Tk, Pillow and Tesseract with Homebrew"
brew install python python-tk pillow tesseract
PY="$BREW/bin/python3"
"$PY" -c "import tkinter, PIL" || { echo "Homebrew's Python can't load Tk or Pillow." >&2; exit 1; }

# Czech OCR data only (a few MB), rather than every language in tesseract-lang (hundreds of MB).
TESSDATA="$BREW/share/tessdata"
if ! "$BREW/bin/tesseract" --list-langs 2>/dev/null | grep -qx ces; then
    echo "==> Downloading Czech data for Tesseract"
    # Pinned to one commit and checked against its Git hash, so the file can't change under us.
    curl -fL --proto '=https' --retry 3 -o "$TESSDATA/ces.traineddata.part" \
        https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/923915d4ced2a7235221788285785a29c4a42d4a/ces.traineddata
    if [ "$(git hash-object "$TESSDATA/ces.traineddata.part")" != dd6fc79a62f9fcd1c7c6da06b31bb4fdb10dc173 ]; then
        rm -f "$TESSDATA/ces.traineddata.part"
        echo "The Czech data didn't match its expected hash; not installed." >&2
        exit 1
    fi
    mv "$TESSDATA/ces.traineddata.part" "$TESSDATA/ces.traineddata"
fi

DEST="$HOME/Library/Application Support/CzGram"
echo "==> Installing CzGram to $DEST"
rm -rf "$DEST/lib" "$DEST/extension"
mkdir -p "$DEST/lib/czgram"
cp czgram/*.py "$DEST/lib/czgram/"
# The browser connector must run with Homebrew's Python, not the system stub.
sed -i '' "1s|.*|#!$PY|" "$DEST/lib/czgram/nmhost.py"
chmod 755 "$DEST/lib/czgram/nmhost.py"
cp -R extension "$DEST/extension"
"$PY" -m compileall -q "$DEST/lib"

cat > "$BREW/bin/czgram" <<EOF
#!/bin/sh
export PATH="$BREW/bin:\$PATH"
PYTHONPATH="$DEST/lib" exec "$PY" -m czgram "\$@"
EOF
chmod 755 "$BREW/bin/czgram"

APP="$HOME/Applications/CzGram.app"
echo "==> Creating $APP"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cat > "$APP/Contents/MacOS/CzGram" <<EOF
#!/bin/sh
exec "$BREW/bin/czgram" "\$@"
EOF
chmod 755 "$APP/Contents/MacOS/CzGram"
VERSION=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' czgram/__init__.py)
cat > "$APP/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>CzGram</string>
  <key>CFBundleDisplayName</key><string>CzGram</string>
  <key>CFBundleIdentifier</key><string>cz.czgram.app</string>
  <key>CFBundleExecutable</key><string>CzGram</string>
  <key>CFBundleIconFile</key><string>czgram</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>$VERSION</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
</dict></plist>
EOF

# App icon: the mascot, drawn at 1024 px and turned into an .icns.
ICONSET=$(mktemp -d)/czgram.iconset
mkdir -p "$ICONSET"
"$PY" - "$ICONSET/icon_512x512@2x.png" <<'EOF'
import sys
from PIL import Image, ImageDraw
im = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
d.rounded_rectangle((64, 64, 960, 960), radius=200, fill="#262321")
cell, ox, oy = 52, 122, 200
def rect(x, y, w, h, c):
    d.rectangle((ox + x * cell, oy + y * cell, ox + (x + w) * cell - 1, oy + (y + h) * cell - 1), fill=c)
rect(3, 3, 9, 6, "#D97757"); rect(1, 5, 2, 2, "#D97757"); rect(12, 5, 2, 2, "#D97757")
for x in (4, 6, 8, 10):
    rect(x, 9, 1, 2, "#B95F42")
rect(5, 4, 1, 2, "#1F1E1D"); rect(9, 4, 1, 2, "#1F1E1D")
im.save(sys.argv[1])
EOF
for s in 16 32 128 256 512; do
    sips -z $s $s "$ICONSET/icon_512x512@2x.png" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
    sips -z $((s * 2)) $((s * 2)) "$ICONSET/icon_512x512@2x.png" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/czgram.icns"
rm -rf "$(dirname "$ICONSET")"

echo
echo "CzGram $VERSION is installed. Open it from ~/Applications or run: czgram"
echo "Then allow it under System Settings → Privacy & Security:"
echo "  - Screen Recording, so it can read the screen"
echo "  - Accessibility, only for the Selected word (manual) mode"
