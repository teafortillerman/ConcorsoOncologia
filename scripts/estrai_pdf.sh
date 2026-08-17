#!/bin/bash
# Estrae in testo (pdftotext -layout) tutti i PDF di una patologia da AIOM, ESMO/CPG_PDF e Congressi.
# Uso: ./estrai_pdf.sh <parola_chiave> [cartella_output]
# Esempio: ./estrai_pdf.sh Polmone
#          ./estrai_pdf.sh "NSCLC|Polmone"
#
# Output: file .txt in /tmp/onco_extract/<parola_chiave>/ con nome uguale al PDF sorgente.

set -e

ROOT="/Users/lorenzodemarchi/Library/CloudStorage/OneDrive-UniversitàdegliStudidiUdine/OncologiaConcorso"
KEYWORD="$1"
SAFE_NAME=$(echo "$1" | tr -c 'A-Za-z0-9_' '_')
OUTDIR="${2:-/tmp/onco_extract/$SAFE_NAME}"

if [ -z "$KEYWORD" ]; then
  echo "Uso: $0 <parola_chiave_regex_case_insensitive> [cartella_output]"
  exit 1
fi

mkdir -p "$OUTDIR"

echo "== Ricerca PDF corrispondenti a '$KEYWORD' =="
FILES=$(find "$ROOT/AIOM" "$ROOT/ESMO/CPG_PDF" "$ROOT/Congressi" -iname "*.pdf" 2>/dev/null | grep -iE "$KEYWORD" || true)

if [ -z "$FILES" ]; then
  echo "Nessun PDF trovato per '$KEYWORD'."
  exit 1
fi

echo "$FILES" | while read -r f; do
  base=$(basename "$f" .pdf)
  out="$OUTDIR/${base}.txt"
  echo "-> $base"
  pdftotext -layout "$f" "$out" 2>/dev/null
done

echo ""
echo "== Riepilogo file estratti in $OUTDIR =="
wc -l "$OUTDIR"/*.txt
