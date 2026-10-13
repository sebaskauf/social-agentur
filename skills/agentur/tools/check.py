#!/usr/bin/env python3
"""Einrichtungs-Check der Social-Media-Agentur: Was ist schon da?

Aufruf:
  python3 check.py              JSON
  python3 check.py --lesbar     Checkliste mit ✅/❌
  python3 check.py --online     zusätzlich Apify- und Instagram-Schlüssel live prüfen
Inhalte von Zugangsschlüsseln werden nie gelesen oder ausgegeben, nur ob die Datei existiert und wie alt sie ist.
"""
import argparse
import datetime
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
import _gemeinsam as G  # noqa: E402
import personas  # noqa: E402

AGENTEN = ["profil-agent", "trend-agent", "content-agent", "community-agent", "follower-agent", "viral-agent", "analyse-agent"]


def pruefe_agentur():
    skill = HIER.parent
    als_plugin = "plugins" in skill.parts
    if als_plugin:
        agenten = skill.parent.parent / "agents"
    else:
        agenten = G.claude_ordner() / "agents"
    vorhanden = [a for a in AGENTEN if (agenten / (a + ".md")).is_file()]
    return {"ok": (skill / "SKILL.md").is_file() and len(vorhanden) == len(AGENTEN),
            "weg": "plugin" if als_plugin else "kopie", "skill": str(skill),
            "agenten": "{}/{}".format(len(vorhanden), len(AGENTEN)), "fehlende_agenten": [a for a in AGENTEN if a not in vorhanden]}


def pruefe_python():
    v = sys.version_info
    return {"ok": v >= (3, 8), "version": "{}.{}.{}".format(v.major, v.minor, v.micro)}


def scrapling_pfad():
    venv = G.daten_ordner() / "venv"
    kandidaten = [venv / "bin" / "scrapling", venv / "Scripts" / "scrapling.exe"]
    for k in kandidaten:
        if k.is_file():
            return str(k)
    if os.environ.get("SOCIAL_AGENTUR_NUR_VENV") == "1":
        return None  # für Tests: so tun, als gäbe es keine andere Scrapling-Installation
    return shutil.which("scrapling")


def pruefe_scrapling():
    cli = scrapling_pfad()
    modul = importlib.util.find_spec("scrapling") is not None
    # Die Agenten nutzen die Befehlszeile (scrapling extract …), das Python-Modul allein reicht nicht.
    return {"ok": bool(cli), "cli": cli, "modul_importierbar": modul}


def token_status(name, mit_datum=False):
    pfad = G.daten_ordner() / name
    info = {"ok": pfad.is_file() and pfad.stat().st_size > 0, "datei": str(pfad)}
    if info["ok"] and os.name != "nt":
        info["rechte_600"] = (pfad.stat().st_mode & 0o077) == 0
    if mit_datum:
        datum_datei = G.daten_ordner() / (name + "_datum")
        info["alter_tage"] = None
        if datum_datei.is_file():
            try:
                datum = datetime.date.fromisoformat(datum_datei.read_text(encoding="utf-8").strip())
                info["alter_tage"] = (datetime.date.today() - datum).days
            except ValueError:
                info["alter_tage"] = None
    return info


def online(tool, befehl):
    """Ruft apify.py check bzw. instagram.py status auf und meldet nur ok/Fehler, nie Schlüssel."""
    try:
        r = subprocess.run([sys.executable, str(HIER / tool), befehl, "--json"], capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired:
        return {"gueltig": False, "meldung": "Zeitüberschreitung"}
    if r.returncode == 0:
        try:
            return {"gueltig": True, "daten": json.loads(r.stdout)}
        except ValueError:
            return {"gueltig": True}
    return {"gueltig": False, "meldung": G.maske((r.stderr or r.stdout).strip()[:300])}


def pruefe_profil():
    pfad = Path.cwd() / "meine-agentur" / "profil.md"
    try:
        personas.lies_zielgruppe(pfad)
        return {"ok": True, "datei": str(pfad)}
    except personas.ProfilFehler as e:
        return {"ok": False, "datei": str(pfad), "meldung": str(e)}


def stand(mit_online=False):
    s = {
        "agentur_installiert": pruefe_agentur(),
        "python": pruefe_python(),
        "scrapling": pruefe_scrapling(),
        "apify": token_status("apify_token"),
        "instagram": token_status("instagram_token", mit_datum=True),
        "profil": pruefe_profil(),
    }
    if mit_online:
        if s["apify"]["ok"]:
            s["apify"].update(online("apify.py", "check"))
            s["apify"]["ok"] = s["apify"]["gueltig"]
        if s["instagram"]["ok"]:
            s["instagram"].update(online("instagram.py", "status"))
            s["instagram"]["ok"] = s["instagram"]["gueltig"]
    return s


def lesbar(s):
    h = lambda ok: "✅" if ok else "❌"
    ig = s["instagram"]
    ig_text = "Instagram"
    if ig["ok"] and ig.get("alter_tage") is not None:
        ig_text += " (Schlüssel {} Tage alt{})".format(ig["alter_tage"], ", bald erneuern" if ig["alter_tage"] >= 50 else "")
    zeilen = [
        "{} Agentur installiert ({}, {} Agenten)".format(h(s["agentur_installiert"]["ok"]), s["agentur_installiert"]["weg"].capitalize(),
                                                          s["agentur_installiert"]["agenten"].replace("/", " von ")),
        "{} Python {}".format(h(s["python"]["ok"]), s["python"]["version"]),
        "{} Scrapling".format(h(s["scrapling"]["ok"])),
        "{} Apify".format(h(s["apify"]["ok"])),
        "{} {}".format(h(ig["ok"]), ig_text),
        "{} Profil".format(h(s["profil"]["ok"])),
    ]
    kurz = " · ".join(zeilen)
    return kurz + "\n\n" + "\n".join(zeilen)


def main(argv=None):
    G.utf8_ausgabe()
    p = argparse.ArgumentParser(description="Einrichtungs-Check")
    p.add_argument("--lesbar", action="store_true")
    p.add_argument("--online", action="store_true")
    a = p.parse_args(argv)
    s = stand(a.online)
    if a.lesbar:
        print(G.maske(lesbar(s)))
    else:
        print(G.maske(json.dumps(s, ensure_ascii=False, indent=2)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
