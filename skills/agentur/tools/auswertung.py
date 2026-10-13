#!/usr/bin/env python3
"""Wertet die Urteile der Follower-Agenten aus: Quoten, Absprung-Stellen, Gründe mit Zitaten.

Aufruf:
  python3 auswertung.py --ordner meine-agentur/tests/<beitrag>/ [--vorher meine-agentur/tests/<beitrag-vorher>/]
Schreibt ergebnis.json und ergebnis.md in den Ordner. Kaputte Einträge werden gemeldet, nicht abgebrochen.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _gemeinsam as G  # noqa: E402

KATEGORIEN = {"hook_trifft_nicht", "zu_lang", "unklar", "kenne_ich_schon", "nicht_meine_zielgruppe",
              "wirkt_wie_werbung", "unglaubwuerdig", "stark"}
BOOL_FELDER = ("stehen_geblieben", "bis_ende", "gespeichert", "geteilt", "kommentiert")
TEXT_FELDER = ("persona_id", "absprung_stelle", "geteilt_an", "kategorie", "grund", "zitat")
# Diese Felder sind oft zu Recht leer (bis zum Ende geschaut, nicht geteilt). null oder fehlend zählt dann als "".
DARF_LEER = ("absprung_stelle", "geteilt_an", "grund", "zitat")
QUOTEN = [("wegwisch", "Wegwisch-Quote"), ("ende", "Ende-Quote (von den Stehengebliebenen)"),
          ("speichern", "Speicher-Quote"), ("teilen", "Teil-Quote"), ("kommentieren", "Kommentar-Quote")]


def pruefe_eintrag(eintrag):
    """Gibt eine Liste von Problemen zurück, leer = gültig."""
    if not isinstance(eintrag, dict):
        return ["kein Objekt"]
    for feld in DARF_LEER:
        if eintrag.get(feld) is None:
            eintrag[feld] = ""
    probleme = []
    for feld in BOOL_FELDER:
        if not isinstance(eintrag.get(feld), bool):
            probleme.append("{} fehlt oder ist nicht true/false".format(feld))
    for feld in TEXT_FELDER:
        if not isinstance(eintrag.get(feld), str):
            probleme.append("{} fehlt oder ist kein Text".format(feld))
    if isinstance(eintrag.get("kategorie"), str) and eintrag["kategorie"] not in KATEGORIEN:
        probleme.append("unbekannte kategorie \"{}\"".format(eintrag["kategorie"]))
    return probleme


def stelle(text):
    """Fasst Schreibweisen zusammen: „nach Hook (0:04)“ → „0:04“, „Absatz 2 (nach …)“ → „Absatz 2“, „Hook/Intro“ → „Hook“."""
    t = (text or "").strip()
    if not t:
        return "–"
    zeit = re.search(r"\b(\d{1,2}:\d{2})\b", t)
    if zeit:
        return zeit.group(1)
    teil = re.search(r"\b(folie|slide|absatz|zeile)\s*(\d+)", t, re.I)
    if teil:
        name = teil.group(1).lower()
        return "{} {}".format("Folie" if name in ("folie", "slide") else name.capitalize(), teil.group(2))
    if re.search(r"\bhook\b", t, re.I):
        return "Hook"
    return t


def lies_urteile(ordner):
    ordner = Path(ordner)
    gueltig, fehler, hinweise = [], [], []
    dateien = sorted(ordner.glob("urteile_*.json"))
    for datei in dateien:
        try:
            daten = json.loads(datei.read_text(encoding="utf-8"))
        except ValueError as e:
            fehler.append({"datei": datei.name, "eintrag": None, "problem": "kein gültiges JSON ({})".format(e)})
            continue
        if not isinstance(daten, list):
            fehler.append({"datei": datei.name, "eintrag": None, "problem": "erwartet eine Liste von Urteilen"})
            continue
        for i, eintrag in enumerate(daten):
            probleme = pruefe_eintrag(eintrag)
            if probleme:
                fehler.append({"datei": datei.name, "eintrag": i, "problem": "; ".join(probleme)})
                continue
            e = dict(eintrag)
            if not e["stehen_geblieben"]:
                # Wer wegwischt, kann nicht zu Ende schauen, speichern, teilen oder kommentieren.
                widerspruch = [f for f in ("bis_ende", "gespeichert", "geteilt", "kommentiert") if e[f]]
                if widerspruch:
                    hinweise.append("{} Eintrag {}: weggewischt, aber {} = true, als false gewertet".format(
                        datei.name, i, ", ".join(widerspruch)))
                    for f in widerspruch:
                        e[f] = False
            gueltig.append(e)
    return gueltig, fehler, hinweise, [d.name for d in dateien]


def berechne(urteile):
    n = len(urteile)
    stehen = sum(u["stehen_geblieben"] for u in urteile)
    ende = sum(u["bis_ende"] for u in urteile if u["stehen_geblieben"])
    quoten = {
        "wegwisch": round(1 - stehen / n, 4) if n else 0.0,
        "ende": round(ende / stehen, 4) if stehen else 0.0,
        "speichern": round(sum(u["gespeichert"] for u in urteile) / n, 4) if n else 0.0,
        "teilen": round(sum(u["geteilt"] for u in urteile) / n, 4) if n else 0.0,
        "kommentieren": round(sum(u["kommentiert"] for u in urteile) / n, 4) if n else 0.0,
    }
    absprung = Counter(stelle(u["absprung_stelle"]) for u in urteile if u["stehen_geblieben"] and not u["bis_ende"])
    kategorien = Counter(u["kategorie"] for u in urteile)
    gruende = []
    for kat, anzahl in Counter(u["kategorie"] for u in urteile if u["kategorie"] != "stark").most_common(3):
        zitate = [u["zitat"] for u in urteile if u["kategorie"] == kat and u["zitat"].strip()][:3]
        gruende.append({"kategorie": kat, "anzahl": anzahl, "zitate": zitate})
    haeufigste = kategorien.most_common(1)[0][0] if kategorien else None
    return {
        "anzahl_urteile": n,
        "stehen_geblieben": stehen,
        "quoten": quoten,
        "absprung_stellen": dict(absprung.most_common()),
        "haeufigste_absprung_stelle": absprung.most_common(1)[0][0] if absprung else None,
        "kategorien": dict(kategorien.most_common()),
        "haeufigste_kategorie": haeufigste,
        "zitate_haeufigste_kategorie": [u["zitat"] for u in urteile if u["kategorie"] == haeufigste][:3] if haeufigste else [],
        "top_absprung_gruende": gruende,
        "geteilt_an": [u["geteilt_an"] for u in urteile if u["geteilt"] and u["geteilt_an"].strip()],
    }


def lade_vorher(ordner):
    ordner = Path(ordner)
    datei = ordner / "ergebnis.json"
    if datei.is_file():
        return json.loads(datei.read_text(encoding="utf-8"))["quoten"]
    urteile, _, _, _ = lies_urteile(ordner)
    if not urteile:
        raise ValueError("Im Vorher-Ordner {} gibt es weder ergebnis.json noch gültige Urteile.".format(ordner))
    return berechne(urteile)["quoten"]


def prozent(x):
    return "{:.0f} %".format(x * 100)


def markdown(ergebnis):
    z = ["# Ergebnis Follower-Test", "",
         "{} Urteile, davon {} stehen geblieben.".format(ergebnis["anzahl_urteile"], ergebnis["stehen_geblieben"]), "",
         "| Quote | Wert |" + (" Vorher | Veränderung |" if ergebnis.get("vorher") else ""),
         "|---|---|" + ("---|---|" if ergebnis.get("vorher") else "")]
    for key, name in QUOTEN:
        zeile = "| {} | {} |".format(name, prozent(ergebnis["quoten"][key]))
        if ergebnis.get("vorher"):
            d = ergebnis["veraenderung"][key]
            zeile += " {} | {:+.0f} Punkte |".format(prozent(ergebnis["vorher"][key]), d * 100)
        z.append(zeile)
    z += ["", "## Häufigste Absprung-Gründe"]
    if ergebnis["top_absprung_gruende"]:
        for g in ergebnis["top_absprung_gruende"]:
            z.append("- **{}** ({}×){}".format(g["kategorie"], g["anzahl"], ": „{}“".format(g["zitate"][0]) if g["zitate"] else ""))
    else:
        z.append("- keine")
    z += ["", "## Absprung-Stellen"]
    z += ["- {}: {}×".format(k, v) for k, v in ergebnis["absprung_stellen"].items()] or ["- keine"]
    if ergebnis["geteilt_an"]:
        z += ["", "## Geteilt an"] + ["- {}".format(x) for x in ergebnis["geteilt_an"]]
    if ergebnis["fehler"]:
        z += ["", "## Kaputte Einträge (nicht gezählt)"] + ["- {} Eintrag {}: {}".format(f["datei"], f["eintrag"], f["problem"]) for f in ergebnis["fehler"]]
    if ergebnis["hinweise"]:
        z += ["", "## Hinweise"] + ["- " + h for h in ergebnis["hinweise"]]
    z += ["", "_Simulation mit KI-Personas, keine Prognose. Echte Menschen sind meist strenger._", ""]
    return "\n".join(z)


def main(argv=None):
    G.utf8_ausgabe()
    p = argparse.ArgumentParser(description="Follower-Test auswerten")
    p.add_argument("--ordner", required=True)
    p.add_argument("--vorher")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    ordner = Path(a.ordner)
    if not ordner.is_dir():
        G.fehler_ende("Ordner {} gibt es nicht.".format(ordner))
    urteile, fehler, hinweise, dateien = lies_urteile(ordner)
    if not urteile:
        G.fehler_ende("Keine gültigen Urteile in {} (Dateien: {}). {}".format(
            ordner, ", ".join(dateien) or "keine urteile_*.json", "; ".join(f["problem"] for f in fehler[:3])))
    ergebnis = berechne(urteile)
    ergebnis.update({"dateien": dateien, "fehler": fehler, "hinweise": hinweise})
    if a.vorher:
        try:
            vorher = lade_vorher(a.vorher)
        except (ValueError, OSError) as e:
            G.fehler_ende(str(e))
        ergebnis["vorher"] = vorher
        ergebnis["veraenderung"] = {k: round(ergebnis["quoten"][k] - vorher[k], 4) for k in ergebnis["quoten"]}
    (ordner / "ergebnis.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = markdown(ergebnis)
    (ordner / "ergebnis.md").write_text(md, encoding="utf-8")
    G.drucke(ergebnis, md, a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
