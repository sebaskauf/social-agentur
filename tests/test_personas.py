import json
import tempfile
import unittest
from pathlib import Path

from _laden import PROFIL, ausfuehren
import personas


class TestPersonas(unittest.TestCase):
    def setUp(self):
        self.ordner = Path(tempfile.mkdtemp())
        self.profil = self.ordner / "profil.md"
        self.profil.write_text(PROFIL, encoding="utf-8")

    def test_gleicher_seed_gleiche_personas(self):
        zg = personas.lies_zielgruppe(self.profil)
        self.assertEqual(personas.ziehe_personas(zg, 100, 42), personas.ziehe_personas(zg, 100, 42))
        self.assertNotEqual(personas.ziehe_personas(zg, 100, 42), personas.ziehe_personas(zg, 100, 43))

    def test_anzahl_felder_und_werte(self):
        zg = personas.lies_zielgruppe(self.profil)
        liste = personas.ziehe_personas(zg, 100, 1)
        self.assertEqual(len(liste), 100)
        self.assertEqual(liste[0]["persona_id"], "p001")
        self.assertEqual(liste[-1]["persona_id"], "p100")
        felder = {"persona_id", "alter", "lebenslage", "interessen", "scroll_tempo", "teil_verhalten", "plattform", "einwand"}
        for p in liste:
            self.assertEqual(set(p), felder)
            self.assertTrue(25 <= p["alter"] <= 45)
            self.assertIn(p["lebenslage"], zg["lebenslagen"])
            self.assertIn(len(p["interessen"]), (2, 3))
            # genau ein fremdes Allgemein-Interesse
            self.assertEqual(sum(1 for i in p["interessen"] if i not in zg["interessen"]), 1)
            self.assertIn(p["scroll_tempo"], ("schnell", "mittel", "langsam"))
            self.assertIn(p["teil_verhalten"], ("selten", "manchmal", "oft"))
        tempi = [p["scroll_tempo"] for p in personas.ziehe_personas(zg, 2000, 5)]
        self.assertAlmostEqual(tempi.count("schnell") / 2000, 0.5, delta=0.05)

    def test_dateien_zu_je_zehn(self):
        ziel = self.ordner / "tests" / "beitrag"
        code, out, _ = ausfuehren(personas.main, ["ziehen", "--profil", str(self.profil), "--anzahl", "100", "--seed", "3", "--ziel", str(ziel)])
        self.assertEqual(code, 0)
        dateien = sorted(ziel.glob("personas_*.json"))
        self.assertEqual([d.name for d in dateien][:2], ["personas_01.json", "personas_02.json"])
        self.assertEqual(len(dateien), 10)
        self.assertTrue(all(len(json.loads(d.read_text(encoding="utf-8"))) == 10 for d in dateien))
        self.assertEqual(json.loads(out)["personas"], 100)

    def test_schnell_sind_zwanzig(self):
        ziel = self.ordner / "schnell"
        ausfuehren(personas.main, ["ziehen", "--profil", str(self.profil), "--schnell", "--seed", "3", "--ziel", str(ziel)])
        self.assertEqual(len(list(ziel.glob("personas_*.json"))), 2)

    def test_fehlender_block_deutsche_meldung(self):
        kaputt = self.ordner / "leer.md"
        kaputt.write_text("# Profil ohne Block\n", encoding="utf-8")
        code, _, err = ausfuehren(personas.main, ["ziehen", "--profil", str(kaputt), "--seed", "1", "--ziel", str(self.ordner / "x")])
        self.assertEqual(code, 2)
        self.assertIn("/agentur start", err)
        self.assertIn("zielgruppe", err)


if __name__ == "__main__":
    unittest.main()
