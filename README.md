# Claude Code x Home Assistant (Windows)

Dein Smart Home per natuerlicher Sprache verwalten -- mit [Claude Code](https://docs.anthropic.com/en/docs/claude-code), der Kommandozeilen-KI von Anthropic.

> Sage Claude was du willst. Er schreibt das YAML, validiert es, deployt es auf deinen HA-Server und prueft ob alles laeuft. 

## Features

- **Automationen per Sprache** -- "Schreib eine Automation die bei Wasseralarm alle Bewohner benachrichtigt"
- **KNX-Import aus ETS** -- GA-CSV exportieren, Claude erstellt alle Entities automatisch
- **Automatische Validierung** -- Hooks pruefen jede Aenderung, blockieren fehlerhafte Deploys
- **Dashboards bauen** -- Claude erstellt Lovelace-Cards ueber MCP
- **Debugging** -- "Warum feuert meine Automation nicht?" (liest Log, Config, History)
- **Bulk-Operationen** -- 400 KNX-Entities anlegen, Benennungen vereinheitlichen, Duplikate finden
- **Kontext per CLAUDE.md** -- Claude kennt dein gesamtes Setup und arbeitet sofort produktiv
- **Safe Deployments** -- Pre-Push-Validation verhindert kaputte Configs auf dem Live-System

## Wie funktioniert das?

```
                              bash ha push
  ┌──────────────┐    <───────────────────    ┌───────────────┐    git push    ┌──────────┐
  │  HA Server   │                            │  Workspace    │  ──────────>   │  GitHub  │
  │  (live)      │    ───────────────────>    │  (lokal)      │                │ (Backup) │
  └──────┬───────┘    bash ha pull            └───────┬───────┘                └──────────┘
         │                                            │
         │  MCP: Entities steuern,                    │  Claude Code: YAML editieren,
         │  Services aufrufen, Logs lesen             │  validieren, SSH/SCP deployen
         └────────────────────────────────────────────┘
```

1. `bash ha pull` -- Config vom HA-Server holen
2. Claude editiert Packages, Hooks validieren automatisch
3. `bash ha push` -- Pre-Push-Hook blockiert bei Fehlern, sonst Deploy
4. Claude laedt Config via MCP neu und prueft das Ergebnis

## Quick Start

### Voraussetzungen

| PC (Windows) | Home Assistant |
|--------------|---------------|
| [Node.js 18+](https://nodejs.org/) | SSH-Zugang (Port 22, Root) |
| [Python 3.10+](https://www.python.org/) + `pip install pyyaml` | [MCP Server Add-on](https://github.com/home-assistant/mcp-server) |
| [Git + Git Bash](https://git-scm.com/) | Long-Lived Access Token |
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code): `npm install -g @anthropic-ai/claude-code` | |
| [Anthropic Abo](https://claude.ai/upgrade) (Pro $20/Max $100 pro Monat) | |

### 1. Repo klonen & Setup

```powershell
git clone https://github.com/dashdevil/claude-hawin.git
cd claude-hawin
powershell -ExecutionPolicy Bypass -File setup.ps1
```

Das Setup-Script prueft alle Dependencies und erstellt die MCP-Config-Vorlage.

### 2. CLAUDE.md anpassen

Die `CLAUDE.md` wird bei jedem Claude-Start automatisch geladen. Sie macht Claude zu deinem HA-Experten. Oeffne sie und passe an:

- Bewohner-Namen & Notification-Targets
- SSH-Hostname (falls nicht `homeassistant.local`)
- Deine Schluessel-Entities

> **Tipp:** Starte Claude und sag: *"Pruefe mein HA ueber MCP und ergaenze die CLAUDE.md."* -- er macht das selbst.

### 3. MCP-Verbindung einrichten

```bash
# In Claude Code:
/mcp add home-assistant
# URL: http://homeassistant.local:8123/mcp/sse
# Header: Authorization: Bearer DEIN_TOKEN
```

### 4. SSH testen & loslegen

```bash
ssh root@homeassistant.local "ha core info"

# Claude starten:
claude

# Erster Befehl:
> Pruefe alle Verbindungen (SSH, MCP, Python) und sag mir was fehlt.
```

## Projektstruktur

```
.claude/
├── settings.json            # Hook-Config (validiert bei Edit & Push)
├── hooks/
│   ├── post-yaml-validate.sh    # Nach Edit: YAML pruefen (informativ)
│   └── pre-push-validate.sh     # Vor Push: YAML pruefen (blockierend!)
└── skills/
    ├── knx/skill.md             # KNX-Patterns (bei Bedarf geladen)
    └── ha-overview/skill.md     # Package-Architektur (bei Bedarf geladen)

tools/
├── yaml_validator.py            # Syntax, Encoding, Struktur, doppelte IDs
├── entity_reference_checker.py  # Entity-Referenzen, Umlaut-Fehler
└── run_tests.py                 # Test-Orchestrator

packages/                        # HA-Packages (Beispiele zum Anpassen)
├── beispiel_alarm.yaml          # Wassermelder-Benachrichtigung
├── beispiel_beleuchtung.yaml    # Aussenbeleuchtung mit Daemmerung
└── knx/                         # KNX GA-Mappings
    ├── beispiel_zentral.yaml
    └── licht/beispiel_schalten.yaml

CLAUDE.md          # Kontext fuer Claude (DAS Herzstuck)
ha                 # Workflow-Script (bash ha <befehl>)
setup.ps1          # Windows Setup-Script
```

## Workflow-Befehle

```bash
bash ha pull           # Packages vom HA-Server holen
bash ha push <file>    # Validieren + ein Package deployen
bash ha push-all       # Alle Packages deployen
bash ha test           # Alle Validatoren lokal ausfuehren
bash ha check          # HA Config-Check auf dem Server
bash ha errors         # ERROR-Zeilen aus dem HA-Log
bash ha backup         # Timestamped Backup vom Server
```

## Was kann ich Claude sagen?

### Automationen

```
"Schreib eine Automation: Gartenbeleuchtung an bei Daemmerung, aus ab 23 Uhr."

"Wenn der Briefkasten geoeffnet wird und es kein Feiertag ist,
 schick mir eine Push-Benachrichtigung mit 'Post ist da!'."

"Erstelle ein Bewaesserungs-Package mit 4 Kreisen, Timern und Regensensor-Sperre."
```

### KNX

```
"Lies meine KNX-GA-CSV und zeig mir die Struktur."

"Erstelle alle Licht-Entities aus der CSV als KNX light-Entities."

"Lege alle Praesenzmelder als binary_sensor mit sync_state an."
```

### Debugging & Wartung

```
"Warum zeigt sensor.pv_erzeugung 'unavailable'?"

"Finde alle Automationen die notify.altes_handy nutzen und ersetze es."

"Strukturiere meine Packages um: Steckdosen raus aus melden.yaml, eigenes Package."
```

### Dashboards

```
"Erstelle ein Dashboard mit allen Temperatur-Sensoren als Gauge-Cards."

"Fuege dem Energie-Dashboard eine Card mit PV-Erzeugung und Netzbezug hinzu."
```

## Validierung

Zwei Ebenen schuetzen dein Live-System:

| Hook | Wann | Verhalten |
|------|------|-----------|
| **Post-Edit** | Nach jedem Edit/Write | Informiert Claude ueber Fehler (nicht blockierend) |
| **Pre-Push** | Vor SSH-Deploy | **Blockiert Push** bei YAML-Fehlern (Exit Code 2) |

**Was geprueft wird:**
- YAML-Syntax inkl. HA-Tags (`!include`, `!secret`, `!input`)
- UTF-8 Encoding (faengt Windows-CRLF ab)
- Package-Struktur (triggers + actions, scripts brauchen sequence)
- Doppelte Automation-IDs ueber alle Packages
- Umlaut-Fehler in Entity-IDs (`praesenz` falsch, `prasenz` richtig)

## Packages: Warum und Wie

Dieses Setup nutzt ausschliesslich [HA Packages](https://www.home-assistant.io/docs/configuration/packages/) -- keine GUI-Automationen, kein `automations.yaml`. Ein Package buendelt alles was zusammengehoert:

```yaml
# packages/alarm.yaml
automation:
  - id: alarm_kueche_wasser
    alias: "Alarm: Kueche - Wassermelder"
    triggers:
      - trigger: state
        entity_id: binary_sensor.kueche_wasser
        to: 'on'
    actions:
      - action: notify.mobile_app_mein_handy
        data:
          title: Alarm
          message: "Wassermelder Kueche!"

input_boolean:
  wassermelder_stumm:
    name: "Wassermelder stumm"
```

**Vorteile:** Git-freundlich, Claude versteht Packages als Einheiten, kein GUI/`.storage`-Chaos.

**KNX-Packages** liegen in `packages/knx/` und enthalten nur GA-Mappings:

```yaml
# packages/knx/licht/schalten.yaml
knx:
  light:
    - name: "EG Kueche Deckenlampe"
      address: "5/0/1"
      state_address: "5/0/2"
```

## CLAUDE.md -- Der Kontext

Die `CLAUDE.md` macht Claude von einem generischen Assistenten zu deinem HA-Experten. Sie wird bei jedem Start geladen und enthaelt:

- **Regeln** -- "Alles in Packages", "Keine GUI-Scenes", "MCP nur zum Pruefen"
- **Entities** -- Deine zentralen Schalter, Notification-Targets, Praesenz-Gruppen
- **Workflow** -- Verfuegbare `bash ha`-Befehle
- **Konventionen** -- Namensschema, Umlaut-Regeln

Claude kann die CLAUDE.md auch selbst aktualisieren: *"Ergaenze die Package-Tabelle."*

## Linux / macOS

Dieser Workspace ist fuer **Windows (Git Bash)** gebaut. Unter Linux/macOS funktioniert fast alles identisch -- ggf. `python3` statt `python` im `ha`-Script anpassen. Oder sag Claude: *"Passe den Workspace fuer Linux an."*

## Credits

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) -- Anthropic
- [philippb/claude-homeassistant](https://github.com/philippb/claude-homeassistant) -- Inspiration fuer Validation-Hooks und das Deployment-Konzept
- [Home Assistant MCP Server](https://github.com/home-assistant/mcp-server)

## Lizenz

MIT -- siehe [LICENSE](LICENSE)
