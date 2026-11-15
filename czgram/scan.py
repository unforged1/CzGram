"""One scan, run as a short-lived child process of the bar.

Prints JSON lines on stdout: {"event":"captured"} once the screen has been read
(the bar waits for this so it doesn't photograph itself), then {"event":"result"}.
Keeping this separate means the image and OCR memory go back to the OS on exit.
"""
import json
import sys

from . import config
from .macos import key_text


def emit(**msg):
    print(json.dumps(msg, ensure_ascii=False), flush=True)


def read_screenshot(cfg, image_path=None):
    """Returns (lines, error). Always emits "captured", even when capture fails."""
    from . import capture, ocr
    try:
        if image_path:
            with open(image_path, "rb") as f:
                head = f.read(2)
            if head == b"P5":
                with open(image_path, "rb") as f:
                    pgm = f.read()
            else:
                pgm = capture._png_to_pgm(image_path)
        else:
            pgm = capture.capture()
    except (capture.CaptureError, OSError, ImportError) as e:
        emit(event="captured")
        return [], str(e)
    emit(event="captured")
    if not cfg["low_ram"]:
        try:
            pgm = capture.upscale_pgm(pgm)
        except ImportError:
            pass
    result = ocr.run(pgm)
    del pgm
    return result.lines, (None if result.ok else result.reason)


def read_page():
    from . import bridge
    res = bridge.snapshot()
    return res.lines, (res.error or None)


def scan(cfg, image_path=None):
    from .analyze import analyze
    lang = cfg["language"]
    notice, source, items = "", "", []

    if cfg["detection"] == "html" and not image_path:
        emit(event="captured")
        lines, err = read_page()
        source = "page code"
        if not err:
            items = analyze(lines, lang)
        else:
            notice = "Page code unavailable: %s. Used the screenshot instead." % err
            lines, err2 = read_screenshot_after_captured(cfg)
            source = "screenshot"
            if err2:
                notice = "Couldn't read the page code (%s) or the screenshot (%s)." % (err, err2)
            else:
                items = analyze(lines, lang)
    else:
        lines, err = read_screenshot(cfg, image_path)
        source = "screenshot"
        if not err:
            items = analyze(lines, lang)
        # A screenshot that can't be read switches to page code. So does one with no
        # targets: gaps made of form fields are invisible to OCR but plain in the HTML.
        if (err or not items) and cfg["auto_fallback"] and not image_path:
            page_lines, page_err = read_page()
            if not page_err:
                page_items = analyze(page_lines, lang)
                if page_items or err:
                    items, source = page_items, "page code"
                    if err:
                        notice = "Screenshot unreadable (%s), switched to page code." % err
                    err = None
            elif err:
                notice = "Couldn't read the screenshot (%s) or the page code (%s)." % (err, page_err)
                err = None
        if err:
            notice = "Couldn't read the screenshot: %s." % err
    emit(event="result", source=source, notice=notice, items=items)


def read_selection(cfg, primary):
    """Manual mode: the highlighted text. Takes no screenshot."""
    from . import bridge
    from .analyze import describe_selection
    from .htmlread import find_selection
    emit(event="captured")
    lang = cfg["language"]
    primary = " ".join(primary.split())
    reply = bridge.read_page() if bridge.connected() else {}
    in_browser, context = "", ""
    for frame in reply.get("frames", []):
        in_browser, context = find_selection(frame)
        if in_browser:
            break
    # The system selection is the newest thing selected anywhere, so it wins. The browser
    # can only add the surrounding sentence if it's talking about the same text.
    text = primary or in_browser
    if text != in_browser:
        context = ""
    items = describe_selection(text, lang, context, reply.get("title", "") if not primary or text == in_browser else "")
    if items:
        emit(event="result", source="selected text", notice="", items=items)
    else:
        emit(event="result", source="", notice="", items=[],
             empty_title="Nothing selected",
             empty_text=key_text("Highlight a word with the mouse, then press PrintScreen."))


def read_screenshot_after_captured(cfg):
    """Screenshot fallback from HTML mode. The bar is up by now, so hide it first."""
    emit(event="hide")
    import time
    time.sleep(0.25)
    lines, err = read_screenshot(cfg)
    return lines, err


def main(argv):
    cfg = config.load()
    image = argv[0] if argv and argv[0] != "--manual" else None
    try:
        if argv and argv[0] == "--manual":
            read_selection(cfg, sys.stdin.read())
        else:
            scan(cfg, image)
    except Exception as e:  # the bar must always get an answer
        emit(event="result", source="", notice="Scan failed: %s" % e, items=[])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
