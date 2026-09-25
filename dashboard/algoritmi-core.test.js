const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const core = require("./algoritmi-core.js");

const ALGO = {
  id: "prova",
  start: "q1",
  nodes: {
    q1: { type: "question", text: "Setting?", short: "Setting",
          answers: [{ label: "A", next: "r1" }, { label: "B", next: "q2" }] },
    q2: { type: "question", text: "Sottotipo?",
          answers: [{ label: "X", next: "r2" }, { label: "Y", next: "r2" }] },
    r1: { type: "recommendation", title: "1ª linea",
          options: [{ name: "F1", aifa: "reimbursed", key: "k" }],
          next: { label: "Alla progressione → 2ª linea", node: "r2" } },
    r2: { type: "recommendation", title: "2ª linea",
          options: [{ name: "F2", aifa: "standard", key: "k" }] },
  },
};

test("senza risposte il nodo corrente è start", () => {
  assert.equal(core.currentNodeId(ALGO, []), "q1");
});

test("choose porta alla destinazione della risposta e crea la pillola", () => {
  const h = core.choose(ALGO, [], 1);
  assert.deepEqual(h, [{ nodeId: "q1", choice: 1 }]);
  assert.equal(core.currentNodeId(ALGO, h), "q2");
  assert.deepEqual(core.pills(ALGO, h), [{ index: 0, label: "Setting: B" }]);
});

test("senza short la pillola usa il testo della domanda", () => {
  const h = core.choose(ALGO, core.choose(ALGO, [], 1), 0);
  assert.equal(core.pills(ALGO, h)[1].label, "Sottotipo?: X");
});

test("proceed segue next e la pillola usa il titolo della raccomandazione", () => {
  const h = core.proceed(ALGO, core.choose(ALGO, [], 0));
  assert.equal(core.currentNodeId(ALGO, h), "r2");
  assert.deepEqual(core.pills(ALGO, h)[1], { index: 1, label: "1ª linea" });
});

test("choose non modifica la cronologia originale", () => {
  const h0 = core.choose(ALGO, [], 0);
  const copy = JSON.parse(JSON.stringify(h0));
  core.proceed(ALGO, h0);
  assert.deepEqual(h0, copy);
});

test("errori: risposta non valida, choose su raccomandazione, proceed senza next", () => {
  assert.throws(() => core.choose(ALGO, [], 5), /non valida/);
  const atRec = core.choose(ALGO, [], 0);
  assert.throws(() => core.choose(ALGO, atRec, 0), /non valida/);
  const atEnd = core.proceed(ALGO, atRec);
  assert.throws(() => core.proceed(ALGO, atEnd), /non ha un seguito/);
});

test("Review Focus 1: nodo condiviso, le pillole mostrano il percorso realmente seguito", () => {
  const viaA = core.proceed(ALGO, core.choose(ALGO, [], 0));
  const viaB = core.choose(ALGO, core.choose(ALGO, [], 1), 1);
  assert.equal(core.currentNodeId(ALGO, viaA), "r2");
  assert.equal(core.currentNodeId(ALGO, viaB), "r2");
  assert.deepEqual(core.pills(ALGO, viaA).map(p => p.label), ["Setting: A", "1ª linea"]);
  assert.deepEqual(core.pills(ALGO, viaB).map(p => p.label), ["Setting: B", "Sottotipo?: Y"]);
});

test("Review Focus 2: tornare a una pillola e cambiare risposta elimina le risposte successive", () => {
  const deep = core.choose(ALGO, core.choose(ALGO, [], 1), 0);
  const back = core.rewind(deep, 0);
  assert.equal(core.currentNodeId(ALGO, back), "q1");
  const changed = core.choose(ALGO, back, 0);
  assert.deepEqual(core.pills(ALGO, changed).map(p => p.label), ["Setting: A"]);
  assert.equal(core.currentNodeId(ALGO, changed), "r1");
});

test("aifaLabel: etichette esatte e fallback", () => {
  assert.equal(core.aifaLabel("reimbursed"), "Rimborsato AIFA");
  assert.equal(core.aifaLabel("not_reimbursed"), "Non rimborsato AIFA");
  assert.equal(core.aifaLabel("unknown"), "Da verificare");
  assert.equal(core.aifaLabel("standard"), "Standard");
  assert.equal(core.aifaLabel("boh"), "Da verificare");
});

