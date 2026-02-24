#!/usr/bin/env bash
# Claude Code Hook: PostToolUse (Edit|Write)
# Validiert YAML-Dateien automatisch nach jeder Bearbeitung.
# Non-blocking: zeigt Warnungen/Fehler, blockiert aber nicht.

INPUT=$(cat)

# Datei-Pfad aus dem stdin-JSON extrahieren (Python statt jq -- portabler)
FILE_PATH=$(echo "$INPUT" | python -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('file_path', ''))
except:
    print('')
" 2>/dev/null)

# Nur .yaml-Dateien in packages/ validieren
if [[ -z "$FILE_PATH" ]]; then
    exit 0
fi

if [[ "$FILE_PATH" != *.yaml ]]; then
    exit 0
fi

if [[ "$FILE_PATH" != *packages* ]]; then
    exit 0
fi

# Validator ausfuehren
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
VALIDATOR="$PROJECT_DIR/tools/yaml_validator.py"

if [[ ! -f "$VALIDATOR" ]]; then
    exit 0
fi

# Nur die bearbeitete Datei validieren
OUTPUT=$(python "$VALIDATOR" "$FILE_PATH" 2>&1)
EXIT_CODE=$?

if [[ $EXIT_CODE -ne 0 ]]; then
    echo "$OUTPUT" >&2
    # Exit 0: nicht blockieren, nur informieren (Claude kann iterieren)
    exit 0
fi

exit 0
