"""Render an exercise screenshot with Pillow, as a browser or worksheet would show it."""
import sys
from PIL import Image, ImageDraw, ImageFont

LINES = ["Pracovní list: český jazyk", "",
         "1. Doplňte i/y: Maminka b_dlí v malém městě.",
         "2. Na stole leží m_š a voní tam s_r.",
         "3. Kluci běhal_ po hřišti celý den.",
         "4. Mluví o (mě/mně) a o tobě.",
         "5. Vidím ____ psa na zahradě.",
         "6. Který pád je ve větě použit?"]
out, dark = sys.argv[1], "--dark" in sys.argv
size = 15
for a in sys.argv[2:]:
    if a.startswith("--size="):
        size = int(a[7:])
W, H = 1366, 768
fg, bg = (225, 30) if dark else (20, 250)
img = Image.new("L", (W, H), bg)
d = ImageDraw.Draw(img)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
y = 120
for line in LINES:
    d.text((180, y), line, fill=fg, font=font)
    y += size + 16
# Underlined link: must NOT read as a gap.
d.text((180, y), "Zpět na stránku kurzu", fill=fg, font=font)
w = d.textlength("Zpět na stránku kurzu", font=font)
d.line((180, y + size + 2, 180 + w, y + size + 2), fill=fg, width=1)
img.save(out)
