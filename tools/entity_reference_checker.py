#!/usr/bin/env python3
"""Entity Reference Checker fuer Home Assistant Packages.

Extrahiert alle Entity-Referenzen aus YAML-Packages und prueft auf:
  1. Umlaut-Fehler (praesenz statt prasenz, etc.)
  2. Doppelte Automation-IDs
  3. Uebersicht aller referenzierten Entities nach Domain
"""

import sys
import os
import re
import yaml
import argparse
from pathlib import Path
from collections import defaultdict

# Windows-Encoding fix: UTF-8 erzwingen
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

# HA YAML Loader (gleich wie in yaml_validator.py)
class HAYamlLoader(yaml.SafeLoader):
    pass

def _ha_tag_constructor(loader, tag_suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return f"!{tag_suffix} {loader.construct_scalar(node)}"
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    return None

for tag in ("include", "include_dir_list", "include_dir_named",
            "include_dir_merge_list", "include_dir_merge_named",
            "secret", "input", "env_var"):
    HAYamlLoader.add_constructor(
        f"!{tag}",
        lambda loader, node, t=tag: _ha_tag_constructor(loader, t, node),
    )


# ---------------------------------------------------------------------------
# Umlaut-Pruefregeln
# ---------------------------------------------------------------------------
UMLAUT_MISTAKES = [
    ("ae", "a", "ae->a", ["praesenz", "waerme", "kaelte", "laenge", "naehe"]),
    ("oe", "o", "oe->o", ["oeffn", "hoehe", "groesse"]),
    ("ue", "u", "ue->u", ["kuech", "tuere", "lueft", "gruess", "schluessel"]),
]

# Woerter wo ae/oe/ue natuerlich vorkommt (kein Umlaut-Fehler)
UMLAUT_FALSE_POSITIVES = {
    "ae": ["aero", "israel"],
    "oe": ["does", "poet", "goes"],
    "ue": ["feuer", "steuer", "neuer", "teuer", "quer", "queue", "blue", "true",
           "muell", "blaue", "graue", "value", "aktuelle"],
}


def check_umlaut_errors(entity_id: str) -> list[str]:
    """Prueft ob eine Entity-ID falsche Umlaut-Ersetzungen enthaelt."""
    warnings = []
    lower = entity_id.lower()
    for wrong, correct, rule, examples in UMLAUT_MISTAKES:
        if wrong in lower:
            # False-Positive-Check: ist der Treffer Teil eines normalen Worts?
            is_fp = False
            for fp_word in UMLAUT_FALSE_POSITIVES.get(wrong, []):
                if fp_word in lower:
                    is_fp = True
                    break
            if is_fp:
                continue

            idx = lower.find(wrong)
            context = lower[max(0, idx-3):idx+len(wrong)+3]
            warnings.append(
                f"Umlaut-Verdacht ({rule}): '{entity_id}' enthaelt '{wrong}' "
                f"(Kontext: ...{context}...) -- sollte '{correct}' sein?"
            )
    return warnings


# ---------------------------------------------------------------------------
# Entity-ID Extraktion
# ---------------------------------------------------------------------------
ENTITY_PATTERN = re.compile(
    r'\b([a-z_]+\.[a-z0-9][a-z0-9_]*)\b'
)

VALID_DOMAINS = {
    "automation", "binary_sensor", "button", "calendar", "camera", "climate",
    "counter", "cover", "device_tracker", "fan", "group", "humidifier",
    "input_boolean", "input_button", "input_datetime", "input_number",
    "input_select", "input_text", "light", "lock", "media_player", "notify",
    "number", "person", "remote", "scene", "script", "select", "sensor",
    "siren", "sun", "switch", "timer", "update", "vacuum", "water_heater",
    "weather", "zone",
}

# HA Service-Actions die wie Entity-IDs aussehen, aber keine sind
SERVICE_ACTIONS = {
    "turn_on", "turn_off", "toggle", "reload",
    # cover
    "close_cover", "open_cover", "stop_cover", "set_cover_position",
    "set_cover_tilt_position",
    # lock
    "lock", "unlock", "open",
    # timer
    "start", "cancel", "pause", "finish", "change",
    # climate
    "set_temperature", "set_hvac_mode", "set_fan_mode", "set_preset_mode",
    # light
    "turn_on", "turn_off",
    # media_player
    "play_media", "media_play", "media_pause", "media_stop",
    "volume_set", "volume_up", "volume_down",
    # fan
    "set_speed", "set_percentage", "set_direction",
    # notify (special: notify.xyz IS a valid service target)
    # vacuum
    "start_pause", "return_to_base", "send_command",
    # homeassistant
    "check_config", "reload_core_config", "restart",
    # automation/script
    "trigger",
}


def is_service_call(entity_like: str) -> bool:
    """Prueft ob ein domain.xyz-String ein Service-Call ist statt eine Entity."""
    parts = entity_like.split(".", 1)
    if len(parts) != 2:
        return False
    domain, object_id = parts
    return object_id in SERVICE_ACTIONS


def extract_entity_ids(obj, found: set, path: str = ""):
    """Rekursiv alle Entity-IDs aus einem YAML-Objekt extrahieren."""
    if isinstance(obj, str):
        # Direkte entity_id Werte
        if "." in obj and not obj.startswith("!"):
            matches = ENTITY_PATTERN.findall(obj)
            for m in matches:
                domain = m.split(".")[0]
                if domain in VALID_DOMAINS and not is_service_call(m):
                    found.add(m)
        # Jinja2 Templates: states('sensor.xyz'), is_state('sensor.xyz', ...)
        for tmpl_match in re.finditer(r"(?:states|is_state|state_attr)\s*\(\s*['\"]([^'\"]+)['\"]", obj):
            entity = tmpl_match.group(1)
            if "." in entity:
                domain = entity.split(".")[0]
                if domain in VALID_DOMAINS and not is_service_call(entity):
                    found.add(entity)

    elif isinstance(obj, list):
        for item in obj:
            extract_entity_ids(item, found, path)

    elif isinstance(obj, dict):
        for key, value in obj.items():
            # Skip: 'action:' Keys enthalten Service-Calls, keine Entity-IDs
            if key == "action" and isinstance(value, str):
                continue
            extract_entity_ids(value, found, f"{path}.{key}")


def extract_automation_ids(content) -> list[tuple[str, str]]:
    """Extrahiert alle Automation-IDs und Aliase."""
    ids = []
    if isinstance(content, dict) and "automation" in content:
        automations = content["automation"]
        if isinstance(automations, list):
            for auto in automations:
                if isinstance(auto, dict):
                    aid = auto.get("id", "")
                    alias = auto.get("alias", "(kein alias)")
                    if aid:
                        ids.append((aid, alias))
    elif isinstance(content, list):
        for auto in content:
            if isinstance(auto, dict):
                aid = auto.get("id", "")
                alias = auto.get("alias", "(kein alias)")
                if aid:
                    ids.append((aid, alias))
    return ids


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="HA Entity Reference Checker")
    parser.add_argument("files", nargs="*", help="YAML-Dateien zum Pruefen")
    parser.add_argument("--packages-dir", "-d",
                        help="Packages-Verzeichnis (prueft alle .yaml darin)")
    args = parser.parse_args()

    # Dateien sammeln
    files = []
    if args.files:
        files = [Path(f) for f in args.files]
    elif args.packages_dir:
        pkg_dir = Path(args.packages_dir)
        if pkg_dir.is_dir():
            files = sorted(pkg_dir.glob("**/*.yaml"))
    else:
        project_dir = Path(__file__).resolve().parent.parent
        pkg_dir = project_dir / "packages"
        if pkg_dir.is_dir():
            files = sorted(pkg_dir.glob("**/*.yaml"))

    if not files:
        print("Keine YAML-Dateien gefunden.")
        return 0

    all_entities = set()
    all_auto_ids = []
    entities_by_file = {}
    umlaut_warnings = []
    errors = []

    for filepath in files:
        if not filepath.exists():
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = yaml.load(f, Loader=HAYamlLoader)
        except (yaml.YAMLError, UnicodeDecodeError):
            continue

        if content is None:
            continue

        # Entity-IDs extrahieren
        file_entities = set()
        extract_entity_ids(content, file_entities)
        entities_by_file[filepath.name] = file_entities
        all_entities.update(file_entities)

        # Automation-IDs sammeln
        auto_ids = extract_automation_ids(content)
        for aid, alias in auto_ids:
            all_auto_ids.append((filepath.name, aid, alias))

        # Umlaut-Check auf alle gefundenen Entities
        for entity in file_entities:
            warnings = check_umlaut_errors(entity)
            for w in warnings:
                umlaut_warnings.append((filepath.name, w))

    # --- Doppelte Automation-IDs ---
    id_counts = defaultdict(list)
    for fname, aid, alias in all_auto_ids:
        id_counts[aid].append((fname, alias))

    duplicate_ids = {aid: locs for aid, locs in id_counts.items() if len(locs) > 1}

    # --- Ausgabe ---
    print(f"\n{'='*60}")
    print(f"  HA Entity Reference Checker -- {len(files)} Datei(en)")
    print(f"{'='*60}")

    # Entities nach Domain gruppiert
    by_domain = defaultdict(set)
    for entity in sorted(all_entities):
        domain = entity.split(".")[0]
        by_domain[domain].add(entity)

    print(f"\n  Referenzierte Entities: {len(all_entities)} (in {len(by_domain)} Domains)")
    for domain in sorted(by_domain.keys()):
        entities = sorted(by_domain[domain])
        print(f"\n  [{domain}] ({len(entities)})")
        for e in entities:
            # Zeige in welchen Dateien
            in_files = [fn for fn, ents in entities_by_file.items() if e in ents]
            print(f"    {e}  ({', '.join(in_files)})")

    # Automation-IDs
    print(f"\n  Automation-IDs: {len(all_auto_ids)}")

    # Duplikate
    if duplicate_ids:
        errors.append(f"{len(duplicate_ids)} doppelte Automation-ID(s)")
        print(f"\n  FEHLER: Doppelte Automation-IDs:")
        for aid, locs in duplicate_ids.items():
            print(f"    '{aid}' in:")
            for fname, alias in locs:
                print(f"      - {fname}: {alias}")

    # Umlaut-Warnungen
    if umlaut_warnings:
        print(f"\n  WARNUNG: Moegliche Umlaut-Fehler ({len(umlaut_warnings)}):")
        for fname, warning in umlaut_warnings:
            print(f"    {fname}: {warning}")

    # Ergebnis
    if errors:
        print(f"\n  ERGEBNIS: {len(errors)} FEHLER gefunden")
        print(f"{'='*60}\n")
        return 1
    elif umlaut_warnings:
        print(f"\n  ERGEBNIS: BESTANDEN mit {len(umlaut_warnings)} Warnung(en)")
        print(f"{'='*60}\n")
        return 0
    else:
        print(f"\n  ERGEBNIS: BESTANDEN")
        print(f"{'='*60}\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
