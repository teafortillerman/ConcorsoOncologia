"""Validazione e riepilogo dei file algoritmo (Algoritmi/*.algo.json)."""
import json
from pathlib import Path

AIFA_VALUES = {"reimbursed", "not_reimbursed", "unknown", "standard"}
REQUIRED_TOP = ("id", "title", "theme", "scheda", "start", "nodes")


def validate_algorithm(data, root):
    """Restituisce l'elenco degli errori; lista vuota = algoritmo valido."""
    if not isinstance(data, dict):
        return ["il file deve contenere un oggetto JSON"]
    errors = [f"manca il campo '{key}'" for key in REQUIRED_TOP if key not in data]
    if errors:
        return errors

    nodes = data["nodes"]
    if not isinstance(nodes, dict) or not nodes:
        return ["'nodes' deve essere un oggetto non vuoto"]
    if not (Path(root) / data["scheda"]).is_file():
        errors.append(f"la scheda '{data['scheda']}' non esiste")
    if data["start"] not in nodes:
        errors.append(f"il nodo iniziale '{data['start']}' non esiste")

    edges = {}
    for node_id, node in nodes.items():
        where = f"nodo '{node_id}'"
        kind = node.get("type") if isinstance(node, dict) else None
        targets = []
        if kind == "question":
            if not node.get("text"):
                errors.append(f"{where}: manca 'text'")
            answers = node.get("answers") or []
            if len(answers) < 2:
                errors.append(f"{where}: una domanda deve avere almeno 2 risposte")
            for i, answer in enumerate(answers, start=1):
                if not answer.get("label"):
                    errors.append(f"{where}: la risposta {i} non ha 'label'")
                targets.append(answer.get("next"))
        elif kind == "recommendation":
            if not node.get("title"):
                errors.append(f"{where}: manca 'title'")
            options = node.get("options") or []
            if not options:
                errors.append(f"{where}: una raccomandazione deve avere almeno 1 opzione")
            for i, option in enumerate(options, start=1):
                for field in ("name", "key"):
                    if not option.get(field):
                        errors.append(f"{where}: l'opzione {i} non ha '{field}'")
                if option.get("aifa") not in AIFA_VALUES:
                    errors.append(f"{where}: l'opzione {i} ha uno stato AIFA non valido: {option.get('aifa')!r}")
            if "next" in node:
                nxt = node["next"] or {}
                if not nxt.get("label"):
                    errors.append(f"{where}: 'next' non ha 'label'")
                targets.append(nxt.get("node"))
        else:
            errors.append(f"{where}: tipo non valido {kind!r}")
            continue
        for target in targets:
            if target not in nodes:
                errors.append(f"{where}: punta a un nodo inesistente {target!r}")
        edges[node_id] = [t for t in targets if t in nodes]

    if errors:
        return errors

    # Visita in profondità da start: segna i nodi raggiunti e rileva i cicli.
    status = {}
    cycles = []

    def visit(node_id, path):
        status[node_id] = "aperto"
        for nxt in edges[node_id]:
            if status.get(nxt) == "aperto":
                cycles.append(" → ".join(path + [nxt]))
            elif nxt not in status:
                visit(nxt, path + [nxt])
        status[node_id] = "chiuso"

    visit(data["start"], [data["start"]])
    errors.extend(f"ciclo: {loop}" for loop in cycles)
    errors.extend(
        f"nodo '{node_id}' non raggiungibile da '{data['start']}'"
        for node_id in nodes if node_id not in status
    )
    return errors


def algorithm_summary(data, rel_path):
    start = data["nodes"][data["start"]]
    settings = [a["label"] for a in start["answers"]] if start["type"] == "question" else []
    return {
        "id": data["id"],
        "title": data["title"],
        "theme": data["theme"],
        "scheda": data["scheda"],
        "path": rel_path,
        "settings": settings,
    }


def load_algorithms(root):
    """Legge e valida Algoritmi/*.algo.json. Restituisce (riepiloghi, errori)."""
    root = Path(root)
    summaries, errors = [], []
    seen = {}
    for path in sorted((root / "Algoritmi").glob("*.algo.json")):
        rel = path.relative_to(root).as_posix()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            errors.append(f"{rel}: JSON non valido ({exc})")
            continue
        problems = validate_algorithm(data, root)
        if problems:
            errors.extend(f"{rel}: {p}" for p in problems)
            continue
        if data["id"] in seen:
            errors.append(f"{rel}: id '{data['id']}' già usato da {seen[data['id']]}")
            continue
        seen[data["id"]] = rel
        summaries.append(algorithm_summary(data, rel))
    return summaries, errors
