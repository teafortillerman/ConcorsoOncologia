#!/usr/bin/env python3
import json
import re
from pathlib import Path
from datetime import datetime

ROOT = Path("/Users/lorenzodemarchi/Library/CloudStorage/OneDrive-UniversitàdegliStudidiUdine/OncologiaConcorso")
OUT = ROOT / "data" / "study-index.json"
SCHEDE_ROOT = ROOT / "Schede"

CATEGORIES = [
    ("Schede", SCHEDE_ROOT, [".md"]),
    ("AIOM", ROOT / "AIOM", [".pdf"]),
    ("ESMO CPG", ROOT / "ESMO" / "CPG_PDF", [".pdf"]),
    ("Congressi", ROOT / "Congressi", [".pdf", ".ppt", ".pptx"]),
]

# Le Schede sono organizzate in sottocartelle per tema (Schede/<Tema>/*.md):
# il nome della cartella è la fonte di verità, non serve keyword-matching sul titolo.
THEME_ORDER = [
    "Torace", "Mammella", "Gastrointestinali", "Urologici", "Ginecologici",
    "Cute", "Testa-Collo", "Neuro-oncologia", "Sarcomi", "Ematologia",
    "Trasversali", "Altro",
]

# Usato SOLO per classificare i PDF originali (AIOM/ESMO/Congressi), che restano
# in cartelle piatte. Match a parola intera (word-boundary) per evitare falsi
# positivi tipo "ano" dentro "melanoma". Le chiavi più lunghe/specifiche vengono
# verificate per prime.
THEME_RULES = {
    "mammella": "Mammella",
    "polmone": "Torace", "nsclc": "Torace", "sclc": "Torace", "mesotelioma": "Torace",
    "carcinoidi": "Torace", "toraciche": "Torace",
    "colon retto": "Gastrointestinali", "colonretto": "Gastrointestinali",
    "colon": "Gastrointestinali", "retto": "Gastrointestinali",
    "pancreas": "Gastrointestinali", "esofago": "Gastrointestinali", "stomaco": "Gastrointestinali",
    "gastrico": "Gastrointestinali", "gist": "Gastrointestinali",
    "neuroendocrini": "Gastrointestinali", "nen": "Gastrointestinali",
    "epatocarcinoma": "Gastrointestinali", "vie biliari": "Gastrointestinali",
    "biliari": "Gastrointestinali", "tumorieredit": "Gastrointestinali",
    "melanoma": "Cute", "merkel": "Cute", "cutanee": "Cute",
    "testa e collo": "Testa-Collo", "testa collo": "Testa-Collo", "testacollo": "Testa-Collo",
    "nasofaringeo": "Testa-Collo", "tiroide": "Testa-Collo",
    "rene": "Urologici", "prostata": "Urologici", "urotelio": "Urologici", "testicolo": "Urologici",
    "urologiche": "Urologici",
    "ovaio": "Ginecologici", "endometrio": "Ginecologici", "cervice": "Ginecologici",
    "ginecologiche": "Ginecologici",
    "gliomi": "Neuro-oncologia", "cerebrali": "Neuro-oncologia",
    "linfomi primitivisnc": "Neuro-oncologia",
    "sarcomi": "Sarcomi",
    "linfoma": "Ematologia", "linfomi": "Ematologia", "hodgkin": "Ematologia",
    "biomarcatori": "Trasversali", "supportive": "Trasversali", "terapie target": "Trasversali",
    "tossicita": "Trasversali", "immunotossicita": "Trasversali", "urgenze": "Trasversali",
    "principi generali": "Trasversali", "cardioncologia": "Trasversali", "dolore": "Trasversali",
    "nutrizione": "Trasversali", "antiemetica": "Trasversali", "cachessia": "Trasversali",
    "fertilita": "Trasversali", "metastasi ossee": "Trasversali", "ossea": "Trasversali",
    "tumori ereditari": "Trasversali",
    "trials": "Trasversali",
    "primitivo sconosciuto": "Altro", "primitivosconosciuto": "Altro",
    "corticosurrenalico": "Altro", "fecromocitoma": "Altro", "feocromocitoma": "Altro",
}
# Ordina per lunghezza chiave decrescente: le chiavi più specifiche/lunghe vengono
# controllate per prime, così "vie biliari" batte "biliari", ecc.
_THEME_RULES_SORTED = sorted(THEME_RULES.items(), key=lambda kv: -len(kv[0]))

