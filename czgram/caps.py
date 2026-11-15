"""Capital letters (velká písmena): when a Czech word starts with a capital.

Offline this settles the common cases: the start of a sentence, days and months,
languages and inhabitants, holidays, well-known places and possessive adjectives.
Words whose case depends on meaning (Země the planet × země the soil) are named as
such and left to the reader or the AI.
"""
import re

_LOWER = {}
_UPPER = {}
_MEANING = {}


def _add(table, reason, words):
    for w in words.split():
        table[w] = reason


# Keys are lower-case with accents kept: stripping them would merge Češka and česká.
_add(_LOWER, "day", "pondělí úterý středa středu středy čtvrtek čtvrtku pátek pátku sobota sobotu soboty "
                    "neděle neděli")
_add(_LOWER, "month", "leden ledna únor února březen března duben dubna květen května červen června "
                      "červenec července srpen srpna září říjen října listopad listopadu prosinec prosince")
_add(_LOWER, "language", "čeština češtinu češtiny češtině slovenština slovenštinu angličtina angličtinu "
                         "angličtiny angličtině němčina němčinu němčiny francouzština francouzštinu "
                         "španělština italština ruština ruštinu polština maďarština ukrajinština latina "
                         "latinu japonština čínština česky slovensky anglicky německy francouzsky rusky")
_add(_UPPER, "people", "čech čecha čechovi čechem češi čechů čechům češka češky slovák slováka slováci "
                       "slovenka němec němce němci němců němka angličan angličané američan američané "
                       "evropan evropané pražan pražané pražák brňan ostravan rus rusové polák poláci "
                       "ital italové španěl španělé maďar ukrajinec francouz francouzi")
_add(_UPPER, "holiday", "vánoce vánoc vánocům vánocích vánocemi velikonoce velikonoc velikonocích "
                        "silvestr silvestra silvestru")
_add(_UPPER, "place", "česko česka česku českem čechy čechách praha prahy praze prahu prahou "
                      "brno brna brně brnem ostrava ostravy ostravě ostravu ostravou evropa evropy evropě "
                      "evropu evropou amerika ameriky americe ameriku německo německa německu německem "
                      "slovensko slovenska slovensku rakousko rakouska rakousku vltava vltavy vltavě vltavu "
                      "vltavou labe labi labem morava moravy moravě moravu moravou krkonoše krkonoš "
                      "krkonoších šumava šumavy šumavě šumavu šumavou sněžka sněžky sněžce sněžku "
                      "karlštejn karlštejna říp řípu plzeň plzně plzni olomouc olomouce")
_add(_MEANING, "meaning", "země zemi zemí slunce slunci měsíc měsíce měsíci bůh boha bohu vy vás vám vámi "
                          "váš vaše vašeho mikuláš mikuláše")
# "Čech" is both a Czech person and a form of Čechy (Bohemia). Both are capitalised; it's
# listed once, under people.
_SENTENCE_END = re.compile(r"(?:^|[.!?]\s*|[.!?][\"“„»]\s*|:\s*[\"“„«])$")


def decide(word, before=""):
    """("upper" | "lower" | "", reason code) for a word in lower case, given the text before it."""
    w = word.lower()
    if not w:
        return "", None
    if _SENTENCE_END.search(before.rstrip()) or not before.strip(" („\"“"):
        return "upper", ("caps_start", word)
    if w in _UPPER:
        return "upper", ("caps_" + _UPPER[w], word)
    if w in _LOWER:
        return "lower", ("caps_" + _LOWER[w], word)
    if w in _MEANING:
        return "", ("caps_meaning", word)
    # Possessive adjectives from names: Karlův most, Petrův dům.
    if w.endswith("ův") and len(w) > 3:
        return "upper", ("caps_possessive", word)
    # Adjectives from places are lower case (pražský, český) unless they open a name.
    if re.search(r"(?:sk|ck)(?:ý|á|é|ého|ému|ém|ým|ou|ých|ými|í)$", w):
        return "lower", ("caps_adjective", word)
    return "", None


def is_case_pair(options):
    """True for choices like V/v or Č/č: the same letter in both cases."""
    opts = [o.strip() for o in options]
    return (len(opts) == 2 and all(len(o) == 1 and o.isalpha() for o in opts)
            and opts[0].lower() == opts[1].lower() and opts[0] != opts[1])


def is_size_choice(options):
    """True for buttons that ask "velké, nebo malé?" (capital or small letter)."""
    low = [o.strip().lower() for o in options]
    return len(low) == 2 and {o.split()[0][:4] for o in low if o} == {"velk", "malé"[:4]}


def pick(case, options):
    """The option matching "upper"/"lower" among V/v or velké/malé buttons."""
    for o in options:
        s = o.strip()
        if is_case_pair(options):
            if (case == "upper") == s.isupper():
                return s
        elif s.lower().startswith("velk" if case == "upper" else "mal"):
            return s
    return ""


REASONS = {
    "cs": {"caps_start": "„%s“ začíná větu", "caps_day": "„%s“: dny se píšou s malým písmenem",
           "caps_month": "„%s“: měsíce se píšou s malým písmenem",
           "caps_language": "„%s“: jazyky se píšou s malým písmenem",
           "caps_people": "„%s“: obyvatelé a národy se píšou s velkým písmenem",
           "caps_holiday": "„%s“: svátky se píšou s velkým písmenem",
           "caps_place": "„%s“ je zeměpisné jméno",
           "caps_possessive": "„%s“ je přivlastňovací přídavné jméno od jména",
           "caps_adjective": "„%s“: přídavná jména od míst se píšou s malým, pokud nezačínají jméno",
           "caps_meaning": "u „%s“ rozhoduje význam (Země planeta × země půda, Vy z úcty × vy)"},
    "en": {"caps_start": "“%s” starts a sentence", "caps_day": "“%s”: days are lower case",
           "caps_month": "“%s”: months are lower case", "caps_language": "“%s”: languages are lower case",
           "caps_people": "“%s”: inhabitants and nationalities are capitalised",
           "caps_holiday": "“%s”: holidays are capitalised", "caps_place": "“%s” is a place name",
           "caps_possessive": "“%s” is a possessive adjective from a name",
           "caps_adjective": "“%s”: adjectives from places are lower case unless they open a name",
           "caps_meaning": "for “%s” the meaning decides (Země the planet × země soil, Vy of respect × vy)"},
}
