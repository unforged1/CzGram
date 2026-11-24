"""End-to-end check on a real Windows desktop (the windows CI job). Exits non-zero on failure.

Covers what the unit tests can't: the screenshot, Tesseract with the downloaded Czech data,
the PrintScreen listener, the bar and its pipe, copying the selection, the settings window,
saving settings (Snipping Tool option, sign-in entry, browser registration) and the native host
started through its .bat as a browser would start it.
"""
import json
import os
import struct
import subprocess
import sys
import threading
import time
import tkinter as tk

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from czgram import bridge, capture, config, install, ipc, ocr, scan, shortcuts, windows  # noqa: E402

failures = []


def check(name, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (": " + str(detail)) if detail else ""), flush=True)
    if not ok:
        failures.append(name)


def wait_for(pred, seconds):
    end = time.time() + seconds
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.1)
    return False


def screenshot_and_ocr():
    pgm = capture.capture()
    w, h, _ = capture._pgm_header(pgm)
    check("screenshot", w > 100 and h > 100, "%dx%d" % (w, h))
    ok, msg = ocr.status()
    check("Tesseract with Czech data", ok, msg)
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("L", (1200, 300), 250)
    font = ImageFont.truetype(os.path.join(os.environ["WINDIR"], "Fonts", "segoeui.ttf"), 32)
    ImageDraw.Draw(img).text((40, 100), "Doplň: Maminka b_dlí doma. Vidím (mě/mně) v zrcadle.",
                             fill=20, font=font)
    res = ocr.run(capture._pgm(img.width, img.height, img.tobytes()))
    text = " ".join(res.lines)
    check("OCR reads Czech", "Maminka" in text and "doma" in text,
          "%r ok=%s reason=%r conf=%.0f" % (text[:120], res.ok, res.reason, res.mean_conf))
    if "Maminka" not in text:
        # Diagnosis: the same image through a file and through stdin, straight from Tesseract.
        exe, extra = ocr._tesseract()
        png = os.path.join(config.runtime_dir(), "diag.png")
        img.save(png)
        pgm = capture._pgm(img.width, img.height, img.tobytes())
        for label, cmd, data in (("file", [exe, png, "stdout"] + extra + ["-l", "ces"], None),
                                 ("stdin", [exe, "stdin", "stdout"] + extra + ["-l", "ces"], pgm)):
            r = subprocess.run(cmd, input=data, capture_output=True, timeout=60)
            print("DIAG %s rc=%d out=%r err=%r" % (label, r.returncode, r.stdout[:200], r.stderr[-300:]))
    path = os.path.join(config.runtime_dir(), "smoke.png")
    img.save(path)
    out = subprocess.run([sys.executable, "-m", "czgram", "--scan-file", path], cwd=REPO,
                         capture_output=True, text=True, timeout=120)
    events = [json.loads(line) for line in out.stdout.splitlines() if line.strip()]
    items = next((e.get("items", []) for e in events if e.get("event") == "result"), [])
    check("scan finds the gaps", any("b_dl" in i.get("snippet", "") for i in items),
          [i.get("snippet") for i in items])


def selection_copy():
    root = tk.Tk()
    entry = tk.Entry(root, width=40)
    entry.pack()
    entry.insert(0, "vyjmenovaná slova")
    root.update()
    root.lift()
    root.attributes("-topmost", True)
    root.focus_force()
    entry.focus_set()
    entry.select_range(0, "end")
    windows.set_clipboard_text("before")
    result = []

    def worker():
        time.sleep(0.8)
        result.append(windows.read_selection())
        root.after(0, root.destroy)

    threading.Thread(target=worker, daemon=True).start()
    root.mainloop()
    check("selection is copied", result == ["vyjmenovaná slova"], result)
    check("clipboard is put back", windows.get_clipboard_text() == "before", windows.get_clipboard_text())


def settings_window():
    from czgram import ui_config
    win = ui_config.ConfigWindow()
    win.root.after(1500, win.root.destroy)
    win.run()
    check("settings window opens", True)


