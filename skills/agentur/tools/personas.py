#!/usr/bin/env python3
"""Follower-Personas für den Vorab-Test: reproduzierbar aus dem Zielgruppen-Block in profil.md.

Aufruf:
  python3 personas.py ziehen --profil meine-agentur/profil.md --anzahl 100 --seed 1 --ziel meine-agentur/tests/<beitrag>/
"""
import argparse
import json
import math
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _gemeinsam as G  # noqa: E402

# Fremde Allgemein-Interessen: jede Persona bekommt eins dazu, damit nicht alle perfekt zur Nische passen.
ALLGEMEIN = ["Reisen", "Kochen", "Fußball", "Serien", "Musik", "Familie", "Haustiere", "Mode",
             "Gaming", "Autos", "Garten", "Sparen", "Fitness", "Fotografie", "Wohnen"]
SCROLL_TEMPO = (["schnell", "mittel", "langsam"], [0.50, 0.35, 0.15])
TEIL_VERHALTEN = (["selten", "manchmal", "oft"], [0.60, 0.30, 0.10])
PRO_DATEI = 10


class ProfilFehler(Exception):
    pass


def lies_zielgruppe(profil_pfad):
    """Liest den JSON-Block "zielgruppe" aus profil.md und prüft ihn. Wirft ProfilFehler mit deutscher Meldung."""
    pfad = Path(profil_pfad)
    if not pfad.is_file():
        raise ProfilFehler("{} gibt es noch nicht. Leg zuerst mit /agentur start das Profil an.".format(pfad))
    text = pfad.read_text(encoding="utf-8")
    bloecke = re.findall(r"```json\s*\n(.*?)\n```", text, re.S)
    for block in bloecke:
        try:
            daten = json.loads(block)
        except ValueError:
            continue
        if isinstance(daten, dict) and isinstance(daten.get("zielgruppe"), dict):
            zg = daten["zielgruppe"]
            break
    else:
        raise ProfilFehler("In {} fehlt der JSON-Block \"zielgruppe\". Leg das Profil mit /agentur start an "
                           "oder trag den Block wie in vorlagen/profil.md ein.".format(pfad))
    probleme = []
    for feld in ("alter_von", "alter_bis"):
        if not isinstance(zg.get(feld), int):
            probleme.append("{} muss eine ganze Zahl sein".format(feld))
    if not probleme and zg["alter_von"] > zg["alter_bis"]:
        probleme.append("alter_von ist größer als alter_bis")
    for feld in ("lebenslagen", "interessen"):
        wert = zg.get(feld)
        if not isinstance(wert, list) or not wert or not all(isinstance(x, str) and x.strip() for x in wert):
            probleme.append("{} muss eine Liste mit mindestens einem Eintrag sein".format(feld))
    if not isinstance(zg.get("plattform"), str) or not zg.get("plattform"):
        probleme.append("plattform fehlt")
    if not isinstance(zg.get("einwaende", []), list):
        probleme.append("einwaende muss eine Liste sein")
    if probleme:
        raise ProfilFehler("Der Zielgruppen-Block in {} ist unvollständig: {}. Ergänze ihn oder starte /agentur start.".format(
            pfad, "; ".join(probleme)))
    return zg


def ziehe_personas(zg, anzahl, seed):
    """Zieht `anzahl` Personas. Gleicher Seed und gleiche Zielgruppe ergeben exakt dieselben Personas."""
    rng = random.Random(seed)
    nischen = list(dict.fromkeys(zg["interessen"]))
    fremde = [x for x in ALLGEMEIN if x not in nischen]
    einwaende = zg.get("einwaende") or ["keiner"]
    personas = []
    for i in range(anzahl):
        k = rng.choice([2, 3])
        eigene = rng.sample(nischen, min(k - 1, len(nischen)))
        interessen = eigene + [rng.choice(fremde)]
        rng.shuffle(interessen)
        personas.append({
            "persona_id": "p{:03d}".format(i + 1),
            "alter": rng.randint(zg["alter_von"], zg["alter_bis"]),
            "lebenslage": rng.choice(zg["lebenslagen"]),
            "interessen": interessen,
            "scroll_tempo": rng.choices(*SCROLL_TEMPO)[0],
            "teil_verhalten": rng.choices(*TEIL_VERHALTEN)[0],
            "plattform": zg["plattform"],
            "einwand": rng.choice(einwaende),
        })
    return personas


def schreibe(personas, ziel):
    ziel = Path(ziel)
    ziel.mkdir(parents=True, exist_ok=True)
    dateien = []
    for nr in range(math.ceil(len(personas) / PRO_DATEI)):
        teil = personas[nr * PRO_DATEI:(nr + 1) * PRO_DATEI]
        pfad = ziel / "personas_{:02d}.json".format(nr + 1)
        pfad.write_text(json.dumps(teil, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        dateien.append(str(pfad))
    return dateien


def main(argv=None):
    G.utf8_ausgabe()
    p = argparse.ArgumentParser(description="Follower-Personas ziehen")
    sub = p.add_subparsers(dest="befehl", required=True)
    z = sub.add_parser("ziehen", help="Personas aus profil.md ziehen")
    z.add_argument("--profil", required=True)
    z.add_argument("--anzahl", type=int, default=100)
    z.add_argument("--schnell", action="store_true", help="nur 20 Personas")
    z.add_argument("--seed", type=int, required=True)
    z.add_argument("--ziel", required=True)
    a = p.parse_args(argv)
    anzahl = 20 if a.schnell else a.anzahl
    if anzahl < 1 or anzahl > 1000:
        G.fehler_ende("--anzahl muss zwischen 1 und 1000 liegen.")
    try:
        zg = lies_zielgruppe(a.profil)
    except ProfilFehler as fehler:
        G.fehler_ende(str(fehler))
    personas = ziehe_personas(zg, anzahl, a.seed)
    dateien = schreibe(personas, a.ziel)
    print(json.dumps({"personas": len(personas), "seed": a.seed, "dateien": dateien}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
