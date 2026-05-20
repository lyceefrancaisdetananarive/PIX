#!/bin/bash
# Raccourci à double-cliquer pour démarrer l'agent Pix LFT.
# Tu peux aussi le mettre sur ton Bureau via un alias.
#
# Le venv local (~/.local/share/pix-sync/venv) contient playwright +
# pandas + openpyxl. Le venv dans OneDrive est évité car macOS TCC bloque
# parfois son accès depuis certains contextes.

LOCAL_VENV="$HOME/.local/share/pix-sync/venv"
REPO_AGENT="$(cd "$(dirname "$0")" && pwd)"
REPO_SITE="$(dirname "$(dirname "$REPO_AGENT")")"  # site/

# Si le venv local manque, redirige vers l'installateur
if [ ! -x "$LOCAL_VENV/bin/python" ]; then
  echo "⚠  Venv local introuvable : $LOCAL_VENV"
  echo "   Lance d'abord : $REPO_AGENT/install-launchagent.sh"
  echo "   (ce script crée le venv avec playwright + pandas + openpyxl)"
  echo ""
  echo "Appuie sur une touche pour fermer…"
  read -n1
  exit 1
fi

# Sanity check : les 3 paquets critiques doivent être importables
if ! "$LOCAL_VENV/bin/python" -c "import playwright, pandas, openpyxl" 2>/dev/null; then
  echo "⚠  Dépendances manquantes dans $LOCAL_VENV"
  echo "   Installation des paquets manquants…"
  "$LOCAL_VENV/bin/pip" install --quiet playwright pandas openpyxl
  "$LOCAL_VENV/bin/python" -m playwright install chromium
fi

# Évite que deux instances tournent en même temps (port 7777)
if lsof -nP -iTCP:7777 >/dev/null 2>&1; then
  echo "⚠  Un agent tourne déjà sur le port 7777 :"
  lsof -nP -iTCP:7777 | head -3
  echo ""
  echo "   Pour le remplacer par CET agent (avec ce venv) :"
  echo "   → pkill -9 -f 'pix-sync|agent.py' puis relance start.command"
  echo ""
  echo "Appuie sur une touche pour fermer…"
  read -n1
  exit 0
fi

clear
echo "──────────────────────────────────────────────"
echo "  PIX LFT — Agent local de synchronisation"
echo "──────────────────────────────────────────────"
echo "  Python : $LOCAL_VENV/bin/python"
echo "  Repo   : $REPO_SITE"
echo "──────────────────────────────────────────────"
echo ""
echo "  Garde cette fenêtre OUVERTE pendant la sync."
echo "  Ctrl+C pour arrêter l'agent."
echo "──────────────────────────────────────────────"
echo ""

export PIX_REPO="$REPO_SITE"
"$LOCAL_VENV/bin/python" "$REPO_AGENT/pix-sync-agent.py"
RC=$?

# Si python sort (crash ou Ctrl+C), on garde la fenêtre ouverte pour voir l'erreur
echo ""
echo "──────────────────────────────────────────────"
if [ $RC -eq 0 ]; then
  echo "  Agent arrêté proprement."
else
  echo "  ⚠ Agent terminé avec le code $RC"
  echo ""
  echo "  Causes fréquentes :"
  echo "    • Code 1 ou autre : exception Python (voir la trace ci-dessus)"
  echo "    • Code 130        : Ctrl+C (arrêt normal)"
  echo "    • [Errno 48]      : port 7777 déjà utilisé par un autre agent"
  echo "      → pkill -9 -f 'pix-sync|agent.py' puis relance"
fi
echo "──────────────────────────────────────────────"
echo ""
echo "Appuie sur une touche pour fermer cette fenêtre…"
read -n1
