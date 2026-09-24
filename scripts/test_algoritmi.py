import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from algoritmi import algorithm_summary, load_algorithms, validate_algorithm


def make_algo():
    return {
        "id": "prova",
        "title": "Prova",
        "theme": "Mammella",
        "scheda": "Schede/Mammella/Prova.md",
        "start": "q1",
        "nodes": {
            "q1": {"type": "question", "text": "Setting?", "short": "Setting",
                   "answers": [{"label": "A", "next": "r1"}, {"label": "B", "next": "r2"}]},
            "r1": {"type": "recommendation", "title": "1ª linea",
                   "options": [{"name": "Farmaco X", "aifa": "reimbursed", "key": "Trial X"}],
                   "next": {"label": "Alla progressione → 2ª linea", "node": "r2"}},
            "r2": {"type": "recommendation", "title": "2ª linea",
                   "options": [{"name": "Farmaco Y", "aifa": "standard", "key": "Trial Y"}]},
        },
    }


class ValidateAlgorithmTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "Schede" / "Mammella").mkdir(parents=True)
        (self.root / "Schede" / "Mammella" / "Prova.md").write_text("# Prova\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_algorithm_has_no_errors(self):
        self.assertEqual(validate_algorithm(make_algo(), self.root), [])

    def test_non_object_is_rejected(self):
        self.assertEqual(validate_algorithm(["id"], self.root), ["il file deve contenere un oggetto JSON"])

    def test_missing_top_level_field(self):
        algo = make_algo()
        del algo["start"]
        self.assertIn("manca il campo 'start'", validate_algorithm(algo, self.root))

    def test_missing_scheda_file(self):
        algo = make_algo()
        algo["scheda"] = "Schede/Mammella/Inesistente.md"
        self.assertIn("la scheda 'Schede/Mammella/Inesistente.md' non esiste", validate_algorithm(algo, self.root))

    def test_start_node_must_exist(self):
        algo = make_algo()
        algo["start"] = "nessuno"
        errors = validate_algorithm(algo, self.root)
        self.assertIn("il nodo iniziale 'nessuno' non esiste", errors)

    def test_answer_pointing_to_missing_node(self):
        algo = make_algo()
        algo["nodes"]["q1"]["answers"][1]["next"] = "fantasma"
        errors = validate_algorithm(algo, self.root)
        self.assertIn("nodo 'q1': punta a un nodo inesistente 'fantasma'", errors)

    def test_question_needs_two_answers(self):
        algo = make_algo()
        algo["nodes"]["q1"]["answers"] = [{"label": "A", "next": "r1"}]
        errors = validate_algorithm(algo, self.root)
        self.assertIn("nodo 'q1': una domanda deve avere almeno 2 risposte", errors)

    def test_invalid_aifa_value(self):
        algo = make_algo()
        algo["nodes"]["r2"]["options"][0]["aifa"] = "si"
        errors = validate_algorithm(algo, self.root)
        self.assertIn("nodo 'r2': l'opzione 1 ha uno stato AIFA non valido: 'si'", errors)

    def test_option_needs_name_and_key(self):
        algo = make_algo()
        del algo["nodes"]["r2"]["options"][0]["key"]
        errors = validate_algorithm(algo, self.root)
        self.assertIn("nodo 'r2': l'opzione 1 non ha 'key'", errors)

    def test_valid_regimen_is_accepted(self):
        algo = make_algo()
        algo["nodes"]["r1"]["options"][0]["regimen"] = {
            "trial": "Trial X", "endpoint": "PFS 10,0 vs 5,0 mesi, HR 0,50",
            "rows": [["Farmaco X", "10 mg/die per os"]], "note": "Fino a progressione.",
            "sources": [{"type": "rimborsabilita"}, {"type": "pubmed", "label": "Trial X", "doi": "10.1/x"}]}
        self.assertEqual(validate_algorithm(algo, self.root), [])

    def test_regimen_rows_must_be_pairs(self):
        algo = make_algo()
        algo["nodes"]["r1"]["options"][0]["regimen"] = {"rows": [["solo farmaco"]], "sources": [{"type": "standard"}]}
        errors = validate_algorithm(algo, self.root)
        self.assertTrue(any("[farmaco, dose]" in e for e in errors), errors)

    def test_regimen_pubmed_source_needs_doi(self):
        algo = make_algo()
        algo["nodes"]["r1"]["options"][0]["regimen"] = {
            "rows": [["X", "1 mg"]], "sources": [{"type": "pubmed", "label": "Trial X"}]}
        errors = validate_algorithm(algo, self.root)
        self.assertTrue(any("'label' e 'doi'" in e for e in errors), errors)

    def test_regimen_endpoint_must_be_pfs_or_os(self):
        algo = make_algo()
        algo["nodes"]["r1"]["options"][0]["regimen"] = {
            "trial": "Trial X", "endpoint": "pCR 64,8% vs 51,2%",
            "rows": [["X", "1 mg"]], "sources": [{"type": "standard"}]}
        errors = validate_algorithm(algo, self.root)
        self.assertTrue(any("PFS o OS" in e for e in errors), errors)

    def test_regimen_endpoint_needs_trial(self):
        algo = make_algo()
        algo["nodes"]["r1"]["options"][0]["regimen"] = {
            "endpoint": "PFS 10 vs 5 mesi", "rows": [["X", "1 mg"]], "sources": [{"type": "standard"}]}
        errors = validate_algorithm(algo, self.root)
        self.assertTrue(any("richiede 'regimen.trial'" in e for e in errors), errors)

    def test_regimen_source_type_is_checked(self):
        algo = make_algo()
        algo["nodes"]["r1"]["options"][0]["regimen"] = {"rows": [["X", "1 mg"]], "sources": [{"type": "web"}]}
        errors = validate_algorithm(algo, self.root)
        self.assertTrue(any("tipo non valido" in e for e in errors), errors)

    def test_invalid_node_type(self):
        algo = make_algo()
        algo["nodes"]["r2"]["type"] = "milestone"
        errors = validate_algorithm(algo, self.root)
        self.assertIn("nodo 'r2': tipo non valido 'milestone'", errors)

    def test_unreachable_node(self):
        algo = make_algo()
        algo["nodes"]["orfano"] = copy.deepcopy(algo["nodes"]["r2"])
        errors = validate_algorithm(algo, self.root)
        self.assertIn("nodo 'orfano' non raggiungibile da 'q1'", errors)

    def test_cycle_is_rejected(self):
        algo = make_algo()
        algo["nodes"]["r2"]["next"] = {"label": "Di nuovo", "node": "q1"}
        errors = validate_algorithm(algo, self.root)
        self.assertTrue(any(e.startswith("ciclo:") for e in errors), errors)


class SummaryAndLoadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "Schede" / "Mammella").mkdir(parents=True)
        (self.root / "Schede" / "Mammella" / "Prova.md").write_text("# Prova\n", encoding="utf-8")
        (self.root / "Algoritmi").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, content):
        (self.root / "Algoritmi" / name).write_text(content, encoding="utf-8")

    def test_summary_lists_start_answers_as_settings(self):
        summary = algorithm_summary(make_algo(), "Algoritmi/prova.algo.json")
        self.assertEqual(summary, {
            "id": "prova", "title": "Prova", "theme": "Mammella",
            "scheda": "Schede/Mammella/Prova.md", "path": "Algoritmi/prova.algo.json",
            "settings": ["A", "B"],
        })

    def test_load_valid_file(self):
        self.write("prova.algo.json", json.dumps(make_algo()))
        summaries, errors = load_algorithms(self.root)
        self.assertEqual(errors, [])
        self.assertEqual([s["id"] for s in summaries], ["prova"])

    def test_load_ignores_other_files(self):
        self.write("vecchio.html", "<html></html>")
        self.assertEqual(load_algorithms(self.root), ([], []))

    def test_load_reports_invalid_json_with_file_name(self):
        self.write("rotto.algo.json", "{ non json")
        summaries, errors = load_algorithms(self.root)
        self.assertEqual(summaries, [])
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("Algoritmi/rotto.algo.json: JSON non valido"), errors)

    def test_load_prefixes_validation_errors_with_file_name(self):
        algo = make_algo()
        algo["start"] = "nessuno"
        self.write("prova.algo.json", json.dumps(algo))
        _, errors = load_algorithms(self.root)
        self.assertIn("Algoritmi/prova.algo.json: il nodo iniziale 'nessuno' non esiste", errors)

    def test_load_rejects_duplicate_ids(self):
        self.write("a.algo.json", json.dumps(make_algo()))
        self.write("b.algo.json", json.dumps(make_algo()))
        summaries, errors = load_algorithms(self.root)
        self.assertEqual(len(summaries), 1)
        self.assertIn("Algoritmi/b.algo.json: id 'prova' già usato da Algoritmi/a.algo.json", errors)


