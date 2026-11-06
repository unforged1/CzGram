"""Any OpenAI-compatible service: FreeLLMAPI, Groq, OpenRouter, a local server, ...

Standard library only, so choosing this route adds nothing to the app's memory use.
"""
import json
import re
import signal
import urllib.error
import urllib.parse
import urllib.request

CONNECT_TIMEOUT_S = 30
TOTAL_TIMEOUT_S = 120
_LOCAL = {"localhost", "127.0.0.1", "::1"}


class ExternalError(Exception):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    # urllib would resend the Authorization header to wherever a redirect points.
    def redirect_request(self, *args, **kwargs):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def normalize(base_url):
    """Accepts the base address, or a pasted .../chat/completions or .../models URL."""
    url = base_url.strip().rstrip("/")
    url = re.sub(r"/(chat/completions|models)$", "", url)
    parts = urllib.parse.urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ExternalError("The address must start with http:// or https://")
    return url


def is_unencrypted(base_url):
    """True when a key and exercise text would cross the network in the clear."""
    try:
        parts = urllib.parse.urlparse(base_url.strip())
        return parts.scheme == "http" and parts.hostname not in _LOCAL
    except ValueError:
        return False


def _request(url, key, body=None):
    headers = {"Accept": "application/json", "User-Agent": "CzGram"}
    if key:
        headers["Authorization"] = "Bearer " + key
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    try:
        return _OPENER.open(urllib.request.Request(url, data=data, headers=headers),
                            timeout=CONNECT_TIMEOUT_S)
    except urllib.error.HTTPError as e:
        with e:
            raise ExternalError(_http_message(e)) from None
    except (urllib.error.URLError, OSError, ValueError) as e:
        reason = getattr(e, "reason", e)
        raise ExternalError("Can't reach the service (%s)." % reason) from None


def _http_message(err):
    if 300 <= err.code < 400:
        return "The service redirected the request. Check the address."
    if err.code in (401, 403):
        return "The service rejected the API key."
    if err.code == 404:
        return "Not found (404). Check the address and the model."
    if err.code == 429:
        return "The service's rate limit was reached. Try again shortly."
    detail = ""
    try:
        body = json.loads(err.read(4096).decode("utf-8", "replace"))
        error = body.get("error", body)
        detail = error.get("message", "") if isinstance(error, dict) else str(error)
    except (ValueError, OSError, AttributeError):
        pass
    return "The service answered with error %d%s" % (err.code, ": " + detail[:140] if detail else ".")


def list_models(base_url, key):
    """Sorted model ids from GET /models. Raises ExternalError."""
    with _request(normalize(base_url) + "/models", key) as res:
        try:
            body = json.loads(res.read(2_000_000).decode("utf-8", "replace"))
        except ValueError:
            raise ExternalError("The service's model list wasn't readable.") from None
    rows = body.get("data", body.get("models", [])) if isinstance(body, dict) else body
    ids = [r.get("id") or r.get("name") if isinstance(r, dict) else r for r in rows or []]
    ids = sorted({i for i in ids if isinstance(i, str) and i})
    if not ids:
        raise ExternalError("The service listed no models.")
    return ids


class _ThinkFilter:
    """Hides <think>...</think> reasoning, which can be split across stream chunks."""
    OPEN, CLOSE = "<think>", "</think>"

    def __init__(self):
        self.buf, self.inside = "", False

    def feed(self, text):
        self.buf += text
        out = []
        while self.buf:
            tag = self.CLOSE if self.inside else self.OPEN
            at = self.buf.find(tag)
            if at >= 0:
                if not self.inside:
                    out.append(self.buf[:at])
                self.buf = self.buf[at + len(tag):]
                self.inside = not self.inside
                continue
            # Hold back only what could be the start of the tag.
            keep = next((n for n in range(min(len(tag) - 1, len(self.buf)), 0, -1)
                         if self.buf.endswith(tag[:n])), 0)
            if not self.inside:
                out.append(self.buf[:len(self.buf) - keep])
            self.buf = self.buf[len(self.buf) - keep:] if keep else ""
            break
        return "".join(out)

    def flush(self):
        rest, self.buf = ("" if self.inside else self.buf), ""
        return rest


def _text_of(choice):
    part = choice.get("delta") or choice.get("message") or {}
    content = part.get("content")
    return content if isinstance(content, str) else ""


def run(prompt, system, emit, base_url, key, model):
    """Stream one answer through emit(text=...), ending in emit(done=True) or emit(error=...)."""
    if not model:
        emit(error="Choose a model for this service in Settings.")
        return

    def too_long(*_):
        raise ExternalError("The service took too long to answer.")

    signal.signal(signal.SIGALRM, too_long)
    signal.alarm(TOTAL_TIMEOUT_S)
    think = _ThinkFilter()
    wrote = False

    def send(text):
        nonlocal wrote
        text = think.feed(text)
        if text:
            # Leading blank lines are what's left after a removed <think> block.
            if not wrote:
                text = text.lstrip()
            if text:
                wrote = True
                emit(text=text)

    try:
        body = {"model": model, "stream": True, "max_tokens": 2000,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": prompt}]}
        with _request(normalize(base_url) + "/chat/completions", key, body) as res:
            if "text/event-stream" in res.headers.get("Content-Type", ""):
                for raw in res:
                    line = raw.decode("utf-8", "replace").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        msg = json.loads(data)
                    except ValueError:
                        continue
                    if msg.get("error"):
                        err = msg["error"]
                        raise ExternalError(str(err.get("message", err) if isinstance(err, dict) else err)[:160])
                    for choice in msg.get("choices") or []:
                        send(_text_of(choice))
            else:
                # Some services ignore stream=true and answer in one piece.
                try:
                    msg = json.loads(res.read(2_000_000).decode("utf-8", "replace"))
                except ValueError:
                    raise ExternalError("The service's answer wasn't readable.") from None
                if isinstance(msg, dict) and msg.get("error"):
                    err = msg["error"]
                    raise ExternalError(str(err.get("message", err) if isinstance(err, dict) else err)[:160])
                for choice in (msg.get("choices") or []) if isinstance(msg, dict) else []:
                    send(_text_of(choice))
        rest = think.flush()
        if rest:
            emit(text=rest)
            wrote = True
        if wrote:
            emit(done=True)
        else:
            emit(error="The service sent an empty answer.")
    except ExternalError as e:
        emit(error=str(e))
    except OSError as e:
        emit(error="The connection to the service failed (%s)." % e)
    finally:
        signal.alarm(0)
