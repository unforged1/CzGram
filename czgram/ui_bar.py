"""The small bar at the top of the screen. Single-threaded: Tk file handlers drive everything."""
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tkinter as tk

from . import config, speed

BG = "#1F1E1D"
PANEL = "#2B2A28"
FG = "#F4F1EA"
MUTED = "#A8A29A"
ACCENT = "#D97757"
HINT = "#E8B48F"
FONT = "DejaVu Sans"
MAX_TEXT_LINES = 9
CHARS_PER_TICK = 7  # at 8 ticks a second: quick to read but visibly "spoken"
QUICK_CHARS_PER_TICK = 40  # quick mode is about getting the answer now
THEME_NORMAL = {"bg": BG, "panel": PANEL, "fg": FG, "muted": MUTED, "accent": ACCENT, "hint": HINT}
THEME_SPEED = {"bg": "#0B1830", "panel": "#14294D", "fg": "#EAF6FF", "muted": "#8FB2D9",
               "accent": "#4FA8FF", "hint": "#9AD8FF"}
PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Child:
    """A child process whose stdout JSON lines arrive through a Tk file handler."""

    def __init__(self, root, args, on_message, on_exit, stdin_data=None):
        self.root, self.on_message, self.on_exit = root, on_message, on_exit
        self.buf = b""
        self.proc = subprocess.Popen(
            [sys.executable, "-m"] + args, stdout=subprocess.PIPE, cwd=PKG_DIR,
            stdin=subprocess.PIPE if stdin_data else subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
        if stdin_data:
            self.proc.stdin.write(stdin_data)
            self.proc.stdin.close()
        self.fd = self.proc.stdout.fileno()
        root.createfilehandler(self.fd, tk.READABLE, self._readable)

    def _readable(self, _fd, _mask):
        data = os.read(self.fd, 65536)
        if not data:
            self.close()
            self.on_exit()
            return
        self.buf += data
        *lines, self.buf = self.buf.split(b"\n")
        for line in lines:
            try:
                self.on_message(json.loads(line))
            except ValueError:
                pass

    def close(self):
        if self.proc is None:
            return
        self.root.deletefilehandler(self.fd)
        self.proc.stdout.close()
        if self.proc.poll() is None:
            self.proc.terminate()
        self.proc.wait()
        self.proc = None


class Bar:
    def __init__(self):
        self.cfg = config.load()
        self.items, self.index = [], 0
        self.scan = self.ai = self.watch = None
        self.pending = ""      # text still to be "spoken"
        self.ai_cache = {}
        self.ai_started = False
        self.visible = False
        self.mascot = None
        self.colors = THEME_NORMAL
        self.reported = None   # for model "default": what Claude said it's using
        self.reported_for = None
        self.notice_base = ""

        self.root = tk.Tk(className="czgram")
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=ACCENT)
        self._build()
        self._listen()
        signal.signal(signal.SIGTERM, lambda *_: self.quit())

    # ---------------------------------------------------------- layout

    def _build(self):
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True, padx=0, pady=(0, 2))  # accent line along the bottom
        head = tk.Frame(outer, bg=BG)
        head.pack(fill="x", padx=8, pady=(6, 2))

        self.canvas = None
        self.mascot_box = tk.Frame(head, bg=BG)
        self.mascot_box.pack(side="left", padx=(0, 8))

        right = tk.Frame(head, bg=BG)
        right.pack(side="right", anchor="n")
        self.prev_btn = self._button(right, "◀", lambda: self.step(-1))
        self.count = tk.Label(right, bg=BG, fg=MUTED, font=(FONT, 9))
        self.next_btn = self._button(right, "▶", lambda: self.step(1))
        self.settings_btn = self._button(right, "⚙", self.open_settings)
        self.close_btn = self._button(right, "✕", self.dismiss)
        self.settings_btn.pack(side="left")
        self.close_btn.pack(side="left")

        info = tk.Frame(head, bg=BG)
        info.pack(side="left", fill="x", expand=True)
        self.title = tk.Label(info, bg=BG, fg=FG, font=(FONT, 11, "bold"), anchor="w", justify="left")
        self.title.pack(fill="x")
        self.snippet = tk.Label(info, bg=BG, fg=ACCENT, font=(FONT, 10), anchor="w", justify="left")
        self.snippet.pack(fill="x")
        self.hint = tk.Label(info, bg=BG, fg=HINT, font=(FONT, 10, "bold"), anchor="w", justify="left")

        self.text = tk.Text(outer, bg=PANEL, fg=FG, font=(FONT, 10), wrap="word", height=1, bd=0,
                            highlightthickness=0, padx=10, pady=6, cursor="arrow", spacing1=1)
        self.text.configure(state="disabled")
        self.text.bind("<Button-1>", lambda _e: self.finish_speaking())
        self.notice = tk.Label(outer, bg=BG, fg=MUTED, font=(FONT, 8), anchor="w", justify="left")
        self.root.bind("<Escape>", lambda _e: self.dismiss())

    def _button(self, parent, text, command):
        b = tk.Label(parent, text=text, bg=BG, fg=MUTED, font=(FONT, 11), padx=5, cursor="hand2")
        b.bind("<Button-1>", lambda _e: command())
        b.bind("<Enter>", lambda _e: b.configure(fg=self.colors["fg"]))
        b.bind("<Leave>", lambda _e: b.configure(fg=self.colors["muted"]))
        return b

    def _ensure_mascot(self):
        """The canvas exists only while the mascot option is on."""
        if self.cfg["mascot"] and self.canvas is None:
            from .mascot import HEIGHT, WIDTH, Mascot
            self.canvas = tk.Canvas(self.mascot_box, width=WIDTH, height=HEIGHT, bg=self.colors["bg"],
                                    highlightthickness=0, cursor="hand2")
            self.canvas.pack()
            self.canvas.bind("<Button-1>", lambda _e: self.finish_speaking())
            self.mascot = Mascot(self.canvas, on_tick=self._speak_tick)
            self.mascot.running = self.colors is THEME_SPEED
        elif not self.cfg["mascot"] and self.canvas is not None:
            self.mascot.stop()
            self.canvas.destroy()
            self.canvas = self.mascot = None

    def _update_speed(self):
        """Switches the blue look on or off to match the model in use."""
        # A report only describes the setup it came from.
        setup = (self.cfg["claude_backend"], self.cfg["code_model"])
        if setup != self.reported_for:
            self.reported, self.reported_for = None, setup
        new = THEME_SPEED if speed.should_run(self.cfg, self.reported) else THEME_NORMAL
        if new is self.colors:
            return
        old, self.colors = self.colors, new
        swap = {old[k].lower(): new[k] for k in old}
        stack = [self.root]
        while stack:
            widget = stack.pop()
            stack.extend(widget.winfo_children())
            for option in ("bg", "fg"):
                try:
                    value = str(widget.cget(option)).lower()
                except tk.TclError:
                    continue
                if value in swap:
                    widget.configure({option: swap[value]})
        if self.mascot:
            self.mascot.set_running(new is THEME_SPEED)

    def _fast_text(self):
        return self.watch is not None or self.colors is THEME_SPEED

    def _width(self):
        return min(760, int(self._screen()[2] * 0.8))

    def _screen(self):
        """(x, y, width, height) of the primary monitor, under XWayland too."""
        if shutil.which("xrandr"):
            try:
                out = subprocess.run(["xrandr", "--query"], capture_output=True, text=True,
                                     timeout=2).stdout
                fallback = None
                for line in out.splitlines():
                    if " connected" not in line:
                        continue
                    for word in line.split():
                        if "+" in word and "x" in word:
                            size, x, y = word.split("+")
                            w, h = size.split("x")
                            geo = (int(x), int(y), int(w), int(h))
                            if " primary " in line:
                                return geo
                            fallback = fallback or geo
                if fallback:
                    return fallback
            except (OSError, subprocess.SubprocessError, ValueError):
                pass
        return 0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight()

    def _place(self):
        self.root.update_idletasks()
        x0, y0, sw, _sh = self._screen_cached
        w = self._width()
        wrap = w - 150 - (70 if self.canvas else 0)
        for label in (self.title, self.snippet, self.hint):
            label.configure(wraplength=wrap)
        self.notice.configure(wraplength=w - 20)
        self.root.update_idletasks()
        h = self.root.winfo_reqheight()
        self.root.geometry("%dx%d+%d+%d" % (w, h, x0 + (sw - w) // 2, y0))

    # ---------------------------------------------------------- scanning

    def start_scan(self):
        if self.scan is not None:
            return  # one at a time; a second press during a scan is ignored
        self.cfg = config.load()
        self._update_speed()
        if self.cfg["quick_mode"] and self.cfg["detection"] != "manual":
            # PrintScreen is the on/off switch. Page code only: no screenshot is taken.
            if self.watch is not None:
                self.dismiss()
            else:
                self.start_watch()
            return
        self._stop_watch()
        self.ai_cache = {}
        self._stop_ai()
        self.hide()
        self.root.update()
        # Let the compositor drop the bar so it isn't in the screenshot.
        self.root.after(150, self._spawn_scan)

    def _spawn_scan(self):
        if self.cfg["detection"] == "manual":
            self.scan = Child(self.root, ["czgram.scan", "--manual"], self._on_scan_message,
                              self._on_scan_exit, self._read_primary().encode("utf-8"))
        else:
            self.scan = Child(self.root, ["czgram.scan"], self._on_scan_message, self._on_scan_exit)

    def _read_primary(self):
        """The system's current selection, whichever app holds it. Empty if there is none."""
        for kind in ("UTF8_STRING", "STRING"):
            try:
                return self.root.selection_get(selection="PRIMARY", type=kind)[:500]
            except tk.TclError:
                pass
        return ""

    def _on_scan_message(self, msg):
        event = msg.get("event")
        if event == "captured":
            self.show_reading()
        elif event == "hide":
            self.hide()
            self.root.update()
        elif event == "result":
            self.show_result(msg)

    def _on_scan_exit(self):
        self.scan = None

    # ---------------------------------------------------------- quick mode

    def start_watch(self):
        self._stop_ai()
        self.ai_cache = {}
        self.show_reading()
        self.title.configure(text="Quick mode")
        self.snippet.configure(text="Waiting for a question…")
        if self.mascot:
            self.mascot.rest = "busy"
            self.mascot.set_state("busy")
        self._place()
        self.watch = Child(self.root, ["czgram.watch"], self._on_watch_message, self._on_watch_exit)

    def _on_watch_message(self, msg):
        if msg.get("event") == "result":
            self.show_result(msg)
        elif msg.get("event") == "status":
            text = msg.get("message", "")
            if text.startswith("Waiting"):
                self._set_notice("")
            else:
                self._set_notice("Quick mode: %s" % text)
            self._place()

    def _on_watch_exit(self):
        self.watch = None
        if self.visible:
            self._set_notice("Quick mode stopped unexpectedly. Press PrintScreen to start it again.")
            if self.mascot:
                self.mascot.rest = "idle"
                self.mascot.set_state("sad")
            self._place()

    def _stop_watch(self):
        if self.watch is not None:
            self.watch.close()
            self.watch = None
        if self.mascot:
            self.mascot.rest = "idle"

    def show_reading(self):
        self._ensure_mascot()
        self.items = []
        self.title.configure(text="Reading the screen…")
        self.snippet.configure(text="")
        self.hint.pack_forget()
        self.text.pack_forget()
        self.notice.pack_forget()
        for w in (self.prev_btn, self.count, self.next_btn):
            w.pack_forget()
        self.show()
        if self.mascot:
            self.mascot.set_state("think")

    def show_result(self, msg):
        self._ensure_mascot()
        self.items, self.index = msg.get("items", []), 0
        self.source = msg.get("source", "")
        note = msg.get("notice", "")
        if not self.visible:
            self.show()
        if self.items:
            source_text = "Read from: %s" % self.source if self.source else ""
            self.notice_base = " · ".join(x for x in (note, source_text) if x)
            self._set_notice(self.notice_base)
            self.show_item()
        else:
            self.title.configure(text=msg.get("empty_title") or (
                "No grammar exercise found" if not note else "Couldn't read this"))
            self.snippet.configure(text=msg.get("empty_text") or (
                "Nothing that looks like a Czech gap or question is on screen." if not note else ""))
            self.hint.pack_forget()
            self.text.pack_forget()
            self._set_notice(note)
            if self.mascot:
                self.mascot.set_state("sad")
            self._place()

    def _set_notice(self, text):
        self.notice.pack_forget()
        if text:
            self.notice.configure(text=text)
            self.notice.pack(fill="x", padx=10, pady=(2, 2))

    def show_item(self):
        self._stop_ai()
        item = self.items[self.index]
        self.title.configure(text=item["title"])
        context = item.get("context")
        self.snippet.configure(text=_shorten(item["snippet"] + (" · " + context if context else "")))
        cached = self.ai_cache.get((item["snippet"], item["line"]))
        if item.get("hint") and not cached:
            self.hint.configure(text=item["hint"])
            self.hint.pack(fill="x")
        else:
            self.hint.pack_forget()

        many = len(self.items) > 1
        for w in (self.prev_btn, self.count, self.next_btn):
            w.pack_forget()
        if many:
            self.count.configure(text="%d/%d" % (self.index + 1, len(self.items)))
            self.prev_btn.pack(side="left", before=self.settings_btn)
            self.count.pack(side="left", before=self.settings_btn)
            self.next_btn.pack(side="left", before=self.settings_btn)

        self.text.pack(fill="x", padx=8, pady=(2, 6), before=self.notice if self.notice.winfo_manager() else None)
        self._clear_text()
        self.say(cached or item["text"])
        if self.cfg["use_claude"] and not cached:
            self._start_ai(item)

    def step(self, delta):
        if self.items:
            self.index = (self.index + delta) % len(self.items)
            self.show_item()

    # ---------------------------------------------------------- explanation text

    def _clear_text(self):
        self.pending = ""
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled", height=1)
        if self.visible:
            self._place()  # shrink at once, or a long previous text leaves empty space

    def say(self, text):
        if self.mascot:
            self.pending += text
            self.mascot.set_state("talk")
        else:
            self._append(text)
        self._fit_text()

    def _append(self, text):
        self.text.configure(state="normal")
        self.text.insert("end", text)
        self.text.configure(state="disabled")

    def _speak_tick(self):
        if not self.pending:
            return
        size = QUICK_CHARS_PER_TICK if self._fast_text() else CHARS_PER_TICK
        chunk, self.pending = self.pending[:size], self.pending[size:]
        self._append(chunk)
        self._fit_text()
        if not self.pending and self.ai is None:
            self.mascot.set_state("wave")

    def finish_speaking(self):
        if self.pending:
            self._append(self.pending)
            self.pending = ""
            self._fit_text()
            if self.mascot and self.ai is None:
                self.mascot.set_state("wave")

    def _fit_text(self):
        self.root.update_idletasks()
        lines = self.text.count("1.0", "end", "displaylines")
        count = lines[0] if isinstance(lines, tuple) else (lines or 1)
        height = max(1, min(MAX_TEXT_LINES, count))
        if int(self.text.cget("height")) != height:
            self.text.configure(height=height)
            self._place()
        self.text.see("end")

    # ---------------------------------------------------------- Claude

    def _start_ai(self, item):
        self.ai_started = False
        self.ai_text = ""
        self.ai_key = (item["snippet"], item["line"])
        payload = json.dumps({"snippet": item["snippet"], "line": item["line"],
                              "options": item.get("options", []),
                              "context": item.get("context", ""),
                              "selected": item.get("selected", False),
                              "exercise": item.get("exercise", "")}).encode()
        self.ai = Child(self.root, ["czgram.ai"], self._on_ai_message, self._on_ai_exit, payload)
        if self.mascot and not self.pending:
            self.mascot.set_state("think")

    def _on_ai_message(self, msg):
        if "model" in msg:
            self.reported = msg["model"]
            self._update_speed()
        elif "tokens" in msg:
            self._show_tokens(msg["tokens"])
        elif "text" in msg:
            if not self.ai_started:
                # The first real words replace the offline rule.
                self.ai_started = True
                self._clear_text()
                # Its answer replaces the offline guess, so the two can't disagree on screen.
                self.hint.pack_forget()
                self._place()
            self.ai_text += msg["text"]
            self.say(msg["text"])
        elif "error" in msg:
            self._set_notice(msg["error"])
            self._place()
        elif msg.get("done"):
            self.ai_cache[self.ai_key] = self.ai_text

    def _show_tokens(self, tokens):
        from .usage import short
        text = "%s tokens" % short(tokens["this"])
        if tokens.get("today") is not None:
            text += " (%s today)" % short(tokens["today"])
        self._set_notice(" · ".join(x for x in (self.notice_base, text) if x))
        self._place()

    def _on_ai_exit(self):
        self.ai = None
        if self.mascot and not self.pending:
            self.mascot.set_state(self.mascot.rest)

    def _stop_ai(self):
        if self.ai is not None:
            self.ai.close()
            self.ai = None

    # ---------------------------------------------------------- window state

    def show(self):
        self._screen_cached = self._screen()
        self.visible = True
        self._place()
        self.root.deiconify()
        self.root.lift()
        if self.mascot:
            self.mascot.start()

    def hide(self):
        self.visible = False
        if self.mascot:
            self.mascot.stop()
        self.root.withdraw()

    def dismiss(self):
        self._stop_watch()
        self._stop_ai()
        self.pending = ""
        self.hide()
        if self.cfg["low_ram"] and self.scan is None:
            self.quit()  # nothing stays in memory between presses

    def open_settings(self):
        subprocess.Popen([sys.executable, "-m", "czgram", "--config"], cwd=PKG_DIR,
                         start_new_session=True)

    def quit(self):
        self._stop_watch()
        self._stop_ai()
        if self.scan is not None:
            self.scan.close()
        try:
            os.unlink(config.ui_socket())
        except OSError:
            pass
        self.root.destroy()

    # ---------------------------------------------------------- commands from other processes

    def _listen(self):
        path = config.ui_socket()
        try:
            os.unlink(path)
        except OSError:
            pass
        self.srv = socket.socket(socket.AF_UNIX)
        self.srv.bind(path)
        os.chmod(path, 0o600)
        self.srv.listen(4)
        self.root.createfilehandler(self.srv.fileno(), tk.READABLE, self._on_command)

    def _on_command(self, _fd, _mask):
        conn, _ = self.srv.accept()
        conn.settimeout(0.5)
        try:
            cmd = conn.recv(32).decode("ascii", "ignore").strip()
        except OSError:
            cmd = ""
        finally:
            conn.close()
        if cmd == "scan":
            self.start_scan()
        elif cmd == "reload":
            self.cfg = config.load()
            self._update_speed()
        elif cmd == "quit":
            self.quit()


def _shorten(text, limit=110):
    return text if len(text) <= limit else text[:limit - 1] + "…"


def main(scan_now=True):
    bar = Bar()
    if scan_now:
        bar.root.after(10, bar.start_scan)
    bar.root.mainloop()
    return 0