ROOT = Path(__file__).resolve().parent.parent
MAMMELLA = ROOT / "Algoritmi" / "mammella.algo.json"


class MammellaAlgorithmTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(MAMMELLA.read_text(encoding="utf-8"))

    def test_is_valid(self):
        self.assertEqual(validate_algorithm(self.data, ROOT), [])

    def test_four_settings(self):
        start = self.data["nodes"][self.data["start"]]
        self.assertEqual(
            [a["label"] for a in start["answers"]],
            ["Precoce operabile", "Localmente avanzato (neoadiuvante)", "Metastatico", "Recidiva locoregionale"],
        )

    def aifa_of(self, fragment):
        found = {
            option["aifa"]
            for node in self.data["nodes"].values() if node["type"] == "recommendation"
            for option in node["options"] if fragment.lower() in option["name"].lower()
        }
        self.assertTrue(found, f"nessuna opzione contiene {fragment!r}")
        return found

    def test_key_aifa_statuses_match_the_scheda(self):
        self.assertEqual(self.aifa_of("Imlunestrant"), {"not_reimbursed"})
        self.assertEqual(self.aifa_of("Datopotamab"), {"not_reimbursed"})
        self.assertEqual(self.aifa_of("Neratinib"), {"not_reimbursed"})
        self.assertEqual(self.aifa_of("Atezolizumab"), {"reimbursed"})
        self.assertEqual(self.aifa_of("Alpelisib"), {"reimbursed"})
        self.assertEqual(self.aifa_of("Tucatinib"), {"reimbursed"})
        self.assertEqual(self.aifa_of("Ribociclib 3 anni"), {"reimbursed"})
        self.assertEqual(self.aifa_of("Sacituzumab"), {"reimbursed"})


    def test_keynote355_status_is_unknown(self):
        option = next(o for o in self.data["nodes"]["m1_tn_pdl1"]["options"] if o["name"] == "Pembrolizumab + chemioterapia")
        self.assertEqual(option["aifa"], "unknown")

    def test_genomic_test_exceptions_are_shown(self):
        info = self.data["nodes"]["precoce_hr_test"].get("info", "")
        for fragment in ("TAILORx", "RS 16-25", "RxPONDER", "pre-menopausa"):
            self.assertIn(fragment, info)

    def test_genomic_test_reimbursement_matches_scheda(self):
        info = self.data["nodes"]["precoce_hr_rischio"]["info"]
        self.assertIn("DM 18/05/2021", info)
        self.assertNotIn("regione", info)

    def test_endocrine_extension_matches_scheda(self):
        detail = self.data["nodes"]["precoce_hr_basso"]["options"][0]["detail"]
        self.assertNotIn("solo con rischio residuo", detail)
        self.assertIn("fino a 10 anni solo con alto rischio residuo", detail)

