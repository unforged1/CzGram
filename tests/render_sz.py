"""Measures OCR on s/z/vz, z/ze and s/se exercises across fonts, sizes and themes.

Usage: python3 tests/render_sz.py
Prints each line Tesseract got wrong, and a score per setup.
"""
import glob
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from czgram import capture, ocr  # noqa: E402

LINES = [
    "Doplňte předpony a předložky:",
    "Musíme (s/z)míchat těsto.",
    "Květiny (s/z/vz)kvétají na jaře.",
    "Letadlo s/z/vz létlo vysoko.",
    "Vrátil se (z/ze) školy pozdě.",
    "Šel do kina (s/se) sestrou.",
    "Přišla z/ze zahrady.",
    "Mluvil s/se mnou včera.",
    "Vzal to s/z poličky.",
    "Musel ___ běhnout dolů.",
    "Led _mrzl přes noc.",
    "Přišel _e školy.",
    "Šli _e sestrou domů.",
]
FONTS = ["DejaVuSans", "LiberationSans-Regular", "NotoSans-Regular", "LiberationSerif-Regular"]
if os.name == "nt":
    # The closest Windows fonts: a humanist sans, two grotesques and a serif.
    FONTS = ["segoeui", "arial", "calibri", "times"]


def find_font(name):
    if os.name == "nt":
        path = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", name + ".ttf")
        return path if os.path.exists(path) else None
    hits = glob.glob("/usr/share/fonts/**/%s.ttf" % name, recursive=True)
    return hits[0] if hits else None


def render(font_path, size, dark):
    fg, bg = (225, 30) if dark else (20, 250)
    img = Image.new("L", (1366, 768), bg)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, size)
    y = 70
    for line in LINES:
        draw.text((180, y), line, fill=fg, font=font)
        y += size + 18
    return capture._pgm(img.width, img.height, img.tobytes())


def targets(lines):
    """(snippet, suggestion) for every exercise target the analyzer finds."""
    from czgram.analyze import analyze
    return {(i["snippet"], i["suggest"]) for i in analyze(lines, limit=50) if i["kind"] == "gap"}


def main():
    want = targets(LINES)
    total = good = exact_lines = line_total = 0
    misses = {}
    for name in FONTS:
        path = find_font(name)
        if not path:
            continue
        for size in (13, 15, 18, 22):
            for dark in (False, True):
                for upscale in (True, False):
                    pgm = render(path, size, dark)
                    if upscale:
                        pgm = capture.upscale_pgm(pgm)
                    lines = ocr.run(pgm).lines
                    got = targets(lines)
                    total += len(want)
                    good += len(want & got)
                    for miss in want - got:
                        misses[miss] = misses.get(miss, 0) + 1
                    line_total += len(LINES)
                    exact_lines += len(set(LINES) & set(lines))
    print("exercise targets found with the right suggestion: %d of %d (%.1f%%)" % (good, total, 100 * good / total))
    print("lines read letter for letter: %d of %d (%.1f%%)" % (exact_lines, line_total, 100 * exact_lines / line_total))
    if "-v" in sys.argv:
        for (snippet, suggest), n in sorted(misses.items(), key=lambda kv: -kv[1]):
            print("  missed %2d×  %r -> %r" % (n, snippet, suggest))


if __name__ == "__main__":
    main()
