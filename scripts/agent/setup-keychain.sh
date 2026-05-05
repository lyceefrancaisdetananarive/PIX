#!/bin/bash
# Setup interactif des identifiants Pix Orga dans le Keychain macOS
# Le mot de passe N'EST JAMAIS visible dans un fichier ni dans Claude.

set -e

SERVICE="pix-lft-sync"

echo ""
echo "  Configuration des identifiants Pix Orga"
echo "  ──────────────────────────────────────"
echo ""
echo "  Ces identifiants sont stockés UNIQUEMENT dans le Keychain"
echo "  macOS de cet ordinateur (chiffrés par le système)."
echo ""

read -p "  Email Pix Orga : " EMAIL
echo ""
echo -n "  Mot de passe Pix Orga (caché) : "
read -s PASSWORD
echo ""

# Stocke l'email
security add-generic-password -U \
  -s "$SERVICE" \
  -a "pix-orga-email" \
  -w "$EMAIL" \
  -T /usr/bin/security \
  -T "$(which python3)" \
  2>/dev/null

# Stocke le mot de passe
security add-generic-password -U \
  -s "$SERVICE" \
  -a "pix-orga" \
  -w "$PASSWORD" \
  -T /usr/bin/security \
  -T "$(which python3)" \
  2>/dev/null

unset PASSWORD

echo ""
echo "  ✓ Identifiants enregistrés dans le Keychain (service: $SERVICE)"
echo ""
echo "  Pour les modifier plus tard, relance ce script."
echo "  Pour les supprimer :"
echo "    security delete-generic-password -s '$SERVICE' -a 'pix-orga'"
echo "    security delete-generic-password -s '$SERVICE' -a 'pix-orga-email'"
echo ""
