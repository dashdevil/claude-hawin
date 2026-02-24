#!/usr/bin/env bash
## Home Assistant -- Workflow-Script
## Nutzung: bash ha <command> [args]
## Funktioniert ohne GNU Make auf Windows/Git Bash.

set -euo pipefail

# =============================================================================
# KONFIGURATION -- Passe diese Werte an dein Setup an!
# =============================================================================
HA_HOST="root@homeassistant.local"     # SSH-Zugang zu deinem HA
HA_PKG_DIR="/config/packages"          # Package-Pfad auf dem HA-Server
HA_LOG="/config/home-assistant.log"    # HA-Log-Pfad
LOCAL_PKG="packages"                   # Lokaler Package-Ordner
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VALIDATOR="python $SCRIPT_DIR/tools/yaml_validator.py"
REF_CHECKER="python $SCRIPT_DIR/tools/entity_reference_checker.py"
ORCHESTRATOR="python $SCRIPT_DIR/tools/run_tests.py"

# ---------- Farben ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ---------- Funktionen ----------

cmd_help() {
    echo ""
    echo -e "  ${BLUE}Home Assistant -- Workflow-Kommandos${NC}"
    echo "  ===================================="
    echo ""
    echo "  Validation:"
    echo "    bash ha validate       YAML-Syntax + Struktur aller Packages pruefen"
    echo "    bash ha check-refs     Entity-Referenzen extrahieren"
    echo "    bash ha test           Alle Validatoren ausfuehren"
    echo ""
    echo "  HA-Server:"
    echo "    bash ha check          HA Config Check (ha core check)"
    echo "    bash ha log            Letzte 50 Log-Zeilen"
    echo "    bash ha errors         Nur ERROR-Zeilen aus dem Log"
    echo "    bash ha status         Packages auf Server + lokal + Git"
    echo ""
    echo "  Sync:"
    echo "    bash ha pull           Alle Packages vom Server holen"
    echo "    bash ha push <file>    Ein Package auf den Server pushen"
    echo "    bash ha push-all       ALLE Packages auf den Server pushen"
    echo "    bash ha backup         Timestamped Backup aller Server-Packages"
    echo ""
}

cmd_validate() {
    $VALIDATOR --packages-dir "$SCRIPT_DIR/$LOCAL_PKG"
}

cmd_check_refs() {
    $REF_CHECKER --packages-dir "$SCRIPT_DIR/$LOCAL_PKG"
}

cmd_test() {
    $ORCHESTRATOR
}

cmd_check() {
    ssh "$HA_HOST" "ha core check"
}

cmd_log() {
    ssh "$HA_HOST" "tail -50 $HA_LOG"
}

cmd_errors() {
    ssh "$HA_HOST" "tail -100 $HA_LOG | grep -i error" || echo -e "  ${GREEN}Keine Fehler gefunden.${NC}"
}

