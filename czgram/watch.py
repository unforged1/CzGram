"""Quick mode: keep reading the active tab's HTML and report each new question.

Runs as a child of the bar and only ever reads: it has no way to click or type on
the page. Prints JSON lines:
  {"event":"status","message":...}   nothing to show yet, or a problem to mention
  {"event":"result",...}             a new question, in the same form as a scan's result
  {"event":"bulk_offer","count":n}   the whole tab holds n questions; a double tap of the bulk key accepts
  {"event":"bulk_offer_end"}         that set is gone before it was accepted
  {"event":"bulk_on","items":[...]}  accepted: answer these, in this order
  {"event":"bulk_next","index":i}    the user answered; show answer i (0-based)
  {"event":"bulk_end","reason":...}  the set is finished, or the page moved on

`python3 -m czgram.watch --offer` only offers bulk mode for the page (after a PrintScreen
scan in page-code mode), and exits when the offer lapses or the set is done.
"""
import json
import sys
import time

from . import bridge, config
from .analyze import analyze, analyze_in_order, describe_exercise
from .htmlread import find_exercise, find_state, to_lines

MIN_INTERVAL_S = 0.5
LOW_RAM_INTERVAL_S = 1.0
WAITING = "Waiting for a question…"
FULL_READ_EVERY = 4     # polls between whole-tab reads that look for a set of questions
MAX_BULK = 40
OFFER_ONLY_S = 45       # how long a PrintScreen scan's offer stays open


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


def page_state(reply):
    """(Alt double-taps, answers) summed over the page's frames."""
    alt = answers = 0
    for frame in reply.get("frames", []):
        a, n = find_state(frame)
        alt, answers = alt + a, answers + n
    return alt, answers


class Bulk:
    """Bulk mode for one set of questions: offer, accept, then follow the user's answers.

    The page itself counts answers (clicks on options, finished text gaps), so this works on
    any page that shows the whole set at once, without knowing its markup.
    """

    def __init__(self, lang):
        self.lang = lang
        self.state = "none"     # "none" | "offered" | "on"
        self.items, self.key, self.url = [], None, ""
        self.done_keys = set()  # sets already used or finished aren't offered again
        self.answered = set()   # (snippet, line) of items bulk mode answered: quick mode skips them
        self.alt0 = self.answers0 = 0
        self.index = 0

    def items_of(self, reply):
        lines = [line for frame in reply.get("frames", []) for line in to_lines(frame)]
        return analyze_in_order(lines, self.lang, MAX_BULK)

    def look(self, full_reply):
        """A whole-tab read: offers bulk mode for a new set, or withdraws a stale offer."""
        if self.state == "on":
            return []
        items = self.items_of(full_reply)
        key = (full_reply.get("url", ""), tuple((i["snippet"], i["line"]) for i in items))
        if len(items) < 2 or key in self.done_keys:
            if self.state == "offered":
                self.state = "none"
                return [{"event": "bulk_offer_end"}]
            return []
        if self.state == "offered" and key == self.key:
            return []
        self.state, self.items, self.key = "offered", items, key
        self.url = full_reply.get("url", "")
        self.alt0, self.answers0 = page_state(full_reply)
        return [{"event": "bulk_offer", "count": len(items)}]

    def watch(self, reply):
        """Every poll: notices the Alt double tap, and each answer while bulk mode is on."""
        alt, answers = page_state(reply)
        if self.state == "offered":
            if reply.get("url", "") != self.url:
                self.state = "none"
                return [{"event": "bulk_offer_end"}]
            if alt > self.alt0:
                self.state, self.index, self.answers0 = "on", 0, answers
                self.done_keys.add(self.key)
                self.answered.update((i["snippet"], i["line"]) for i in self.items)
                return [{"event": "bulk_on", "items": self.items, "title": reply.get("title", "")}]
            return []
        if self.state != "on":
            return []
        if reply.get("url", "") != self.url:
            self.state = "none"
            return [{"event": "bulk_end", "reason": "The page changed, so bulk mode ended."}]
        if answers < self.answers0:  # the page reloaded and its counter restarted
            self.answers0 = answers
        if answers > self.answers0:
            self.index += answers - self.answers0
            self.answers0 = answers
            if self.index >= len(self.items):
                self.state = "none"
                return [{"event": "bulk_end", "reason": "That was the last one in this set."}]
            return [{"event": "bulk_next", "index": self.index}]
        return []


def main(argv=()):
    offer_only = "--offer" in argv
    cfg = config.load()
    floor = LOW_RAM_INTERVAL_S if cfg["low_ram"] else MIN_INTERVAL_S
    watcher = Watcher(cfg["language"])
    bulk = Bulk(cfg["language"])
    key = config.bulk_key(cfg)
    last_status = None
    polls = 0
    started_at = time.monotonic()

    def status(message):
        nonlocal last_status
        if message != last_status:
            last_status = message
            emit(event="status", message=message)

    if not offer_only:
        status(WAITING)
    while True:
        started = time.monotonic()
        if bulk.state != "on" and polls % FULL_READ_EVERY == 0:
            # Settings may have changed the key since this started; the bar shows the new one.
            key = config.bulk_key(config.load())
            full = bridge.read_page(full=True, key=key)
            if not full.get("error"):
                for event in bulk.look(full):
                    emit(**event)
        polls += 1
        reply = bridge.read_page(armed=bulk.state == "offered", key=key)
        if reply.get("error"):
            if offer_only:
                # Without a browser there's nothing to offer; don't outlive the offer's time.
                if bulk.state != "on" and time.monotonic() - started_at > OFFER_ONLY_S:
                    return 0
            else:
                status(reply["error"])
            time.sleep(2)
            continue
        events = bulk.watch(reply)
        for event in events:
            emit(**event)
        if offer_only:
            ended = any(e["event"] in ("bulk_end", "bulk_offer_end") for e in events)
            lapsed = bulk.state != "on" and time.monotonic() - started_at > OFFER_ONLY_S
            if ended or lapsed or (bulk.state == "none" and polls > 1):
                return 0
        elif bulk.state != "on":
            status(WAITING)
            items = [i for i in watcher.feed(reply) or []
                     if (i.get("snippet"), i.get("line")) not in bulk.answered]
            if items:
                emit(event="result", source="page code", notice="", items=items)
        # A very large page takes longer to read, so give it room to breathe.
        time.sleep(max(floor, 3 * (time.monotonic() - started)))


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (BrokenPipeError, KeyboardInterrupt):
        sys.exit(0)  # the bar closed
