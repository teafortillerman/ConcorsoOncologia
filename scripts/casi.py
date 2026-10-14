"""Validazione e riepilogo dei casi clinici (Casi/*.case.json)."""
import json
from pathlib import Path

GRADES = {"best", "ok", "wrong"}
FLAGS = {"high", "low"}
REQUIRED_TOP = ("id", "title", "theme", "scheda", "patient", "steps")


def validate_step(step, where):
    errors = []
    for field in ("title", "question", "explanation"):
        if not (isinstance(step.get(field), str) and step[field].strip()):
            errors.append(f"{where}: manca '{field}'")
    options = step.get("options")
    if not isinstance(options, list) or len(options) < 2:
        return errors + [f"{where}: servono almeno 2 opzioni"]
    for i, opt in enumerate(options, start=1):
        if not (isinstance(opt, dict) and opt.get("text") and opt.get("why")):
            errors.append(f"{where}: l'opzione {i} deve avere 'text' e 'why'")
        elif opt.get("grade") not in GRADES:
            errors.append(f"{where}: l'opzione {i} ha un giudizio non valido: {opt.get('grade')!r}")
    if not any(isinstance(o, dict) and o.get("grade") == "best" for o in options):
        errors.append(f"{where}: serve almeno un'opzione 'best'")
    for i, row in enumerate(step.get("exams", []), start=1):
        if not (isinstance(row, dict) and row.get("name") and row.get("value")):
            errors.append(f"{where}: l'esame {i} deve avere 'name' e 'value'")
        elif row.get("flag", "") not in FLAGS | {""}:
            errors.append(f"{where}: l'esame {i} ha un flag non valido: {row.get('flag')!r}")
    for i, item in enumerate(step.get("evidence", []), start=1):
        if not (isinstance(item, dict) and item.get("trial") and item.get("finding")):
            errors.append(f"{where}: lo studio {i} deve avere 'trial' e 'finding'")
    if "multi" in step and not isinstance(step["multi"], bool):
        errors.append(f"{where}: 'multi' deve essere vero o falso")
    return errors


def validate_case(data, root, algorithm_ids=()):
    if not isinstance(data, dict):
        return ["il file deve contenere un oggetto JSON"]
    errors = [f"manca il campo '{key}'" for key in REQUIRED_TOP if key not in data]
    if errors:
        return errors
    if not (Path(root) / data["scheda"]).is_file():
        errors.append(f"la scheda '{data['scheda']}' non esiste")
    if data.get("algorithm") and algorithm_ids and data["algorithm"] not in algorithm_ids:
        errors.append(f"l'algoritmo '{data['algorithm']}' non esiste")
    steps = data["steps"]
    if not isinstance(steps, list) or not steps:
        return errors + ["'steps' deve essere una lista non vuota"]
    for i, step in enumerate(steps, start=1):
        errors.extend(validate_step(step, f"tappa {i}"))
    return errors


def case_summary(data, rel_path):
    return {"id": data["id"], "title": data["title"], "theme": data["theme"], "scheda": data["scheda"],
            "algorithm": data.get("algorithm"), "patient": data["patient"], "steps": len(data["steps"]), "path": rel_path}


def load_cases(root, algorithm_ids=()):
    """Legge e valida Casi/*.case.json. Restituisce (riepiloghi, errori)."""
    root = Path(root)
    summaries, errors, seen = [], [], {}
    for path in sorted((root / "Casi").glob("*.case.json")):
        rel = path.relative_to(root).as_posix()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            errors.append(f"{rel}: JSON non valido ({exc})")
            continue
        problems = validate_case(data, root, algorithm_ids)
        if problems:
            errors.extend(f"{rel}: {p}" for p in problems)
            continue
        if data["id"] in seen:
            errors.append(f"{rel}: id '{data['id']}' già usato da {seen[data['id']]}")
            continue
        seen[data["id"]] = rel
        summaries.append(case_summary(data, rel))
    return summaries, errors
