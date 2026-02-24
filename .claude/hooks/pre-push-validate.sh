#!/usr/bin/env bash
# Claude Code Hook: PreToolUse (Bash)
# Blockiert SSH-Push auf HA wenn YAML-Validation fehlschlaegt.
# Exit 2 = blockieren, Exit 0 = durchlassen.

INPUT=$(cat)

# Bash-Command aus stdin-JSON extrahieren
COMMAND=$(echo "$INPUT" | python -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('command', ''))
except:
    print('')
" 2>/dev/null)

# Nur SSH-Befehle Richtung HA abfangen die Dateien kopieren
if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# Pruefe ob der Befehl Dateien auf den HA-Server schreibt
# Patterns: ssh ... cp, scp ... homeassistant, ssh ... mv, ssh ... tee
IS_PUSH=false
if echo "$COMMAND" | grep -qE 'ssh.*homeassistant.*(cp |mv |tee |cat.*>)'; then
    IS_PUSH=true
fi
if echo "$COMMAND" | grep -qE 'scp.*homeassistant'; then
    IS_PUSH=true
fi

if [[ "$IS_PUSH" != "true" ]]; then
    exit 0
fi

# === VALIDATION GATE ===
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
VALIDATOR="$PROJECT_DIR/tools/yaml_validator.py"

if [[ ! -f "$VALIDATOR" ]]; then
    echo "WARNUNG: yaml_validator.py nicht gefunden -- Push wird trotzdem erlaubt" >&2
    exit 0
fi

echo "Pre-Push Validation: Pruefe alle Packages..." >&2
OUTPUT=$(python "$VALIDATOR" --packages-dir "$PROJECT_DIR/packages" 2>&1)
EXIT_CODE=$?

if [[ $EXIT_CODE -ne 0 ]]; then
    echo "" >&2
    echo "===== PUSH BLOCKIERT =====" >&2
    echo "YAML-Validation fehlgeschlagen. Bitte Fehler zuerst beheben." >&2
    echo "" >&2
    echo "$OUTPUT" >&2
    echo "==========================" >&2
    exit 2
fi

echo "Validation bestanden -- Push wird fortgesetzt." >&2
exit 0
