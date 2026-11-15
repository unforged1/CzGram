"""The settings window, shown on first run and from the bar's gear button."""
import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk

from . import claude_code, config, external, install, ipc, ocr, usage
from .macos import key_text

BG = "#F4F1EA"
FG = "#1F1E1D"
MUTED = "#6B665E"
OK = "#2F7D4F"
BAD = "#B3402A"
ACCENT = "#D97757"
FONT = "Helvetica Neue" if sys.platform == "darwin" else "DejaVu Sans"
WRAP = 470
ANTHROPIC_MODELS = ("claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5", "claude-fable-5-1")


_MODEL_VAR = {"code": "code_model", "api": "model", "custom": "custom_model"}
_MODEL_HINT = {
    "code": "“default” lets your Claude account choose. Load models lists what your plan offers.",
    "api": "You can also type any other Anthropic model name.",
    "custom": "Enter the service's address and key, then Load models. FreeLLMAPI's key is in its dashboard.",
}


class ConfigWindow:
    def __init__(self):
        self.cfg = config.load()
        self.saved = False
        self.model_lists = {"code": list(claude_code.FALLBACK_MODELS), "api": list(ANTHROPIC_MODELS)}
        self.model_loading = False
        self.model_result = None
        self.root = tk.Tk(className="czgram")
        self.root.title("CzGram settings")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self._style()
        v = self.vars = {
            "detection": tk.StringVar(value=self.cfg["detection"]),
            "auto_fallback": tk.BooleanVar(value=self.cfg["auto_fallback"]),
            "quick_mode": tk.BooleanVar(value=self.cfg["quick_mode"]),
            "low_ram": tk.BooleanVar(value=self.cfg["low_ram"]),
            "mascot": tk.BooleanVar(value=self.cfg["mascot"]),
            "speed_mode": tk.BooleanVar(value=self.cfg["speed_mode"]),
            "language": tk.StringVar(value=self.cfg["language"]),
            "use_claude": tk.BooleanVar(value=self.cfg["use_claude"]),
            "claude_backend": tk.StringVar(value=self.cfg["claude_backend"]),
            "code_model": tk.StringVar(value=self.cfg["code_model"]),
            "custom_base_url": tk.StringVar(value=self.cfg["custom_base_url"]),
            "custom_api_key": tk.StringVar(value=self.cfg["custom_api_key"]),
            "custom_model": tk.StringVar(value=self.cfg["custom_model"]),
            "api_key": tk.StringVar(value=self.cfg["api_key"]),
            "model": tk.StringVar(value=self.cfg["model"]),
            "bind_printscreen": tk.BooleanVar(value=self.cfg["bind_printscreen"]),
        }
        body = ttk.Frame(self.root, padding=18)
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="CzGram", style="Title.TLabel").pack(anchor="w")
        ttk.Label(body, text="Press PrintScreen while solving Czech grammar. A small bar at the top of the "
                             "screen shows the rule for what it finds.", style="Note.TLabel").pack(anchor="w")

        columns = ttk.Frame(body)
        columns.pack(fill="both", expand=True)
        left = ttk.Frame(columns)
        left.pack(side="left", anchor="n", padx=(0, 24))
        right = ttk.Frame(columns)
        right.pack(side="left", anchor="n")

        self._section(left, "How to detect exercises")
        ttk.Radiobutton(left, text="Read from a screenshot (OCR)", value="screenshot",
                        variable=v["detection"], command=self._refresh).pack(anchor="w")
        self.fallback = ttk.Checkbutton(
            left, text="Switch to page code automatically if the screenshot can't be read",
            variable=v["auto_fallback"])
        self.fallback.pack(anchor="w", padx=(22, 0))
        ttk.Radiobutton(left, text="Read the page code directly (HTML)", value="html",
                        variable=v["detection"], command=self._refresh).pack(anchor="w", pady=(4, 0))
        ttk.Radiobutton(left, text="Selected word (manual): highlight it, then press PrintScreen",
                        value="manual", variable=v["detection"], command=self._refresh).pack(anchor="w", pady=(4, 0))
        self.ocr_status = ttk.Label(left, wraplength=WRAP)
        self.ocr_status.pack(anchor="w", pady=(6, 0))
        self.bridge_status = ttk.Label(left, wraplength=WRAP)
        self.bridge_status.pack(anchor="w")
        self.ext_row = ttk.Frame(left)
        self.ext_row.pack(anchor="w", pady=(4, 0), fill="x")
        ttk.Button(self.ext_row, text="Open extension folder", command=self._open_ext).pack(side="left")
        self.ext_help = self._note(left, "Page code needs the CzGram browser connector, added once. "
                                         "Chromium or Chrome: chrome://extensions → Developer mode → "
                                         "Load unpacked → the “chromium” folder. Firefox: "
                                         "about:debugging → This Firefox → Load Temporary Add-on → "
                                         "“firefox/manifest.json” (lasts until the browser restarts).")

        self._section(left, "Quick mode")
        ttk.Checkbutton(left, text="Keep reading the page and answer each new question",
                        variable=v["quick_mode"]).pack(anchor="w")
        self._note(left, "PrintScreen then turns it on and off. It reads page code only, so it needs "
                         "the browser connector, and you still click the answers yourself. With AI "
                         "answers on, each new question makes one request. Manual detection "
                         "turns it off.")

        self._section(left, "Claude tokens used by CzGram")
        token_row = ttk.Frame(left)
        token_row.pack(anchor="w", fill="x")
        self.token_label = ttk.Label(token_row, wraplength=WRAP - 70, justify="left")
        self.token_label.pack(side="left")
        ttk.Button(token_row, text="Reset", command=self._reset_tokens).pack(side="right")
        self._note(left, "Counts Claude lookups only, not your other Claude use, and it isn't your plan's "
                         "remaining limit. Details: czgram --usage")

        self._section(left, "Memory")
        ttk.Checkbutton(left, text="Minimize RAM usage", variable=v["low_ram"]).pack(anchor="w")
        self._note(left, "Closes the bar completely when dismissed and skips 2x upscaling before OCR. "
                         "Uses less memory; the bar opens a little slower and very small text is "
                         "read less reliably.")

        self._section(right, "Explanations")
        ttk.Checkbutton(right, text="Let the Claude mascot explain it (animated)",
                        variable=v["mascot"]).pack(anchor="w")
        ttk.Checkbutton(right, text="Speed mode: blue look and instant text with Opus or Fable",
                        variable=v["speed_mode"]).pack(anchor="w")
        lang = ttk.Frame(right)
        lang.pack(anchor="w", pady=(4, 0))
        ttk.Label(lang, text="Language:").pack(side="left", padx=(0, 8))
        ttk.Radiobutton(lang, text="English", value="en", variable=v["language"]).pack(side="left")
        ttk.Radiobutton(lang, text="Čeština", value="cs", variable=v["language"]).pack(side="left", padx=8)

        self._section(right, "AI answers (optional)")
        ttk.Checkbutton(right, text="Ask an AI for specific answers", variable=v["use_claude"],
                        command=self._refresh).pack(anchor="w")
        self._note(right, "Off: everything stays on this computer and you get general rules. On: the "
                         "recognised text of each item you view goes to the service chosen here.")
        ttk.Radiobutton(right, text="My Claude plan, through Claude Code", value="code",
                        variable=v["claude_backend"], command=self._on_backend).pack(anchor="w", pady=(4, 0))
        self.code_row = ttk.Frame(right)
        self.code_row.pack(anchor="w", fill="x", padx=(22, 0))
        self.code_status = ttk.Label(self.code_row, wraplength=WRAP - 22, justify="left")
        self.code_status.pack(side="left")
        self.login_btn = ttk.Button(self.code_row, text="Sign in", command=self._sign_in)
        self.login_proc = None
        ttk.Radiobutton(right, text="Anthropic API key (billed per use)", value="api",
                        variable=v["claude_backend"], command=self._on_backend).pack(anchor="w")
        ttk.Radiobutton(right, text="Another provider (OpenAI-compatible, like FreeLLMAPI)", value="custom",
                        variable=v["claude_backend"], command=self._on_backend).pack(anchor="w")

        self.api_row = ttk.Frame(right)
        self.api_row.pack(anchor="w", fill="x", pady=(4, 0))
        self.url_label = ttk.Label(self.api_row, text="Address:")
        self.url_label.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.url_entry = ttk.Entry(self.api_row, textvariable=v["custom_base_url"], width=36)
        self.url_entry.grid(row=0, column=1, sticky="w")
        self.url_entry.bind("<KeyRelease>", lambda _e: self._show_warning())
        self.key_label = ttk.Label(self.api_row, text="API key:")
        self.key_label.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.key_entry = ttk.Entry(self.api_row, show="•", width=36)
        self.key_entry.grid(row=1, column=1, sticky="w", pady=(4, 0))
        ttk.Label(self.api_row, text="Model:").grid(row=2, column=0, sticky="w", pady=(4, 0))
        self.model_entry = ttk.Combobox(self.api_row, width=34)
        self.model_entry.grid(row=2, column=1, sticky="w", pady=(4, 0))
        self.load_btn = ttk.Button(self.api_row, text="Load models", command=self._load_models)
        self.load_btn.grid(row=2, column=2, sticky="w", padx=(6, 0), pady=(4, 0))
        self.model_note = ttk.Label(right, style="Note.TLabel", wraplength=WRAP, justify="left")
        self.model_note.pack(anchor="w", pady=(2, 0))

        self._section(right, "Keyboard")
        ttk.Checkbutton(right, text="Use the PrintScreen key for CzGram",
                        variable=v["bind_printscreen"]).pack(anchor="w")
        self._note(right, "Listens for ⌃⌥G, and F13 on extended keyboards, whenever you're logged in. "
                          "Turn it off by unticking this, or by running: czgram --restore-shortcut"
                   if sys.platform == "darwin" else
                   "Replaces your desktop's PrintScreen shortcut. Undo it by unticking this, "
                   "or by running: czgram --restore-shortcut")

        self.status = ttk.Label(body, wraplength=2 * WRAP)
        # Claimed before the rest of the window, so a tall window can't push them off screen.
        btns = ttk.Frame(body)
        btns.pack(side="bottom", fill="x", pady=(10, 0), before=columns)
        self.status.pack(side="bottom", anchor="w", pady=(10, 0), before=btns)
        ttk.Button(btns, text="Save", style="Accent.TButton", command=self.save).pack(side="right")
        ttk.Button(btns, text="Close", command=self.root.destroy).pack(side="right", padx=8)
        self._refresh()
        self._poll_bridge()
        # Starts the large Claude Code binary, so wait until the window is on screen.
        self.root.after(50, self._refresh_code_status)
        self.root.after(100, self._fit_window)

    def _style(self):
        s = ttk.Style(self.root)
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=FG, font=(FONT, 10))
        s.configure("TEntry", fieldbackground="#FFFFFF")
        s.configure("Title.TLabel", font=(FONT, 16, "bold"))
        s.configure("Section.TLabel", font=(FONT, 10, "bold"), foreground=ACCENT)
        s.configure("Note.TLabel", foreground=MUTED, font=(FONT, 9))
        s.configure("TCheckbutton", background=BG)
        s.configure("TRadiobutton", background=BG)
        s.map("TCheckbutton", background=[("active", BG)])
        s.map("TRadiobutton", background=[("active", BG)])
        s.configure("Accent.TButton", background=ACCENT, foreground="#FFFFFF")
        s.map("Accent.TButton", background=[("active", "#C4623F")])

    def _section(self, parent, text):
        ttk.Label(parent, text=text, style="Section.TLabel").pack(anchor="w", pady=(12, 3))

    def _note(self, parent, text):
        label = ttk.Label(parent, text=text, style="Note.TLabel", wraplength=WRAP, justify="left")
        label.pack(anchor="w", pady=(2, 0))
        return label

    def _refresh(self):
        screenshot = self.vars["detection"].get() == "screenshot"
        self.fallback.state(["!disabled"] if screenshot else ["disabled"])
        self._on_backend()
        ok, msg = ocr.status()
        self.ocr_status.configure(text=("✓ " if ok else "✗ ") + msg, foreground=OK if ok else BAD)

    def _on_backend(self):
        """Point the shared address, key and model fields at the chosen service."""
        kind = self.vars["claude_backend"].get()
        self.model_entry.configure(textvariable=self.vars[_MODEL_VAR[kind]],
                                   values=self.model_lists.get(kind, ()))
        if kind == "custom":
            self.url_label.grid()
            self.url_entry.grid()
        else:
            self.url_label.grid_remove()
            self.url_entry.grid_remove()
        if kind == "code":
            self.key_label.grid_remove()
            self.key_entry.grid_remove()
        else:
            self.key_label.grid()
            self.key_entry.grid()
            self.key_entry.configure(textvariable=self.vars["api_key" if kind == "api" else "custom_api_key"])
        if kind == "api":
            self.load_btn.grid_remove()
        else:
            self.load_btn.grid()
        on = self.vars["use_claude"].get()
        state = ["!disabled"] if on else ["disabled"]
        for widget in (self.url_entry, self.key_entry, self.model_entry, self.load_btn):
            widget.state(state)
        self._show_warning()

    def _show_warning(self):
        kind = self.vars["claude_backend"].get()
        if kind == "custom" and external.is_unencrypted(self.vars["custom_base_url"].get()):
            text = "Warning: this address isn't encrypted, so your key and text can be read in transit."
            self.model_note.configure(text=text, foreground=BAD)
        elif not self.model_loading:
            self.model_note.configure(text=_MODEL_HINT[kind], foreground=MUTED)

    def _load_models(self):
        """Fetch the chosen service's list on a thread; a slow server mustn't freeze the window."""
        kind = self.vars["claude_backend"].get()
        url, key = self.vars["custom_base_url"].get(), self.vars["custom_api_key"].get().strip()

        def work():
            try:
                models = claude_code.list_models() if kind == "code" else external.list_models(url, key)
                self.model_result = (kind, models, None)
            except external.ExternalError as e:
                self.model_result = (kind, None, str(e))

        self.model_result = None
        self.model_loading = True
        self.load_btn.state(["disabled"])
        self.model_note.configure(text="Loading models…", foreground=MUTED)
        threading.Thread(target=work, daemon=True).start()
        self._poll_models()

    def _poll_models(self):
        if self.model_result is None:
            self.root.after(100, self._poll_models)
            return
        kind, models, error = self.model_result
        self.model_loading = False
        self._on_backend()
        if error:
            self.model_note.configure(text=error, foreground=BAD)
            return
        self.model_lists[kind] = models
        self._on_backend()
        if kind == self.vars["claude_backend"].get():
            self.model_note.configure(text="%d models available. Pick one from the list." % len(models),
                                      foreground=OK)

    def _refresh_code_status(self):
        state, msg = claude_code.status()
        ready = state == "ready"
        self.code_status.configure(text=("✓ " if ready else "– ") + msg, foreground=OK if ready else MUTED)
        if state in ("signed_out", "api_billing") and self.login_proc is None:
            self.login_btn.pack(side="left", padx=(8, 0))
        else:
            self.login_btn.pack_forget()

    def _sign_in(self):
        self.login_proc = claude_code.login()
        self.login_btn.pack_forget()
        self.code_status.configure(text="– Finish signing in in your browser…", foreground=MUTED)
        self._poll_login()

    def _poll_login(self):
        if self.login_proc is not None and self.login_proc.poll() is None:
            self.root.after(1000, self._poll_login)
            return
        self.login_proc = None
        self._refresh_code_status()

    def _fit_window(self):
        """On a short screen, stay within it. The buttons are packed first, so they stay visible."""
        self.root.update_idletasks()
        room = self.root.winfo_screenheight() - 70
        if self.root.winfo_reqheight() > room:
            self.root.geometry("%dx%d+%d+0" % (self.root.winfo_reqwidth(), room, self.root.winfo_rootx()))

    def _show_tokens(self):
        rows = usage.summary(None)
        lookups = sum(r.get("requests", 0) for r in rows.values())
        thinking = sum(r.get("thinking", 0) for r in rows.values())
        self.token_label.configure(text="Today %s · 7 days %s · All %s\n%d lookups, %s thinking" % (
            usage.short(usage.total(1)), usage.short(usage.total(7)), usage.short(usage.total()),
            lookups, usage.short(thinking)))

    def _reset_tokens(self):
        from tkinter import messagebox
        if messagebox.askyesno("Reset token counts", "Clear CzGram's token counts? This can't be undone.",
                               parent=self.root):
            usage.reset()
            self._show_tokens()

    def _poll_bridge(self):
        self._show_tokens()
        from . import bridge
        ok = bridge.connected()
        self.bridge_status.configure(
            text="✓ Browser connector is active" if ok else "– Browser connector isn't active",
            foreground=OK if ok else MUTED)
        self.root.after(2000, self._poll_bridge)

    def _open_ext(self):
        path = install.extension_dir()
        if sys.platform == "darwin":
            from . import macos
            macos.open_path(path)
        elif shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", path])
        self.status.configure(text="Extension folder: " + path, foreground=MUTED)

    def save(self):
        new = dict(self.cfg)
        for key, var in self.vars.items():
            new[key] = var.get().strip() if isinstance(var, tk.StringVar) else var.get()
        new["model"] = new["model"] or config.DEFAULTS["model"]
        new["code_model"] = new["code_model"] or config.DEFAULTS["code_model"]
        config.save(new)
        self.cfg = new
        self.saved = True
        messages = install.apply(new)
        ipc.send("reload")
        ok = all(m[0] for m in messages)
        self.status.configure(
            text="Saved. " + " ".join(m[1] for m in messages if m[1]),
            foreground=OK if ok else BAD)

    def _mac_key_names(self, widget):
        """Macs have no PrintScreen key: name the Mac shortcut instead."""
        for child in widget.winfo_children():
            try:
                text = child.cget("text")
            except tk.TclError:
                text = ""
            if isinstance(text, str) and "PrintScreen" in text:
                child.configure(text=key_text(text))
            self._mac_key_names(child)

    def run(self):
        if sys.platform == "darwin":
            self._mac_key_names(self.root)
        self.root.mainloop()
        return self.saved


def main():
    return 0 if ConfigWindow().run() or config.exists() else 1


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    sys.exit(main())
