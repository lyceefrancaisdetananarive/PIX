#!/bin/bash
# Installation de l'agent Pix LFT (à lancer UNE FOIS)

set -e

cd "$(dirname "$0")"

echo ""
echo "  Installation de l'agent Pix LFT"
echo "  ──────────────────────────────"
echo ""

# Détection Python
if ! command -v python3 &>/dev/null; then
  echo "  ✗ Python 3 introuvable. Installe-le depuis python.org."
  exit 1
fi
PY=$(python3 --version)
echo "  → $PY"

# Création d'un venv local
VENV=".venv"
if [ ! -d "$VENV" ]; then
  echo "  → Création de l'environnement virtuel ($VENV/)"
  python3 -m venv "$VENV"
fi

# Activation et install
source "$VENV/bin/activate"

echo "  → Installation de Playwright et dépendances…"
pip install --upgrade pip --quiet
pip install playwright --quiet

echo "  → Téléchargement de Chromium pour Playwright (~140 Mo)…"
playwright install chromium

echo ""
echo "  ✓ Agent installé."
echo ""
echo "  Étape suivante : configurer tes identifiants Pix Orga"
echo "      ./scripts/agent/setup-keychain.sh"
echo ""
echo "  Puis pour démarrer l'agent :"
echo "      ./scripts/agent/start.command"
echo ""
