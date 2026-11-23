"""Run Tesseract on a PGM image and judge whether the result is usable.

Tesseract treats underscores as line art and drops them, so "b_dlí" comes back as
"b dlí" and the gap is gone. It even stretches word boxes over them, so looking
between words isn't enough. Instead we ask for per-character boxes (hOCR), scan each
text line in the image for thin strokes with nothing above them, and place every
stroke among the characters by its x position.
"""
import html
import os
import re
import shutil
import subprocess
from statistics import median

MIN_WORDS = 3
MIN_MEAN_CONF = 45.0
_LINE = re.compile(r"class='(?:ocr_line|ocr_header|ocr_caption|ocr_textfloat)'")
_WORD = re.compile(r"class='ocrx_word'[^>]*x_wconf (\d+)")
_CHAR = re.compile(r"class='ocrx_cinfo' title='x_bboxes (\d+) (\d+) (\d+) (\d+)[^']*'>([^<]*)<")
_TOKEN = re.compile("%s|%s|%s" % (_LINE.pattern, _WORD.pattern, _CHAR.pattern))


class OcrResult:
    __slots__ = ("lines", "ok", "reason", "mean_conf")

    def __init__(self, lines, ok, reason="", mean_conf=0.0):
        self.lines, self.ok, self.reason, self.mean_conf = lines, ok, reason, mean_conf


class Piece:
    """A recognised character, or (text == "_") a stroke found in the image."""
    __slots__ = ("text", "left", "top", "right", "bottom", "word")

    def __init__(self, text, left, top, right, bottom, word):
        self.text, self.left, self.top, self.right, self.bottom, self.word = \
            text, left, top, right, bottom, word


def _tesseract():
    """(path or None, extra arguments such as where the Czech data is)."""
    exe = shutil.which("tesseract")
    if os.name == "nt":
        from . import windows
        return windows.tesseract(exe)
    return exe, []


def _flags():
    if os.name == "nt":
        from .windows import child_flags
        return child_flags()
    return {}


def status():
    """(ok, message) for the settings window."""
    exe, extra = _tesseract()
    if not exe:
        return False, "Tesseract is not installed"
    try:
        out = subprocess.run([exe, "--list-langs"] + extra, capture_output=True, text=True,
                             timeout=10, **_flags())
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, "Tesseract failed to start: %s" % e
    if "ces" not in (out.stdout + out.stderr).split():
        return False, "Czech language data is missing (%s)" % (
            "run the CzGram installer again" if os.name == "nt" else "tesseract-ocr-ces")
    return True, "Tesseract with Czech data is ready"


def run(pgm):
    exe, extra = _tesseract()
    if not exe:
        return OcrResult([], False, "Tesseract is not installed")
    env = dict(os.environ)
    # Essential, not just thrifty: with OpenMP threads a page that takes 0.2 s can
    # take over 40 s on a many-core machine (measured on 16 cores, Tesseract 5.5).
    env["OMP_THREAD_LIMIT"] = "1"
    # Grey PGM over stdin: no screenshot is ever written to disk here.
    cmd = [exe, "stdin", "stdout"] + extra + ["-l", "ces", "--psm", "3", "-c", "hocr_char_boxes=1", "hocr"]
    try:
        res = subprocess.run(cmd, input=pgm, capture_output=True, env=env, timeout=60, **_flags())
    except subprocess.TimeoutExpired:
        return OcrResult([], False, "OCR timed out")
    except OSError as e:
        return OcrResult([], False, "OCR failed to start: %s" % e)
    if res.returncode != 0:
        err = res.stderr.decode("utf-8", "replace").strip().splitlines()
        return OcrResult([], False, "OCR error: " + (err[-1] if err else "exit %d" % res.returncode))
    return parse_hocr(res.stdout.decode("utf-8", "replace"), pgm)


