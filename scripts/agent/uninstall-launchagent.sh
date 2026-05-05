#!/bin/bash
# Désinstalle le LaunchAgent et arrête l'agent.
# Conserve le venv local au cas où tu veuilles réutiliser plus tard.

set -euo pipefail
LABEL="com.lft.pixsync"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"

echo "Arrêt et désinstallation de ${LABEL}..."
launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
[ -f "$PLIST" ] && rm "$PLIST" && echo "  ✓ $PLIST supprimé"

# Confirmation
if curl -sf --max-time 1 http://127.0.0.1:7777/health >/dev/null 2>&1; then
  echo "  ⚠ L'agent répond encore — il y a peut-être une instance manuelle (start.command). Ferme-la."
else
  echo "  ✓ Agent arrêté"
fi
