import json
import unittest
from unittest import mock

from _laden import GEHEIM_APIFY, ausfuehren, temp_home
import _gemeinsam as G
import apify

AKTEUR = {"data": {"pricingInfos": [{"pricingPerEvent": {"actorChargeEvents": {
    "reel": {"eventTieredPricingUsd": {"FREE": {"tieredEventPriceUsd": 0.0026}, "GOLD": {"tieredEventPriceUsd": 0.001}}},
    "actor-start": {"eventTieredPricingUsd": {"FREE": {"tieredEventPriceUsd": 0.001}}}}}}]}}


class TestApify(unittest.TestCase):
    def setUp(self):
        temp_home()
        self.aufrufe = []

    def falsches_netz(self, antworten):
        def http(methode, url, daten=None, header=None, timeout=60, roh=False):
            self.aufrufe.append((methode, url, daten, header))
            for teil, antwort in antworten:
                if teil in url:
                    return antwort
            raise AssertionError("unerwartete Anfrage " + url)
        return http

    def test_schaetzung_ohne_lauf(self):
        with mock.patch.object(G, "http", self.falsches_netz([("/acts/apify~instagram-reel-scraper", AKTEUR)])):
            code, out, _ = ausfuehren(apify.main, ["reels", "--accounts", "@a,https://www.instagram.com/b/", "--tage", "30",
                                                   "--max-ergebnisse", "30", "--max-kosten", "0.5", "--json"])
        self.assertEqual(code, 0)
        plan = json.loads(out)
        self.assertFalse(plan["gestartet"])
        self.assertEqual(plan["accounts"], ["a", "b"])
        self.assertAlmostEqual(plan["geschaetzte_kosten_usd"], 0.001 + 2 * 30 * 0.0026, places=4)
        self.assertTrue(all(m == "GET" for m, *_ in self.aufrufe), "ohne --bestaetigt darf nichts gestartet werden")

    def test_lauf_mit_bestaetigung_und_auswertung(self):
        items = [{"ownerUsername": "a", "videoPlayCount": v, "timestamp": "2026-10-01T10:00:00Z", "caption": "Hook {}".format(v), "url": "https://x/{}".format(v)}
                 for v in (100, 120, 110, 900)]
        netz = self.falsches_netz([("/acts/apify~instagram-reel-scraper/runs", {"data": {"id": "lauf1", "defaultDatasetId": "ds1"}}),
                                   ("/acts/apify~instagram-reel-scraper", AKTEUR),
                                   ("/actor-runs/lauf1", {"data": {"status": "SUCCEEDED", "usageTotalUsd": 0.012}}),
                                   ("/datasets/ds1/items", items)])
        with mock.patch.object(G, "http", netz), mock.patch.object(apify.time, "sleep"):
            code, out, _ = ausfuehren(apify.main, ["reels", "--accounts", "a", "--tage", "30", "--max-kosten", "0.2", "--bestaetigt", "--json"])
        self.assertEqual(code, 0)
        erg = json.loads(out)
        start = [a for a in self.aufrufe if a[0] == "POST"][0]
        self.assertIn("maxTotalChargeUsd=0.2", start[1])
        self.assertEqual(start[2]["username"], ["a"])
        self.assertFalse(start[2]["skipTrialReels"])
        a = erg["accounts_auswertung"]["a"]
        self.assertEqual(a["median_aufrufe"], 115.0)
        self.assertEqual([r["aufrufe"] for r in a["ausreisser"]], [900])
        self.assertEqual(erg["tatsaechliche_kosten_usd"], 0.012)

    def test_schluessel_wird_maskiert(self):
        apify.token()
        fehler = G.ApiFehler("HTTP 401: Bearer {} ungültig, token={}".format(GEHEIM_APIFY, GEHEIM_APIFY))
        self.assertNotIn(GEHEIM_APIFY, str(fehler))

    def test_check_fehler_ohne_schluessel_in_ausgabe(self):
        def http(*a, **k):
            raise G.ApiFehler("HTTP 401: invalid token " + GEHEIM_APIFY, code=401)
        with mock.patch.object(G, "http", http):
            code, out, err = ausfuehren(apify.main, ["check"])
        self.assertEqual(code, 2)
        self.assertNotIn(GEHEIM_APIFY, out + err)
        self.assertIn("nicht akzeptiert", err)

    def test_ohne_schluessel_klare_meldung(self):
        temp_home(mit_tokens=False)
        code, _, err = ausfuehren(apify.main, ["check"])
        self.assertEqual(code, 2)
        self.assertIn("noch nicht eingerichtet", err)


    def test_kaputte_schluessel_datei_ohne_traceback_und_ohne_inhalt(self):
        ordner = temp_home(mit_tokens=False)
        faelle = [b"\x89PNG\r\n\x1a\n\xe3\x81 kein text",                      # Bild in der Zwischenablage
                  (GEHEIM_APIFY + "\nnoch etwas anderes kopiert").encode("utf-8"),  # Schlüssel plus Fremdtext
                  b"kurz"]
        for inhalt in faelle:
            G._GEHEIMNISSE.clear()
            (ordner / "apify_token").write_bytes(inhalt)
            def http(*a, **k):
                raise AssertionError("darf mit kaputtem Schlüssel keine Anfrage senden")
            with mock.patch.object(G, "http", http):
                code, out, err = ausfuehren(apify.main, ["check"])
            self.assertEqual(code, 2)
            self.assertIn("keinen gültigen Zugangsschlüssel", err)
            self.assertNotIn("Traceback", out + err)
            self.assertNotIn(GEHEIM_APIFY, out + err)
            self.assertNotIn("anderes kopiert", out + err)


if __name__ == "__main__":
    unittest.main()
