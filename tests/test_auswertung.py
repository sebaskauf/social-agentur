import json
import tempfile
import unittest
from pathlib import Path

from _laden import ausfuehren
import auswertung


def urteil(pid, stehen=True, ende=False, stelle="", gespeichert=False, geteilt=False, an="", kommentiert=False, kat="zu_lang", zitat="zu lang"):
    return {"persona_id": pid, "stehen_geblieben": stehen, "bis_ende": ende, "absprung_stelle": stelle, "gespeichert": gespeichert,
            "geteilt": geteilt, "geteilt_an": an, "kommentiert": kommentiert, "kategorie": kat, "grund": "…", "zitat": zitat}


class TestAuswertung(unittest.TestCase):
    def setUp(self):
        self.ordner = Path(tempfile.mkdtemp())

    def schreibe(self, nr, liste, ordner=None):
        (ordner or self.ordner).joinpath("urteile_{:02d}.json".format(nr)).write_text(json.dumps(liste), encoding="utf-8")

    def test_quoten(self):
        liste = [urteil("p{:03d}".format(i), stehen=False, kat="hook_trifft_nicht", zitat="langweilig") for i in range(6)]
        liste += [urteil("p007", ende=True, gespeichert=True, geteilt=True, an="meiner Schwester", kat="stark"),
                  urteil("p008", ende=True, kommentiert=True, kat="stark"),
                  urteil("p009", stelle="Absatz 3"), urteil("p010", stelle="Absatz 3")]
        self.schreibe(1, liste)
        code, _, _ = ausfuehren(auswertung.main, ["--ordner", str(self.ordner)])
        self.assertEqual(code, 0)
        e = json.loads((self.ordner / "ergebnis.json").read_text(encoding="utf-8"))
        self.assertEqual(e["quoten"], {"wegwisch": 0.6, "ende": 0.5, "speichern": 0.1, "teilen": 0.1, "kommentieren": 0.1})
        self.assertEqual(e["haeufigste_absprung_stelle"], "Absatz 3")
        self.assertEqual(e["top_absprung_gruende"][0]["kategorie"], "hook_trifft_nicht")
        self.assertEqual(e["top_absprung_gruende"][0]["zitate"][0], "langweilig")
        self.assertEqual(e["geteilt_an"], ["meiner Schwester"])
        self.assertTrue((self.ordner / "ergebnis.md").read_text(encoding="utf-8").startswith("# Ergebnis Follower-Test"))

    def test_null_bei_leeren_feldern_ist_gueltig(self):
        a = urteil("p001", ende=True, kat="stark"); a["absprung_stelle"] = None; a["geteilt_an"] = None
        b = urteil("p002", stelle="Absatz 2"); del b["geteilt_an"]
        self.schreibe(1, [a, b])
        code, _, _ = ausfuehren(auswertung.main, ["--ordner", str(self.ordner)])
        self.assertEqual(code, 0)
        e = json.loads((self.ordner / "ergebnis.json").read_text(encoding="utf-8"))
        self.assertEqual(e["anzahl_urteile"], 2)
        self.assertEqual(e["fehler"], [])

    def test_absprung_stellen_zusammengefasst(self):
        self.assertEqual(auswertung.stelle("nach Hook (0:04)"), "0:04")
        self.assertEqual(auswertung.stelle("bei Stoppuhr (0:10)"), "0:10")
        self.assertEqual(auswertung.stelle("Absatz 2 (nach 20 Minuten-Nennung)"), "Absatz 2")
        self.assertEqual(auswertung.stelle("slide 3"), "Folie 3")
        self.assertEqual(auswertung.stelle("Hook/Intro"), "Hook")
        self.assertEqual(auswertung.stelle(""), "–")
        self.assertEqual(auswertung.stelle("Nach dem Rezept"), "Nach dem Rezept")
        liste = [urteil("p001", stelle="0:10"), urteil("p002", stelle="bei Stoppuhr (0:10)"), urteil("p003", stelle="Absatz 1")]
        self.schreibe(1, liste)
        ausfuehren(auswertung.main, ["--ordner", str(self.ordner)])
        e = json.loads((self.ordner / "ergebnis.json").read_text(encoding="utf-8"))
        self.assertEqual(e["absprung_stellen"], {"0:10": 2, "Absatz 1": 1})
        self.assertEqual(e["haeufigste_absprung_stelle"], "0:10")

    def test_kaputter_eintrag_wird_gemeldet_nicht_abgebrochen(self):
        self.schreibe(1, [urteil("p001"), {"persona_id": "p002", "stehen_geblieben": "ja"}])
        (self.ordner / "urteile_02.json").write_text("{kein json", encoding="utf-8")
        code, _, _ = ausfuehren(auswertung.main, ["--ordner", str(self.ordner)])
        self.assertEqual(code, 0)
        e = json.loads((self.ordner / "ergebnis.json").read_text(encoding="utf-8"))
        self.assertEqual(e["anzahl_urteile"], 1)
        self.assertEqual(len(e["fehler"]), 2)

    def test_widerspruch_weggewischt_aber_geteilt(self):
        self.schreibe(1, [urteil("p001", stehen=False, geteilt=True, an="x"), urteil("p002")])
        ausfuehren(auswertung.main, ["--ordner", str(self.ordner)])
        e = json.loads((self.ordner / "ergebnis.json").read_text(encoding="utf-8"))
        self.assertEqual(e["quoten"]["teilen"], 0.0)
        self.assertEqual(len(e["hinweise"]), 1)

    def test_vorher_veraenderung(self):
        vorher = Path(tempfile.mkdtemp())
        self.schreibe(1, [urteil("p001", stehen=False), urteil("p002", stehen=False)], vorher)
        self.schreibe(1, [urteil("p001", stehen=False), urteil("p002", ende=True, kat="stark")])
        ausfuehren(auswertung.main, ["--ordner", str(self.ordner), "--vorher", str(vorher)])
        e = json.loads((self.ordner / "ergebnis.json").read_text(encoding="utf-8"))
        self.assertEqual(e["vorher"]["wegwisch"], 1.0)
        self.assertEqual(e["veraenderung"]["wegwisch"], -0.5)

    def test_ohne_urteile_fehler(self):
        code, _, err = ausfuehren(auswertung.main, ["--ordner", str(self.ordner)])
        self.assertEqual(code, 2)
        self.assertIn("Keine gültigen Urteile", err)


if __name__ == "__main__":
    unittest.main()