// Percorre ogni ramo di un algoritmo scegliendo ogni terapia indicata; gli stati con lo stesso nodo
// e le stesse classi attive si visitano una volta sola.
function explore(algo) {
  const visited = new Set(), seen = new Set(), deadEnds = [];
  let endings = 0;
  (function walk(history) {
    const id = core.currentNodeId(algo, history);
    const node = algo.nodes[id];
    visited.add(id);
    const key = id + "|" + [...core.exposures(algo, history).active].sort().join(",");
    if (seen.has(key)) return;
    seen.add(key);
    if (node.type === "question") {
      node.answers.forEach((_, i) => walk(core.choose(algo, history, i)));
    } else if (node.select) {
      const ok = node.options.map((o, i) => [o, i]).filter(([o]) => core.optionStatus(algo, history, o).available);
      if (ok.length) ok.forEach(([, i]) => walk(core.pick(algo, history, i)));
      else if (node.next) walk(core.proceed(algo, history));
      else deadEnds.push(id);
    } else if (node.next) {
      walk(core.proceed(algo, history));
    } else {
      endings += 1;
      assert.ok(core.pills(algo, history).length > 0);
    }
  })([]);
  return { visited, endings, deadEnds };
}

const ALGO_DIR = path.join(__dirname, "..", "Algoritmi");
for (const file of fs.readdirSync(ALGO_DIR).filter(f => f.endsWith(".algo.json"))) {
  test(`${file}: ogni percorso arriva a una raccomandazione finale, senza vicoli ciechi, e tocca tutti i nodi`, () => {
    const algo = JSON.parse(fs.readFileSync(path.join(ALGO_DIR, file), "utf8"));
    const { visited, endings, deadEnds } = explore(algo);
    assert.ok(endings > 0);
    assert.deepEqual(deadEnds, []);
    // i nodi raggiungibili solo tramite una domanda saltata non contano
    const skipped = Object.entries(algo.nodes).filter(([, n]) => n.only_if_any || n.skip_if_any || n.auto_route).map(([id]) => id);
    assert.deepEqual(Object.keys(algo.nodes).filter(id => !visited.has(id) && !skipped.includes(id)), []);
  });
}

test("Mammella: l'esplorazione copre molti percorsi", () => {
  const algo = JSON.parse(fs.readFileSync(path.join(ALGO_DIR, "mammella.algo.json"), "utf8"));
  assert.ok(explore(algo).endings > 20);
});

test("trail distingue risposte e linee di terapia superate", () => {
  const h = core.proceed(ALGO, core.choose(ALGO, [], 0));
  assert.deepEqual(core.trail(ALGO, h), [
    { index: 0, kind: "answer", nodeId: "q1", label: "Setting", value: "A" },
    { index: 1, kind: "line", nodeId: "r1", label: "1ª linea", options: ["F1"] },
  ]);
});

test("preview descrive la destinazione di una risposta", () => {
  assert.deepEqual(core.preview(ALGO, "q2"), { kind: "question", label: "Sottotipo?" });
  assert.deepEqual(core.preview(ALGO, "r1"), { kind: "recommendation", label: "1ª linea", options: ["F1"] });
  assert.equal(core.preview(ALGO, "manca"), null);
});

test("reachable elenca le raccomandazioni in ordine di distanza", () => {
  assert.deepEqual(core.reachable(ALGO, "q1"), ["r1", "r2"]);
  assert.deepEqual(core.reachable(ALGO, "q2"), ["r2"]);
});

test("sequence mostra linea corrente e successive, poi quelle superate", () => {
  const h1 = core.choose(ALGO, [], 0);
  assert.deepEqual(core.sequence(ALGO, h1), { done: [], current: { nodeId: "r1", title: "1ª linea" }, upcoming: [["2ª linea"]] });
  const h2 = core.proceed(ALGO, h1);
  assert.deepEqual(core.sequence(ALGO, h2), {
    done: [{ index: 1, nodeId: "r1", title: "1ª linea" }],
    current: { nodeId: "r2", title: "2ª linea" },
    upcoming: [],
  });
  assert.deepEqual(core.sequence(ALGO, []), { done: [], current: null, upcoming: [] });
});

