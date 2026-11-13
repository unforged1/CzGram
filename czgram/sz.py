"""s / z / vz as prefixes, and s / z / se / ze as prepositions.

Offline these decide only what a rule settles: a common prefixed word, the case a
preposition's noun is in when its ending shows it, and se/ze before s, š, z, ž.
Everything else gets the rule and no suggested answer.
"""
import unicodedata


def _strip(text):
    return "".join(c for c in unicodedata.normalize("NFD", text)
                   if not unicodedata.combining(c)).lower()


# Roots after the prefix, accent-free. Only words where one prefix is the standard
# spelling; meaning pairs such as sběhnout (run down) / zběhnout (desert) stay out.
_PREFIXED = {
    "s": ("michat", "smichat", "pojit", "ejmout", "ecist", "ectl", "jet", "jezd", "letet", "letl",
          "louc", "epsat", "vazat", "vazal", "esit", "hromazd", "tahnout", "tahl", "padnout", "padl",
          "loz", "raz", "chovat", "chova", "estoupit", "vlekn", "vlekl", "birat", "bira", "tekat",
          "teka", "jednot", "bliz", "hnit", "hnil", "mazat", "maza"),
    "z": ("mrz", "cerven", "hasn", "hasl", "meri", "meril", "mizet", "mizel", "leps", "hors",
          "mens", "vets", "nic", "ranit", "ranil", "kazit", "kazil", "kusit", "kusil", "eptat", "eptal",
          "jist", "volit", "volil", "hubn", "trat", "redit", "bavit", "bavil", "menit", "menil",
          "bledn", "bledl", "chladn", "chladl", "kontrol", "vedn", "vedl", "krot", "tichn",
          "tichl", "mlkn", "mlkl"),
    "vz": ("letn", "letl", "kvet", "pomen", "pomin", "budit", "budil", "dalit", "dalil", "dych",
           "plan", "primit", "primil", "tyc", "bour", "dor", "hled", "duch"),
}
# Endings that only the instrumental has here answer "s kým? s čím?" and call for s.
_INSTRUMENTAL = ("ou", "em", "ím", "ým", "ami", "emi", "mi", "ma")
# Endings that only the genitive has here answer "z čeho?" and call for z. Endings
# shared by both cases (-y, -i, -í: s hrady × z ženy) are left undecided.
_GENITIVE = ("a", "u", "e", "ě", "ů", "ch")
# Words that take se/ze though they don't start with s, š, z or ž.
_ALWAYS_VOCALISED = {"mnou", "mne", "mě", "mně", "dne", "tří", "čtyř", "třemi", "čtyřmi", "všech",
                     "všemi", "všeho", "vším", "psem"}


def prefix(stem, options):
    """(letter, reason code) for a prefix gap such as _míchat, or ("", None)."""
    root = _strip(stem)
    longest = {}
    for letter, roots in _PREFIXED.items():
        if letter in options:
            longest[letter] = max((len(r) for r in roots if root.startswith(r)), default=0)
    found = [letter for letter, n in longest.items() if n]
    if len(found) != 1:
        # sletět (fly down) and vzlétnout (fly up) share a root: only the meaning decides.
        return "", (("sz_meaning", stem) if found else None)
    return found[0], ("sz_prefix", found[0])


def _looks_prefixed(word, options):
    """A spaced choice followed by a known prefixed root, and no case ending, is a prefix."""
    letter, _why = prefix(word, options)
    return bool(letter) and not word.lower().endswith(_INSTRUMENTAL + _GENITIVE)


def preposition(following, options):
    """(answer, reason code) for a preposition choice, from the word after it."""
    words = following.split()
    word = words[0].strip(".,;:!?„“\"()") if words else ""
    if not word:
        return "", None
    low = word.lower()
    vocal = low[:1] in "sšzž" or low in _ALWAYS_VOCALISED
    letter, why = "", None
    if options & {"s", "se"} and options & {"z", "ze"}:
        # s or z depends on the case, which only some endings give away.
        if low.endswith(_INSTRUMENTAL):
            letter, why = "s", ("sz_case7", word)
        elif low.endswith(_GENITIVE):
            letter, why = "z", ("sz_case2", word)
        else:
            return "", ("sz_case_open", word)
    else:
        letter = "s" if options & {"s", "se"} else "z"
    long_form = letter + "e"
    if long_form in options and letter in options:
        answer = long_form if vocal else letter
        return answer, why or (("sz_vocal" if vocal else "sz_plain"), word)
    if long_form in options:
        return long_form, why
    return letter if letter in options else "", why


def classify(pre, options, suf, following):
    """(topic, suggestion, reason) for any s/z/vz/se/ze choice."""
    low = {o.strip().lower() for o in options}
    word = following.split()[0].strip(".,;:!?„“\"()") if following.split() else ""
    # vz- is never a preposition, so "s/z/vz létlo" is a prefix written apart from its word.
    if not suf and not pre and word and ("vz" in low or _looks_prefixed(word, low)):
        suf = word
    if suf and not pre:
        letter, why = prefix(suf, low)
        return "s_z_predpony", letter, why
    if suf or pre:
        return "s_z_predpony", "", None
    answer, why = preposition(following, low)
    return "s_z_predlozky", answer, why


REASONS = {
    "cs": {"sz_meaning": "u „%s“ rozhoduje význam: s- dolů nebo dohromady, z- změna, vz- nahoru",
           "sz_prefix": "běžná předpona %s-", "sz_case7": "„%s“ je v 7. pádě (s kým? s čím?)",
           "sz_case2": "„%s“ je ve 2. pádě (z čeho?)",
           "sz_case_open": "rozhoduje pád slova „%s“: s + 7. pád, z + 2. pád",
           "sz_vocal": "před „%s“ se píše se/ze", "sz_plain": "před „%s“ stačí s/z"},
    "en": {"sz_meaning": "for “%s” the meaning decides: s- down or together, z- a change, vz- upward",
           "sz_prefix": "the usual prefix is %s-", "sz_case7": "“%s” is instrumental (s kým? s čím?)",
           "sz_case2": "“%s” is genitive (z čeho?)",
           "sz_case_open": "the case of “%s” decides: s + instrumental, z + genitive",
           "sz_vocal": "se/ze is used before “%s”", "sz_plain": "plain s/z fits before “%s”"},
}
