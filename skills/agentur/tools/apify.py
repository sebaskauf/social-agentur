#!/usr/bin/env python3
"""Konkurrenz-Daten über die Apify-API (optional). Schlüssel aus ~/.social-agentur/apify_token, wird nie ausgegeben.

Aufruf:
  python3 apify.py check
  python3 apify.py reels --accounts a,b,c --tage 30 [--max-ergebnisse 30] --max-kosten 0.50            (nur Schätzung)
  python3 apify.py reels --accounts a,b,c --tage 30 [--max-ergebnisse 30] --max-kosten 0.50 --bestaetigt  (startet den Lauf)
"""
import argparse
import datetime
import json
import statistics
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _gemeinsam as G  # noqa: E402

API = "https://api.apify.com/v2"
ACTOR = "apify~instagram-reel-scraper"
ERSATZ_PREIS_REEL = 0.0026   # höchster Tarifpreis pro Reel, falls der Preis nicht abrufbar ist
ERSATZ_PREIS_START = 0.001
WARTE_SEKUNDEN = 5
MAX_WARTEZEIT = 15 * 60


def token():
    t = G.lies_token("apify_token")
    if not t:
        G.fehler_ende("Apify ist noch nicht eingerichtet. Starte /agentur einrichten full oder lies in der README den Abschnitt „Apify“.")
    return t


def anfrage(methode, pfad, daten=None, mit_token=True, roh=False, timeout=60):
    kopf = {"Authorization": "Bearer " + token()} if mit_token else {}
    return G.http(methode, API + pfad, daten=daten, header=kopf, timeout=timeout, roh=roh)


def befehl_check(als_json):
    try:
        ich = anfrage("GET", "/users/me")["data"]
        grenzen = anfrage("GET", "/users/me/limits")["data"]
    except G.ApiFehler as e:
        if e.code in (401, 403):
            G.fehler_ende("Der Apify-Schlüssel wird nicht akzeptiert. Kopiere ihn in der Apify Console neu und speichere ihn mit dem sicheren Befehl aus der README.")
        G.fehler_ende("Apify antwortet nicht wie erwartet: {}".format(e))
    limit = (grenzen.get("limits") or {}).get("maxMonthlyUsageUsd")
    verbraucht = (grenzen.get("current") or {}).get("monthlyUsageUsd")
    rest = round(limit - verbraucht, 2) if isinstance(limit, (int, float)) and isinstance(verbraucht, (int, float)) else None
    if isinstance(verbraucht, (int, float)):
        verbraucht = round(verbraucht, 2)
    ergebnis = {"konto": ich.get("username"), "tarif": (ich.get("plan") or {}).get("id"),
                "monatslimit_usd": limit, "verbraucht_usd": verbraucht, "verbleibend_usd": rest,
                "zyklus_ende": (grenzen.get("monthlyUsageCycle") or {}).get("endAt")}
    lesbar = "Apify-Konto: {}\nTarif: {}\nDiesen Monat verbraucht: {} $ von {} $ (verbleibend: {} $)".format(
        ergebnis["konto"], ergebnis["tarif"], verbraucht, limit, rest)
    G.drucke(ergebnis, lesbar, als_json)
    return 0


def preise():
    """Aktueller Preis pro Reel und pro Start laut Apify. Nimmt den höchsten Tarif als sichere Obergrenze."""
    try:
        akteur = anfrage("GET", "/acts/" + ACTOR)["data"]
        info = (akteur.get("pricingInfos") or [])[-1]
        ereignisse = info["pricingPerEvent"]["actorChargeEvents"]

        def hoechster(ereignis):
            stufen = ereignisse[ereignis]["eventTieredPricingUsd"]
            return max(v["tieredEventPriceUsd"] for v in stufen.values())
        return hoechster("reel"), hoechster("actor-start"), "laut Apify (höchster Tarif)"
    except (G.ApiFehler, KeyError, IndexError, TypeError, ValueError):
        return ERSATZ_PREIS_REEL, ERSATZ_PREIS_START, "Ersatzwert, Preis nicht abrufbar"


