#!/usr/bin/env python3
"""Offizielle Instagram-API (Instagram-Login, graph.instagram.com). Optional, nur für den eigenen Professional-Account.

Schlüssel aus ~/.social-agentur/instagram_token, wird nie ausgegeben (auch nicht in URLs oder Fehlern).
Alles, was nach außen wirkt (posten, antworten, ausblenden, Nachricht senden), zeigt ohne --bestaetigt nur eine Vorschau.

Befehle: status · erneuern · profil · beitraege --anzahl N · insights <id> | --letzte N · kommentare <id> ·
antworten <kommentar-id> --text "…" [--bestaetigt] · ausblenden <kommentar-id> [--bestaetigt] · nachrichten ·
nachricht-senden <empfaenger-id> --text "…" [--bestaetigt] · limit · posten-bild --url … --caption … [--bestaetigt] ·
posten-karussell --urls u1,u2 --caption … [--bestaetigt] · posten-reel --url … --caption … [--bestaetigt | --nur-hochladen]
"""
import argparse
import datetime
import json
import os
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _gemeinsam as G  # noqa: E402

API_VERSION = "v24.0"
BASIS = "https://graph.instagram.com"
API = BASIS + "/" + API_VERSION
PROFI_TYPEN = {"BUSINESS", "MEDIA_CREATOR", "CREATOR"}
METRIKEN_ALLE = ["views", "reach", "shares", "saved", "comments", "likes", "total_interactions"]
METRIKEN_REELS = ["ig_reels_avg_watch_time", "reels_skip_rate"]
CONTAINER_WARTEN = 5
CONTAINER_MAX = 10 * 60


def token():
    t = G.lies_token("instagram_token")
    if not t:
        G.fehler_ende("Instagram ist noch nicht verbunden. Starte /agentur einrichten full oder lies in der README den Abschnitt „Instagram verbinden“.")
    return t


def url(pfad, **parameter):
    parameter["access_token"] = token()
    basis = pfad if pfad.startswith("http") else API + pfad
    trenner = "&" if "?" in basis else "?"
    return basis + trenner + urllib.parse.urlencode(parameter)


def erklaere(fehler):
    text = str(fehler)
    if '"code":190' in text.replace(" ", "") or "OAuthException" in text:
        return "Der Instagram-Schlüssel ist abgelaufen oder ungültig (Fehler 190). Lösung: /agentur instagram erneuern oder in der README die Schritte 7 und 8 wiederholen."
    return "Instagram meldet: " + text


def hole(pfad, **parameter):
    try:
        return G.http("GET", url(pfad, **parameter))
    except G.ApiFehler as e:
        G.fehler_ende(erklaere(e))


def sende(pfad, daten=None, **parameter):
    try:
        return G.http("POST", url(pfad, **parameter), daten=daten)
    except G.ApiFehler as e:
        G.fehler_ende(erklaere(e))


def token_alter():
    datei = G.daten_ordner() / "instagram_token_datum"
    if not datei.is_file():
        return None
    try:
        return (datetime.date.today() - datetime.date.fromisoformat(datei.read_text(encoding="utf-8").strip())).days
    except ValueError:
        return None


def vorschau_oder_weiter(bestaetigt, beschreibung, daten):
    """Sperre für alles, was nach außen wirkt. Ohne --bestaetigt nur Vorschau, Rückgabe False."""
    if bestaetigt:
        return True
    print(G.maske(json.dumps({"vorschau": True, "aktion": beschreibung, "daten": daten}, ensure_ascii=False, indent=2)))
    print("Nur Vorschau, nichts wurde ausgeführt. Nach ausdrücklichem Ja denselben Befehl mit --bestaetigt ausführen.")
    return False


# ---------------- Lesen ----------------

def befehl_status(a):
    ich = hole("/me", fields="user_id,username,account_type,followers_count,media_count")
    alter = token_alter()
    profi = ich.get("account_type") in PROFI_TYPEN
    erg = {"account": ich.get("username"), "kontotyp": ich.get("account_type"), "professional": profi,
           "follower": ich.get("followers_count"), "beitraege": ich.get("media_count"), "schluessel_alter_tage": alter}
    z = ["Verbunden mit @{} ({}).".format(erg["account"], erg["kontotyp"]),
         "Follower: {} · Beiträge: {}".format(erg["follower"], erg["beitraege"])]
    if not profi:
        z.append("Achtung: Kein Professional-Account. Wechsle in Instagram zu Creator oder Business.")
    if alter is not None:
        z.append("Schlüssel {} Tage alt (läuft nach 60 Tagen ab{}).".format(alter, ", bitte jetzt erneuern" if alter >= 50 else ""))
    G.drucke(erg, "\n".join(z), a.json)
    return 0


