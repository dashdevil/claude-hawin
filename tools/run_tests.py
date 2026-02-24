#!/usr/bin/env python3
"""Test-Orchestrator: Fuehrt alle Validatoren nacheinander aus.

Reihenfolge:
  1. YAML Syntax + Struktur (yaml_validator.py)
  2. Entity Reference Check (entity_reference_checker.py)
"""

import sys
import subprocess
import time
from pathlib import Path

# Windows-Encoding fix: UTF-8 erzwingen
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")


def run_validator(name: str, script: str, args: list[str]) -> bool:
    """Fuehrt einen Validator aus und gibt True bei Erfolg zurueck."""
    print(f"\n{'─'*60}")
    print(f"  [{name}]")
    print(f"{'─'*60}")

    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, script] + args,
            capture_output=False,
            timeout=120,
        )
        elapsed = time.time() - start
        status = "BESTANDEN" if result.returncode == 0 else "FEHLGESCHLAGEN"
        print(f"  -> {status} ({elapsed:.1f}s)")
        return result.returncode == 0
    except FileNotFoundError:
        print(f"  -> UEBERSPRUNGEN (Script nicht gefunden: {script})")
        return True
    except subprocess.TimeoutExpired:
        print(f"  -> TIMEOUT nach 120s")
        return False


def main():
    project_dir = Path(__file__).resolve().parent.parent
    tools_dir = project_dir / "tools"
    pkg_dir = project_dir / "packages"

    pkg_args = ["--packages-dir", str(pkg_dir)]

    print(f"\n{'='*60}")
    print(f"  HA Test-Orchestrator")
    print(f"  Packages: {pkg_dir}")
    print(f"{'='*60}")

    results = {}

    # 1. YAML Validator
    results["YAML Syntax"] = run_validator(
        "YAML Syntax + Struktur",
        str(tools_dir / "yaml_validator.py"),
        pkg_args,
    )

    # 2. Entity Reference Checker
    results["Entity Refs"] = run_validator(
        "Entity Reference Check",
        str(tools_dir / "entity_reference_checker.py"),
        pkg_args,
    )

    # Gesamtergebnis
    all_passed = all(results.values())
    print(f"\n{'='*60}")
    print(f"  GESAMTERGEBNIS")
    print(f"{'='*60}")
    for name, passed in results.items():
        icon = "OK" if passed else "FAIL"
        print(f"  [{icon:>4}] {name}")

    if all_passed:
        print(f"\n  Alle Tests bestanden.")
    else:
        failed = [n for n, p in results.items() if not p]
        print(f"\n  {len(failed)} Test(s) fehlgeschlagen: {', '.join(failed)}")

    print(f"{'='*60}\n")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
