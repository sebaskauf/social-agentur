import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _laden import GEHEIM_IG, ausfuehren, temp_home
import _gemeinsam as G
import instagram


class TestInstagram(unittest.TestCase):
    def setUp(self):
        temp_home(ig_alter_tage=3)
        self.aufrufe = []

    def netz(self, antworten):
        def http(methode, url, daten=None, header=None, timeout=60, roh=False):
            self.aufrufe.append((methode, url, daten, header))
            for teil, antwort in antworten:
                if teil in url:
                    if isinstance(antwort, Exception):
                        raise antwort
                    return antwort
            raise AssertionError("unerwartete Anfrage")
        return http

    def test_url_bau(self):
        u = instagram.url("/me", fields="username")
        self.assertTrue(u.startswith("https://graph.instagram.com/v24.0/me?"))
        self.assertIn("fields=username", u)
        self.assertIn("access_token=", u)
        self.assertNotIn(GEHEIM_IG, G.maske(u))

    def test_status_ohne_schluessel_in_ausgabe(self):
        with mock.patch.object(G, "http", self.netz([("/me?", {"username": "test", "account_type": "MEDIA_CREATOR", "followers_count": 5, "media_count": 2})])):
            code, out, err = ausfuehren(instagram.main, ["status", "--json"])
        self.assertEqual(code, 0)
        erg = json.loads(out)
        self.assertTrue(erg["professional"])
        self.assertEqual(erg["schluessel_alter_tage"], 3)
        self.assertNotIn(GEHEIM_IG, out + err)

    def test_fehler_190_verstaendlich_und_maskiert(self):
        fehler = G.ApiFehler('HTTP 400: {"error":{"code":190,"type":"OAuthException"}} https://graph.instagram.com/me?access_token=' + GEHEIM_IG)
        with mock.patch.object(G, "http", self.netz([("/me?", fehler)])):
            code, out, err = ausfuehren(instagram.main, ["status"])
        self.assertEqual(code, 2)
        self.assertIn("abgelaufen", err)
        self.assertNotIn(GEHEIM_IG, out + err)

    def test_bestaetigt_sperre(self):
        for argv in (["antworten", "123", "--text", "Danke!"], ["ausblenden", "123"], ["nachricht-senden", "9", "--text", "Hallo"],
                     ["posten-bild", "--url", "https://x/b.jpg", "--caption", "c"],
                     ["posten-karussell", "--urls", "https://x/1.jpg,https://x/2.jpg"],
                     ["posten-reel", "--url", "https://x/r.mp4"]):
            with mock.patch.object(G, "http", self.netz([])):
                code, out, _ = ausfuehren(instagram.main, argv)
            self.assertEqual(code, 0, argv)
            self.assertIn("Nur Vorschau", out)
        self.assertEqual(self.aufrufe, [], "ohne --bestaetigt darf keine Anfrage rausgehen")

    def test_antworten_mit_bestaetigung(self):
        with mock.patch.object(G, "http", self.netz([("/123/replies", {"id": "r1"})])):
            code, out, _ = ausfuehren(instagram.main, ["antworten", "123", "--text", "Danke!", "--bestaetigt"])
        self.assertEqual(code, 0)
        self.assertEqual(self.aufrufe[0][0], "POST")
        self.assertIn("message=Danke%21", self.aufrufe[0][1])

    def test_insights_einzeln_nachfragen(self):
        def http(methode, url, daten=None, header=None, timeout=60, roh=False):
            self.aufrufe.append(url)
            if "metric=views%2C" in url:
                raise G.ApiFehler("HTTP 400: metric not supported")
            if "metric=views" in url:
                return {"data": [{"name": "views", "values": [{"value": 10}]}]}
            if "metric=reach" in url:
                return {"data": [{"name": "reach", "values": [{"value": 8}]}]}
            if "metric=" in url:
                raise G.ApiFehler("HTTP 400: metric not supported")
            return {"id": "1", "media_product_type": "FEED", "timestamp": "2026-10-01T00:00:00+0000", "caption": "x"}
        with mock.patch.object(G, "http", http):
            code, out, _ = ausfuehren(instagram.main, ["insights", "1", "--json"])
        self.assertEqual(code, 0)
        w = json.loads(out)[0]["insights"]
        self.assertEqual(w["views"], 10)
        self.assertEqual(w["reach"], 8)
        self.assertEqual(w["shares"], "–")

    def test_reel_von_datei_klare_meldung_ohne_anfrage(self):
        with mock.patch.object(G, "http", self.netz([])):
            code, _, err = ausfuehren(instagram.main, ["posten-reel", "--datei", "video.mp4", "--bestaetigt"])
        self.assertEqual(code, 2)
        self.assertIn("öffentlich erreichbare video_url", err)
        self.assertEqual(self.aufrufe, [])

    def test_reel_nur_hochladen_veroeffentlicht_nicht(self):
        antworten = [("/me/media?", {"id": "c1"}), ("/c1?", {"status_code": "FINISHED"})]
        with mock.patch.object(G, "http", self.netz(antworten)), mock.patch.object(instagram.time, "sleep"):
            code, out, _ = ausfuehren(instagram.main, ["posten-reel", "--url", "https://x/r.mp4", "--nur-hochladen", "--json"])
        self.assertEqual(code, 0)
        self.assertFalse(json.loads(out)["veroeffentlicht"])
        self.assertIn("media_type=REELS", self.aufrufe[0][1])
        self.assertFalse(any("media_publish" in a[1] for a in self.aufrufe))

    def test_erneuern_schreibt_neuen_schluessel(self):
        temp_home(ig_alter_tage=40)
        with mock.patch.object(G, "http", self.netz([("refresh_access_token", {"access_token": "NEU123", "expires_in": 5184000})])):
            code, out, _ = ausfuehren(instagram.main, ["erneuern"])
        self.assertEqual(code, 0)
        self.assertIn("60 Tage", out)
        self.assertEqual((G.daten_ordner() / "instagram_token").read_text().strip(), "NEU123")


if __name__ == "__main__":
    unittest.main()
