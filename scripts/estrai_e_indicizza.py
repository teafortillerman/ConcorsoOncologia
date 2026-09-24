#!/usr/bin/env python3
"""
Estrae i PDF da AIOM/, ESMO/ e Congressi/Grandangolo/.

Importante: ROOT viene calcolata in base alla posizione di questo script,
non in base alla cartella corrente del terminale.

Uso:
    /usr/bin/python3 /percorso/OncologiaConcorso/scripts/estrai_e_indicizza_v3.py
"""

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import fitz  # installazione: python3 -m pip install pymupdf

# scripts/estrai_e_indicizza_v3.py -> OncologiaConcorso/scripts -> OncologiaConcorso
ROOT = Path(__file__).resolve().parent.parent

FOLDERS = {
    "AIOM": ROOT / "AIOM",
    "ESMO": ROOT / "ESMO",
    "Grandangolo": ROOT / "Congressi" / "Grandangolo",
}

TESTO_DIR = ROOT / "Testo_Estratto"
DATA_DIR = ROOT / "data"
INDEX_PATH = DATA_DIR / "study-index.json"

FONTE_LABELS = {
    "AIOM": "Linee guida AIOM",
    "ESMO": "Linee guida ESMO (CPG)",
    "Grandangolo": "Congresso Grandangolo",
}

TOPIC_MAP = [
    ("Polmone", ["polmone", "nsclc", "sclc", "carcinoidi polmonari", "timici"]),
    ("Mammella", ["mammella"]),
    ("Colon-Retto", ["colonretto", "colon", "retto"]),
    ("Pancreas", ["pancreas"]),
    ("Vie Biliari ed Epatocarcinoma", ["epatocarcinoma", "vie biliari", "fegato"]),
    ("Esofago e Gastrico", ["esofago", "gastrico"]),
    ("Prostata", ["prostata"]),
    ("Rene", ["rene"]),
    ("Vescica e Urotelio", ["urotelio", "vescica"]),
    ("Testicolo", ["testicolo"]),
    ("Ginecologici - Ovaio", ["ovaio"]),
    ("Ginecologici - Endometrio", ["endometrio"]),
    ("Ginecologici - Cervice", ["cervice"]),
    ("Melanoma e Cute", ["melanoma", "cutanee", "merkel"]),
    ("Sarcomi e GIST", ["sarcomi", "gist"]),
    ("Testa e Collo", ["testa e collo", "testacollo", "nasofaringeo", "tiroide"]),
    ("Tumori Neuroendocrini", ["neuroendocrini", "nen", "carcinoidi"]),
    ("SNC e Tumori Cerebrali", ["cerebrali", "snc", "linfomi primitivi snc"]),
    ("Linfomi", ["linfoma", "linfomi", "hodgkin", "tnk"]),
    ("Tumori Endocrini Rari", ["corticosurrenalico", "feocromocitoma"]),
    ("Primitivo Sconosciuto", ["primitivosconosciuto", "primitivo sconosciuto"]),
    ("Tumori Ereditari", ["ereditari"]),
    ("Altre Neoplasie Toraciche", ["altre toraciche", "altreneotoraciche", "mesotelioma"]),
    ("Metastasi Ossee", ["metastasi ossee", "metastasiossee"]),
    ("Urgenze Oncologiche", ["urgenze", "urgenzeoncologiche"]),
    ("Tossicita e Supporto", ["tossicita", "immunotossicita", "emopoietica"]),
    ("Cachessia e Nutrizione", ["cachessia", "nutrizione"]),
    ("Cardioncologia", ["cardioncologia"]),
    ("Gestione del Dolore", ["dolore"]),
    ("Fertilita", ["fertilita"]),
    ("Antiemetica e Supporto", ["antiemetica"]),
    ("Trials e Novita Congressuali", ["trials"]),
]


def normalizza(testo: str) -> str:
    testo = testo.lower().replace("_", " ").replace("-", " ")
    testo = unicodedata.normalize("NFKD", testo)
    return "".join(c for c in testo if not unicodedata.combining(c))


def estrai_anno(nome: str) -> str:
    match = re.search(r"(?:19|20)\d{2}", nome)
    return match.group(0) if match else "sconosciuto"


def assegna_tema(nome: str) -> str:
    nome_norm = normalizza(nome)
    for tema, parole in TOPIC_MAP:
        if any(normalizza(parola) in nome_norm for parola in parole):
            return tema
    return "Da Classificare"


def trova_pdf(cartella: Path):
    if not cartella.exists():
        return []
    return sorted(
        file_path for file_path in cartella.rglob("*")
        if file_path.is_file() and file_path.suffix.lower() == ".pdf"
    )


def estrai_testo(pdf_path: Path) -> str:
    pagine = []
    with fitz.open(pdf_path) as doc:
        for numero, pagina in enumerate(doc, start=1):
            testo = pagina.get_text("text").strip()
            if testo:
                pagine.append(f"\n--- PAGINA {numero} ---\n{testo}")
    return "\n".join(pagine).strip()


def main():
    print(f"ROOT rilevata: {ROOT}")
    print(f"Output testo: {TESTO_DIR}")
    print(f"Output indice: {INDEX_PATH}")

    TESTO_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    indice = {}
    errori = []
    totale = 0

    for fonte, cartella in FOLDERS.items():
        files = trova_pdf(cartella)
        print(f"\n--- {fonte}: {len(files)} PDF trovati in {cartella} ---")

        for pdf_path in files:
            totale += 1
            tema = assegna_tema(pdf_path.stem)
            tema_dir = TESTO_DIR / tema
            tema_dir.mkdir(parents=True, exist_ok=True)
            txt_path = tema_dir / f"{pdf_path.stem}.txt"

            try:
                testo = estrai_testo(pdf_path)
                if not testo:
                    raise ValueError("nessun testo estraibile; possibile PDF scansionato")
                txt_path.write_text(testo + "\n", encoding="utf-8")
            except Exception as exc:
                errori.append({
                    "file": str(pdf_path.relative_to(ROOT)),
                    "errore": str(exc),
                })
                print(f"  ERRORE [{tema}] {pdf_path.name}: {exc}")
                continue

            voce = {
                "fonte": fonte,
                "fonte_label": FONTE_LABELS[fonte],
                "anno": estrai_anno(pdf_path.name),
                "tema": tema,
                "nome_originale": pdf_path.name,
                "percorso_pdf": str(pdf_path.relative_to(ROOT)),
                "percorso_testo": str(txt_path.relative_to(ROOT)),
                "num_caratteri": len(testo),
            }
            indice.setdefault(tema, []).append(voce)
            print(f"  OK [{tema}] {pdf_path.relative_to(ROOT)}")

    for voci in indice.values():
        voci.sort(key=lambda voce: (voce["anno"], voce["fonte"], voce["nome_originale"]), reverse=True)

    output = {
        "generato_il": datetime.now().isoformat(timespec="seconds"),
        "root": str(ROOT),
        "totale_documenti_trovati": totale,
        "totale_documenti_elaborati": totale - len(errori),
        "totale_errori": len(errori),
        "errori": errori,
        "fonti": {
            fonte: str(cartella.relative_to(ROOT))
            for fonte, cartella in FOLDERS.items()
        },
        "temi": indice,
    }
    INDEX_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== COMPLETATO ===")
    print(f"PDF trovati: {totale}")
    print(f"PDF elaborati: {totale - len(errori)}")
    print(f"Errori: {len(errori)}")
    print(f"Temi: {len(indice)}")
    print(f"Indice: {INDEX_PATH}")


if __name__ == "__main__":
    main()
