# Home Assistant -- Claude Code Context

> HA 2025.x | Bewohner: BEWOHNER_1 & BEWOHNER_2

## Regeln

- **Alles in Packages** -- niemals `automations.yaml`, `scripts.yaml` oder GUI
- **Keine HA-Scenes** -- ausschliesslich Scripts verwenden
- **MCP nur zum Pruefen** -- Coding in YAML-Packages, Deployment per SSH
- **Validation ist Pflicht** -- Hooks laufen automatisch, Pre-Push blockiert bei Fehlern
- **Vor KNX-Aufgaben** immer `KNX_group_addresses_xml.csv` lesen
- **NIEMALS `.storage/`-Dateien manipulieren** -- nur HA-UI, MCP oder REST API
- **Vor groesseren Umbauten** Backup erstellen (`bash ha backup`)

## Entity-ID Umlaute

HA slugifiziert Umlaute **ohne** ae/oe/ue-Ersetzung:

| Zeichen | Entity-ID | Falsch |
|---------|-----------|--------|
| ae | `prasenz` | `praesenz` |
| oe | `scholl` | `schoell` |
| ue | `kuche` | `kueche` |
| ss | `strasse` | -- |

## Zugang

```bash
ssh root@homeassistant.local          # TODO: Dein HA-Host
# Packages: /config/packages/
# Secrets:  /config/secrets.yaml      # NIE ausgeben!
```

## Workflow

```bash
bash ha pull                # Packages vom Server holen
bash ha push <datei.yaml>   # Validieren + pushen
bash ha push-all            # Alle Packages pushen
bash ha test                # Validatoren lokal ausfuehren
bash ha check               # Config-Check auf dem Server
bash ha errors              # ERROR-Zeilen aus HA-Log
bash ha backup              # Timestamped Backup
```

**Nach Push:** Reload via MCP (`automation.reload` / `script.reload`). Nicht `ha core reload`!

## Schluessel-Entities

```
notify.mobile_app_DEIN_HANDY              # TODO: Haupt-Benachrichtigung
# notify.mobile_app_PARTNER               # TODO: Partner
# switch.tag_nacht                        # Tag/Nacht
# binary_sensor.jemand_zuhause            # Praesenz
```

## Namensschema

- **Alias:** `[Gewerk]: [Ort --] Funktion`
- **ID:** slugifizierter Alias (`alarm_kueche_wassermelder`)
- **Gewerke:** Alarm, Beleuchtung, Beschattung, Heizung, ...
