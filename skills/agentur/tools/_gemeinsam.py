"""Gemeinsame Helfer der Social-Media-Agentur. Nur Standardbibliothek, Python >= 3.8.

Zugangsschlüssel werden nur hier gelesen und in jeder Ausgabe maskiert.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

VERSION = "1.0.0"


def utf8_ausgabe():
    """Emojis und Umlaute auch in der Windows-Konsole ausgeben."""
    for strom in (sys.stdout, sys.stderr):
        try:
            strom.reconfigure(encoding="utf-8")
        except Exception:
            pass


def daten_ordner():
    """Ordner mit den Zugangsschlüsseln (~/.social-agentur, für Tests über SOCIAL_AGENTUR_HOME änderbar)."""
    return Path(os.environ.get("SOCIAL_AGENTUR_HOME") or (Path.home() / ".social-agentur"))


def claude_ordner():
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude"))


_GEHEIMNISSE = []


def lies_token(dateiname):
    """Liest einen Zugangsschlüssel. Gibt None zurück, wenn er fehlt. Der Wert wird nie ausgegeben."""
    pfad = daten_ordner() / dateiname
    if not pfad.is_file():
        return None
    kaputt = ("Die Datei {} enthält keinen gültigen Zugangsschlüssel (falsches Format, mehrere Zeilen oder Leerzeichen). "
              "Kopier den Schlüssel neu und speichere ihn mit dem sicheren Befehl aus der README. Den Inhalt der Datei zeige ich aus Sicherheitsgründen nicht an.").format(pfad)
    try:
        wert = pfad.read_bytes().decode("utf-8").strip()
    except UnicodeDecodeError:
        fehler_ende(kaputt)
    if not wert:
        return None
    if len(wert) < 10 or len(wert) > 1000 or any(z.isspace() for z in wert):
        # Nie den Inhalt ausgeben: Steckt darin ein echter Schlüssel plus Fremdtext, wäre er sonst im Chat.
        fehler_ende(kaputt)
    if wert not in _GEHEIMNISSE:
        _GEHEIMNISSE.append(wert)
    return wert


def maske(text):
    """Entfernt Zugangsschlüssel aus jedem Text, bevor er ausgegeben wird."""
    s = str(text)
    for geheim in _GEHEIMNISSE:
        s = s.replace(geheim, "***")
    s = re.sub(r"(access_token=)[^&\s\"']+", r"\1***", s)
    s = re.sub(r"((?:Bearer|OAuth) )[A-Za-z0-9._\-]+", r"\1***", s)
    s = re.sub(r"([?&]token=)[^&\s\"']+", r"\1***", s)
    return s


class ApiFehler(Exception):
    """Fehler einer Schnittstelle, Meldung ist bereits maskiert."""

    def __init__(self, meldung, code=None):
        super().__init__(maske(meldung))
        self.code = code


def http(methode, url, daten=None, header=None, timeout=60, roh=False):
    """Eine HTTP-Anfrage. JSON rein, JSON raus. Fehler kommen als ApiFehler mit maskierter Meldung."""
    kopf = dict(header or {})
    koerper = None
    if daten is not None:
        if isinstance(daten, (bytes, bytearray)):
            koerper = bytes(daten)
        else:
            koerper = json.dumps(daten).encode("utf-8")
            kopf.setdefault("Content-Type", "application/json")
    anfrage = urllib.request.Request(url, data=koerper, method=methode, headers=kopf)
    try:
        with urllib.request.urlopen(anfrage, timeout=timeout) as antwort:
            inhalt = antwort.read()
    except urllib.error.HTTPError as fehler:
        try:
            detail = fehler.read().decode("utf-8", "replace")
        except Exception:
            detail = ""
        raise ApiFehler("HTTP {}: {}".format(fehler.code, detail[:500]), code=fehler.code)
    except urllib.error.URLError as fehler:
        raise ApiFehler("Keine Verbindung: {}".format(maske(str(fehler.reason))))
    except (ValueError, OSError) as fehler:
        raise ApiFehler("Anfrage fehlgeschlagen: {}".format(maske(str(fehler))[:300]))
    if roh:
        return inhalt
    if not inhalt:
        return {}
    return json.loads(inhalt.decode("utf-8"))


def drucke(obj, lesbar=None, als_json=False):
    """Gibt das Ergebnis lesbar aus, mit --json als JSON. Immer maskiert."""
    if als_json or lesbar is None:
        print(maske(json.dumps(obj, ensure_ascii=False, indent=2)))
    else:
        print(maske(lesbar))


def fehler_ende(meldung, code=2):
    print(maske("Fehler: " + meldung), file=sys.stderr)
    sys.exit(code)
