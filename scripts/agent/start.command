#!/bin/bash
# Raccourci à double-cliquer pour démarrer l'agent Pix LFT.
# Tu peux aussi le mettre sur ton Bureau via un alias.

cd "$(dirname "$0")"

# Active le venv si présent, sinon utilise le python système
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
fi

clear
echo "──────────────────────────────────────────────"
echo "  PIX LFT — Agent local de synchronisation"
echo "──────────────────────────────────────────────"
python3 pix-sync-agent.py
