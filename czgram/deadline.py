"""A time limit for a whole lookup.

POSIX: SIGALRM, so the handler runs in the main thread and can raise there.
Windows has no SIGALRM, so a timer thread calls the handler instead; there it can't
interrupt the main thread, and handlers end the lookup process themselves.
"""
import signal
import threading


def start(seconds, handler):
    """Calls handler() once `seconds` have passed. Returns a token for cancel()."""
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, lambda *_: handler())
        signal.alarm(seconds)
        return None
    timer = threading.Timer(seconds, handler)
    timer.daemon = True
    timer.start()
    return timer


def cancel(token):
    if token is None:
        signal.alarm(0)
    else:
        token.cancel()
