#!/usr/bin/env bash
# Installation de la passerelle Mistral sur le VPS Allovente (exécuter une seule fois).
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "Clé API Mistral requise (console.mistral.ai > Clés API)."
  read -rsp "Collez votre clé API Mistral : " KEY
  echo
  echo "MISTRAL_API_KEY=$KEY" > .env
  chmod 600 .env
  echo ".env créé."
fi

echo "Création du venv et installation des dépendances..."
python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt

echo "Installation du service systemd..."
sudo cp allovente-gateway.service /etc/systemd/system/allovente-gateway.service
sudo systemctl daemon-reload
sudo systemctl enable --now allovente-gateway

sleep 3
echo "--- Statut du service ---"
systemctl --no-pager status allovente-gateway | head -12
echo
echo "Logs en direct : journalctl -u allovente-gateway -f"
