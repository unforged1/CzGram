"""Ask connected browsers (through the native-messaging host) for the active page."""
import glob
import json
import os
import socket

from . import config


MAX_REPLY = 8 * 1024 * 1024
# One per connected browser: a Unix socket, or on Windows a file naming the host's pipe.
PATTERN = "bridge-*.json" if os.name == "nt" else "bridge-*.sock"


class BridgeResult:
    __slots__ = ("lines", "url", "title", "error")

    def __init__(self, lines=(), url="", title="", error=""):
        self.lines, self.url, self.title, self.error = list(lines), url, title, error


def _ask_windows(path, timeout, request):
    from . import windows
    conn = windows.connect(path)
    try:
        conn.send_bytes(request)
        if not conn.poll(timeout):
            raise TimeoutError("the browser did not answer in time")
        try:
            data = conn.recv_bytes(MAX_REPLY)
        except OSError as e:
            if "length" in str(e):
                raise ValueError("the page is too large to read") from None
            raise
    finally:
        conn.close()
    return json.loads(data.decode("utf-8"))


def _ask(path, timeout, request=b"snapshot"):
    if os.name == "nt":
        return _ask_windows(path, timeout, request)
    s = socket.socket(socket.AF_UNIX)
    s.settimeout(timeout)
    try:
        s.connect(path)
        s.sendall(request + b"\n")
        chunks, size = [], 0
        while True:
            c = s.recv(65536)
            if not c:
                break
            size += len(c)
            if size > MAX_REPLY:
                raise ValueError("the page is too large to read")
            chunks.append(c)
    finally:
        s.close()
    return json.loads(b"".join(chunks).decode("utf-8"))


def connected():
    return bool(glob.glob(os.path.join(config.runtime_dir(), PATTERN)))


def read_page(timeout=4.0, full=False, armed=False, key="Alt"):
    """The raw reply from the focused browser, or the first that answered, or {"error": ...}.

    full: the whole page rather than what's in view. armed: a bulk-mode offer is open, so the
    page keeps Alt from opening the browser's menu bar. key: the key whose double taps the page
    counts for bulk mode (one of config.BULK_KEYS).
    """
    request = b" ".join([b"snapshot"] + [b"full"] * full + [b"armed"] * armed +
                        [b"key=" + key.encode("ascii", "ignore")])
    socks = glob.glob(os.path.join(config.runtime_dir(), PATTERN))
    if not socks:
        return {"error": "the browser connector isn't active "
                         "(install the CzGram extension, see Settings)"}
    best, last_error = None, "the browser did not answer"
    for path in socks:
        try:
            reply = _ask(path, timeout, request)
        except (ConnectionRefusedError, FileNotFoundError):
            # Left behind by a browser that crashed.
            try:
                os.unlink(path)
            except OSError:
                pass
            continue
        except (OSError, ValueError) as e:
            last_error = "browser connector error: %s" % e
            continue
        if reply.get("error"):
            last_error = reply["error"]
            continue
        if best is None or (reply.get("focused") and not best.get("focused")):
            best = reply
    return best if best is not None else {"error": last_error}


def snapshot(timeout=4.0):
    from .htmlread import to_lines
    reply = read_page(timeout)
    if reply.get("error"):
        return BridgeResult(error=reply["error"])
    lines = []
    for frame in reply.get("frames", []):
        lines.extend(to_lines(frame))
    return BridgeResult(lines, reply.get("url", ""), reply.get("title", ""))
