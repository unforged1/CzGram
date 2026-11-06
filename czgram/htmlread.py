"""Turn page HTML into plain lines, keeping exercise structure that a screenshot can't show.

An empty <input> becomes "___", a <select> becomes "(a/b/c)", so that fill-in
exercises built from form controls reach the analyzer as ordinary gaps.
"""
from html.parser import HTMLParser

_SKIP = {"czgram-selection", "script", "style", "noscript", "template", "svg", "canvas", "head", "title"}
_BLOCK = {"address", "article", "aside", "blockquote", "br", "dd", "details", "div", "dl",
          "dt", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4",
          "h5", "h6", "header", "hr", "li", "main", "nav", "ol", "p", "pre", "section",
          "summary", "table", "td", "th", "tr", "ul"}
_TEXT_INPUTS = {"", "text", "search"}
GAP = "___"


class _Reader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines, self.buf = [], []
        self.skip = 0
        self.select_opts = None
        self.option_buf = None
        self.textarea = None

    def flush(self):
        text = " ".join("".join(self.buf).split())
        if text:
            self.lines.append(text)
        self.buf = []

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP:
            self.skip += 1
            return
        if self.skip:
            return
        a = dict(attrs)
        if tag == "input":
            kind = (a.get("type") or "").lower()
            if kind in _TEXT_INPUTS:
                val = (a.get("value") or "").strip()
                self.buf.append(" [%s] " % val if val else GAP)
        elif tag == "textarea":
            self.textarea = []
        elif tag == "select":
            self.select_opts = []
        elif tag == "option" and self.select_opts is not None:
            self.option_buf = []
        elif tag in _BLOCK:
            self.flush()

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag in _SKIP:
            self.skip -= 1

    def handle_endtag(self, tag):
        if tag in _SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag == "textarea" and self.textarea is not None:
            val = " ".join("".join(self.textarea).split())
            self.buf.append(" [%s] " % val if val else GAP)
            self.textarea = None
        elif tag == "option" and self.option_buf is not None:
            text = " ".join("".join(self.option_buf).split())
            if text and not _is_placeholder(text):
                self.select_opts.append(text)
            self.option_buf = None
        elif tag == "select" and self.select_opts is not None:
            self.buf.append("(%s)" % "/".join(self.select_opts) if self.select_opts else GAP)
            self.select_opts = None
        elif tag in _BLOCK:
            self.flush()

    def handle_data(self, data):
        if self.skip:
            return
        if self.option_buf is not None:
            self.option_buf.append(data)
        elif self.textarea is not None:
            self.textarea.append(data)
        elif self.select_opts is None:
            self.buf.append(data)


class _Exercise(HTMLParser):
    """Finds a question with answer buttons, as marked up on the Umíme sites.

    Any other visible text in the question area counts as context: a note or word beside
    the question can decide its meaning or change which rule applies. Reading the whole
    area, not named fields, also catches context in places not seen yet.
    """
    _VOID = {"input", "img", "br", "hr", "meta", "link"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.question, self.options, self.context = [], [], []
        self.answered = False
        self.kind, self.depth, self.buf = None, 0, []
        self.wrapper = 0     # nesting depth inside the question area
        self.skipped = 0     # nesting depth inside the page's own explanation

    def handle_starttag(self, tag, attrs):
        if tag in self._VOID:
            if tag == "input" and self.kind:
                self.buf.append(GAP)
            return
        role = dict(attrs).get("data-data")
        if role == "next" or tag == "exercise-explanation":
            # Both only appear on the page once the question has been answered.
            self.answered = True
        if self.skipped or tag == "exercise-explanation":
            self.skipped += 1
        if self.wrapper or role == "wrapper":
            self.wrapper += 1
        if self.kind:
            self.depth += 1
        elif role in ("question", "option"):
            self.kind, self.depth, self.buf = role, 1, []

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self._VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in self._VOID:
            return
        if self.skipped:
            self.skipped -= 1
        if self.wrapper:
            self.wrapper -= 1
            # A closing block separates pieces of context.
            if not self.kind and tag in _BLOCK:
                self.context.append("\n")
        if not self.kind:
            return
        self.depth -= 1
        if self.depth == 0:
            text = " ".join("".join(self.buf).split())
            if text:
                (self.question if self.kind == "question" else self.options).append(text)
            self.kind = None

    def handle_data(self, data):
        if self.kind:
            self.buf.append(data)
        elif self.wrapper and not self.skipped:
            self.context.append(data)


def find_exercise(html):
    """{"question", "options", "context", "answered"} if the HTML holds an exercise, else None."""
    reader = _Exercise()
    reader.feed(html)
    reader.close()
    if not reader.question or not reader.options:
        return None
    pieces = (" ".join(p.split()) for p in "".join(reader.context).split("\n"))
    return {"question": " ".join(reader.question), "options": reader.options,
            "context": " · ".join(p for p in pieces if p), "answered": reader.answered}


class _Selection(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.found, self.text, self.context = False, [], ""

    def handle_starttag(self, tag, attrs):
        if tag == "czgram-selection":
            self.found = True
            self.context = dict(attrs).get("data-context") or ""

    def handle_endtag(self, tag):
        if tag == "czgram-selection":
            self.found = False

    def handle_data(self, data):
        if self.found:
            self.text.append(data)


def find_selection(html):
    """(selected text, its sentence) from a page snapshot; empty if nothing is highlighted."""
    if "<czgram-selection" not in html:
        return "", ""
    # It's always written first, so the rest of the page needn't be parsed.
    reader = _Selection()
    reader.feed(html[:html.index("</czgram-selection>") + 19])
    reader.close()
    return " ".join("".join(reader.text).split()), " ".join(reader.context.split())


def _is_placeholder(text):
    low = text.lower().strip(" .-…")
    return low in {"", "vyberte", "vyber", "zvolte", "zvol", "select", "choose", "?"} \
        or low.startswith(("vyberte", "zvolte", "choose", "select"))


def to_lines(html):
    r = _Reader()
    r.feed(html)
    r.close()
    r.flush()
    return r.lines