if __name__ == "__main__":
    unittest.main()


class MammellaRegimenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(MAMMELLA.read_text(encoding="utf-8"))
        text = (ROOT / "Schede" / "Trasversali" / "Rimborsabilita.md").read_text(encoding="utf-8")
        cls.rimborsabilita = text.split("\n## Mammella", 1)[1].split("\n## ", 1)[0]

    def options(self):
        for node_id, node in self.data["nodes"].items():
            if node["type"] == "recommendation":
                for option in node["options"]:
                    yield node_id, option

    def test_every_drug_option_has_a_regimen(self):
        # solo i trattamenti locali della recidiva non hanno uno schema farmacologico
        missing = [(n, o["name"]) for n, o in self.options() if "regimen" not in o and not n.startswith("rec_")]
        self.assertEqual(missing, [])

    def test_rimborsabilita_doses_match_the_scheda(self):
        for node_id, option in self.options():
            regimen = option.get("regimen")
            if not regimen or {s["type"] for s in regimen["sources"]} != {"rimborsabilita"}:
                continue
            for drug, dose in regimen["rows"]:
                for amount in re.findall(r"\d+(?:,\d+)? mg(?:/kg)?", dose):
                    self.assertIn(amount, self.rimborsabilita, f"{node_id} / {drug}: {amount}")

    def test_new_targeted_drugs_name_their_registration_trial(self):
        expected = {"Elacestrant": "EMERALD", "Capivasertib + fulvestrant": "CAPItello-291",
                    "Tucatinib + trastuzumab + capecitabina": "HER2CLIMB", "Datopotamab deruxtecan": "TROPION-Breast01"}
        found = {o["name"]: o["regimen"].get("trial") for _, o in self.options() if o["name"] in expected}
        self.assertEqual(found, expected)


NSCLC = ROOT / "Algoritmi" / "polmone_nsclc.algo.json"


class NsclcAlgorithmTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(NSCLC.read_text(encoding="utf-8"))
        text = (ROOT / "Schede" / "Trasversali" / "Rimborsabilita.md").read_text(encoding="utf-8")
        cls.rimborsabilita = text.split("\n## NSCLC", 1)[1].split("\n## ", 1)[0]

    def options(self):
        for node_id, node in self.data["nodes"].items():
            if node["type"] == "recommendation":
                for option in node["options"]:
                    yield node_id, option

    def test_is_valid(self):
        self.assertEqual(validate_algorithm(self.data, ROOT), [])

    def test_three_settings(self):
        start = self.data["nodes"][self.data["start"]]
        self.assertEqual([a["label"] for a in start["answers"]],
                         ["Precoce resecabile (stadio I-III)", "Stadio III non resecabile", "Avanzato / metastatico"])

    def test_driver_groups(self):
        labels = [a["label"] for a in self.data["nodes"]["m1_driver"]["answers"]]
        self.assertEqual(len(labels), 6)
        self.assertIn("Nessun driver (non oncogene-addicted)", labels)

    def test_aifa_statuses_match_the_scheda(self):
        status = {o["name"]: o["aifa"] for _, o in self.options()}
        self.assertEqual(status["Repotrectinib"], "not_reimbursed")
        self.assertEqual(status["Trastuzumab deruxtecan"], "not_reimbursed")
        self.assertEqual(status["Tislelizumab perioperatorio"], "not_reimbursed")
        self.assertEqual(status["Nivolumab perioperatorio"], "unknown")
        self.assertEqual(status["Pembrolizumab perioperatorio"], "reimbursed")
        self.assertEqual(status["Amivantamab + lazertinib"], "reimbursed")

    def test_rimborsabilita_doses_match_the_scheda(self):
        for node_id, option in self.options():
            regimen = option.get("regimen")
            if not regimen or {s["type"] for s in regimen["sources"]} != {"rimborsabilita"}:
                continue
            for drug, dose in regimen["rows"]:
                for amount in re.findall(r"\d+(?:,\d+)? mg(?:/kg|/m²)?", dose):
                    self.assertIn(amount, self.rimborsabilita, f"{node_id} / {drug}: {amount}")

    def test_egfr_alk_never_reach_perioperative_immunotherapy(self):
        # dai rami EGFR/ALK del precoce non si deve arrivare alla CT-ICI perioperatoria
        from collections import deque
        for start in ("precoce_egfr", "precoce_alk"):
            seen, queue = {start}, deque([start])
            while queue:
                node = self.data["nodes"][queue.popleft()]
                nxt = [a["next"] for a in node.get("answers", [])] + ([node["next"]["node"]] if "next" in node else [])
                for n in nxt:
                    if n not in seen:
                        seen.add(n); queue.append(n)
            self.assertNotIn("precoce_perio", seen)


def rimborsabilita_section(title):
    text = (ROOT / "Schede" / "Trasversali" / "Rimborsabilita.md").read_text(encoding="utf-8")
    return text.split(f"\n## {title}", 1)[1].split("\n## ", 1)[0]