# Tesseract reads the slash in short choices as l, í, i, I, | or nothing, and s as 5,
# z as 2: "slz", "zíze", "(2/ze)", "sse", "slzivz". Put the slashes back.
_SEP = r"[/|lIíi1\\é]"
_NOT_LETTER_BEFORE = r"(?<![^\W\d_])"
_NOT_LETTER_AFTER = r"(?![^\W\d_])"
_CHOICE_REPAIRS = (
    (re.compile(_NOT_LETTER_BEFORE + r"[s5]%s?z%s?vz" % (_SEP, _SEP) + _NOT_LETTER_AFTER), "s/z/vz"),
    (re.compile(_NOT_LETTER_BEFORE + r"[z2]%s?ze" % _SEP + _NOT_LETTER_AFTER), "z/ze"),
    (re.compile(_NOT_LETTER_BEFORE + r"[s5]%s?se" % _SEP + _NOT_LETTER_AFTER), "s/se"),
    (re.compile(_NOT_LETTER_BEFORE + r"[s5]%s?z" % _SEP + _NOT_LETTER_AFTER), "s/z"),
)
# "slz" is also a real word (bez slz: without tears); after these it stays as it is.
_TEARS = re.compile(r"(?:bez|plný|plné|plná|plna|mnoho|spousta|kapky|kapek|proud|potok)\s+$", re.I)


_UP, _LO = "A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ", "a-záčďéěíňóřšťúůýž"
_CASE_SEP = r"[/|lIíiyý1\\]"
# (V/v), (v/V), (Kik), (pP), (Č/čJ: one letter in both cases, slash or bracket misread.
_CASE_IN_BRACKETS = re.compile(r"\(\s*([%s%s])\s*%s?\s*([%s%s])\s*[)Jj]" % (_UP, _LO, _CASE_SEP, _UP, _LO))
# (V/) and (/Č): one half lost.
_CASE_HALF = re.compile(r"\(\s*(?:([%s%s])\s*/|/\s*([%s%s]))\s*\)" % (_UP, _LO, _UP, _LO))
# V/vánoce read as Vývánoce or V|vánoce. Plain i and l stay out: they are real letters in names.
_CASE_BARE = re.compile(r"(?<![^\W\d_])([%s])[/|íý]([%s])(?=[%s]{2})" % (_UP, _LO, _LO))
# (V/v)Itava: a capital I read for the l that follows.
_CASE_THEN_I = re.compile(r"(\([%s]/[%s]\)|\([%s]/[%s]\))I(?=[%s])" % (_UP, _LO, _LO, _UP, _LO))
# (V/v)itava: a small i read for the l, too. Only fixed when that spells a known word.
_CASE_THEN_SMALL_I = re.compile(r"(\(([%s%s])/[%s%s]\))i([%s]+)" % (_UP, _LO, _UP, _LO, _LO))


def _l_for_i(m):
    from .caps import decide
    letter, rest = m.group(2).lower(), m.group(3)
    if not decide(letter + "i" + rest, "x ")[1] and decide(letter + "l" + rest, "x ")[1]:
        return m.group(1) + "l" + rest
    return m.group(0)


# "(vánocích" with no closing bracket: the whole choice was lost but the word stayed.
_CASE_LOST = re.compile(r"\(([%s%s])([%s]{2,})" % (_UP, _LO, _LO))


def _repair_case_choices(line):
    def bracket(m):
        a, b = m.group(1), m.group(2)
        if a.lower() != b.lower() or a == b:
            return m.group(0)
        # With no slash or misread bracket at all, "(Vv)" is only a lost choice if the
        # word continues straight after it, as in "(pP)ondělí"; "(Vv) model" is text.
        plain = m.group(0).endswith(")") and not re.search(_CASE_SEP, m.group(0)[1:-1].replace(a, "", 1)
                                                            .replace(b, "", 1))
        after = m.string[m.end():m.end() + 1]
        if plain and not after.isalpha():
            return m.group(0)
        return "(%s/%s)" % (a, b)
    line = _CASE_IN_BRACKETS.sub(bracket, line)
    line = _CASE_HALF.sub(lambda m: "(%s/%s)" % ((m.group(1) or m.group(2)).upper(),
                                                 (m.group(1) or m.group(2)).lower()), line)
    line = _CASE_BARE.sub(lambda m: "%s/%s" % (m.group(1), m.group(2)) if m.group(1).lower() == m.group(2)
                          else m.group(0), line)
    line = _CASE_THEN_I.sub(lambda m: m.group(1) + "l", line)
    line = _CASE_THEN_SMALL_I.sub(_l_for_i, line)
    if ")" not in line:
        # A bracket can also just wrap onto the next line ("(viz obrázek"), so only rebuild
        # the choice for a word a capital-letter rule actually covers.
        from .caps import decide

        def lost(m):
            if not decide(m.group(1).lower() + m.group(2), "x ")[1]:
                return m.group(0)
            return "(%s/%s)%s" % (m.group(1).upper(), m.group(1).lower(), m.group(2))
        line = _CASE_LOST.sub(lost, line, count=1)
    return line