def befehl_profil(a):
    p = hole("/me", fields="username,name,biography,website,profile_picture_url,followers_count,follows_count,media_count")
    felder = ["username", "name", "biography", "website", "profile_picture_url", "followers_count", "follows_count", "media_count"]
    erg = {f: p.get(f, "–") if p.get(f) not in (None, "") else "–" for f in felder}
    lesbar = "\n".join("{}: {}".format(k, v) for k, v in erg.items())
    G.drucke(erg, lesbar, a.json)
    return 0


def lade_beitraege(anzahl):
    felder = "id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count"
    daten = hole("/me/media", fields=felder, limit=min(anzahl, 50))
    liste = list(daten.get("data", []))
    weiter = (daten.get("paging") or {}).get("next")
    while weiter and len(liste) < anzahl:
        try:
            daten = G.http("GET", weiter)
        except G.ApiFehler as e:
            G.fehler_ende(erklaere(e))
        liste += daten.get("data", [])
        weiter = (daten.get("paging") or {}).get("next")
    return liste[:anzahl]


def befehl_beitraege(a):
    liste = lade_beitraege(a.anzahl)
    z = ["{} · {} · {} Likes · {} Kommentare · {}".format(
        (b.get("timestamp") or "")[:10], b.get("media_product_type") or b.get("media_type"), b.get("like_count", "–"),
        b.get("comments_count", "–"), " ".join((b.get("caption") or "").split())[:70]) for b in liste]
    G.drucke(liste, "\n".join(z) or "Keine Beiträge gefunden.", a.json)
    return 0


def insights_fuer(media_id, produkt):
    metriken = METRIKEN_ALLE + (METRIKEN_REELS if produkt == "REELS" else [])
    werte = {}
    try:
        antwort = G.http("GET", url("/{}/insights".format(media_id), metric=",".join(metriken)))
        for eintrag in antwort.get("data", []):
            werte[eintrag["name"]] = eintrag["values"][0]["value"]
    except G.ApiFehler:
        # Nicht jede Metrik gibt es für jeden Beitragstyp: einzeln nachfragen statt abbrechen.
        for m in metriken:
            try:
                antwort = G.http("GET", url("/{}/insights".format(media_id), metric=m))
                for eintrag in antwort.get("data", []):
                    werte[eintrag["name"]] = eintrag["values"][0]["value"]
            except G.ApiFehler as e:
                if '"code":190' in str(e).replace(" ", ""):
                    G.fehler_ende(erklaere(e))
    return {m: werte.get(m, "–") for m in metriken}


def befehl_insights(a):
    if a.letzte:
        ziele = [(b["id"], b.get("media_product_type"), b) for b in lade_beitraege(a.letzte)]
    elif a.id:
        info = hole("/" + a.id, fields="id,media_product_type,timestamp,caption,permalink")
        ziele = [(a.id, info.get("media_product_type"), info)]
    else:
        G.fehler_ende("Gib eine Beitrags-ID an oder --letzte N.")
    erg = []
    for media_id, produkt, info in ziele:
        werte = insights_fuer(media_id, produkt)
        erg.append({"id": media_id, "typ": produkt, "datum": (info.get("timestamp") or "")[:10],
                    "caption": " ".join((info.get("caption") or "").split())[:70], "link": info.get("permalink"), "insights": werte})
    z = []
    for e in erg:
        w = e["insights"]
        teil = "{} {} · Aufrufe {} · Reichweite {} · geteilt {} · gespeichert {} · Kommentare {}".format(
            e["datum"], e["typ"], w.get("views"), w.get("reach"), w.get("shares"), w.get("saved"), w.get("comments"))
        if e["typ"] == "REELS":
            dauer = w.get("ig_reels_avg_watch_time")
            teil += " · Ø Wiedergabe {} s · Weiterwisch-Rate {} %".format(round(dauer / 1000, 1) if isinstance(dauer, (int, float)) else "–", w.get("reels_skip_rate"))
        z.append(teil)
    G.drucke(erg, "\n".join(z), a.json)
    return 0


def befehl_kommentare(a):
    daten = hole("/{}/comments".format(a.id), fields="id,text,username,timestamp,like_count", limit=50)
    liste = list(daten.get("data", []))
    weiter = (daten.get("paging") or {}).get("next")
    while weiter and len(liste) < a.max:
        try:
            daten = G.http("GET", weiter)
        except G.ApiFehler as e:
            G.fehler_ende(erklaere(e))
        liste += daten.get("data", [])
        weiter = (daten.get("paging") or {}).get("next")
    liste = liste[:a.max]
    z = ["{} @{}: {} (ID {})".format((k.get("timestamp") or "")[:10], k.get("username"), " ".join((k.get("text") or "").split()), k.get("id")) for k in liste]
    G.drucke(liste, "\n".join(z) or "Keine Kommentare.", a.json)
    return 0


