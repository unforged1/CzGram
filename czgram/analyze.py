"""Find grammar targets in text lines and match each to a rule.

Targets are gaps (b_dlet, "Vidím ___ psa", (s/z)bít) and Czech questions or
instructions. Offline this returns hints, not guaranteed answers: `suggest` is
only filled in where a rule actually decides the letter.
"""
import re
import unicodedata

from . import caps, sz
from .kb import TOPICS

LETTERS = "a-zA-ZáčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ"
MAX_LINE = 2000
_GAP = r"_+|…+|\.{3,}|—{2,}|-{3,}"
_WORD_GAP = re.compile(r"(?<![%s\d_.:/])([%s]*)(%s)([%s]*)(?![\d_/])" % (LETTERS, LETTERS, _GAP, LETTERS))
_OPT = r"[%s]{1,12}(?: [%s]{1,8})?" % (LETTERS, LETTERS)
# The look-behind makes a match start at a word's beginning: without it, a long run of letters
# is rescanned from every position, which a web page could use to stall the app.
_CHOICE = re.compile(r"(?<![%s])([%s]*)[(\[]\s*(%s(?:\s*/\s*%s)+)\s*[)\]]([%s]*)"
                     % (LETTERS, LETTERS, _OPT, _OPT, LETTERS))
_BARE_OPT = r"(?:i|y|í|ý|s|z|se|ze|vz|ú|ů|mě|mně|bě|bje|vě|vje|ji|jí|mi|my)"
# Two or three options, e.g. s/z, z/ze or s/z/vz, written without brackets.
_BARE_CHOICE = re.compile(r"(?<![%s/])(%s(?:/%s){1,2})(?![%s/:])"
                          % (LETTERS, _BARE_OPT, _BARE_OPT, LETTERS))
_TOKEN = re.compile(r"[%s]+" % LETTERS)
_UPPER_L = "A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ"
_LOWER_L = "a-záčďéěíňóřšťúůýž"
# V/vánoce: a capital and a small letter written in front of the rest of the word.
_CASE_CHOICE = re.compile(r"(?<![%s/])([%s])/([%s])([%s]+)" % (LETTERS, _UPPER_L, _LOWER_L, _LOWER_L))
# "Napište nám" (write to us) is the Umíme sites' contact button; "napište" looks like a task.
_IGNORED = {"napiste nam"}
_DIACRITIC = re.compile("[áčďéěíňóřšťúůýž]", re.I)

_STOP = {"a", "i", "je", "jsou", "se", "si", "na", "ve", "ze", "to", "do", "pro", "jak", "kde",
         "co", "kdo", "byl", "ale", "nebo", "tak", "od", "po", "za", "ten", "ta", "ty", "by",
         "aby", "kdy", "proc", "ktery", "ktera", "ktere", "jaky", "jaka", "jake", "mam", "ma",
         "slovo", "slova", "veta", "vete", "vetu"}
_INSTRUCT = ("dopln", "vyber", "urci", "napis", "oznac", "podtrhn", "najdi", "rozhodn", "oprav",
             "zvol", "pojmenuj", "vysklon", "vycasuj", "roztrid", "prirad")
# Commands only: "Doplňte" starts an exercise, the heading "Doplňovací cvičení" doesn't.
_IMPERATIVE = re.compile(r"(dopln|vyber|urci|urcete|napis|oznac|podtrhni|podtrhnete|najdi|rozhodni|"
                         r"rozhodnete|oprav|zvol|pojmenuj|vysklonuj|vycasuj|roztrid|prirad)(te)?")

_QUESTION_WORDS = {"kam", "kde", "kdo", "kdy", "jak", "jaky", "jaka", "jake", "jaci", "ktery", "ktera",
                   "ktere", "proc", "kolik", "koho", "komu", "cim", "kym", "ceho", "cemu", "odkud"}

HARD = {"h", "k", "r"}          # ch handled separately; d, t, n depend on the sound
SOFT = set("žšřčcjďťň")
BOTH = set("blmpsvzf")

