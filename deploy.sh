#!/bin/bash
# Aggiorna l'indice e sincronizza le modifiche sul repo GitHub Pages.
# Uso: ./deploy.sh [messaggio di commit]

set -euo pipefail

ORIGINE="/Users/lorenzodemarchi/Library/CloudStorage/OneDrive-UniversitàdegliStudidiUdine/OncologiaConcorso"
DEST="$(cd "$(dirname "$0")" && pwd)"
MSG="${1:-Aggiornamento schede}"

echo "==> Rieseguo genera_indice.py..."
python3 "$ORIGINE/scripts/genera_indice.py"

echo "==> Sincronizzo Schede..."
rsync -av --delete --exclude='.git' --exclude='.DS_Store' --exclude='.Rhistory' \
  "$ORIGINE/Schede/" "$DEST/Schede/"

echo "==> Sincronizzo data..."
rsync -av --delete --exclude='.git' --exclude='.DS_Store' \
  "$ORIGINE/data/" "$DEST/data/"

echo "==> Sincronizzo dashboard..."
rsync -av --delete --exclude='.git' --exclude='.DS_Store' \
  "$ORIGINE/dashboard/" "$DEST/dashboard/"

echo "==> Push..."
cd "$DEST"
git add -A
if git diff --cached --quiet; then
  echo "Nessuna modifica da caricare."
else
  git commit -m "$MSG"
  git push
  echo "==> Fatto! Pubblicato su GitHub Pages."
fi
