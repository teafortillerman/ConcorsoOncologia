#!/usr/bin/env python3
"""Costruisce il sito statico per GitHub Pages in `_site/`.

Copia solo i file necessari alla visualizzazione (dashboard, schede, dati,
algoritmi) e aggiunge una pagina iniziale che apre la dashboard.

I PDF delle fonti (AIOM, ESMO, congressi) restano solo in locale: nella copia
pubblicata della dashboard i link "Apri PDF" verso file non presenti vengono
trasformati in una ricerca online del titolo, invece di finire su un 404.
I file sorgente non vengono modificati, quindi la sincronizzazione dalla
cartella locale può continuare a sovrascriverli senza problemi.
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"
DASHBOARD = "dashboard/oncologia-concorso.html"
COPY_DIRS = ["dashboard", "Schede", "data", "Algoritmi"]
# *.dc.html sono sorgenti del canvas di design e richiedono file non presenti nel repo
IGNORE = shutil.ignore_patterns("*.dc.html", ".DS_Store", "__pycache__")

INDEX_HTML = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Oncologia Medica</title>
<meta http-equiv="refresh" content="0; url={DASHBOARD}">
<link rel="canonical" href="{DASHBOARD}">
</head>
<body>
<p><a href="{DASHBOARD}">Apri la dashboard di Oncologia Medica</a></p>
</body>
</html>
"""

PDF_FALLBACK_JS = """
<script>
/* Aggiunto in fase di pubblicazione (tools/build_site.py):
   i PDF non pubblicati diventano una ricerca online del titolo. */
(function () {
  var MISSING = new Set(%s);
  function fix(root) {
    root.querySelectorAll('a[href$=".pdf"]:not([data-pdf-fixed])').forEach(function (a) {
      var path = decodeURI(a.getAttribute("href")).replace(/^(\\.\\.\\/)+/, "");
      if (!MISSING.has(path)) return;
      a.setAttribute("data-pdf-fixed", "1");
      var card = a.closest(".related-card");
      var titleEl = card && card.querySelector(".rc-title");
      var title = titleEl ? titleEl.textContent : path.split("/").pop().replace(/\\.pdf$/, "");
      a.href = "https://www.google.com/search?q=" + encodeURIComponent(title + " pdf");
      a.title = "PDF non pubblicato: cerca la fonte online";
      for (var n = a.firstChild; n; n = n.nextSibling) {
        if (n.nodeType === 3 && n.textContent.trim()) { n.textContent = "Cerca fonte "; break; }
      }
    });
  }
  new MutationObserver(function () { fix(document); })
    .observe(document.documentElement, { childList: true, subtree: true });
  document.addEventListener("DOMContentLoaded", function () { fix(document); });
})();
</script>
"""


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    for d in COPY_DIRS:
        if (ROOT / d).is_dir():
            shutil.copytree(ROOT / d, OUT / d, ignore=IGNORE)

    (OUT / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    index = json.loads((ROOT / "data/study-index.json").read_text(encoding="utf-8"))
    missing = sorted(
        i["relative_path"]
        for i in index.get("items", [])
        if i.get("extension") == ".pdf" and not (ROOT / i["relative_path"]).is_file()
    )

    dash = OUT / DASHBOARD
    html = dash.read_text(encoding="utf-8")
    if "</body>" not in html:
        sys.exit(f"Errore: </body> non trovato in {DASHBOARD}")
    snippet = PDF_FALLBACK_JS % json.dumps(missing, ensure_ascii=False)
    head, sep, tail = html.rpartition("</body>")
    dash.write_text(head + snippet + sep + tail, encoding="utf-8")

    print(f"Sito generato in {OUT.relative_to(ROOT)}/ ({len(missing)} PDF sostituiti da ricerca online)")


if __name__ == "__main__":
    main()
