"""Quick mode: keep reading the active tab's HTML and report each new question.

Runs as a child of the bar and only ever reads: it has no way to click or type on
the page. Prints JSON lines:
  {"event":"status","message":...}   nothing to show yet, or a problem to mention
  {"event":"result",...}             a new question, in the same form as a scan's result
"""
import json
import sys
import time

from . import bridge, config
from .analyze import analyze, describe_exercise
from .htmlread import find_exercise, to_lines

MIN_INTERVAL_S = 0.5
LOW_RAM_INTERVAL_S = 1.0
WAITING = "Waiting for a question…"


def emit(**msg):
    print(json.dumps(msg, ensure_ascii=False), flush=True)


class Watcher:
    """Decides what counts as a new question. Separate from the loop so tests can drive it."""

    def __init__(self, lang):
        self.lang = lang
        self.shown = None      # the question on display; a repeat of it asks nothing new
        self.candidate = None  # seen once; must hold for a second poll before it counts

    def feed(self, reply):
        """Takes one browser snapshot and returns the items to show, or None."""
        frames = reply.get("frames", [])
        exercise = next(filter(None, map(find_exercise, frames)), None)
        if exercise:
            if exercise["answered"]:
                # The page fills the gap in once answered, which changes the text. That
                # isn't a new question. Forgetting it also lets a later repeat show again.
                self.shown = self.candidate = None
                return None
            key = (exercise["question"], tuple(exercise["options"]), exercise["context"])
            items = None
        else:
            lines = [line for frame in frames for line in to_lines(frame)]
            items = analyze(lines, self.lang)
            if not items:
                self.candidate = None
                return None
            key = tuple(i["snippet"] for i in items)
        if key == self.shown:
            self.candidate = None
            return None
        # A page part-way through swapping questions mustn't cost a lookup.
        if key != self.candidate:
            self.candidate = key
            return None
        self.shown, self.candidate = key, None
        if exercise:
            return [describe_exercise(exercise["question"], exercise["options"], self.lang,
                                      reply.get("title", ""), exercise["context"])]
        return items


def main():
    cfg = config.load()
    floor = LOW_RAM_INTERVAL_S if cfg["low_ram"] else MIN_INTERVAL_S
    watcher = Watcher(cfg["language"])
    last_status = None

    def status(message):
        nonlocal last_status
        if message != last_status:
            last_status = message
            emit(event="status", message=message)

    status(WAITING)
    while True:
        started = time.monotonic()
        reply = bridge.read_page()
        if reply.get("error"):
            status(reply["error"])
            time.sleep(2)
            continue
        status(WAITING)
        items = watcher.feed(reply)
        if items:
            emit(event="result", source="page code", notice="", items=items)
        # A very large page takes longer to read, so give it room to breathe.
        time.sleep(max(floor, 3 * (time.monotonic() - started)))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (BrokenPipeError, KeyboardInterrupt):
        sys.exit(0)  # the bar closed