def save_settings_and_hotkey():
    cfg = dict(config.DEFAULTS)
    config.save(cfg)
    results = install.apply(cfg)
    check("settings apply", all(ok for ok, _ in results), results)
    import winreg
    check("sign-in entry", windows._reg_get(winreg.HKEY_CURRENT_USER, windows.RUN_KEY, windows.RUN_VALUE) is not None)
    check("Snipping Tool option off", windows._reg_get(winreg.HKEY_CURRENT_USER, windows.SNIP_KEY,
                                                        windows.SNIP_VALUE) == 0)
    check("hotkey listener running", wait_for(lambda: os.path.exists(windows.pid_path()), 5))
    for key in windows.HOST_KEYS["chromium"] + windows.HOST_KEYS["firefox"]:
        manifest = windows._reg_get(winreg.HKEY_CURRENT_USER, key + "\\" + windows.HOST_NAME, "")
        check("browser registration " + key.split("\\")[1], manifest and os.path.exists(manifest), manifest)

    # PrintScreen, pressed for real: the listener starts the bar, which scans.
    u = windows._user32()
    u.keybd_event(0x2C, 0, 0, None)
    u.keybd_event(0x2C, 0, 2, None)
    check("PrintScreen starts the bar", wait_for(lambda: os.path.exists(config.ui_socket()), 20))
    check("bar answers on its pipe", wait_for(lambda: ipc.send("reload"), 5))
    check("a second press reaches the running bar", ipc.send("scan"))
    time.sleep(3)
    check("bar quits on request", ipc.send("quit"))
    check("bar removed its pipe file", wait_for(lambda: not os.path.exists(config.ui_socket()), 10))

    ok, msg = shortcuts.restore()
    check("restore", ok, msg)
    check("sign-in entry removed", windows._reg_get(winreg.HKEY_CURRENT_USER, windows.RUN_KEY,
                                                     windows.RUN_VALUE) is None)
    check("hotkey listener stopped", not os.path.exists(windows.pid_path()))


def native_host_bat():
    """Starts the host through its .bat, exactly as Chrome would, and asks for a page."""
    bat = os.path.join(windows.local_dir(), "native-host", "czgram-bridge.bat")
    check("native host .bat", os.path.exists(bat), bat)
    proc = subprocess.Popen(["cmd.exe", "/d", "/c", bat, "chrome-extension://x/"], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE)
    try:
        check("host registers", wait_for(bridge.connected, 10))

        requests = []

        def browser(count):
            for _ in range(count):
                head = proc.stdout.read(4)
                msg = json.loads(proc.stdout.read(struct.unpack("=I", head)[0]))
                requests.append(msg)
                data = json.dumps({"id": msg["id"], "url": "https://example.cz/\n", "title": "T",
                                   "frames": []}).encode()
                proc.stdin.write(struct.pack("=I", len(data)) + data)
                proc.stdin.flush()

        threading.Thread(target=browser, args=(2,), daemon=True).start()
        reply = bridge.read_page(timeout=5)
        # The newline would come back as \r\n if the host's stdio weren't in binary mode.
        check("page through the host", reply.get("url") == "https://example.cz/\n", reply)
        reply = bridge.read_page(timeout=5, full=True, armed=True, key="Shift")
        last = requests[-1] if requests else {}
        check("bulk request reaches the browser", reply.get("url") and last.get("full") is True
              and last.get("armed") is True and last.get("key") == "Shift", last)
    finally:
        proc.stdin.close()
        proc.wait(timeout=10)
    check("host cleans up", wait_for(lambda: not bridge.connected(), 5))


def main():
    for step in (screenshot_and_ocr, selection_copy, settings_window, save_settings_and_hotkey,
                 native_host_bat):
        try:
            step()
        except Exception as e:  # noqa: BLE001  report and go on to the next step
            import traceback
            traceback.print_exc()
            check(step.__name__, False, e)
    print("\n%d failure(s)" % len(failures), flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