class OrganAlgorithmsTest(unittest.TestCase):
    CASES = {"polmone_sclc.algo.json": "SCLC (Polmone)", "mesotelioma.algo.json": "Mesotelioma",
             "esofago.algo.json": "Esofago", "stomaco.algo.json": "Stomaco", "colonretto.algo.json": "Colon-Retto",
             "ano.algo.json": "Ano", "pancreas.algo.json": "Pancreas", "viebiliari.algo.json": "Vie Biliari",
             "epatocarcinoma.algo.json": "Epatocarcinoma (HCC)", "gist.algo.json": "GIST", "net.algo.json": "NET (Tumori Neuroendocrini)"}

    def load(self, name):
        return json.loads((ROOT / "Algoritmi" / name).read_text(encoding="utf-8"))

    def statuses(self, data):
        return {o["name"]: o["aifa"] for n in data["nodes"].values() if n["type"] == "recommendation" for o in n["options"]}

    def test_are_valid(self):
        for name in self.CASES:
            with self.subTest(name=name):
                self.assertEqual(validate_algorithm(self.load(name), ROOT), [])

    def test_rimborsabilita_doses_match_the_scheda(self):
        missing = []
        for name, section in self.CASES.items():
            text = rimborsabilita_section(section).replace("/m²", "/m").replace("m2", "m")
            for node_id, node in self.load(name)["nodes"].items():
                for option in node.get("options", []):
                    regimen = option.get("regimen")
                    if not regimen or {s["type"] for s in regimen["sources"]} != {"rimborsabilita"}:
                        continue
                    for drug, dose in regimen["rows"]:
                        for amount in re.findall(r"\d+(?:,\d+)? mg(?:/kg|/m²)?", dose):
                            if amount.replace("/m²", "/m") not in text:
                                missing.append(f"{name} {node_id} / {drug}: {amount}")
        self.assertEqual(missing, [])

    def test_sclc_statuses_match_the_scheda(self):
        status = self.statuses(self.load("polmone_sclc.algo.json"))
        self.assertEqual(status["Tarlatamab"], "not_reimbursed")
        self.assertEqual(status["Lurbinectedin + atezolizumab"], "not_reimbursed")
        self.assertEqual(status["Durvalumab fino a 24 mesi"], "reimbursed")
        self.assertEqual(status["Atezolizumab + carboplatino-etoposide"], "reimbursed")

    def test_mesotelioma_statuses_match_the_scheda(self):
        data = self.load("mesotelioma.algo.json")
        nonepi = {o["name"]: o["aifa"] for o in data["nodes"]["adv_nonepi"]["options"]}
        epi = {o["name"]: o["aifa"] for o in data["nodes"]["adv_epi"]["options"]}
        self.assertEqual(nonepi["Nivolumab + ipilimumab"], "reimbursed")
        self.assertEqual(epi["Nivolumab + ipilimumab"], "not_reimbursed")
        self.assertEqual(nonepi["Pembrolizumab + platino-pemetrexed"], "unknown")

    def test_mesotelioma_nivolumab_monotherapy_never_after_immunotherapy(self):
        names = [o["name"] for o in self.load("mesotelioma.algo.json")["nodes"]["adv_2l_post_io"]["options"]]
        self.assertNotIn("Nivolumab in monoterapia", names)



class GastrointestinaliStatusTest(unittest.TestCase):
    def status(self, name, node, option):
        data = json.loads((ROOT / "Algoritmi" / name).read_text(encoding="utf-8"))
        return {o["name"]: o["aifa"] for o in data["nodes"][node]["options"]}[option]

    def test_trap_statuses_match_the_schede(self):
        cases = [
            ("esofago.algo.json", "loc_adj", "Nivolumab adiuvante 1 anno se malattia residua", "not_reimbursed"),
            ("esofago.algo.json", "adv_scc", "Nivolumab + ipilimumab", "not_reimbursed"),
            ("stomaco.algo.json", "adv_cldn", "Zolbetuximab + CAPOX", "not_reimbursed"),
            ("stomaco.algo.json", "loc_perio", "Durvalumab + FLOT perioperatorio", "not_reimbursed"),
            ("stomaco.algo.json", "st_2l_pos", "Trastuzumab deruxtecan", "reimbursed"),
            ("colonretto.algo.json", "m_later", "Sotorasib + panitumumab (KRAS G12C)", "not_reimbursed"),
            ("colonretto.algo.json", "m_msi", "Nivolumab + ipilimumab", "reimbursed"),
            ("pancreas.algo.json", "m1_fit", "NALIRIFOX", "not_reimbursed"),
            ("pancreas.algo.json", "m1_brca_mant", "Olaparib", "reimbursed"),
            ("viebiliari.algo.json", "adv_her2", "Zanidatamab", "not_reimbursed"),
            ("epatocarcinoma.algo.json", "hcc_1l_atezobev", "Nivolumab + ipilimumab", "not_reimbursed"),
            ("epatocarcinoma.algo.json", "hcc_2l", "Ramucirumab se AFP ≥400 ng/mL", "not_reimbursed"),
            ("gist.algo.json", "m1_ntrk", "Entrectinib", "not_reimbursed"),
            ("ano.algo.json", "adv_1l", "Retifanlimab + carboplatino-paclitaxel", "not_reimbursed"),
            ("net.algo.json", "adv_2l_pan", "Cabozantinib", "reimbursed"),
        ]
        for name, node, option, expected in cases:
            with self.subTest(algo=name, option=option):
                self.assertEqual(self.status(name, node, option), expected)

    def test_gist_d842v_never_gets_adjuvant_imatinib(self):
        data = json.loads((ROOT / "Algoritmi" / "gist.algo.json").read_text(encoding="utf-8"))
        names = [o["name"] for o in data["nodes"]["adj_nessuna_mut"]["options"]]
        self.assertEqual(names, ["Nessuna terapia adiuvante"])
