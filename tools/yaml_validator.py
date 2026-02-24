#!/usr/bin/env python3
"""YAML-Validator fuer Home Assistant Packages.

Prueft:
  1. YAML-Syntax (inkl. HA-Tags wie !include, !secret, !input)
  2. UTF-8 Encoding
  3. Struktur: automations brauchen trigger+action, scripts brauchen sequence
  4. Doppelte Automation-IDs ueber alle Packages
"""

import sys
import yaml
import argparse
from pathlib import Path
from collections import defaultdict

# Windows-Encoding fix: UTF-8 erzwingen
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------------
# HA-kompatibler YAML-Loader (unterstuetzt !include, !secret, !input, etc.)
# ---------------------------------------------------------------------------
class HAYamlLoader(yaml.SafeLoader):
    """YAML-Loader mit Home Assistant Custom Tags."""
    pass


def _ha_tag_constructor(loader, tag_suffix, node):
    """Generischer Konstruktor fuer HA-Tags -- gibt Platzhalter zurueck."""
    if isinstance(node, yaml.ScalarNode):
        return f"!{tag_suffix} {loader.construct_scalar(node)}"
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    return None


# Alle HA-spezifischen Tags registrieren
for tag in ("include", "include_dir_list", "include_dir_named",
            "include_dir_merge_list", "include_dir_merge_named",
            "secret", "input", "env_var"):
    HAYamlLoader.add_constructor(
        f"!{tag}",
        lambda loader, node, t=tag: _ha_tag_constructor(loader, t, node),
    )


# ---------------------------------------------------------------------------
# Validierungs-Logik
# ---------------------------------------------------------------------------
class ValidationResult:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, file: str, msg: str):
        self.errors.append(f"  FEHLER  {file}: {msg}")

    def warn(self, file: str, msg: str):
        self.warnings.append(f"  WARNUNG {file}: {msg}")

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