def befehl_nachrichten(a):
    daten = hole("/me/conversations", platform="instagram", fields="participants,updated_time,messages.limit(3){message,from,created_time}")
    G.drucke(daten.get("data", []), None, True)
    return 0


def befehl_limit(a):
    d = hole("/me/content_publishing_limit", fields="config,quota_usage")
    eintrag = (d.get("data") or [{}])[0]
    gesamt = (eintrag.get("config") or {}).get("quota_total")
    erg = {"genutzt_24h": eintrag.get("quota_usage"), "maximal_24h": gesamt}
    G.drucke(erg, "API-Posts in den letzten 24 Stunden: {} von {} (ein Karussell zählt als 1).".format(erg["genutzt_24h"], gesamt), a.json)
    return 0


# ---------------- Schreiben (nur mit --bestaetigt) ----------------

def befehl_antworten(a):
    if not vorschau_oder_weiter(a.bestaetigt, "Antwort auf Kommentar {}".format(a.id), {"text": a.text}):
        return 0
    erg = sende("/{}/replies".format(a.id), message=a.text)
    G.drucke(erg, "Antwort gesendet (ID {}).".format(erg.get("id")), a.json)
    return 0


def befehl_ausblenden(a):
    if not vorschau_oder_weiter(a.bestaetigt, "Kommentar {} ausblenden".format(a.id), {}):
        return 0
    erg = sende("/" + a.id, hide="true")
    G.drucke(erg, "Kommentar ausgeblendet.", a.json)
    return 0


def befehl_nachricht_senden(a):
    daten = {"recipient": {"id": a.id}, "message": {"text": a.text}}
    if not vorschau_oder_weiter(a.bestaetigt, "Nachricht an {} (nur innerhalb von 24 Stunden nach deren letzter Nachricht möglich)".format(a.id), daten):
        return 0
    erg = sende("/me/messages", daten=daten)
    G.drucke(erg, "Nachricht gesendet.", a.json)
    return 0


def warte_auf_container(container_id):
    start = time.time()
    while True:
        s = hole("/" + container_id, fields="status_code,status")
        code = s.get("status_code")
        if code in ("FINISHED", "PUBLISHED"):
            return code
        if code in ("ERROR", "EXPIRED"):
            G.fehler_ende("Instagram konnte die Datei nicht verarbeiten ({}): {}".format(code, s.get("status")))
        if time.time() - start > CONTAINER_MAX:
            G.fehler_ende("Instagram verarbeitet die Datei seit über 10 Minuten. Container {} später erneut prüfen.".format(container_id))
        time.sleep(CONTAINER_WARTEN)


def veroeffentlichen(container_id):
    warte_auf_container(container_id)
    return sende("/me/media_publish", creation_id=container_id)


def befehl_posten_bild(a):
    if not vorschau_oder_weiter(a.bestaetigt, "Bild posten", {"url": a.url, "caption": a.caption}):
        return 0
    container = sende("/me/media", image_url=a.url, caption=a.caption)
    erg = veroeffentlichen(container["id"])
    G.drucke(erg, "Bild veröffentlicht (ID {}).".format(erg.get("id")), a.json)
    return 0


def befehl_posten_karussell(a):
    urls = [u.strip() for u in a.urls.split(",") if u.strip()]
    if not 2 <= len(urls) <= 10:
        G.fehler_ende("Ein Karussell braucht 2 bis 10 Bilder oder Videos.")
    if not vorschau_oder_weiter(a.bestaetigt, "Karussell posten", {"urls": urls, "caption": a.caption}):
        return 0
    kinder = []
    for u in urls:
        if u.lower().split("?")[0].endswith((".mp4", ".mov")):
            k = sende("/me/media", media_type="VIDEO", video_url=u, is_carousel_item="true")
        else:
            k = sende("/me/media", image_url=u, is_carousel_item="true")
        warte_auf_container(k["id"])
        kinder.append(k["id"])
    container = sende("/me/media", media_type="CAROUSEL", children=",".join(kinder), caption=a.caption)
    erg = veroeffentlichen(container["id"])
    G.drucke(erg, "Karussell veröffentlicht (ID {}).".format(erg.get("id")), a.json)
    return 0


DATEI_HINWEIS = ("Ein Reel direkt vom Rechner hochzuladen geht mit der Instagram-API mit Instagram-Login nicht "
                 "(Stand 13.10.2026: Meta verlangt eine öffentlich erreichbare video_url). Lade das Video an einen Ort mit "
                 "öffentlichem Link hoch und nutze --url, oder poste es direkt in der Instagram-App.")