def repair_choices(line):
    line = _repair_case_choices(line)
    for pattern, fixed in _CHOICE_REPAIRS:
        def swap(m, fixed=fixed):
            if fixed == "s/z" and m.group(0) == "slz" and _TEARS.search(line[:m.start()]):
                return m.group(0)
            return fixed
        line = pattern.sub(swap, line)
    return line


def parse_hocr(doc, pgm=None):
    rows, confs, word_id = [], [], 0
    for m in _TOKEN.finditer(doc):
        token = m.group(0)
        if token.startswith("class='ocrx_cinfo'"):
            if rows:
                x0, y0, x1, y1 = (int(g) for g in m.group(2, 3, 4, 5))
                text = html.unescape(m.group(6)).strip()
                if text:
                    rows[-1].append(Piece(text, x0, y0, x1, y1, word_id))
        elif token.startswith("class='ocrx_word'"):
            word_id += 1
            confs.append(float(m.group(1)))
        else:
            rows.append([])
    rows = [r for r in rows if r]
    image = _Image(pgm) if pgm else None
    lines = [repair_choices(_assemble(r, image)) for r in rows]
    mean = sum(confs) / len(confs) if confs else 0.0
    if len(confs) < MIN_WORDS:
        return OcrResult(lines, False, "no readable text in the screenshot", mean)
    if mean < MIN_MEAN_CONF:
        return OcrResult(lines, False, "text too unclear to read (%.0f%% confidence)" % mean, mean)
    return OcrResult(lines, True, "", mean)


class _Image:
    def __init__(self, pgm):
        fields, pos = [], 0
        while len(fields) < 4:
            end = pos
            while pgm[end] not in b" \n\t\r":
                end += 1
            fields.append(pgm[pos:end])
            pos = end + 1
        self.w, self.h, self.data, self.offset = int(fields[1]), int(fields[2]), pgm, pos

    def row(self, y, x0, x1):
        start = self.offset + y * self.w
        return self.data[start + x0:start + x1]


def _assemble(chars, image):
    """Build the line's text, adding any strokes found in the image."""
    kept, placements = _place_strokes(chars, image) if image else (chars, {})
    out = []
    for i in range(len(kept) + 1):
        after_stroke = None
        for text, space_before, space_after in placements.get(i, ()):
            if out and space_before and out[-1] != " ":
                out.append(" ")
            out.append(text)
            after_stroke = space_after
        if i == len(kept):
            break
        if out and out[-1] != " ":
            if after_stroke is not None:
                # The ink beside the stroke decides, even across OCR's word split.
                if after_stroke:
                    out.append(" ")
            elif kept[i - 1].word != kept[i].word:
                out.append(" ")
        out.append(kept[i].text)
    return "".join(out)


def _place_strokes(chars, image):
    """(characters to keep, {char index: [(text, space before, space after), ...]})"""
    height = median(c.bottom - c.top for c in chars)
    baseline = int(median(c.bottom for c in chars))
    x0, x1, top, ink = _line_ink(image, chars, height, baseline)
    strokes = _find_strokes(image, x0, x1, top, ink, height, baseline)
    if not strokes:
        return chars, {}
    keep = _drop_guesses(chars, strokes)
    segments = _ink_segments(image, x0, x1, top, baseline - int(height * 0.1), ink)
    glue = max(2, height * 0.3)
    placements = {}
    for start, end in strokes:
        if start is None:
            continue  # Tesseract read this stroke itself
        index, left_seg, right_seg = _locate(keep, segments, start, end)
        before = left_seg is None or start - left_seg[1] > glue
        after = right_seg is None or right_seg[0] - end > glue
        text = "___" if end - start > height * 1.6 else "_"
        placements.setdefault(index, []).append((text, before, after))
    return keep, placements


