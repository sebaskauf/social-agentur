#!/usr/bin/env bash
# Social-Media-Agentur: Kopier-Installation für Mac und Linux (auch Git Bash unter Windows).
# Erster Lauf installiert, jeder weitere Lauf aktualisiert. Danach heißt der Befehl /agentur.
set -euo pipefail

REPO_URL="${SOCIAL_AGENTUR_REPO_URL:-https://github.com/sebaskauf/social-agentur.git}"
DATEN="${SOCIAL_AGENTUR_HOME:-$HOME/.social-agentur}"
QUELLE="$DATEN/repo"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
AGENTEN="profil-agent trend-agent content-agent community-agent follower-agent viral-agent analyse-agent"

command -v git >/dev/null 2>&1 || { echo "git fehlt. Mac: xcode-select --install · Windows: https://git-scm.com" >&2; exit 1; }

mkdir -p "$DATEN"
if [ -d "$QUELLE/.git" ]; then
  git -C "$QUELLE" pull --ff-only -q
  echo "Agentur-Dateien aktualisiert ($QUELLE)."
else
  git clone -q --depth 1 "$REPO_URL" "$QUELLE"
  echo "Agentur heruntergeladen ($QUELLE)."
fi

# Schutz: nichts überschreiben, was nicht von der Agentur stammt
if [ -d "$CLAUDE_DIR/skills/agentur" ] && [ ! -f "$CLAUDE_DIR/skills/agentur/.social-agentur-version" ]; then
  echo "Abbruch: $CLAUDE_DIR/skills/agentur gibt es schon und stammt nicht von der Social-Media-Agentur. Bitte umbenennen und neu starten." >&2
  exit 2
fi
for a in $AGENTEN; do
  f="$CLAUDE_DIR/agents/$a.md"
  if [ -f "$f" ] && ! grep -q "Social-Media-Agentur" "$f"; then
    echo "Abbruch: $f gibt es schon und stammt nicht von der Social-Media-Agentur. Bitte umbenennen und neu starten." >&2
    exit 2
  fi
done

mkdir -p "$CLAUDE_DIR/skills" "$CLAUDE_DIR/agents"
rm -rf "$CLAUDE_DIR/skills/agentur.neu"
cp -R "$QUELLE/skills/agentur" "$CLAUDE_DIR/skills/agentur.neu"
rm -rf "$CLAUDE_DIR/skills/agentur"
mv "$CLAUDE_DIR/skills/agentur.neu" "$CLAUDE_DIR/skills/agentur"
for a in $AGENTEN; do cp "$QUELLE/agents/$a.md" "$CLAUDE_DIR/agents/$a.md"; done

echo "Installiert: Skill /agentur in $CLAUDE_DIR/skills/agentur und 7 Agenten in $CLAUDE_DIR/agents/."
echo "Version: $(cat "$CLAUDE_DIR/skills/agentur/.social-agentur-version")"
echo "Erscheint /agentur nicht sofort: /reload-skills eintippen oder Claude Code einmal neu starten."