# Roots whose y marks a listed word (accent-free). The match must land on the gap.
_ROOTS = {
    "b": "byt byv byd byl bys obyc obyv kobyl byk nabyt dobyt pribyt zbyt zbyv pribysl".split(),
    "l": "slys mlyn blysk blyst polyk plyn plyt vzlyk lysy lysin lyt lyk lyz pelyn plys".split(),
    "m": "myt myd myj mysl myl hmyz mys hlemyz zamyk odemyk smyk dmych chmyr chomyt litomys".split(),
    "p": "pych pytel pytl pysk netopyr slepys pyj kopyt klopyt trpyt zpyt pyk pyr cepyr".split(),
    "s": "syn syt syr sych sykor syc syp sysel".split(),
    "v": "vys zvyk vyk vydr vyr vyzl povyk vyt vyhn vyhen".split(),
    "z": "brzy jazyk nazyv ruzyn".split(),
}
_PREFIXES = re.compile(r"(?:ne|nej|bez|do|na|nad|o|ob|od|po|pod|pro|pre|pri|roz|s|se|u|v|ve|vy|vz|vze|"
                       r"z|za|ze|mimo|pa|pra|sou)*")
# Same sound, different word: the rule alone can't choose, the meaning must.
# Keyed by the accent-free y-spelling. Values: (Czech label, English label).
_HOMOPHONES = {
    "byt": ("byt, být × bit, bít", "byt/být (a flat, to be) × bit/bít (to beat)"),
    "byl": ("byl × bil", "byl (was) × bil (hit)"),
    "byla": ("byla × bila", "byla (was) × bila (hit)"),
    "byli": ("byli × bili", "byli (were) × bili (hit)"),
    "myt": ("mýt × mít", "mýt (to wash) × mít (to have)"),
    "my": ("my × mi", "my (we) × mi (to me)"),
    "vy": ("vy × ví", "vy (you) × ví (knows)"),
    "pyl": ("pyl × pil", "pyl (pollen) × pil (drank)"),
    "vyr": ("výr × vír", "výr (eagle owl) × vír (whirl)"),
    "lyze": ("lyže × líže", "lyže (ski) × líže (licks)"),
    "mysli": ("myslí × mísí", "myslí (thinks) × mísí (mixes)"),
    "vysi": ("výší × visí", "výší (height) × visí (hangs)"),
}
# Very common non-listed v_ words, so the vy- prefix guess doesn't misfire.
_VI_STEMS = ("d", "n", "t", "s", "k", "l", "z", "c", "r")


def strip(text):
    return "".join(c for c in unicodedata.normalize("NFD", text)
                   if not unicodedata.combining(c)).lower()


def is_czech(line):
    if _DIACRITIC.search(line):
        return True
    tokens = [strip(t) for t in _TOKEN.findall(line)]
    if any(t.startswith(_INSTRUCT) for t in tokens):
        return True
    # Without diacritics a question can still give itself away by its first word.
    if line.rstrip().endswith("?") and tokens and tokens[0] in _QUESTION_WORDS:
        return True
    return sum(t in _STOP for t in tokens) >= 2


def listed_root(pre, suf):
    """Listed-word root that puts y exactly at the gap, or None."""
    word = strip(pre) + "y" + strip(suf)
    gap = len(pre)
    if gap == 0:
        return None
    for root in _ROOTS.get(strip(pre)[-1], ()):
        k = root.find("y", 0)
        start = word.find(root)
        while start != -1:
            # Only at the start of a word or after real prefixes: the pyt- of pytel
            # must not match inside neuchop_telný.
            if start + k == gap and _PREFIXES.fullmatch(word[:start]):
                return root
            start = word.find(root, start + 1)
    return None


def _item(kind, snippet, topic, line, suggest="", why=None):
    return {"kind": kind, "snippet": snippet.strip(), "topic": topic, "line": line,
            "suggest": suggest, "why": why}