def validate_yaml_syntax(filepath: Path, result: ValidationResult) -> dict | list | None:
    """Prueft YAML-Syntax und gibt geparsten Inhalt zurueck."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = yaml.load(f, Loader=HAYamlLoader)
        return content
    except UnicodeDecodeError as e:
        result.error(filepath.name, f"Encoding-Fehler (kein gueltiges UTF-8): {e}")
        return None
    except yaml.YAMLError as e:
        result.error(filepath.name, f"YAML-Syntax-Fehler: {e}")
        return None


def validate_package_structure(filepath: Path, content, result: ValidationResult):
    """Prueft HA-Package-Struktur."""
    if content is None:
        return

    name = filepath.name

    # Leere Datei oder nur Kommentare
    if content is None:
        return

    # Sonderfall: automations.yaml darf eine leere Liste sein
    if name == "automations.yaml" and isinstance(content, list) and len(content) == 0:
        return

    # Packages muessen ein Dict auf Top-Level sein
    if not isinstance(content, dict):
        # Koennte eine flat automations.yaml sein (Liste) -- auch ok
        if isinstance(content, list):
            _validate_automation_list(filepath, content, result)
            return
        result.error(name, f"Package muss ein Dict sein, ist aber {type(content).__name__}")
        return

    # Bekannte HA-Domains in Packages
    known_domains = {
        "automation", "script", "input_boolean", "input_number", "input_select",
        "input_text", "input_datetime", "input_button", "timer", "counter",
        "template", "sensor", "binary_sensor", "switch", "light", "cover",
        "fan", "climate", "lock", "media_player", "notify", "group",
        "shell_command", "rest_command", "homeassistant", "knx",
        "alert", "scene", "mqtt",
    }

    for key, value in content.items():
        if key == "automation":
            if isinstance(value, list):
                _validate_automation_list(filepath, value, result)
            elif value is not None:
                result.error(name, f"'automation:' muss eine Liste sein, ist aber {type(value).__name__}")

        elif key == "script":
            if isinstance(value, dict):
                _validate_script_dict(filepath, value, result)
            elif value is not None:
                result.error(name, f"'script:' muss ein Dict sein, ist aber {type(value).__name__}")

        elif key not in known_domains:
            result.warn(name, f"Unbekannte Domain '{key}' -- Tippfehler?")


def _validate_automation_list(filepath: Path, automations: list, result: ValidationResult):
    """Prueft jede Automation auf Pflichtfelder."""
    for i, auto in enumerate(automations):
        if not isinstance(auto, dict):
            result.error(filepath.name, f"Automation #{i+1} ist kein Dict")
            continue

        alias = auto.get("alias", f"#{i+1} (ohne alias)")

        # trigger oder triggers (HA 2024.8+ nutzt Plural)
        has_trigger = any(k in auto for k in ("trigger", "triggers"))
        if not has_trigger:
            result.error(filepath.name, f"Automation '{alias}': 'trigger:' oder 'triggers:' fehlt")

        # action oder actions (HA 2024.8+ nutzt Plural)
        has_action = any(k in auto for k in ("action", "actions"))
        if not has_action:
            result.error(filepath.name, f"Automation '{alias}': 'action:' oder 'actions:' fehlt")


def _validate_script_dict(filepath: Path, scripts: dict, result: ValidationResult):
    """Prueft jedes Script auf 'sequence'."""
    for script_id, script_def in scripts.items():
        if not isinstance(script_def, dict):
            result.error(filepath.name, f"Script '{script_id}' ist kein Dict")
            continue
        if "sequence" not in script_def:
            result.error(filepath.name, f"Script '{script_id}': 'sequence:' fehlt")


def _collect_automation_ids(filepath: Path, content, all_ids: list):
    """Sammelt Automation-IDs aus einem Package."""
    automations = None
    if isinstance(content, dict) and "automation" in content:
        automations = content["automation"]
    elif isinstance(content, list):
        automations = content

    if not isinstance(automations, list):
        return

    for auto in automations:
        if isinstance(auto, dict) and "id" in auto:
            all_ids.append((
                filepath.name,
                auto["id"],
                auto.get("alias", "(kein alias)"),
            ))


def _check_duplicate_ids(all_ids: list, result: ValidationResult):
    """Prueft auf doppelte Automation-IDs ueber alle Dateien."""
    id_map = defaultdict(list)
    for fname, aid, alias in all_ids:
        id_map[aid].append((fname, alias))

    for aid, locations in id_map.items():
        if len(locations) > 1:
            files_str = ", ".join(f"{fn}" for fn, _ in locations)
            result.error("GLOBAL", f"Doppelte Automation-ID '{aid}' in: {files_str}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="HA Package YAML Validator")
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
        # Default: packages/ im Projektverzeichnis
        project_dir = Path(__file__).resolve().parent.parent
        pkg_dir = project_dir / "packages"
        if pkg_dir.is_dir():
            files = sorted(pkg_dir.glob("**/*.yaml"))

    if not files:
        print("Keine YAML-Dateien gefunden.")
        return 0

    result = ValidationResult()
    all_auto_ids = []

    for filepath in files:
        if not filepath.exists():
            result.error(str(filepath), "Datei nicht gefunden")
            continue
        content = validate_yaml_syntax(filepath, result)
        if content is not None:
            validate_package_structure(filepath, content, result)
            # Automation-IDs sammeln fuer Duplikat-Pruefung
            _collect_automation_ids(filepath, content, all_auto_ids)

    # Doppelte Automation-IDs ueber alle Dateien pruefen
    _check_duplicate_ids(all_auto_ids, result)

    # Ausgabe
    total = len(files)
    print(f"\n{'='*60}")
    print(f"  HA YAML Validator -- {total} Datei(en) geprueft")
    print(f"{'='*60}")

    if result.warnings:
        print(f"\n  Warnungen ({len(result.warnings)}):")
        for w in result.warnings:
            print(f"    {w}")

    if result.errors:
        print(f"\n  Fehler ({len(result.errors)}):")
        for e in result.errors:
            print(f"    {e}")
        print(f"\n  ERGEBNIS: FEHLGESCHLAGEN")
        print(f"{'='*60}\n")
        return 1
    else:
        print(f"\n  ERGEBNIS: BESTANDEN")
        print(f"{'='*60}\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