test("sequence raggruppa le alternative dello stesso passo", () => {
  const algo = {
    start: "r0",
    nodes: {
      r0: { type: "recommendation", title: "Neoadiuvante", options: [], next: { label: "Dopo la chirurgia", node: "q" } },
      q: { type: "question", text: "Risposta?", answers: [{ label: "pCR", next: "a" }, { label: "Residuo", next: "b" }] },
      a: { type: "recommendation", title: "Adiuvante", options: [] },
      b: { type: "recommendation", title: "Adiuvante — residuo", options: [], next: { label: "poi", node: "c" } },
      c: { type: "recommendation", title: "Follow-up", options: [] },
    },
  };
  assert.deepEqual(core.sequence(algo, []).upcoming, [["Adiuvante", "Adiuvante — residuo"], ["Follow-up"]]);
});

// ---------- trattamenti ricevuti: scenari sull'algoritmo dell'urotelio ----------
const URO = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "Algoritmi", "urotelio.algo.json"), "utf8"));

// Percorre l'algoritmo: stringhe = etichetta della risposta, { pick } = nome della terapia scelta.
function walk(algo, steps) {
  let h = [];
  for (const s of steps) {
    const node = algo.nodes[core.currentNodeId(algo, h)];
    if (typeof s === "string") {
      const i = node.answers.findIndex(a => a.label.startsWith(s));
      assert.ok(i >= 0, `risposta "${s}" assente in ${core.currentNodeId(algo, h)}`);
      h = core.choose(algo, h, i);
    } else {
      const i = node.options.findIndex(o => o.name.startsWith(s.pick));
      assert.ok(i >= 0, `terapia "${s.pick}" assente in ${core.currentNodeId(algo, h)}`);
      h = core.pick(algo, h, i);
    }
  }
  return h;
}
// Stato delle opzioni nel nodo corrente: { nome: true se indicata }.
function statuses(algo, h) {
  const node = algo.nodes[core.currentNodeId(algo, h)];
  return Object.fromEntries(node.options.map(o => [o.name, core.optionStatus(algo, h, o).available]));
}

test("urotelio: dopo EV-pembrolizumab in 1ª linea non si ripropongono anti-PD-1 né EV", () => {
  const h = walk(URO, ["Avanzato", { pick: "Enfortumab vedotin + pembrolizumab" }]);
  assert.equal(core.currentNodeId(URO, h), "m1_2l");
  const st = statuses(URO, h);
  assert.equal(st["Pembrolizumab"], false);
  assert.equal(st["Enfortumab vedotin"], false);
  assert.equal(st["Erdafitinib (FGFR3 alterato)"], true);
  assert.equal(st["Chemioterapia a base di platino"], true);
});

test("urotelio: chemioterapia senza avelumab lascia la 2ª linea IO-naive", () => {
  const withAve = walk(URO, ["Avanzato", { pick: "Chemioterapia a base di platino" }, "Sì"]);
  const noAve = walk(URO, ["Avanzato", { pick: "Chemioterapia a base di platino" }, "No"]);
  assert.equal(statuses(URO, withAve)["Pembrolizumab"], false);
  assert.equal(statuses(URO, withAve)["Enfortumab vedotin"], true);
  assert.equal(statuses(URO, noAve)["Pembrolizumab"], true);
  assert.equal(statuses(URO, noAve)["Enfortumab vedotin"], false);
  assert.equal(statuses(URO, noAve)["Chemioterapia a base di platino"], false);
  assert.deepEqual(core.exposures(URO, withAve).treatments.map(t => t.name),
    ["Chemioterapia a base di platino ± avelumab di mantenimento", "Avelumab di mantenimento"]);
});

test("urotelio: recidiva entro 12 mesi da durvalumab perioperatorio → linee successive senza IO", () => {
  const h = walk(URO, ["Muscolo-invasivo", "Cisplatino-eleggibile", { pick: "Durvalumab" }, "Entro 12 mesi"]);
  assert.equal(core.currentNodeId(URO, h), "m1_2l");
  assert.equal(statuses(URO, h)["Pembrolizumab"], false);
  assert.throws(() => core.pick(URO, h, URO.nodes.m1_2l.options.findIndex(o => o.name === "Pembrolizumab")));
});

test("urotelio: recidiva oltre 12 mesi riapre la 1ª linea e segna il trattamento come non limitante", () => {
  const h = walk(URO, ["Muscolo-invasivo", "Cisplatino-eleggibile", { pick: "Durvalumab" }, "Oltre 12 mesi"]);
  assert.equal(core.currentNodeId(URO, h), "m1_1l");
  const ex = core.exposures(URO, h);
  assert.equal(ex.active.size, 0);
  assert.equal(ex.treatments[0].expired, "Oltre 12 mesi");
});