def classify_gap(pre, suf):
    """(topic, suggestion, reason) for a gap inside a word."""
    p, s = strip(pre), suf.lower()
    last = p[-1] if p else ""
    two = p[-2:]

    if s[:1] in ("ě", "e") and last in ("m", "b", "v"):
        topic = {"m": "me_mne", "b": "be_bje", "v": "ve_vje"}[last]
        return topic, "", ""
    # A missing "m" or "mn" before ě: Zapo_ěl, _ě.
    if s[:1] == "ě" and (not p or last in "aeiouy"):
        return "me_mne", "", ""
    if not p:
        if s and strip(s[0]) not in "aeiouy":
            return "s_z_predpony", "", ""
        return "u_krouzek" if s else "gap_general", "", ""
    if not s:
        if last == "l" or two in ("la", "ly", "li"):
            return "shoda", "", ""
        if two in ("sk", "ck") or last == "n" and len(p) > 2:
            return "koncovky_prid", "", ""
        return "koncovky_podst", "", ""

    if two == "ch" or last in HARD:
        return "tvrde_mekke", "y", ("hard", "ch" if two == "ch" else last)
    if pre[-1].lower() in SOFT:
        return "tvrde_mekke", "i", ("soft", pre[-1].lower())
    if last in ("d", "t", "n"):
        return "tvrde_mekke", "", ("listen", last)
    if last in BOTH:
        return _classify_ambiguous(pre, s)
    if last in "aeiouy":
        return "spodoba", "", ""
    return "gap_general", "", ""


def _classify_ambiguous(pre, suf):
    filled = strip(pre) + "y" + strip(suf)
    if filled in _HOMOPHONES:
        return "vyjmenovana", "both", ("homophone", filled)
    root = listed_root(pre, suf)
    # klopýtat always continues past the t; a word stopping there is klopit (Neklopit).
    if root == "klopyt" and filled.endswith("klopyt"):
        root = None
    if root:
        return "vyjmenovana", "y", ("listed", root)
    p = strip(pre)
    if p == "v" and len(suf) >= 4 and strip(suf)[0] not in _VI_STEMS:
        return "vyjmenovana", "y", ("prefix", "")
    return "vyjmenovana", "i", ("default", "")


_CHOICE_TOPICS = (
    ({"mě", "mně", "mne"}, "me_mne"),
    ({"bě", "bje"}, "be_bje"),
    ({"vě", "vje"}, "ve_vje"),
    ({"ú", "ů", "u"}, "u_krouzek"),
    ({"ji", "jí", "jim", "jím", "mi", "my", "vy", "ví"}, "ji_ji"),
    ({"sebou", "s sebou"}, "sebou"),
    ({"by", "bych", "bys", "bychom", "bysme", "byste", "aby", "abych", "abychom", "abysme",
      "abyste", "kdyby", "kdybychom", "kdybysme", "kdybyste"}, "podminka_by"),
    ({"byl", "bil", "byli", "bili", "být", "bít", "byt", "bit"}, "byt_bit"),
)


def classify_choice(pre, options, suf, following="", before=""):
    """Topic for a choice such as b(i/y)t or (mě/mně). `following` is the text after it,
    `before` the text in front of the word."""
    if caps.is_case_pair(options):
        case, why = caps.decide(pre + options[0].lower() + suf, before)
        return "velka_pismena", caps.pick(case, options) if case else "", why
    low = {o.strip().lower() for o in options}
    if low & {"i", "y", "í", "ý"}:
        topic, suggest, why = classify_gap(pre, suf)
        return topic, fit_options(suggest, options)[0], why
    if low <= {"s", "z", "vz", "se", "ze"}:
        return sz.classify(pre, options, suf, following)
    for keys, topic in _CHOICE_TOPICS:
        if low & keys:
            return topic, "", ""
    for option in options:
        topic = _match_topic(option)
        if topic:
            return topic, "", ""
    return "gap_general", "", ""


def _match_topic(text):
    norm = " " + " ".join(strip(t) for t in _TOKEN.findall(text)) + " "
    best, best_score = None, 0
    for tid, topic in TOPICS.items():
        score = 0
        for key in topic["keys"]:
            k = strip(key)
            if len(k) < 2:
                continue
            if " " in k.strip():
                score += 3 * len(k) if k.strip() in norm else 0
            elif len(k) <= 3:
                # Short keys only count as whole words: "rod" must not match "rodina".
                score += len(k) if " %s " % k in norm else 0
            elif " " + k in norm:
                score += len(k)
        if score > best_score:
            best, best_score = tid, score
    return best


