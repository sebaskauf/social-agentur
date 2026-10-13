# Social-Media-Agentur: Kopier-Installation für Windows (PowerShell).
# Erster Lauf installiert, jeder weitere Lauf aktualisiert. Danach heißt der Befehl /agentur.
$ErrorActionPreference = "Stop"
$RepoUrl = if ($env:SOCIAL_AGENTUR_REPO_URL) { $env:SOCIAL_AGENTUR_REPO_URL } else { "https://github.com/sebaskauf/social-agentur.git" }
$Daten = if ($env:SOCIAL_AGENTUR_HOME) { $env:SOCIAL_AGENTUR_HOME } else { Join-Path $HOME ".social-agentur" }
$Quelle = Join-Path $Daten "repo"
$ClaudeDir = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $HOME ".claude" }
$Agenten = @("profil-agent","trend-agent","content-agent","community-agent","follower-agent","viral-agent","analyse-agent")

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Write-Error "git fehlt. Installation: https://git-scm.com"; exit 1 }

New-Item -ItemType Directory -Force -Path $Daten | Out-Null
if (Test-Path (Join-Path $Quelle ".git")) {
  git -C $Quelle pull --ff-only -q
  Write-Output "Agentur-Dateien aktualisiert ($Quelle)."
} else {
  git clone -q --depth 1 $RepoUrl $Quelle
  Write-Output "Agentur heruntergeladen ($Quelle)."
}

$SkillZiel = Join-Path $ClaudeDir "skills\agentur"
if ((Test-Path $SkillZiel) -and -not (Test-Path (Join-Path $SkillZiel ".social-agentur-version"))) {
  Write-Error "Abbruch: $SkillZiel gibt es schon und stammt nicht von der Social-Media-Agentur."; exit 2
}
foreach ($a in $Agenten) {
  $f = Join-Path $ClaudeDir "agents\$a.md"
  if ((Test-Path $f) -and -not (Select-String -Path $f -Pattern "Social-Media-Agentur" -Quiet)) {
    Write-Error "Abbruch: $f gibt es schon und stammt nicht von der Social-Media-Agentur."; exit 2
  }
}

New-Item -ItemType Directory -Force -Path (Join-Path $ClaudeDir "skills"), (Join-Path $ClaudeDir "agents") | Out-Null
if (Test-Path $SkillZiel) { Remove-Item -Recurse -Force $SkillZiel }
Copy-Item -Recurse (Join-Path $Quelle "skills\agentur") $SkillZiel
foreach ($a in $Agenten) { Copy-Item (Join-Path $Quelle "agents\$a.md") (Join-Path $ClaudeDir "agents\$a.md") -Force }

Write-Output "Installiert: Skill /agentur in $SkillZiel und 7 Agenten in $(Join-Path $ClaudeDir 'agents')."
Write-Output "Erscheint /agentur nicht sofort: /reload-skills eintippen oder Claude Code einmal neu starten."