def _drop_guesses(chars, strokes):
    """Remove what Tesseract guessed for a stroke ("—", "©"); honour a real "_" it read."""
    keep = list(chars)
    for i, (start, end) in enumerate(strokes):
        over = [c for c in keep if start <= (c.left + c.right) / 2 <= end]
        if any(c.text == "_" for c in over):
            strokes[i] = (None, None)
            continue
        for c in over:
            if not c.text.isalnum():
                keep.remove(c)
    return keep


def _locate(chars, segments, start, end):
    """Index in chars where a stroke belongs, by counting real glyphs.

    Tesseract's boxes drift around strokes, sometimes giving a letter the stroke's own
    box. So: find the nearest character on the left whose box matches its ink, then
    count ink segments from there up to the stroke.
    """
    before = [i for i, seg in enumerate(segments) if seg[1] <= start + 1]
    last_seg = before[-1] if before else -1
    left_seg = segments[last_seg] if before else None
    right_seg = segments[last_seg + 1] if last_seg + 1 < len(segments) else None

    anchor_char, anchor_seg = -1, -1
    for ci, c in enumerate(chars):
        for si, seg in enumerate(segments[:last_seg + 1]):
            if abs(seg[0] - c.left) <= 2 and abs(seg[1] - c.right) <= 2:
                anchor_char, anchor_seg = ci, si
    index = anchor_char + 1 + (last_seg - anchor_seg)
    return min(index, len(chars)), left_seg, right_seg


def _ink_segments(image, x0, x1, top, bottom, ink):
    """Runs of columns holding ink between two rows: close to one per glyph."""
    columns = bytearray(x1 - x0)
    for y in range(top, bottom):
        row = image.row(y, x0, x1).translate(ink)
        if 1 in row:
            columns = bytearray(a | b for a, b in zip(columns, row))
    return [(x0 + m.start(), x0 + m.end()) for m in re.finditer(b"\x01+", bytes(columns))]


def _line_ink(image, chars, height, baseline):
    x0 = max(0, min(c.left for c in chars) - int(height * 10))
    x1 = min(image.w, max(c.right for c in chars) + int(height * 10))
    top = max(0, baseline - int(height * 1.1))
    paper = _median(image.row(max(0, top - 2), x0, x1)) if x1 > x0 else 255
    return x0, x1, top, _ink_table(paper)


def _find_strokes(image, x0, x1, top_of_text, ink, height, baseline):
    """Thin horizontal runs below this line's baseline with nothing above them."""
    run_re = re.compile(b"\x01{%d,}" % max(5, int(height * 0.45)))
    found = []
    # Strictly below the baseline: the curved bottom of "u" sits right on it.
    first = baseline + max(2, int(height * 0.08))
    last = min(image.h - 1, baseline + int(height * 0.55))
    for y in range(first, last + 1):
        for m in run_re.finditer(image.row(y, x0, x1).translate(ink)):
            start, end = x0 + m.start(), x0 + m.end()
            if any(a < end and start < b for a, b, _ in found):
                continue  # the same stroke's next pixel row
            if _clear_above(image, ink, y, start, end, top_of_text, height):
                found.append((start, end, y))
    return sorted((a, b) for a, b, _ in found)


def _clear_above(image, ink, y, start, end, top_of_text, height):
    """Letters above a run mean it's an underline or part of a glyph, not a gap."""
    # Blurred stroke ends can touch the neighbouring letters, so inset the check.
    inset = max(2, (end - start) // 7)
    # Skip just above the stroke to allow for its thickness.
    stop = y - max(2, int(height * 0.2))
    for row_y in range(top_of_text, stop):
        if 1 in image.row(row_y, start + inset, end - inset).translate(ink):
            return False
    return True


def _median(row):
    return sorted(row)[len(row) // 2] if row else 255


def _ink_table(paper, contrast=70):
    """A bytes.translate table mapping ink pixels to 1 and paper to 0."""
    return bytes(1 if abs(v - paper) >= contrast else 0 for v in range(256))