def _whole_word_topic(line):
    return _match_topic(line) or "gap_general"


def is_ignored(line):
    """Fixed site furniture that reads like an exercise instruction but isn't one."""
    return " ".join(strip(t) for t in _TOKEN.findall(line)) in _IGNORED


def analyze_line(line):
    if is_ignored(line):
        return []
    items, seen_spans = [], []
    czech = is_czech(line)

    for m in _CHOICE.finditer(line):
        pre, raw, suf = m.groups()
        options = [o.strip() for o in raw.split("/")]
        topic, suggest, why = classify_choice(pre, options, suf, line[m.end():], line[:m.start()])
        items.append(_item("gap", m.group(0), topic, line, suggest, why))
        seen_spans.append(m.span())

    for m in _CASE_CHOICE.finditer(line):
        if any(a <= m.start() < b for a, b in seen_spans) or m.group(1).lower() != m.group(2):
            continue
        topic, suggest, why = classify_choice("", [m.group(1), m.group(2)], m.group(3), "", line[:m.start()])
        items.append(_item("gap", m.group(0), topic, line, suggest, why))
        seen_spans.append(m.span())

    for m in _BARE_CHOICE.finditer(line):
        if any(a <= m.start() < b for a, b in seen_spans):
            continue
        topic, suggest, why = classify_choice("", m.group(1).split("/"), "", line[m.end():])
        items.append(_item("gap", m.group(0), topic, line, suggest, why))
        seen_spans.append(m.span())

    gaps = list(_WORD_GAP.finditer(line))
    for m in gaps:
        if any(a <= m.start() < b for a, b in seen_spans):
            continue
        pre, _gap, suf = m.groups()
        # "_e školy", "_e sestrou": a preposition missing its consonant.
        if not pre and suf.lower() == "e" and _TOKEN.match(line[m.end():].lstrip()):
            topic, suggest, why = sz.classify("", ["se", "ze"], "", line[m.end():])
            items.append(_item("gap", m.group(0), topic, line, suggest, why))
            continue
        # A gap at the start of a word is a missing prefix: _mrzl, _míchat.
        if not pre and suf and strip(suf[0]) not in "aeiouy" and czech:
            topic, suggest, why = sz.classify("", ["s", "z", "vz"], suf, "")
            items.append(_item("gap", m.group(0), topic, line, suggest, why))
            continue
        if not pre and not suf:
            # Dotted leaders and rulers are not gaps unless the line reads as Czech.
            if czech:
                items.append(_item("gap", _context(line, m), _whole_word_topic(line), line))
            continue
        topic, suggest, why = classify_gap(pre, suf)
        # snake_case and similar: without Czech around it, a "_" needs real evidence.
        if not czech and not _looks_like_exercise(pre, suf, line, len(gaps)):
            continue
        items.append(_item("gap", m.group(0), topic, line, suggest, why))

    if not items and czech:
        tokens = [strip(t) for t in _TOKEN.findall(line)]
        question = line.rstrip().endswith("?") and bool(tokens) and len(tokens) >= 2
        instruct = bool(tokens) and bool(_IMPERATIVE.fullmatch(tokens[0]))
        if question or instruct:
            items.append(_item("question", re.sub(r"^[\d\s.,;:)„\"]+", "", line),
                               _match_topic(line) or "", line))
    return items


def _looks_like_exercise(pre, suf, line, gap_count):
    if listed_root(pre, suf):
        return True
    if pre.lower() in ("ob", "v") and suf[:1].lower() in ("e", "ě"):
        return True
    # A list of short gapped words, with nothing that reads as code.
    return gap_count >= 2 and len(pre) + len(suf) <= 8 and not re.search(r"[=(){};<>#$]", line)


def _context(line, m):
    """A few words either side of a whole-word gap."""
    before = line[:m.start()].split()[-3:]
    after = line[m.end():].split()[:3]
    return " ".join(before + ["___"] + after).lstrip(" .,;:„\"")