cmd_status() {
    echo ""
    echo "=== Packages auf HA-Server ==="
    ssh "$HA_HOST" "find $HA_PKG_DIR -name '*.yaml' | sort"
    echo ""
    echo "=== Lokale Packages ==="
    ls -la "$SCRIPT_DIR/$LOCAL_PKG"/*.yaml 2>/dev/null || echo "  Keine lokalen Packages."
    echo ""
    echo "=== Git Status ==="
    git -C "$SCRIPT_DIR" status --short
    echo ""
}

cmd_pull() {
    echo "Pulling packages von $HA_HOST:$HA_PKG_DIR/ ..."
    mkdir -p "$SCRIPT_DIR/$LOCAL_PKG"
    # Rekursiv alle Packages inkl. Unterordner holen
    ssh "$HA_HOST" "find $HA_PKG_DIR -name '*.yaml' -type f" | while read -r remote_file; do
        local rel_path="${remote_file#$HA_PKG_DIR/}"
        local local_dir="$SCRIPT_DIR/$LOCAL_PKG/$(dirname "$rel_path")"
        mkdir -p "$local_dir"
        scp "$HA_HOST:$remote_file" "$local_dir/"
    done
    echo -e "${GREEN}Done. Lokale Packages aktualisiert.${NC}"
}

cmd_push() {
    local file="${1:-}"
    if [[ -z "$file" ]]; then
        echo -e "${RED}Fehler: Dateiname/Pfad fehlt.${NC}"
        echo "Nutzung: bash ha push beleuchtung.yaml"
        echo "         bash ha push knx/heizung.yaml"
        exit 1
    fi

    if [[ ! -f "$SCRIPT_DIR/$LOCAL_PKG/$file" ]]; then
        echo -e "${RED}Fehler: $LOCAL_PKG/$file nicht gefunden.${NC}"
        exit 1
    fi

    echo ""
    echo "=== Pre-Push: Validiere alle Packages ==="
    $VALIDATOR --packages-dir "$SCRIPT_DIR/$LOCAL_PKG"

    echo "=== Backup auf HA ==="
    ssh "$HA_HOST" "cp '$HA_PKG_DIR/$file' '$HA_PKG_DIR/$file.bak' 2>/dev/null || true"

    echo "=== Push: $file -> HA ==="
    ssh "$HA_HOST" "mkdir -p '$(dirname "$HA_PKG_DIR/$file")'"
    scp "$SCRIPT_DIR/$LOCAL_PKG/$file" "$HA_HOST:$HA_PKG_DIR/$file"

    echo ""
    echo -e "${GREEN}Fertig.${NC} Jetzt 'bash ha check' und dann Reload per MCP ausfuehren."
}

cmd_push_all() {
    echo ""
    echo "=== Pre-Push: Validiere alle Packages ==="
    $VALIDATOR --packages-dir "$SCRIPT_DIR/$LOCAL_PKG"

    echo "=== Backup auf HA ==="
    ssh "$HA_HOST" "cd $HA_PKG_DIR && find . -name '*.yaml' -type f -exec cp {} {}.bak \;"

    echo "=== Push: alle Packages -> HA ==="
    # Rekursiv alle Packages inkl. Unterordner pushen
    find "$SCRIPT_DIR/$LOCAL_PKG" -name '*.yaml' -type f | while read -r local_file; do
        local rel_path="${local_file#$SCRIPT_DIR/$LOCAL_PKG/}"
        ssh "$HA_HOST" "mkdir -p '$(dirname "$HA_PKG_DIR/$rel_path")'"
        scp "$local_file" "$HA_HOST:$HA_PKG_DIR/$rel_path"
    done

    echo ""
    echo -e "${GREEN}Fertig.${NC} Jetzt 'bash ha check' und dann Reload per MCP ausfuehren."
}

cmd_backup() {
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    mkdir -p "$SCRIPT_DIR/backups/$timestamp"
    # Rekursiv alle Packages inkl. Unterordner sichern
    ssh "$HA_HOST" "find $HA_PKG_DIR -name '*.yaml' -type f" | while read -r remote_file; do
        local rel_path="${remote_file#$HA_PKG_DIR/}"
        local local_dir="$SCRIPT_DIR/backups/$timestamp/$(dirname "$rel_path")"
        mkdir -p "$local_dir"
        scp "$HA_HOST:$remote_file" "$local_dir/"
    done
    echo -e "${GREEN}Backup gespeichert in backups/$timestamp/${NC}"
}

# ---------- Main ----------

COMMAND="${1:-help}"
shift || true

case "$COMMAND" in
    help|--help|-h)   cmd_help ;;
    validate)         cmd_validate ;;
    check-refs)       cmd_check_refs ;;
    test)             cmd_test ;;
    check)            cmd_check ;;
    log)              cmd_log ;;
    errors)           cmd_errors ;;
    status)           cmd_status ;;
    pull)             cmd_pull ;;
    push)             cmd_push "$@" ;;
    push-all)         cmd_push_all ;;
    backup)           cmd_backup ;;
    *)
        echo -e "${RED}Unbekannter Befehl: $COMMAND${NC}"
        cmd_help
        exit 1
        ;;
esac
