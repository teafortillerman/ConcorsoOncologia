"""Validazione e riepilogo dei file algoritmo (Algoritmi/*.algo.json)."""
import json
from pathlib import Path

AIFA_VALUES = {"reimbursed", "not_reimbursed", "unknown", "standard"}
REQUIRED_TOP = ("id", "title", "theme", "scheda", "start", "nodes")
SOURCE_TYPES = {"rimborsabilita", "scheda", "pubmed", "standard"}


def validate_regimen(regimen, where):
    """Controlla lo schema posologico di un'opzione: righe [farmaco, dose] e fonti."""
    if not isinstance(regimen, dict):
        return [f"{where}: 'regimen' deve essere un oggetto"]
    errors = []
    rows = regimen.get("rows")
    if not isinstance(rows, list) or not rows:
        errors.append(f"{where}: 'regimen.rows' deve essere una lista non vuota")
    else:
        for i, row in enumerate(rows, start=1):
            if not (isinstance(row, list) and len(row) == 2 and all(isinstance(c, str) and c for c in row)):
                errors.append(f"{where}: la riga {i} dello schema deve essere [farmaco, dose]")
    for field in ("trial", "endpoint"):
        if field in regimen and not (isinstance(regimen[field], str) and regimen[field]):
            errors.append(f"{where}: 'regimen.{field}' deve essere un testo non vuoto")
    endpoint = regimen.get("endpoint")
    if isinstance(endpoint, str) and endpoint:
        if "trial" not in regimen:
            errors.append(f"{where}: 'regimen.endpoint' richiede 'regimen.trial'")
        if not endpoint.startswith(("PFS", "rPFS", "OS")):
            errors.append(f"{where}: l'endpoint primario si riporta solo se è PFS (anche rPFS) o OS")
    sources = regimen.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append(f"{where}: 'regimen.sources' deve essere una lista non vuota")
    else:
        for i, src in enumerate(sources, start=1):
            kind = src.get("type") if isinstance(src, dict) else None
            if kind not in SOURCE_TYPES:
                errors.append(f"{where}: la fonte {i} ha un tipo non valido: {kind!r}")
            elif kind == "pubmed" and not (src.get("label") and src.get("doi")):
                errors.append(f"{where}: la fonte PubMed {i} deve avere 'label' e 'doi'")
    return errors


def validate_tags(value, known, where, field):
    """'gives' / 'expire' / 'only_if_any': lista di classi dichiarate in 'exposures'."""
    if not (isinstance(value, list) and value and all(isinstance(t, str) for t in value)):
        return [f"{where}: '{field}' deve essere una lista non vuota di classi"]
    return [f"{where}: '{field}' usa la classe {t!r} non dichiarata in 'exposures'" for t in value if t not in known]


def validate_rules(value, known, where, field):
    """'requires' / 'excludes': lista di { tag, reason }."""
    if not (isinstance(value, list) and value):
        return [f"{where}: '{field}' deve essere una lista non vuota"]
    errors = []
    for i, rule in enumerate(value, start=1):
        if not (isinstance(rule, dict) and rule.get("tag") and rule.get("reason")):
            errors.append(f"{where}: la regola {i} di '{field}' deve avere 'tag' e 'reason'")
        elif rule["tag"] not in known:
            errors.append(f"{where}: '{field}' usa la classe {rule['tag']!r} non dichiarata in 'exposures'")
    return errors


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

    exposures = data.get("exposures", {})
    if not isinstance(exposures, dict) or not all(isinstance(v, str) and v for v in exposures.values()):
        errors.append("'exposures' deve essere un oggetto { classe: descrizione }")
        exposures = {}
    known = set(exposures)

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
                for field in ("gives", "expire"):
                    if field in answer:
                        errors.extend(validate_tags(answer[field], known, f"{where}, risposta {i}", field))
                targets.append(answer.get("next"))
            for field in ("only_if_any", "skip_if_any"):
                if field in node:
                    errors.extend(validate_tags(node[field], known, where, field))
                    if "skip_to" not in node:
                        errors.append(f"{where}: '{field}' richiede 'skip_to'")
            if "skip_to" in node:
                targets.append(node.get("skip_to"))
            for i, rule in enumerate(node.get("auto_route", []), start=1):
                if not (isinstance(rule, dict) and rule.get("next")):
                    errors.append(f"{where}: la regola {i} di 'auto_route' deve avere 'if_any' e 'next'")
                    continue
                errors.extend(validate_tags(rule.get("if_any"), known, f"{where}, auto_route {i}", "if_any"))
                targets.append(rule["next"])
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
                if "regimen" in option:
                    errors.extend(validate_regimen(option["regimen"], f"{where}, opzione {i}"))
                if "gives" in option:
                    errors.extend(validate_tags(option["gives"], known, f"{where}, opzione {i}", "gives"))
                for field in ("requires", "excludes"):
                    if field in option:
                        errors.extend(validate_rules(option[field], known, f"{where}, opzione {i}", field))
                if "next" in option:
                    if not node.get("select"):
                        errors.append(f"{where}: l'opzione {i} ha 'next' ma il nodo non ha 'select'")
                    onext = option["next"] or {}
                    if not onext.get("label"):
                        errors.append(f"{where}: il 'next' dell'opzione {i} non ha 'label'")
                    targets.append(onext.get("node"))
                elif node.get("select") and "next" not in node:
                    errors.append(f"{where}: l'opzione {i} non ha seguito (serve 'next' sull'opzione o sul nodo)")
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
