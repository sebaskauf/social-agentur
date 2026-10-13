import json
import os
import tempfile
import unittest
from pathlib import Path

from _laden import GEHEIM_APIFY, GEHEIM_IG, PROFIL, ausfuehren, temp_home
import check


class TestCheck(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(ig_alter_tage=55)
        self.arbeit = Path(tempfile.mkdtemp())
        self.alt = os.getcwd()
        os.chdir(self.arbeit)

    def tearDown(self):
        os.chdir(self.alt)

    def test_keine_schluessel_in_der_ausgabe(self):
        for argv in ([], ["--lesbar"]):
            code, out, err = ausfuehren(check.main, argv)
            self.assertEqual(code, 0)
            self.assertNotIn(GEHEIM_IG, out + err)
            self.assertNotIn(GEHEIM_APIFY, out + err)

    def test_token_existenz_und_alter(self):
        s = check.stand()
        self.assertTrue(s["apify"]["ok"])
        self.assertTrue(s["instagram"]["ok"])
        self.assertEqual(s["instagram"]["alter_tage"], 55)
        self.assertIn("bald erneuern", check.lesbar(s))

    def test_ohne_schluessel_und_profil(self):
        temp_home(mit_tokens=False)
        s = check.stand()
        self.assertFalse(s["apify"]["ok"])
        self.assertFalse(s["instagram"]["ok"])
        self.assertFalse(s["profil"]["ok"])
        self.assertIn("❌ Profil", check.lesbar(s))

    def test_profil_mit_zielgruppe(self):
        (self.arbeit / "meine-agentur").mkdir()
        (self.arbeit / "meine-agentur" / "profil.md").write_text(PROFIL, encoding="utf-8")
        self.assertTrue(check.stand()["profil"]["ok"])

    def test_scrapling_in_eigener_venv_wird_erkannt(self):
        cli = self.home / "venv" / "bin" / "scrapling"
        cli.parent.mkdir(parents=True)
        cli.write_text("#!/bin/sh\n", encoding="utf-8")
        s = check.pruefe_scrapling()
        self.assertTrue(s["ok"])
        self.assertEqual(s["cli"], str(cli))


if __name__ == "__main__":
    unittest.main()