def analyze(lines, lang="en", limit=8):
    """Returns result dicts ready for the UI, gaps before plain questions."""
    items, seen = [], set()
    for raw in lines:
        line = " ".join(raw.split())
        if len(line) < 3:
            continue
        if len(line) > MAX_LINE:
            # Exercises are short; a huge line is page text, and could be slow to search.
            line = line[:MAX_LINE].rsplit(" ", 1)[0]
        for item in analyze_line(line):
            key = strip(item["snippet"])
            if key in seen:
                continue
            seen.add(key)
            items.append(item)
    items.sort(key=lambda i: i["kind"] != "gap")
    return [_describe(i, lang) for i in items[:limit]]


def fit_options(suggest, options):
    """Fits a suggested letter to the buttons on offer. Returns (suggestion, length is open).

    The rules decide i or y, not vowel length, so with both lengths on offer it stays open.
    """
    if suggest not in ("i", "y"):
        return suggest, False
    short, long_ = suggest, {"i": "í", "y": "ý"}[suggest]
    low = {o.strip().lower() for o in options}
    if short in low and long_ in low:
        return short, True
    if long_ in low:
        return long_, False
    return short, False


def describe_exercise(question, options, lang="en", exercise="", context=""):
    """Turns a question with known answer buttons into a result item for the bar."""
    gap = _WORD_GAP.search(question)
    low = {o.strip().lower() for o in options}
    if caps.is_size_choice(options):
        # "velké, nebo malé?": judge the gapped word, or the first word a rule can settle.
        words = [gap.group(1) + gap.group(3)] if gap else _TOKEN.findall(question)
        topic, suggest, why = "velka_pismena", "", None
        found = []
        for w in words:
            at = question.find(w)
            case, reason = caps.decide(w, question[:at] if at >= 0 else "")
            if reason:
                found.append((case, reason))
        # Every sentence's first word is capitalised, so that's the answer only when no word
        # has a rule of its own ("Bylo to v pondělí." asks about pondělí, not Bylo).
        found.sort(key=lambda f: f[1][0] == "caps_start")
        if found:
            case, why = found[0]
            suggest = caps.pick(case, options) if case else ""
    elif gap:
        pre, _mark, suf = gap.groups()
        if low & {"i", "y", "í", "ý"}:
            topic, suggest, why = classify_gap(pre, suf)
        else:
            topic, suggest, why = classify_choice(pre, options, suf, question[gap.end():],
                                                  question[:gap.start()])
    else:
        topic, suggest, why = classify_choice("", options, "")
    if topic == "gap_general":
        topic = _match_topic(question + " " + context) or topic
    suggest, length_open = fit_options(suggest, options)
    # The line also identifies the question, so include what makes it different.
    line = "%s (%s)" % (question, context) if context else question
    item = _item("question", question, topic, line, suggest, why or None)
    item["options"] = list(options)
    item["exercise"] = exercise
    item["context"] = context
    item = _describe(item, lang)
    notes = []
    if length_open:
        notes.append(_LENGTH_OPEN[lang])
    # A note beside the question can overturn a spelling rule that only sees the word.
    if context and item["suggest"]:
        notes.append(_CHECK_CONTEXT[lang])
    if notes:
        item["hint"] = " ".join([item["hint"]] + notes)
    return item


def describe_selection(text, lang="en", context="", exercise=""):
    """Result items for text the user highlighted, or [] if it holds no words."""
    text = " ".join(text.split())
    tokens = _TOKEN.findall(text)
    if not tokens or is_ignored(text):
        return []
    # A highlighted exercise line is read as an exercise, even with no Czech around it.
    if _WORD_GAP.search(text) or _CHOICE.search(text):
        found = analyze_line(text)
        if found:
            for item in found:
                item.update(context=context, exercise=exercise, selected=True)
            return [_describe(item, lang) for item in found]
    topic, why, letter = "", None, ""
    if len(tokens) == 1:
        # A known capital-letter case says more than the i/y rule does: Vánoce, pondělí.
        case, reason = caps.decide(tokens[0], "x ")
        if reason and reason[0] != "caps_adjective":
            topic, why = "velka_pismena", reason
        else:
            topic, why, letter = _explain_word(tokens[0])
    if not topic:
        topic = _match_topic(text) or _match_topic(context) or ""
    item = _item("word", text, topic, context or text, "", why)
    item.update(letter=letter, context=context if context != text else "", exercise=exercise,
                selected=True)
    return [_describe(item, lang)]