def befehl_posten_reel(a):
    if a.datei:
        G.fehler_ende(DATEI_HINWEIS)
    if not a.url:
        G.fehler_ende("Gib mit --url eine öffentlich erreichbare Videoadresse an (MP4).")
    if not a.nur_hochladen and not vorschau_oder_weiter(a.bestaetigt, "Reel posten", {"url": a.url, "caption": a.caption}):
        return 0
    container = sende("/me/media", media_type="REELS", video_url=a.url, caption=a.caption)
    status = warte_auf_container(container["id"])
    if a.nur_hochladen:
        erg = {"container_id": container["id"], "status": status, "veroeffentlicht": False}
        G.drucke(erg, "Von Instagram verarbeitet ({}), NICHT veröffentlicht. Der Container verfällt nach 24 Stunden.".format(status), a.json)
        return 0
    erg = sende("/me/media_publish", creation_id=container["id"])
    G.drucke(erg, "Reel veröffentlicht (ID {}).".format(erg.get("id")), a.json)
    return 0


def befehl_erneuern(a):
    alter = token_alter()
    if alter is not None and alter < 1:
        G.fehler_ende("Der Schlüssel ist jünger als 24 Stunden. Instagram erlaubt das Erneuern erst danach.")
    try:
        d = G.http("GET", url(BASIS + "/refresh_access_token", grant_type="ig_refresh_token"))
    except G.ApiFehler as e:
        G.fehler_ende(erklaere(e))
    neu = d.get("access_token")
    if not neu:
        G.fehler_ende("Instagram hat keinen neuen Schlüssel geliefert.")
    ordner = G.daten_ordner()
    datei = ordner / "instagram_token"
    datei.write_text(neu + "\n", encoding="utf-8")
    if os.name != "nt":
        datei.chmod(0o600)
    (ordner / "instagram_token_datum").write_text(datetime.date.today().isoformat() + "\n", encoding="utf-8")
    tage = round((d.get("expires_in") or 0) / 86400)
    G.drucke({"erneuert": True, "gueltig_tage": tage}, "Schlüssel erneuert, gültig für weitere {} Tage.".format(tage), a.json)
    return 0


def main(argv=None):
    G.utf8_ausgabe()
    p = argparse.ArgumentParser(description="Instagram (offizielle API)")
    sub = p.add_subparsers(dest="befehl", required=True)

    def neu(name):
        s = sub.add_parser(name)
        s.add_argument("--json", action="store_true")
        return s
    neu("status"); neu("erneuern"); neu("profil"); neu("nachrichten"); neu("limit")
    s = neu("beitraege"); s.add_argument("--anzahl", type=int, default=10)
    s = neu("insights"); s.add_argument("id", nargs="?"); s.add_argument("--letzte", type=int)
    s = neu("kommentare"); s.add_argument("id"); s.add_argument("--max", type=int, default=100)
    s = neu("antworten"); s.add_argument("id"); s.add_argument("--text", required=True); s.add_argument("--bestaetigt", action="store_true")
    s = neu("ausblenden"); s.add_argument("id"); s.add_argument("--bestaetigt", action="store_true")
    s = neu("nachricht-senden"); s.add_argument("id"); s.add_argument("--text", required=True); s.add_argument("--bestaetigt", action="store_true")
    s = neu("posten-bild"); s.add_argument("--url", required=True); s.add_argument("--caption", default=""); s.add_argument("--bestaetigt", action="store_true")
    s = neu("posten-karussell"); s.add_argument("--urls", required=True); s.add_argument("--caption", default=""); s.add_argument("--bestaetigt", action="store_true")
    s = neu("posten-reel"); s.add_argument("--datei", help="nicht möglich, siehe Hinweis"); s.add_argument("--url"); s.add_argument("--caption", default="")
    s.add_argument("--bestaetigt", action="store_true"); s.add_argument("--nur-hochladen", action="store_true", help="hochladen und verarbeiten lassen, nicht veröffentlichen")
    a = p.parse_args(argv)
    befehle = {"status": befehl_status, "erneuern": befehl_erneuern, "profil": befehl_profil, "beitraege": befehl_beitraege,
               "insights": befehl_insights, "kommentare": befehl_kommentare, "antworten": befehl_antworten,
               "ausblenden": befehl_ausblenden, "nachrichten": befehl_nachrichten, "nachricht-senden": befehl_nachricht_senden,
               "limit": befehl_limit, "posten-bild": befehl_posten_bild, "posten-karussell": befehl_posten_karussell,
               "posten-reel": befehl_posten_reel}
    return befehle[a.befehl](a)


if __name__ == "__main__":
    sys.exit(main())
