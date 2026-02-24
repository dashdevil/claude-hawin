# Skill: HA-Uebersicht

> Wird geladen wenn Claude uebergreifend ueber Packages plant.

## Architektur

Alle Config in `packages/`. Root-`configuration.yaml` enthaelt nur:
```yaml
homeassistant:
  packages: !include_dir_named packages
```

## Package-Typen

| Typ | Pfad | Inhalt |
|-----|------|--------|
| Feature-Packages | `packages/*.yaml` | Automationen + Helpers + Templates |
| KNX-Packages | `packages/knx/*.yaml` | Nur GA-Mappings, keine Logik |

## Regeln

- Ein Package = ein Gewerk (nicht alles in eine Datei)
- KNX-Packages: nur GA-Mappings, Logik in Feature-Packages
- Package-Tabelle in CLAUDE.md aktualisieren bei neuen Packages
- `bash ha check-refs` zeigt alle referenzierten Entities