def _explain_word(word):
    """(topic, reason, consonant) for the i or y in a word: the rule a learner would need."""
    spots = [i for i, c in enumerate(word.lower()) if c in "iíyý" and i > 0]
    # A listed word is the most useful thing to say, wherever it is in the word.
    for i in spots:
        if strip(word[i]) == "y" and listed_root(word[:i], word[i + 1:]):
            return "vyjmenovana", ("listed", listed_root(word[:i], word[i + 1:])), strip(word[:i])[-1]
    for i in spots:
        pre, suf = word[:i], word[i + 1:]
        topic, suggest, why = classify_gap(pre, suf)
        # The word itself is the evidence: a rule pointing elsewhere doesn't explain it.
        if suggest in ("both", "", strip(word[i])) and topic in ("tvrde_mekke", "vyjmenovana"):
            return topic, why or None, strip(pre)[-1]
    return "", None, ""


_LENGTH_OPEN = {"cs": "Délku samohlásky urči podle výslovnosti.",
                "en": "Choose the vowel length by how the word sounds."}
_CHECK_CONTEXT = {"cs": "Ověř to podle poznámky u otázky.",
                  "en": "Check this against the note beside the question."}
_NO_RULE = {
    "cs": "Pro tuhle otázku nemám offline pravidlo. Zapni v nastavení odpovědi AI a dostaneš přesnou odpověď.",
    "en": "I don't have an offline rule for this question. Turn on AI answers in Settings for a specific answer.",
}
_FILL = {"cs": "Doplň: %s", "en": "Fill in: %s"}
_BOTH = {"cs": "y, nebo i", "en": "y or i"}
_REASONS = {
    "cs": {**sz.REASONS["cs"], **caps.REASONS["cs"], "hard": "%s je tvrdá souhláska", "soft": "%s je měkká souhláska",
           "listen": "po %s rozhoduje výslovnost", "listed": "patří k vyjmenovanému slovu (kořen %s-)",
           "prefix": "vypadá to na předponu vy-/vý-%s",
           "default": "žádné vyjmenované slovo nesedí, proto i/í%s",
           "homophone": "stejně znějí, rozhoduje význam: %s"},
    "en": {**sz.REASONS["en"], **caps.REASONS["en"], "hard": "%s is a hard consonant", "soft": "%s is a soft consonant",
           "listen": "after %s, the pronunciation decides", "listed": "it belongs to a listed word (root %s-)",
           "prefix": "looks like the prefix vy-/vý-%s",
           "default": "no listed word matches, so i/í is the default%s",
           "homophone": "same sound, meaning decides: %s"},
}


def _relevant_part(text, item):
    """Of the listed-words table, keep only the row for the letter in question."""
    if item["topic"] != "vyjmenovana" or item["why"] is None:
        return text
    letter = item.get("letter")
    if not letter:
        match = re.search(r"([bfilmpsvz])[_(….\-—]", strip(item["snippet"]))
        if not match:
            return text
        letter = match.group(1)
    letter = letter.upper()
    lines = text.split("\n")
    rows = [l for l in lines[1:] if l.startswith(letter + ":")]
    return "\n".join(lines[:1] + rows) if rows else text


def _describe(item, lang):
    topic = TOPICS.get(item["topic"])
    if topic:
        item["title"] = topic["title"][lang]
        item["text"] = _relevant_part(topic[lang], item)
    else:
        item["title"] = ({"cs": "Vybrané slovo", "en": "Selected word"} if item["kind"] == "word"
                         else {"cs": "Otázka", "en": "Question"})[lang]
        item["text"] = _NO_RULE[lang]
    reason = ""
    if item["why"]:
        code, arg = item["why"]
        if code == "homophone":
            arg = _HOMOPHONES[arg][0 if lang == "cs" else 1]
        reason = _REASONS[lang][code] % arg
    if item["suggest"]:
        shown = _BOTH[lang] if item["suggest"] == "both" else item["suggest"]
        item["hint"] = _FILL[lang] % shown + (" (%s)" % reason if reason else "")
    else:
        item["hint"] = reason
    del item["why"]
    return item