def normalisiere(account):
    a = account.strip()
    if "instagram.com/" in a:
        a = a.split("instagram.com/", 1)[1].split("/")[0].split("?")[0]
    return a.lstrip("@").strip()


def schaetzung(accounts, max_ergebnisse):
    preis_reel, preis_start, quelle = preise()
    return round(preis_start + len(accounts) * max_ergebnisse * preis_reel, 4), preis_reel, preis_start, quelle


def account_von(item):
    name = item.get("ownerUsername")
    if not name and item.get("inputUrl"):
        name = normalisiere(item["inputUrl"])
    return (name or "").lower()


def auswerten(items, accounts, seit=None):
    """Median und Ausreißer pro Account. Fehler-Einträge und Reels vor `seit` (z. B. alte angepinnte) zählen nicht."""
    pro = {a.lower(): [] for a in accounts}
    fehler, zu_alt = {}, {}
    for it in items:
        name = account_von(it)
        if it.get("error"):
            fehler[name] = it.get("errorDescription") or it.get("error")
            continue
        datum = (it.get("timestamp") or "")[:10]
        if seit and datum and datum < seit:
            zu_alt[name] = zu_alt.get(name, 0) + 1
            continue
        aufrufe = it.get("videoPlayCount") or it.get("videoViewCount") or 0
        pro.setdefault(name, []).append({
            "datum": datum, "aufrufe": aufrufe,
            "caption": " ".join((it.get("caption") or "").split())[:90], "link": it.get("url"),
            "likes": it.get("likesCount"), "kommentare": it.get("commentsCount"),
        })
    ergebnis = {}
    for name, reels in pro.items():
        werte = [r["aufrufe"] for r in reels if isinstance(r["aufrufe"], (int, float))]
        median = statistics.median(werte) if werte else 0
        ausreisser = sorted([r for r in reels if median > 0 and r["aufrufe"] >= 3 * median], key=lambda r: -r["aufrufe"])
        ergebnis[name] = {"reels": len(reels), "median_aufrufe": median, "ausreisser": ausreisser,
                          "aelter_als_zeitraum": zu_alt.get(name, 0), "fehler": fehler.get(name)}
    return ergebnis


