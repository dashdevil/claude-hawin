# Skill: KNX

> Wird automatisch geladen bei Arbeit an KNX-Entities, GA-Mappings oder Busadressen.

## KNX Gruppenadress-Schema

KNX nutzt ein **3-stufiges Adressschema**: `Hauptgruppe/Mittelgruppe/Untergruppe` (z.B. `1/2/3`).

Die Zuordnung der Gruppen ist **projektspezifisch** -- jeder ETS-Programmierer strukturiert anders. Gaengige Varianten:

| Gliederung | Hauptgruppe | Mittelgruppe | Beispiel |
|------------|------------|-------------|---------|
| **Nach Gewerk** | Licht, Beschattung, Heizung, ... | Etage oder Raum | `1/0/1` = Licht / EG / Lampe 1 |
| **Nach Etage** | EG, OG, DG, Aussen, ... | Gewerk | `0/1/1` = EG / Licht / Lampe 1 |
| **Nach Raum** | Wohnzimmer, Kueche, Bad, ... | Gewerk | `0/0/1` = WZ / Licht / Lampe 1 |
| **Gemischt** | Kombination aus obigen | variiert | abhaengig vom Projekt |

**Wichtig:** Die GA-Struktur muss aus dem ETS-Export (CSV) gelesen werden. Nicht raten!

## Entity-Patterns fuer HA KNX-Integration

### Licht (Schalten)
```yaml
knx:
  light:
    - name: "Wohnzimmer Deckenlampe"
      address: "x/x/x"           # Schalten (HA -> KNX)
      state_address: "x/x/x"     # Rueckmeldung (KNX -> HA)
```

### Licht (Dimmen)
```yaml
knx:
  light:
    - name: "Wohnzimmer Stehlampe"
      address: "x/x/x"                    # Schalten
      state_address: "x/x/x"              # Schalt-Rueckmeldung
      brightness_address: "x/x/x"         # Dimmwert setzen (0-255)
      brightness_state_address: "x/x/x"   # Dimmwert Rueckmeldung
```

### Jalousien (Hoehe + Lamellenwinkel)
```yaml
knx:
  cover:
    - name: "Wohnzimmer Jalousie"
      move_long_address: "x/x/x"       # Fahren (auf/ab)
      stop_address: "x/x/x"            # Stopp
      position_address: "x/x/x"        # Hoehe setzen (0-100%)
      position_state_address: "x/x/x"  # Hoehe Rueckmeldung
      angle_address: "x/x/x"           # Lamelle setzen
      angle_state_address: "x/x/x"     # Lamelle Rueckmeldung
```

### Rolllaeden (nur Hoehe, kein Winkel)
```yaml
knx:
  cover:
    - name: "Schlafzimmer Rollladen"
      move_long_address: "x/x/x"
      stop_address: "x/x/x"
      position_address: "x/x/x"
      position_state_address: "x/x/x"
```

### Heizung / Fussbodenheizung (Climate)
```yaml
knx:
  climate:
    - name: "Wohnzimmer Heizung"
      temperature_address: "x/x/x"                # Ist-Temperatur
      target_temperature_address: "x/x/x"         # Soll setzen
      target_temperature_state_address: "x/x/x"   # Soll Rueckmeldung
```

### Binaersensoren (Fenster, Praesenz, Alarm)
```yaml
knx:
  binary_sensor:
    - name: "Wohnzimmer Fenster"
      state_address: "x/x/x"
      sync_state: every 60      # Wichtig! Regelmaessig Status abfragen
```

### Schalter (zentrale Funktionen, PM-Sperren, etc.)
```yaml
knx:
  switch:
    - name: "Tag / Nacht"
      address: "x/x/x"           # Schalten
      state_address: "x/x/x"     # Rueckmeldung
```

## GA-Import aus ETS

1. **ETS oeffnen** > Gruppenadressen > Rechtsklick > Export (CSV oder XML)
2. **CSV im Workspace ablegen** als `KNX_group_addresses.xml.csv`
3. **Claude anweisen**, z.B.:
   - "Lies die KNX-GA-CSV und zeige mir die Struktur (Hauptgruppen + Anzahl GAs)"
   - "Erstelle alle Licht-Entities aus den GAs die 'Licht' oder 'Schalten' enthalten"
   - "Erstelle alle Heizungs-Zonen als climate Entities"

Claude analysiert die CSV, erkennt das Adressschema und erstellt passende HA-Entities.

## Wichtige Regeln

- **Vor jeder KNX-Aenderung:** GA-CSV lesen um korrekte Adressen sicherzustellen
- **KNX-Packages enthalten nur GA-Mappings** -- keine Automations-Logik
- **sync_state** bei binary_sensors setzen (z.B. `every 60`) damit HA den Status kennt
- **Umlaute in Entity-IDs:** HA kuerzt ue->u, ae->a, oe->o (nicht ue->ue!)
- **PM-Sperren:** Verhalten ist PM-abhaengig. Manche PMs schalten bei Sperre das Licht aus, andere nicht. **Immer vorher klaeren!**
- **GA-Adressen nie raten** -- immer aus dem ETS-Export ablesen
