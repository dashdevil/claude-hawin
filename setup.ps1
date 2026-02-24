# ============================================================================
# Claude Code x Home Assistant -- Windows Setup
# ============================================================================
# Prueft alle Voraussetzungen und fuehrt durch die Einrichtung.
# Ausfuehren: powershell -ExecutionPolicy Bypass -File setup.ps1
# ============================================================================

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Claude Code x Home Assistant - Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$allGood = $true

# --- 1. Node.js ---
Write-Host "[1/6] Node.js ..." -NoNewline
try {
    $nodeVersion = (node --version 2>$null)
    if ($nodeVersion) {
        Write-Host " $nodeVersion" -ForegroundColor Green
    } else { throw }
} catch {
    Write-Host " FEHLT" -ForegroundColor Red
    Write-Host "       Installieren: https://nodejs.org/" -ForegroundColor Yellow
    $allGood = $false
}

# --- 2. Python ---
Write-Host "[2/6] Python ..." -NoNewline
try {
    $pyVersion = (python --version 2>$null)
    if ($pyVersion) {
        Write-Host " $pyVersion" -ForegroundColor Green
    } else { throw }
} catch {
    Write-Host " FEHLT" -ForegroundColor Red
    Write-Host "       Installieren: https://www.python.org/" -ForegroundColor Yellow
    $allGood = $false
}

# --- 3. PyYAML ---
Write-Host "[3/6] PyYAML ..." -NoNewline
try {
    $pyaml = python -c "import yaml; print(yaml.__version__)" 2>$null
    if ($pyaml) {
        Write-Host " v$pyaml" -ForegroundColor Green
    } else { throw }
} catch {
    Write-Host " FEHLT" -ForegroundColor Red
    Write-Host "       Installieren: pip install pyyaml" -ForegroundColor Yellow
    $allGood = $false
}

# --- 4. Claude Code ---
Write-Host "[4/6] Claude Code ..." -NoNewline
try {
    $claudeVersion = (claude --version 2>$null)
    if ($claudeVersion) {
        Write-Host " v$claudeVersion" -ForegroundColor Green
    } else { throw }
} catch {
    Write-Host " FEHLT" -ForegroundColor Red
    Write-Host "       Installieren: npm install -g @anthropic-ai/claude-code" -ForegroundColor Yellow
    $allGood = $false
}

# --- 5. SSH ---
Write-Host "[5/6] SSH Client ..." -NoNewline
try {
    $sshVersion = (ssh -V 2>&1)
    if ($sshVersion) {
        Write-Host " OK" -ForegroundColor Green
    } else { throw }
} catch {
    Write-Host " FEHLT" -ForegroundColor Red
    Write-Host "       Windows: Einstellungen > Apps > Optionale Features > OpenSSH-Client" -ForegroundColor Yellow
    $allGood = $false
}

# --- 6. Git ---
Write-Host "[6/6] Git ..." -NoNewline
try {
    $gitVersion = (git --version 2>$null)
    if ($gitVersion) {
        Write-Host " $gitVersion" -ForegroundColor Green
    } else { throw }
} catch {
    Write-Host " FEHLT" -ForegroundColor Red
    Write-Host "       Installieren: https://git-scm.com/" -ForegroundColor Yellow
    $allGood = $false
}

Write-Host ""

if (-not $allGood) {
    Write-Host "Einige Voraussetzungen fehlen. Bitte zuerst installieren." -ForegroundColor Red
    Write-Host ""
    exit 1
}

Write-Host "Alle Voraussetzungen erfuellt!" -ForegroundColor Green
Write-Host ""

# --- MCP-Config Template ---
$settingsLocal = ".claude/settings.local.json"
if (-not (Test-Path $settingsLocal)) {
    Write-Host "Erstelle MCP-Template: $settingsLocal" -ForegroundColor Cyan
    $template = @'
{
  "permissions": {
    "allow": [
      "mcp__home-assistant__ha_search_entities",
      "mcp__home-assistant__ha_get_states",
      "mcp__home-assistant__ha_get_state",
      "mcp__home-assistant__ha_get_entity",
      "mcp__home-assistant__ha_call_service",
      "Bash(ssh:*)",
      "Bash(scp:*)"
    ]
  }
}
'@
    $template | Out-File -Encoding utf8 $settingsLocal
    Write-Host "  Erstellt. Wird NICHT ins Git committed (.gitignore)." -ForegroundColor Gray
} else {
    Write-Host "$settingsLocal existiert bereits." -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Naechste Schritte:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. CLAUDE.md oeffnen und an dein Setup anpassen" -ForegroundColor White
Write-Host "     (Bewohner, SSH-Host, Entities)" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. MCP-Server in HA installieren:" -ForegroundColor White
Write-Host "     https://github.com/home-assistant/mcp-server" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. MCP-Verbindung in Claude einrichten:" -ForegroundColor White
Write-Host "     claude starten, dann: /mcp add home-assistant" -ForegroundColor Gray
Write-Host ""
Write-Host "  4. SSH-Verbindung testen:" -ForegroundColor White
Write-Host "     ssh root@homeassistant.local 'ha core info'" -ForegroundColor Gray
Write-Host ""
Write-Host "  5. Claude starten und loslegen:" -ForegroundColor White
Write-Host "     claude" -ForegroundColor Gray
Write-Host ""
Write-Host "  Erster Befehl an Claude:" -ForegroundColor Yellow
Write-Host '  "Pruefe alle Verbindungen (SSH, MCP, Python) und sag mir was fehlt."' -ForegroundColor Yellow
Write-Host ""