def befehl_reels(a):
    accounts = [normalisiere(x) for x in a.accounts.split(",") if normalisiere(x)]
    if not accounts:
        G.fehler_ende("Keine Accounts angegeben. Beispiel: --accounts konto1,konto2")
    if a.max_kosten <= 0:
        G.fehler_ende("--max-kosten muss größer als 0 sein.")
    token()  # prüft früh, ob Apify eingerichtet ist
    geschaetzt, preis_reel, preis_start, quelle = schaetzung(accounts, a.max_ergebnisse)
    seit = (datetime.date.today() - datetime.timedelta(days=a.tage)).isoformat()
    plan = {"accounts": accounts, "seit": seit, "max_ergebnisse_pro_account": a.max_ergebnisse,
            "geschaetzte_kosten_usd": geschaetzt, "obergrenze_usd": a.max_kosten,
            "preis_pro_reel_usd": preis_reel, "preis_start_usd": preis_start, "preisquelle": quelle}
    if not a.bestaetigt:
        hinweis = ""
        if geschaetzt > a.max_kosten:
            hinweis = "\nAchtung: Die Schätzung liegt über der Obergrenze. Apify stoppt bei {} $, dann fehlen Reels.".format(a.max_kosten)
        lesbar = ("Geplanter Apify-Lauf (noch nicht gestartet):\n- Accounts: {}\n- Reels seit {}, höchstens {} pro Account\n"
                  "- Geschätzte Kosten: höchstens {} $ ({} $ pro Reel {}, {} $ Start)\n- Harte Obergrenze: {} ${}\n"
                  "Zum Starten denselben Befehl mit --bestaetigt ausführen.").format(
            ", ".join(accounts), seit, a.max_ergebnisse, geschaetzt, preis_reel, quelle, preis_start, a.max_kosten, hinweis)
        G.drucke(dict(plan, gestartet=False), lesbar, a.json)
        return 0
    eingabe = {"username": accounts, "onlyPostsNewerThan": seit, "resultsLimit": a.max_ergebnisse, "skipTrialReels": False}
    try:
        lauf = anfrage("POST", "/acts/{}/runs?{}".format(ACTOR, urllib.parse.urlencode({"maxTotalChargeUsd": a.max_kosten})), daten=eingabe)["data"]
        lauf_id, dataset = lauf["id"], lauf["defaultDatasetId"]
        start = time.time()
        while True:
            status = anfrage("GET", "/actor-runs/" + lauf_id)["data"]
            if status.get("status") not in ("READY", "RUNNING"):
                break
            if time.time() - start > MAX_WARTEZEIT:
                G.fehler_ende("Der Apify-Lauf dauert länger als 15 Minuten. Lauf-ID {} in der Apify Console prüfen.".format(lauf_id))
            time.sleep(WARTE_SEKUNDEN)
        items = anfrage("GET", "/datasets/{}/items?clean=true&format=json".format(dataset), timeout=120)
        time.sleep(3)  # Apify bucht Kosten kurz nach dem Lauf nach, sonst ist der Wert zu niedrig
        status = anfrage("GET", "/actor-runs/" + lauf_id)["data"]
    except G.ApiFehler as e:
        G.fehler_ende("Apify-Lauf fehlgeschlagen: {}".format(e))
    items = items if isinstance(items, list) else []
    auswertung = auswerten(items, accounts, seit)
    ergebnis = dict(plan, gestartet=True, lauf_id=lauf_id, status=status.get("status"),
                    tatsaechliche_kosten_usd=status.get("usageTotalUsd"), reels_geladen=sum(w["reels"] for w in auswertung.values()),
                    accounts_auswertung=auswertung)
    if a.ausgabe:
        Path(a.ausgabe).write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    kosten = status.get("usageTotalUsd")
    z = ["Apify-Lauf {}: {} Reels im Zeitraum, Kosten {} $ (laut Apify, Stand direkt nach dem Lauf).".format(
        status.get("status"), ergebnis["reels_geladen"], round(kosten, 4) if isinstance(kosten, (int, float)) else kosten)]
    for name, w in auswertung.items():
        if w["fehler"]:
            z.append("\n@{}: keine Daten (Apify meldet: {}). Account privat, falsch geschrieben oder von Instagram gerade nicht abrufbar.".format(name, w["fehler"]))
            continue
        alt = " ({} ältere Reels, z. B. angepinnte, nicht gezählt)".format(w["aelter_als_zeitraum"]) if w["aelter_als_zeitraum"] else ""
        z.append("\n@{}: {} Reels, Median {} Aufrufe{}".format(name, w["reels"], w["median_aufrufe"], alt))
        if 0 < w["reels"] < 5:
            z.append("  Hinweis: Unter 5 Reels ist der Median wenig aussagekräftig.")
        for r in w["ausreisser"][:5]:
            z.append("  Ausreißer {} Aufrufe ({}): {} {}".format(r["aufrufe"], r["datum"], r["caption"], r["link"] or ""))
        if not w["ausreisser"]:
            z.append("  keine Ausreißer (mindestens das Dreifache des Medians)")
    G.drucke(ergebnis, "\n".join(z), a.json)
    return 0


def main(argv=None):
    G.utf8_ausgabe()
    p = argparse.ArgumentParser(description="Apify: Konkurrenz-Daten")
    sub = p.add_subparsers(dest="befehl", required=True)
    c = sub.add_parser("check")
    c.add_argument("--json", action="store_true")
    r = sub.add_parser("reels")
    r.add_argument("--accounts", required=True)
    r.add_argument("--tage", type=int, default=30)
    r.add_argument("--max-ergebnisse", type=int, default=30)
    r.add_argument("--max-kosten", type=float, required=True)
    r.add_argument("--bestaetigt", action="store_true")
    r.add_argument("--ausgabe")
    r.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    if a.befehl == "check":
        return befehl_check(a.json)
    return befehl_reels(a)


if __name__ == "__main__":
    sys.exit(main())