def pretty_title(path: Path) -> str:
    stem = path.stem.replace("_", " ").replace("-", " ")
    # Separa il CamelCase (es. "MelanomaMetastatico" -> "Melanoma Metastatico"),
    # utile sia per la leggibilità del titolo sia per il matching a parola intera.
    stem = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", stem)
    return " ".join(stem.split())

def infer_theme(title: str) -> str:
    t = title.lower()
    for key, value in _THEME_RULES_SORTED:
        pattern = r"\b" + re.escape(key) + r"\b"
        if re.search(pattern, t):
            return value
    return "Altro"

def theme_from_folder(file: Path) -> str:
    """Per le Schede: il tema è il nome della sottocartella diretta sotto Schede/."""
    try:
        rel = file.relative_to(SCHEDE_ROOT)
    except ValueError:
        return "Altro"
    parts = rel.parts
    if len(parts) >= 2:
        return parts[0]
    return "Altro"

COMPLETION_WORD_THRESHOLD = 400  # sopra questa soglia una scheda è considerata "completa"
WPM = 200  # velocità di lettura media per stima tempo di lettura

def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")

def markdown_preview(text: str, max_lines: int = 8) -> str:
    lines = []
    for line in text.splitlines():
        clean = line.strip().lstrip("#-").strip()
        if not clean or clean.endswith(":"):
            continue
        lines.append(clean)
        if len(lines) >= max_lines:
            break
    return " · ".join(lines[:5])

def collect_files(label: str, folder: Path, suffixes: list[str]) -> list[dict]:
    items = []
    if not folder.exists():
        return items

    for file in sorted(folder.rglob("*")):
        if not file.is_file() or file.suffix.lower() not in suffixes:
            continue

        stat = file.stat()
        title = pretty_title(file)
        is_md = file.suffix.lower() == ".md"

        preview = ""
        word_count = None
        reading_time_min = None
        status = None

        if is_md:
            text = read_text(file)
            preview = markdown_preview(text)
            word_count = len(text.split())
            reading_time_min = max(1, round(word_count / WPM))
            status = "completa" if word_count >= COMPLETION_WORD_THRESHOLD else "da_completare"

        theme = theme_from_folder(file) if label == "Schede" else infer_theme(title)

        items.append({
            "category": label,
            "theme": theme,
            "title": title,
            "name": file.name,
            "relative_path": str(file.relative_to(ROOT)),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            "size_bytes": stat.st_size,
            "extension": file.suffix.lower(),
            "preview": preview,
            "word_count": word_count,
            "reading_time_min": reading_time_min,
            "status": status,
        })
    return items

all_items = []
for label, folder, suffixes in CATEGORIES:
    all_items.extend(collect_files(label, folder, suffixes))

payload = {
    "generated_at": datetime.now().isoformat(timespec="seconds"),
    "root": str(ROOT),
    "theme_order": THEME_ORDER,
    "counts": {},
    "themes": {},
    "progress": {"completa": 0, "da_completare": 0, "totale_schede": 0},
    "items": all_items,
}

for item in all_items:
    payload["counts"][item["category"]] = payload["counts"].get(item["category"], 0) + 1
    payload["themes"][item["theme"]] = payload["themes"].get(item["theme"], 0) + 1
    if item["category"] == "Schede":
        payload["progress"]["totale_schede"] += 1
        if item["status"] == "completa":
            payload["progress"]["completa"] += 1
        else:
            payload["progress"]["da_completare"] += 1

OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Creato indice con {len(all_items)} risorse in {OUT}")