"""s/z/vz prefixes, s/z/se/ze prepositions, and repairing how OCR reads them."""
import unittest

from czgram.analyze import analyze, describe_exercise
from czgram.ocr import repair_choices


def first(line):
    return analyze([line])[0]


class Prefixes(unittest.TestCase):
    def test_known_words(self):
        cases = {"Musíme (s/z)míchat těsto.": "s", "Led _mrzl přes noc.": "z", "Musíme _míchat těsto.": "s",
                 "Květiny (s/z/vz)kvétají na jaře.": "vz", "Rád _čerVENAL hned.": "z"}
        for line, answer in cases.items():
            self.assertEqual(first(line)["suggest"], answer, line)

    def test_shared_roots_stay_open(self):
        for line in ("Letadlo s/z/vz létlo vysoko.", "Sníh (s/z)letěl ze střechy.", "(s/z)běhnout dolů"):
            self.assertEqual(first(line)["suggest"], "", line)
        self.assertIn("meaning", first("Letadlo s/z/vz létlo vysoko.")["hint"])

    def test_vz_choice_is_always_a_prefix(self):
        self.assertEqual(first("Letadlo s/z/vz létlo vysoko.")["topic"], "s_z_predpony")

    def test_only_offered_options(self):
        self.assertEqual(describe_exercise("_kvétat", ["s", "z"], "en")["suggest"], "")


class Prepositions(unittest.TestCase):
    def test_vocalised_before_s_s_z_z(self):
        cases = {"Vrátil se (z/ze) školy.": "ze", "Šel do kina (s/se) sestrou.": "se",
                 "Přišla z/ze zahrady.": "ze", "Mluvil s/se mnou.": "se", "Vrátil se z/ze lesa.": "z",
                 "Šel s/se kamarádem.": "s"}
        for line, answer in cases.items():
            self.assertEqual(first(line)["suggest"], answer, line)

    def test_case_from_the_ending(self):
        self.assertEqual(first("Šel s/z kamarádem.")["suggest"], "s")
        self.assertEqual(first("Bez s/z domů.")["suggest"], "z")
        self.assertEqual(first("Vypadl s/z okna.")["suggest"], "z")

    def test_shared_endings_stay_open(self):
        for line in ("Vzal to s/z poličky.", "Přišel _e školy."):
            self.assertEqual(first(line)["suggest"], "", line)
        self.assertIn("case", first("Vzal to s/z poličky.")["hint"])

    def test_missing_consonant(self):
        self.assertEqual(first("Šli _e sestrou domů.")["suggest"], "se")

    def test_buttons(self):
        item = describe_exercise("Vrátil se _ školy.", ["z", "ze"], "cs")
        self.assertEqual((item["suggest"], item["topic"]), ("ze", "s_z_predlozky"))
        self.assertTrue(item["hint"].startswith("Doplň: ze"))

    def test_other_choices_unaffected(self):
        self.assertEqual(first("Maminka b(i/y)dlí doma.")["topic"], "vyjmenovana")
        self.assertEqual(first("Mluví o (mě/mně) a o tobě.")["topic"], "me_mne")


class OcrRepair(unittest.TestCase):
    def test_misreads(self):
        cases = {"Vzal to slz poličky.": "Vzal to s/z poličky.", "Přišla zíze zahrady.": "Přišla z/ze zahrady.",
                 "Vrátil se (2/ze) školy.": "Vrátil se (z/ze) školy.", "Mluvil sse mnou.": "Mluvil s/se mnou.",
                 "Květiny (slzivz)kvétají": "Květiny (s/z/vz)kvétají", "Letadlo 5/z/vz létlo": "Letadlo s/z/vz létlo",
                 "Přišla zéze zahrady": "Přišla z/ze zahrady", "Vzal to síz poličky.": "Vzal to s/z poličky.",
                 "Vzal to s|z poličky.": "Vzal to s/z poličky."}
        for read, fixed in cases.items():
            self.assertEqual(repair_choices(read), fixed, read)

    def test_real_czech_is_left_alone(self):
        for line in ("Byla plná slz smutku.", "zase sešit z lesa", "Jsem se sestrou.", "S kamarádem a z lesa.",
                     "Je to 5 km.", "Vzal to s poličky.", "souhláska z, hláska s"):
            self.assertEqual(repair_choices(line), line, line)


class AiInstructions(unittest.TestCase):
    def test_rules_and_list_reach_the_model(self):
        from czgram import ai
        text = ai.SYSTEM.format(language="English", listed=ai._listed_words())
        self.assertIn("B: být, bydlit", text)
        self.assertIn("Z: brzy, jazyk", text)
        self.assertIn("vz- means upward", text)
        self.assertIn("se/ze", text)
        self.assertNotIn("{", text)


if __name__ == "__main__":
    unittest.main()
