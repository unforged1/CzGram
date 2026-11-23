"""Writes czgram.ico: the mascot from packaging/build_deb.sh, drawn at 256 px and scaled down."""
import sys

from PIL import Image, ImageDraw

SCALE = 4  # the Debian icon is 64 px; Windows wants up to 256
im = Image.new("RGBA", (64 * SCALE, 64 * SCALE), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
cell, body, shade, dark = 4 * SCALE, "#D97757", "#B95F42", "#1F1E1D"


def rect(x, y, w, h, c):
    d.rectangle((x * cell + 2 * SCALE, y * cell + 4 * SCALE,
                 (x + w) * cell + 2 * SCALE - 1, (y + h) * cell + 4 * SCALE - 1), fill=c)


rect(3, 3, 9, 6, body)
rect(1, 5, 2, 2, body)
rect(12, 5, 2, 2, body)
for x in (4, 6, 8, 10):
    rect(x, 9, 1, 2, shade)
rect(5, 4, 1, 2, dark)
rect(9, 4, 1, 2, dark)
im.save(sys.argv[1], sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (256, 256)])
