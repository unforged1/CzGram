"""Ask Claude through the Claude Code CLI, using the user's Claude subscription.

Text from the screen is untrusted, so the CLI runs with no tools, no MCP servers,
no settings and no saved session, in an empty directory. If it ever reports having
tools anyway, the lookup is abandoned before the prompt can do anything.

The environment is rebuilt from scratch: an inherited ANTHROPIC_API_KEY would
silently bill the API instead of using the subscription.
"""
import glob
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading

from . import deadline

IS_WINDOWS = os.name == "nt"

_KEEP_ENV = ("HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "TMPDIR", "XDG_RUNTIME_DIR",
             "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME",
             "DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "BROWSER",
             "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "no_proxy")
# Windows needs these to start programs, find the profile and reach the network.
_KEEP_ENV_WINDOWS = ("USERPROFILE", "USERNAME", "USERDOMAIN", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP",
                     "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "PATHEXT", "PROGRAMDATA",
                     "PROGRAMFILES", "PROGRAMFILES(X86)", "HOMEDRIVE", "HOMEPATH",
                     "CLAUDE_CODE_GIT_BASH_PATH")
TIMEOUT_S = 90
FALLBACK_MODELS = ("default", "opus", "sonnet", "haiku")


def _version_key(path):
    path = path.replace("\\", "/")
    return [int(n) for n in re.findall(r"\d+", path.split("/claude-code/")[-1].split("/")[0])]


def find():
    """Path of the Claude Code binary: on PATH, standard installs, then the desktop app's copy."""
    home = os.path.expanduser("~")
    extra = [os.path.join(home, ".local/bin"), os.path.join(home, ".claude/local"),
             os.path.join(home, ".npm-global/bin"), "/usr/local/bin"]
    if IS_WINDOWS:
        extra.append(os.path.join(os.environ.get("APPDATA", ""), "npm"))
    exe = shutil.which("claude") or shutil.which("claude", path=os.pathsep.join(extra))
    if exe:
        return exe
    bases = [os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")]
    names = ["claude"]
    if IS_WINDOWS:
        bases.append(os.environ.get("APPDATA", ""))
        names.append("claude.exe")
    # The desktop app keeps one copy per version and updates replace them, so look each time.
    bundled = [p for base in bases for name in names
               for p in glob.glob(os.path.join(base, "Claude", "claude-code", "*", "*", name))
               if os.access(p, os.X_OK)]
    return max(bundled, key=_version_key) if bundled else None


def command(exe):
    """How to start exe: a list for subprocess, or None if it can't be run safely.

    npm installs a claude.cmd on Windows. Batch files re-parse their arguments, which the
    system prompt mustn't go through, so the CLI script it points at runs under Node directly.
    """
    if not IS_WINDOWS or not exe.lower().endswith((".cmd", ".bat")):
        return [exe]
    folder = os.path.dirname(exe)
    script = os.path.join(folder, "node_modules", "@anthropic-ai", "claude-code", "cli.js")
    node = shutil.which("node") or shutil.which("node", path=folder)
    return [node, script] if node and os.path.exists(script) else None


def _flags():
    if IS_WINDOWS:
        from .windows import child_flags
        return child_flags()
    return {}


def clean_env():
    if IS_WINDOWS:
        env = {k: os.environ[k] for k in _KEEP_ENV + _KEEP_ENV_WINDOWS if k in os.environ}
        # Claude Code finds Git Bash and Node through PATH, and Windows has no standard short one.
        env["PATH"] = os.environ.get("PATH", "")
        return env
    env = {k: os.environ[k] for k in _KEEP_ENV if k in os.environ}
    env["PATH"] = "/usr/local/bin:/usr/bin:/bin"
    return env


def status():
    """("missing" | "signed_out" | "api_billing" | "ready", message) for the settings window."""
    exe = find()
    if not exe:
        return "missing", "Claude Code isn't installed"
    cmd = command(exe)
    if not cmd:
        return "missing", "Claude Code was installed in a way CzGram can't start; use the native installer"
    try:
        res = subprocess.run(cmd + ["auth", "status"], capture_output=True, text=True,
                             timeout=15, env=clean_env(), **_flags())
        info = json.loads(res.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        return "signed_out", "Couldn't check the Claude Code sign-in"
    if not info.get("loggedIn"):
        return "signed_out", "Claude Code needs you to sign in once"
    plan = info.get("subscriptionType")
    if not plan:
        return "api_billing", "Claude Code is signed in with API billing, not a subscription"
    return "ready", "Signed in to Claude Code (%s plan)" % str(plan).capitalize()


def login():
    """Starts the browser sign-in. Returns the process, or None without a binary."""
    exe = find()
    cmd = command(exe) if exe else None
    if not cmd:
        return None
    return subprocess.Popen(cmd + ["auth", "login", "--claudeai"], env=clean_env(),
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True, **_flags())


def list_models():
    """Model names the signed-in account can use, asked of Claude Code itself.

    Only the startup handshake runs, so no prompt is sent and no usage is spent.
    Returns FALLBACK_MODELS if that fails, for example when signed out.
    """
    exe = find()
    cmd = command(exe) if exe else None
    if not cmd:
        return list(FALLBACK_MODELS)
    with tempfile.TemporaryDirectory(prefix="czgram-") as empty:
        proc = subprocess.Popen(
            cmd + ["-p", "--input-format", "stream-json", "--output-format", "stream-json",
             "--verbose", "--tools", "", "--strict-mcp-config", "--setting-sources", "",
             "--disable-slash-commands", "--no-session-persistence"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            encoding="utf-8", cwd=empty, env=clean_env(), **_flags())
        watchdog = threading.Timer(15, proc.kill)
        watchdog.start()
        models = []
        try:
            proc.stdin.write('{"type":"control_request","request_id":"czgram",'
                             '"request":{"subtype":"initialize"}}\n')
            proc.stdin.flush()
            for line in proc.stdout:
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if msg.get("type") == "control_response":
                    rows = msg.get("response", {}).get("response", {}).get("models", [])
                    models = [r["value"] for r in rows if isinstance(r, dict) and r.get("value")]
                    break
        except (OSError, ValueError):
            pass
        finally:
            watchdog.cancel()
            proc.kill()
            proc.stdin.close()
            proc.stdout.close()
            proc.wait()
    return models or list(FALLBACK_MODELS)


def _friendly(text):
    low = (text or "").lower()
    if "not logged in" in low or "/login" in low or "authentication" in low or "oauth" in low:
        return "Claude Code isn't signed in. Use Sign in under Settings."
    if "limit" in low:
        return "You've reached your Claude usage limit for now. The offline rule still applies."
    if "model" in low:
        return "This model isn't available on your plan. Choose another in Settings."
    return "Claude Code couldn't answer: %s" % (text or "unknown error")[:160]


def run(prompt, system, emit, model="default"):
    """Stream one answer through emit(text=...), ending in emit(done=True) or emit(error=...)."""
    exe = find()
    if not exe:
        emit(error="Claude Code wasn't found. Install it, or use an API key in Settings.")
        return
    start = command(exe)
    if not start:
        emit(error="CzGram can't start this Claude Code install. Use Claude Code's native installer.")
        return
    cmd = start + ["-p", "--output-format", "stream-json", "--verbose", "--include-partial-messages",
           "--effort", "low", "--tools", "", "--strict-mcp-config", "--setting-sources", "",
           "--disable-slash-commands", "--no-session-persistence", "--system-prompt", system]
    if model and model != "default":
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:\[\]-]*", model):
            emit(error="The model name %r isn't valid. Choose one in Settings." % model[:40])
            return
        cmd += ["--model", model]
    with tempfile.TemporaryDirectory(prefix="czgram-") as empty:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                                cwd=empty, env=clean_env(), **_flags())

        def stop(*_):
            proc.kill()
            raise SystemExit(0)

        # Dismissing the bar terminates this process; the CLI must not outlive it.
        signal.signal(signal.SIGTERM, stop)
        alarm = deadline.start(TIMEOUT_S, lambda: (proc.kill(), emit(error="Claude Code took too long."),
                                                   os._exit(0)))
        proc.stdin.write(prompt)
        proc.stdin.close()
        finished = False
        try:
            for line in proc.stdout:
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                kind = msg.get("type")
                if kind == "system" and msg.get("subtype") == "init":
                    if msg.get("tools") or msg.get("mcp_servers"):
                        proc.kill()
                        emit(error="Stopped: Claude Code started with tools enabled.")
                        return
                    if msg.get("model"):
                        emit(model=msg["model"])
                elif kind == "stream_event":
                    event = msg.get("event", {})
                    delta = event.get("delta", {})
                    if event.get("type") == "content_block_delta" and delta.get("type") == "text_delta":
                        emit(text=delta["text"])
                elif kind == "result":
                    finished = True
                    for name, used in (msg.get("modelUsage") or {}).items():
                        emit(usage={"model": name, "input": used.get("inputTokens", 0),
                                    "output": used.get("outputTokens", 0),
                                    "thinking": used.get("thinkingTokens", 0),
                                    "cache_read": used.get("cacheReadInputTokens", 0),
                                    "cache_write": used.get("cacheCreationInputTokens", 0)})
                    if msg.get("is_error"):
                        emit(error=_friendly(str(msg.get("result") or "")))
                    else:
                        emit(done=True)
        finally:
            deadline.cancel(alarm)
            if proc.poll() is None:
                proc.kill()
            proc.wait()
        if not finished:
            emit(error="Claude Code stopped without answering.")