test("urotelio: senza terapia sistemica perioperatoria la domanda sulla recidiva si salta", () => {
  const h = walk(URO, ["Muscolo-invasivo", "Cisplatino-ineleggibile", { pick: "Cistectomia" }, { pick: "Osservazione" }]);
  assert.equal(core.currentNodeId(URO, h), "m1_1l");
  const hu = walk(URO, ["Alta via", { pick: "Nefroureterectomia" }, { pick: "Chemioterapia adiuvante" }]);
  assert.equal(core.currentNodeId(URO, hu), "rec_periop");
});

// ---------- scenari clinici per organo: [algoritmo, percorso, nodo atteso, { terapia: indicata? }] ----------
// Percorso: "etichetta risposta", { pick: "terapia" }, oppure "next" per proseguire.
function walkAny(algo, steps) {
  let h = [];
  for (const s of steps) {
    if (s === "next") { h = core.proceed(algo, h); continue; }
    const node = algo.nodes[core.currentNodeId(algo, h)];
    if (typeof s === "string") {
      const i = node.answers.findIndex(a => a.label.startsWith(s));
      assert.ok(i >= 0, `risposta "${s}" assente in ${core.currentNodeId(algo, h)}`);
      h = core.choose(algo, h, i);
    } else {
      const i = node.options.findIndex(o => o.name === s.pick) >= 0 ? node.options.findIndex(o => o.name === s.pick) : node.options.findIndex(o => o.name.startsWith(s.pick));
      assert.ok(i >= 0, `terapia "${s.pick}" assente in ${core.currentNodeId(algo, h)}`);
      h = core.pick(algo, h, i);
    }
  }
  return h;
}
const SCENARI = [
  ["polmone_nsclc", ["Avanzato", "Nessun driver", "PS 0-1", "TPS ≥50%", { pick: "Pembrolizumab" }], "m1_2l_post_io", { "Doppietta a base di platino": true }],
  ["polmone_nsclc", ["Avanzato", "Nessun driver", "PS 0-1", "TPS <50%", "Non squamoso", { pick: "Pembrolizumab + platino" }], "m1_2l_post_io", { "Doppietta a base di platino": false }],
  ["polmone_nsclc", ["Avanzato", "EGFR mutato", "Classica", { pick: "Osimertinib + platino" }], "m1_egfr_2l", { "Platino + pemetrexed ± bevacizumab": false, "Docetaxel": true }],
  ["mesotelioma", ["Non resecabile", "Epitelioide", { pick: "Nivolumab + ipilimumab" }], "adv_2l_epi", { "Nivolumab in monoterapia": false, "Platino + pemetrexed": true }],
  ["mammella", ["Precoce", "HR+/HER2-", "Alto", { pick: "Abemaciclib" }, "Entro"], "m1_hr_2l", {}],
  ["mammella", ["Precoce", "HR+/HER2-", "Basso", { pick: "Terapia endocrina adiuvante" }, "Durante", "No"], "m1_hr_pik3ca", {}],
  ["mammella", ["Metastatico", "HR+/HER2-", "No", "Endocrino-resistente", "Sì", { pick: "Fulvestrant" }, "PIK3CA"], "m1_hr_2l_pi3k", { "Capivasertib + fulvestrant": false, "Everolimus + exemestane": true }],
  ["stomaco", ["Localizzato", "pMMR", { pick: "Durvalumab" }, "Entro", "HER2 negativo", "PD-L1 CPS ≥5"], "adv_cps5", { "Nivolumab + chemioterapia": false, "Chemioterapia (CAPOX o FOLFOX)": true }],
  ["esofago", ["Avanzato", "Carcinoma squamoso", { pick: "Pembrolizumab" }], "adv_scc_2l", { "Tislelizumab in monoterapia (se IO-naive)": false, "Taxano": true }],
  ["colonretto", ["Colon localizzato", "Stadio III", "pMMR", "Alto", { pick: "FOLFOX" }, "Entro", "Malattia non resecabile", "RAS mutato"], "m_ras", { "FOLFOXIRI + bevacizumab": false }],
  ["colonretto", ["Metastatico", "Malattia non res", "RAS e BRAF", "Colon sinistro", { pick: "Doppietta + anti-EGFR" }], "m_2l", { "Doppietta + anti-EGFR se RAS wild-type e non ancora usato": false }],
  ["pancreas", ["Metastatico", "PS 0-1", { pick: "FOLFIRINOX" }], "pan_2l_postffx", {}],
  ["pancreas", ["Resecabile", "next", { pick: "Gemcitabina + capecitabina" }, "Entro"], "pan_2l_postgem", {}],
  ["epatocarcinoma", ["BCLC C", "Controindicazione all'immunoterapia", { pick: "Lenvatinib" }], "hcc_2l", { "Regorafenib": false, "Sorafenib dopo lenvatinib": true }],
  ["gist", ["Localizzato", "next", "Alto rischio", { pick: "Imatinib per 3 anni" }, "Durante"], "m1_2l", {}],
  ["prostata", ["Metastatico ormono", "Alto volume, fit", { pick: "Tripletta ADT + docetaxel + darolutamide" }], "crpc_post_doce", { "Cabazitaxel": true }],
  ["prostata", ["Metastatico resistente", "Naïve", { pick: "Abiraterone" }], "crpc_post_arsi", { "ARSI (abiraterone o enzalutamide)": false, "Docetaxel": true }],
  ["rene", ["Avanzato", "Cellule chiare", "Intermedio", { pick: "Nivolumab + ipilimumab" }], "m1_2l_post_ioio", {}],
  ["rene", ["Localizzato", { pick: "Nefrectomia radicale" }, "Intermedio", { pick: "Pembrolizumab per 1 anno" }, "Entro", "Cellule chiare", "Favorevole"], "m1_fav", { "Pembrolizumab + axitinib": false, "Sunitinib o pazopanib": true }],
  ["cervice", ["Localmente", "Sì", { pick: "Pembrolizumab + CRT" }, "Entro", "CPS ≥1"], "adv_1l_pembro", { "Pembrolizumab + platino-paclitaxel ± bevacizumab": false, "Cisplatino-paclitaxel + bevacizumab": true }],
  ["endometrio", ["Avanzato", "pMMR", { pick: "Dostarlimab" }], "adv_2l", { "Lenvatinib + pembrolizumab": false }],
  ["ovaio", ["Stadio avanzato", { pick: "Citoriduzione" }, { pick: "Carboplatino" }, "BRCA1/2", { pick: "Olaparib" }, "Platino-sensibile", { pick: "Carboplatino + gemcitabina" }], "rec_mant", { "Niraparib": false, "Nessun mantenimento: sorveglianza": true }],
  ["melanoma", ["Stadio III resecato", "BRAF wild-type", { pick: "Pembrolizumab" }, "Entro", "No", "BRAF wild-type", "PD-L1 <1%"], "adv_io_neg", { "Anti-PD-1 in monoterapia": false, "Nivolumab + ipilimumab": true }],
  ["melanoma", ["Avanzato", "No", "BRAF V600", "Sì", { pick: "BRAF + MEK inibitore" }], "adv_2l", { "Nivolumab + ipilimumab": true }],
  ["testacollo", ["Carcinoma squamoso (cavo", "Localmente", "Chirurgia", { pick: "+ Pembrolizumab" }, "R1", { pick: "Chemioradioterapia" }, "Entro"], "rm_2l", { "Nivolumab (IO-naive)": false }],
  ["sarcomi", ["Malattia avanzata", "No", "Leiomiosarcoma", { pick: "Doxorubicina + trabectedina" }], "adv_2l", { "Trabectedina (leiomiosarcoma, liposarcoma)": false }],
];
for (const [id, steps, expectedNode, expected] of SCENARI) {
  test(`scenario ${id}: ${steps.map(s => typeof s === "string" ? s : s.pick).join(" → ")}`, () => {
    const algo = JSON.parse(fs.readFileSync(path.join(ALGO_DIR, `${id}.algo.json`), "utf8"));
    const h = walkAny(algo, steps);
    assert.equal(core.currentNodeId(algo, h), expectedNode);
    const node = algo.nodes[expectedNode];
    for (const [name, ok] of Object.entries(expected)) {
      const option = node.options.find(o => o.name === name);
      assert.ok(option, `opzione "${name}" assente in ${expectedNode}`);
      assert.equal(core.optionStatus(algo, h, option).available, ok, name);
    }
  });
}
