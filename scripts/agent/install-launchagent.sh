#!/bin/bash
# Installe l'agent Pix LFT en LaunchAgent macOS.
# Après installation : démarre automatiquement à chaque ouverture de session,
# redémarre tout seul s'il crashe, plus besoin de Terminal ouvert.
#
# Usage : ./install-launchagent.sh

set -euo pipefail

LABEL="com.lft.pixsync"
LOCAL_DIR="$HOME/.local/share/pix-sync"
REPO_AGENT="$(cd "$(dirname "$0")" && pwd)"
REPO_SITE="$(dirname "$(dirname "$REPO_AGENT")")"  # site/
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOGS="$HOME/Library/Logs"

echo "──────────────────────────────────────────────"
echo "  Installation LaunchAgent — PIX LFT"
echo "──────────────────────────────────────────────"
echo "  Repo : $REPO_SITE"
echo "  Local: $LOCAL_DIR"
echo

# 1. venv local (hors OneDrive — TCC bloque les venv en CloudStorage sous launchd)
if [ ! -x "$LOCAL_DIR/venv/bin/python" ]; then
  echo "[1/4] Création du venv local..."
  mkdir -p "$LOCAL_DIR"
  python3 -m venv "$LOCAL_DIR/venv"
  "$LOCAL_DIR/venv/bin/pip" install --quiet --upgrade pip
  # Playwright pour le scraping Pix Orga, pandas+openpyxl pour build-data.py
  # (qui est invoqué via sys.executable, donc le venv doit aussi les avoir).
  "$LOCAL_DIR/venv/bin/pip" install --quiet playwright pandas openpyxl
  "$LOCAL_DIR/venv/bin/python" -m playwright install chromium
else
  echo "[1/4] venv local déjà en place ✓"
fi

# 2. Copie du script (le source dans le repo reste la référence éditable)
echo "[2/4] Copie du script agent vers $LOCAL_DIR/agent.py"
cp "$REPO_AGENT/pix-sync-agent.py" "$LOCAL_DIR/agent.py"

# 3. Génère le plist LaunchAgent
echo "[3/4] Écriture du LaunchAgent : $PLIST"
mkdir -p "$HOME/Library/LaunchAgents" "$LOGS"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${LOCAL_DIR}/venv/bin/python</string>
        <string>${LOCAL_DIR}/agent.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${LOCAL_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>ProcessType</key>
    <string>Background</string>
    <key>StandardOutPath</key>
    <string>${LOGS}/pix-sync-agent.log</string>
    <key>StandardErrorPath</key>
    <string>${LOGS}/pix-sync-agent.err.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PIX_REPO</key>
        <string>${REPO_SITE}</string>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>LANG</key>
        <string>fr_FR.UTF-8</string>
        <key>HOME</key>
        <string>${HOME}</string>
    </dict>
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
EOF

plutil -lint "$PLIST" >/dev/null

# 4. (Re)charge l'agent
echo "[4/4] Chargement..."
launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

sleep 2
if curl -sf http://127.0.0.1:7777/health >/dev/null; then
  echo
  echo "✅ Agent en place — http://127.0.0.1:7777/health répond."
  echo "   Tu peux maintenant cliquer 'Synchroniser Pix Orga' depuis le dashboard."
  echo
  echo "   Logs : tail -f $LOGS/pix-sync-agent.log"
  echo "   Stop : ./uninstall-launchagent.sh"
else
  echo
  echo "⚠️  L'agent n'a pas répondu — consulte $LOGS/pix-sync-agent.err.log"
  exit 1
fi
