# Social-Media-Agentur für Claude

Sieben Claude-Agenten übernehmen deinen Social-Media-Auftritt. Kostenlos, MIT-Lizenz, für Claude Code.

## 1. Was es ist

| Agent | Was er macht |
|---|---|
| **Profil-Agent** | baut dein Profil so um, dass aus Besuchern Follower werden |
| **Trend-Agent** | findet die Themen, die in deiner Nische gerade durch die Decke gehen |
| **Content-Agent** | schreibt Posts, Karussells und Reel-Skripte in deiner eigenen Sprache |
| **Community-Agent** | schreibt Antworten auf Kommentare und Nachrichten in deinem Ton |
| **Follower-Agent** | 100 Claude-Personas, die wie deine Zielgruppe ticken, testen jeden Beitrag vorab |
| **Viral-Agent** | baut die schwächste Stelle so lange um, bis der Test besser ausfällt |
| **Analyse-Agent** | wertet jede Woche aus und plant die nächste Woche |

Inhalte für Instagram, TikTok und LinkedIn. Eine direkte API-Anbindung gibt es nur für Instagram (optional). Alles läuft über den Befehl `/agentur`.

Voraussetzungen: [Claude Code](https://claude.com/claude-code) (ab dem Pro-Plan), Python 3.8 oder neuer, git.

## 2. Installation

**Empfohlen: Lass Claude das machen.** Füge in Claude Code ein:

```
Richte mir bitte die Social-Media-Agentur ein: https://github.com/sebaskauf/social-agentur
```

Claude führt dann diese Befehle aus.

**Mac und Linux:**

```bash
[ -d ~/.social-agentur/repo/.git ] || git clone --depth 1 https://github.com/sebaskauf/social-agentur.git ~/.social-agentur/repo
bash ~/.social-agentur/repo/install.sh
```

**Windows (PowerShell):**

```powershell
if (-not (Test-Path "$HOME\.social-agentur\repo\.git")) { git clone --depth 1 https://github.com/sebaskauf/social-agentur.git "$HOME\.social-agentur\repo" }
powershell -ExecutionPolicy Bypass -File "$HOME\.social-agentur\repo\install.ps1"
```

Das Skript kopiert den Skill nach `~/.claude/skills/agentur` und die sieben Agenten nach `~/.claude/agents/`. Danach heißt der Befehl `/agentur`. Claude Code erkennt neue Skills und Agenten ohne Neustart. Erscheint `/agentur` trotzdem nicht, tippe `/reload-skills` oder starte Claude Code einmal neu. **Update:** denselben Befehl noch einmal ausführen.

**Alternative als Plugin** (selbst in Claude Code eintippen):

```
/plugin marketplace add sebaskauf/social-agentur
/plugin install social-agentur@social-agentur
```

Als Plugin heißt der Befehl `/social-agentur:agentur`, die Agenten `social-agentur:profil-agent` usw.

## 3. Tests

```bash
cd ~/.social-agentur/repo && python3 -m unittest discover -s tests -v
```

Die Tests brauchen kein Internet und keine Zugangsschlüssel. Alle Netzaufrufe sind simuliert.

## 4. Scrapling (optional, für Web-Trends)

[Scrapling](https://github.com/D4Vinci/Scrapling) (BSD-3) liest Webseiten, die normale Abfragen blockieren, zum Beispiel Foren oder Konkurrenz-Seiten. Der Trend-Agent nutzt es, wenn es eingerichtet ist. Es braucht **Python 3.10 oder neuer** und kommt in eine eigene Umgebung, damit nichts an deinem System verändert wird. Das dauert 1 bis 3 Minuten, weil Browser heruntergeladen werden.

**Mac und Linux:**

```bash
python3 -m venv ~/.social-agentur/venv
~/.social-agentur/venv/bin/pip install "scrapling[fetchers,shell]"
~/.social-agentur/venv/bin/scrapling install
```

Ist dein `python3` älter als 3.10, nimm eine neuere Version, zum Beispiel `python3.12 -m venv …`.

**Windows (PowerShell):**

```powershell
py -3 -m venv "$HOME\.social-agentur\venv"
& "$HOME\.social-agentur\venv\Scripts\pip.exe" install "scrapling[fetchers,shell]"
& "$HOME\.social-agentur\venv\Scripts\scrapling.exe" install
```

**Kurztest:**

```bash
~/.social-agentur/venv/bin/scrapling extract get "https://example.com" /tmp/scrapling-test.md && head -5 /tmp/scrapling-test.md
```

**So nutzt der Trend-Agent es:** `~/.social-agentur/venv/bin/scrapling extract get "<url>" seite.md` für normale Seiten, `extract stealthy-fetch "<url>" seite.md` für Seiten mit Schutz. Nur öffentliche Seiten, nie hinter einem Login.

## 5. Apify (optional, für Konkurrenz-Daten)

Apify lädt die Reels deiner Konkurrenz mit Aufrufzahlen. Daraus erkennt der Trend-Agent Ausreißer, also Reels mit mindestens dem Dreifachen des üblichen Werts. Apify hat jeden Monat ein Gratis-Guthaben. Die Agentur nennt vor jedem Lauf die geschätzten Kosten, setzt eine harte Obergrenze und startet erst nach deinem Ja.

1. Auf [apify.com](https://apify.com) oben rechts auf **Sign up**, am schnellsten mit Google.
2. In der Apify Console die Einstellungen öffnen, Bereich **API & Integrations**.
3. Bei **Personal API tokens** auf das Kopier-Symbol klicken. Den Schlüssel nicht in einen Chat einfügen.
4. Sicher speichern, direkt aus der Zwischenablage:

   **Mac:** `mkdir -p ~/.social-agentur && pbpaste > ~/.social-agentur/apify_token && chmod 600 ~/.social-agentur/apify_token`

   **Windows (PowerShell):** `New-Item -ItemType Directory -Force "$HOME\.social-agentur" | Out-Null; Get-Clipboard | Set-Content -NoNewline "$HOME\.social-agentur\apify_token"`

   **Linux:** wie Mac, aber `xclip -o -selection clipboard` (oder `wl-paste`) statt `pbpaste`.
5. Prüfen: `python3 ~/.claude/skills/agentur/tools/apify.py check` zeigt Konto und Monatsguthaben.

## 6. Instagram verbinden (optional)

Danach liest die Agentur echte Zahlen, Kommentare und Nachrichten deines Accounts. Posten und Antworten passieren nur nach deinem ausdrücklichen Ja. Es ist die offizielle Instagram-API von Meta (Instagram-Login), ohne Passwort-Weitergabe.

1. Dein Account muss öffentlich und ein **Professional-Account** sein (Creator oder Business). Falls nicht: Instagram → Einstellungen → **Kontotyp und Tools** → **Zu professionellem Konto wechseln** (kostenlos).
2. [developers.facebook.com](https://developers.facebook.com) öffnen → **Log in** mit Facebook → **Get started** → registrieren (Telefonnummer und E-Mail bestätigen, Rolle zum Beispiel Developer).
3. **Create app** → Namen eingeben → Anwendungsfall **Other** (oder direkt **Instagram API**, falls angeboten) → App-Typ **Business** → **Create app**.
4. Beim Produkt **Instagram** auf **Set up**.
5. **App roles** → **Roles** → **Add people** → **Instagram Tester** → eigenen Instagram-Namen → **Add**.
6. In Instagram: **Mehr (☰)** → **Einstellungen** → **Website-Berechtigungen** → **Apps und Websites** → **Tester-Einladungen** → annehmen. (Nicht sichtbar? Instagram im Browser öffnen.)
7. Zurück im Dashboard: **Instagram** → **API setup with Instagram login** → **Generate access tokens** → **Generate token** → einloggen → alle Berechtigungen erlauben → **I understand** → Token kopieren. Nicht in einen Chat einfügen.
8. Sicher speichern, direkt aus der Zwischenablage:

   **Mac:** `mkdir -p ~/.social-agentur && pbpaste > ~/.social-agentur/instagram_token && chmod 600 ~/.social-agentur/instagram_token && date +%F > ~/.social-agentur/instagram_token_datum`

   **Windows (PowerShell):** `New-Item -ItemType Directory -Force "$HOME\.social-agentur" | Out-Null; Get-Clipboard | Set-Content -NoNewline "$HOME\.social-agentur\instagram_token"; Get-Date -Format yyyy-MM-dd | Set-Content "$HOME\.social-agentur\instagram_token_datum"`

   **Linux:** wie Mac, mit `xclip -o -selection clipboard` statt `pbpaste`.
9. Prüfen: `python3 ~/.claude/skills/agentur/tools/instagram.py status` zeigt Account, Kontotyp und Follower.

Der Schlüssel läuft nach **60 Tagen** ab. `/agentur woche` erinnert dich ab Tag 50, `/agentur instagram erneuern` verlängert ihn.

**Reels posten:** Die Instagram-API mit Instagram-Login nimmt Videos nur über eine öffentlich erreichbare Adresse an (`instagram.py posten-reel --url …`). Direkt vom Rechner hochladen geht damit nicht (getestet am 13.10.2026). Dann postest du das fertige Reel in der Instagram-App, die Agentur liefert Skript, Hook und Caption. Bilder und Karussells brauchen ebenfalls eine öffentliche Bild-URL.

## 7. Befehle

| Befehl | Was passiert |
|---|---|
| `/agentur einrichten [schnellstart\|full]` | Einrichtungs-Assistent mit Checkliste |
| `/agentur status` | Was ist eingerichtet |
| `/agentur start` | Profil der Agentur anlegen (ein paar Fragen) |
| `/agentur profil` | Profil-Agent: Bio, Name, Highlights, erste 9 Beiträge |
| `/agentur ideen` | Trend-Agent: 10 Themen mit Hook-Idee |
| `/agentur post [thema]` | Beitrag schreiben, mit 100 Personas testen, verbessern |
| `/agentur test [datei]` | Nur den Follower-Test für einen fertigen Beitrag |
| `/agentur antworten` | Community-Agent: Antworten auf Kommentare und Nachrichten |
| `/agentur woche` | Analyse-Agent: Auswertung und Wochenplan |
| `/agentur instagram status\|erneuern\|posten` | Instagram (nach der Verbindung) |
| `/agentur hilfe` | Übersicht |

Deine Daten liegen im Ordner `meine-agentur/` des Projekts, in dem du Claude Code startest.

## 8. Was es nicht tut

- Es garantiert keine Reichweite. Der Follower-Test ist eine Simulation mit KI-Personas, keine Prognose. Echte Menschen sind strenger.
- Es postet, antwortet und schreibt nie ohne dein ausdrückliches Ja.
- Es nutzt keine inoffiziellen Logins und kein Scraping mit Passwort.
- Nachrichten kann die Instagram-API nur beantworten, wenn dir die Person in den letzten 24 Stunden geschrieben hat. Über die API gehen höchstens 100 Beiträge pro 24 Stunden.
- Die Meta-App bleibt im Entwicklungsmodus und funktioniert nur für deinen eigenen Account (als Tester eingetragen).

## 9. Sicherheit

- Zugangsschlüssel liegen nur in `~/.social-agentur/` auf deinem Rechner (Rechte 600), nie im Projekt und nie im Chat.
- Die Tools lesen die Schlüssel selbst und maskieren sie in jeder Ausgabe und Fehlermeldung.
- Der Instagram-Schlüssel ist ein Generalschlüssel zu deinem Account. Nicht teilen. Wenn er in falsche Hände gerät: in den Meta-App-Einstellungen die App entfernen oder den Schlüssel neu erzeugen.
- Alle Tools nutzen nur die Python-Standardbibliothek. Nichts wird nachinstalliert, außer du richtest Scrapling ein.

## 10. Lizenz

MIT. Gebaut von Sebastian Kauffmann (SKAILE). Scrapling: D4Vinci, BSD-3-Clause. Apify und Instagram sind Marken ihrer Inhaber; dieses Projekt ist nicht mit ihnen verbunden.
