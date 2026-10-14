import copy
import json
import tempfile
import unittest
from pathlib import Path

from algoritmi import load_algorithms
from casi import load_cases, validate_case

ROOT = Path(__file__).resolve().parent.parent


def make_case():
    return {
        "id": "prova", "title": "Prova", "theme": "Mammella", "scheda": "Schede/Mammella/Prova.md",
        "patient": "Paziente di prova.",
        "steps": [{"title": "1ª linea", "question": "Cosa fai?", "explanation": "Perché.",
                   "options": [{"text": "A", "grade": "best", "why": "giusta"}, {"text": "B", "grade": "wrong", "why": "sbagliata"}]}],
    }


class ValidateCaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "Schede" / "Mammella").mkdir(parents=True)
        (self.root / "Schede" / "Mammella" / "Prova.md").write_text("# Prova\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_case(self):
        self.assertEqual(validate_case(make_case(), self.root), [])

    def test_step_needs_a_best_option(self):
        case = make_case(); case["steps"][0]["options"][0]["grade"] = "ok"
        self.assertTrue(any("'best'" in e for e in validate_case(case, self.root)))

    def test_invalid_grade_and_flag(self):
        case = make_case()
        case["steps"][0]["options"][1]["grade"] = "boh"
        case["steps"][0]["exams"] = [{"name": "Creatinina", "value": "2", "flag": "alto"}]
        errors = validate_case(case, self.root)
        self.assertTrue(any("giudizio non valido" in e for e in errors))
        self.assertTrue(any("flag non valido" in e for e in errors))

    def test_unknown_algorithm(self):
        case = make_case(); case["algorithm"] = "inesistente"
        self.assertTrue(any("non esiste" in e for e in validate_case(case, self.root, {"mammella"})))


class RepoCasesTest(unittest.TestCase):
    def test_repo_cases_are_valid_and_indexed(self):
        algorithms, _ = load_algorithms(ROOT)
        cases, errors = load_cases(ROOT, {a["id"] for a in algorithms})
        self.assertEqual(errors, [])
        self.assertGreaterEqual(len(cases), 4)
        index = json.loads((ROOT / "data" / "study-index.json").read_text(encoding="utf-8"))
        self.assertEqual(index.get("cases"), cases)

    def test_every_step_explains_every_option(self):
        for path in (ROOT / "Casi").glob("*.case.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            for i, step in enumerate(data["steps"], start=1):
                for opt in step["options"]:
                    with self.subTest(case=data["id"], step=i, option=opt["text"]):
                        self.assertGreater(len(opt["why"]), 20)


if __name__ == "__main__":
    unittest.main()
