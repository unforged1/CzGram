"""End-to-end checks for macOS CI: OCR on a rendered exercise, the hotkeys, and the settings window."""
import sys

from PIL import Image, ImageDraw, ImageFont

from czgram import analyze, capture, ocr

ok = True

# 1. OCR + rules on a rendered page, with a font every Mac has.
font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 22)
img = Image.new("L", (900, 200), 250)
d = ImageDraw.Draw(img)
d.text((40, 40), "Musíme b_dlet v (P/p)raze.", fill=20, font=font)
d.text((40, 100), "Vrátil se (z/ze) školy.", fill=20, font=font)
print("tesseract:", ocr.status())
lines = ocr.run(capture.upscale_pgm(capture._pgm(img.width, img.height, img.tobytes()))).lines
found = {(i["snippet"], i["suggest"]) for i in analyze.analyze(lines)}
print("ocr lines:", lines)
print("found:", sorted(found))
for want in (("b_dlet", "y"), ("(P/p)raze", "P"), ("(z/ze)", "ze")):
    if want not in found:
        print("MISSING", want)
        ok = False

# 2. Global hotkeys register through Carbon.
from czgram import macos
lib, refs, _cb = macos.register_hotkeys(lambda: None)
print("hotkeys registered:", len(refs))
for ref in refs:
    lib.UnregisterEventHotKey(ref)

# 3. The settings window builds and names the Mac shortcut.
from czgram import ui_config
win = ui_config.ConfigWindow()
win._mac_key_names(win.root)
win.root.update()
texts = []
def walk(w):
    for c in w.winfo_children():
        try:
            texts.append(str(c.cget("text")))
        except Exception:
            pass
        walk(c)
walk(win.root)
joined = " ".join(texts)
print("settings window:", win.root.winfo_width(), "x", win.root.winfo_height())
if "PrintScreen" in joined or "⌃⌥G" not in joined:
    print("KEY NAMES WRONG")
    ok = False
win.root.destroy()

# 4. A real screenshot (works only if the runner allows screen capture).
try:
    pgm = capture.capture()
    print("screenshot:", capture._pgm_header(pgm)[:2])
except capture.CaptureError as e:
    print("screenshot unavailable here:", e)

sys.exit(0 if ok else 1)
