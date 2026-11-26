"""The Internetová jazyková příručka (IJP) of the Czech Language Institute, prirucka.ujc.cas.cz.

CzGram never fetches it: the site's robots.txt bars programs from its word lookups, and its
legal notice allows copying only with the institute's consent. Instead the AI is asked to follow
its codification and to name the word worth checking, and the bar offers a link the user opens
in their own browser.

Settings: "off", "auto" (when the offline rules can't decide, or the AI is unsure) or "always".
"""
import re
import urllib.parse

MODES = ("off", "auto", "always")
URL = "https://prirucka.ujc.cas.cz/?slovo="
# A word or short phrase only: the AI's reply comes from page text, so nothing else may become a link.
_WORD = re.compile(r"^[^\W\d_]+(?:[ -][^\W\d_]+){0,2}$")
_LINE = re.compile(r"^\s*\**\s*IJP\s*:\s*\**\s*(.+?)\s*\**\s*$", re.I)
_SUFFIX = re.compile(r"\s*\(\s*IJP\s*:\s*([^()]+?)\s*\)\s*$", re.I)

ALWAYS = ("Answer by the codification of the Internetová jazyková příručka (IJP, prirucka.ujc.cas.cz). "
          "You can't open it, so never say you checked it. After the answer, add a last line: IJP: and the "
          "one word (in its dictionary form) the user should look up there.")
AUTO = ("Answer by the codification of the Internetová jazyková příručka (IJP, prirucka.ujc.cas.cz). "
        "You can't open it, so never say you checked it. If the answer depends on a fact about one word "
        "that you aren't sure of (its spelling, vowel length, capital letter or an accepted variant), add a "
        "last line: IJP: and that word in its dictionary form. Otherwise don't add it.")
UNSURE = ("CzGram's offline rules couldn't decide this one, so do add the IJP: line.")
BULK_ALWAYS = ("Answer by the codification of the Internetová jazyková příručka (IJP). You can't open it, "
               "so never say you checked it. End every line with (IJP: word), the word to look up there.")
BULK_AUTO = ("Answer by the codification of the Internetová jazyková příručka (IJP). You can't open it, "
             "so never say you checked it. Where an answer depends on a fact about one word you aren't sure "
             "of, end that line with (IJP: word), the word to look up there.")


def mode(cfg):
    value = cfg.get("ijp_check")
    return value if value in MODES else "auto"


def clean(word):
    """The word as a link may use it, or None."""
    word = (word or "").strip().strip(".,;:!?\"'„“”«»").strip()
    return word if len(word) <= 40 and _WORD.match(word) else None


def url(word):
    return URL + urllib.parse.quote(word)


def instruction(cfg, unsure=False):
    """Text for the single-item system prompt, or ""."""
    m = mode(cfg)
    if m == "always":
        return ALWAYS
    if m == "auto":
        return AUTO + (" " + UNSURE if unsure else "")
    return ""


def bulk_instruction(cfg):
    m = mode(cfg)
    return BULK_ALWAYS if m == "always" else BULK_AUTO if m == "auto" else ""


def split_suffix(text):
    """("answer text", word or None) for a bulk line ending in (IJP: word)."""
    m = _SUFFIX.search(text)
    if not m:
        return text, None
    return text[:m.start()].rstrip(), clean(m.group(1))


class LineFilter:
    """Holds back a reply's "IJP: word" line, so the bar gets the word instead of the text.

    Text is passed on as it streams. Only the start of a line is held, and only while it could
    still be the IJP line; once it can't, the rest of that line goes straight through.
    """

    def __init__(self, out):
        self.out = out
        self.word = None
        self.held = ""         # the current line's start, while it may be "IJP: ..."
        self.released = False  # the current line is ordinary text
        self.newlines = ""     # held until more text follows, so the answer never ends in a blank line
        self.ready = []

    def feed(self, text):
        for ch in text:
            if ch == "\n":
                self._end_line()
            elif self.released:
                self._put(ch)
            else:
                self.held += ch
                if not _could_be_ijp(self.held):
                    self.released = True
                    self._put(self.held)
                    self.held = ""
        self._send()

    def _put(self, text):
        self.ready.append(self.newlines + text)
        self.newlines = ""

    def _send(self):
        """Passes on what this chunk released, as one piece like the chunk that came in."""
        if self.ready:
            self.out("".join(self.ready))
            self.ready = []

    def _take(self):
        """The held line: the word if it's the IJP line, else back to text."""
        m = _LINE.match(self.held)
        word = clean(m.group(1)) if m else None
        if word:
            self.word = word
        elif self.held.strip():
            self._put(self.held)
        self.held = ""
        return bool(word)

    def _end_line(self):
        if self.released or not self._take():
            self.newlines += "\n"
        self.released = False

    def finish(self):
        """Ends the reply. Returns the word to check, or None."""
        if not self.released and self.held:
            self._take()
        self._send()
        return self.word


def _could_be_ijp(start):
    """True while a line's start could still become "IJP:" (after spaces or bold markers)."""
    core = start.lstrip(" *\t")
    return core.lower().startswith("ijp:") or "ijp:".startswith(core.lower())
