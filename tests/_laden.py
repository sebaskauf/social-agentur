"""Lädt die Tools aus skills/agentur/tools und isoliert Zugangsschlüssel in einem Temp-Ordner."""
import contextlib
import io
import os
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "skills" / "agentur" / "tools"
sys.path.insert(0, str(TOOLS))

import _gemeinsam as G  # noqa: E402,F401

GEHEIM_IG = "TESTSCHLUESSEL-INSTAGRAM-nicht-echt-4711"
GEHEIM_APIFY = "TESTSCHLUESSEL-APIFY-nicht-echt-0815"


def temp_home(mit_tokens=True, ig_alter_tage=None):
    """Legt einen isolierten Schlüssel-Ordner an und setzt SOCIAL_AGENTUR_HOME."""
    ordner = Path(tempfile.mkdtemp())
    os.environ["SOCIAL_AGENTUR_HOME"] = str(ordner)
    G._GEHEIMNISSE.clear()
    if mit_tokens:
        (ordner / "instagram_token").write_text(GEHEIM_IG + "\n", encoding="utf-8")
        (ordner / "apify_token").write_text(GEHEIM_APIFY + "\n", encoding="utf-8")
        if ig_alter_tage is not None:
            import datetime
            (ordner / "instagram_token_datum").write_text(
                (datetime.date.today() - datetime.timedelta(days=ig_alter_tage)).isoformat(), encoding="utf-8")
    return ordner


def ausfuehren(funktion, argv):
    """Ruft main(argv) auf und gibt (exit_code, stdout, stderr) zurück."""
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = funktion(argv) or 0
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 1
    return code, out.getvalue(), err.getvalue()


PROFIL = """# Profil

## Zielgruppe
```json
{
  "zielgruppe": {
    "beschreibung": "Berufstätige, die nebenbei fit werden wollen",
    "alter_von": 25,
    "alter_bis": 45,
    "lebenslagen": ["Angestellte", "Selbstständige", "Eltern"],
    "interessen": ["Fitness", "Ernährung", "Zeit sparen"],
    "plattform": "instagram",
    "einwaende": ["keine Zeit", "zu anstrengend"]
  }
}
```
"""
