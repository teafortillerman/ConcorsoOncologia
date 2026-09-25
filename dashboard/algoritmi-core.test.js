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

test("Mammella: ogni percorso completo arriva a una raccomandazione finale e tocca tutti i nodi", () => {
  const file = path.join(__dirname, "..", "Algoritmi", "mammella.algo.json");
  const algo = JSON.parse(fs.readFileSync(file, "utf8"));
  const visited = new Set();
  let endings = 0;
  (function walk(history) {
    const id = core.currentNodeId(algo, history);
    const node = algo.nodes[id];
    visited.add(id);
    if (node.type === "question") {
      node.answers.forEach((_, i) => walk(core.choose(algo, history, i)));
    } else if (node.next) {
      walk(core.proceed(algo, history));
    } else {
      endings += 1;
      assert.ok(core.pills(algo, history).length > 0);
    }
  })([]);
  assert.ok(endings > 20, `solo ${endings} percorsi`);
  assert.deepEqual([...Object.keys(algo.nodes)].filter(id => !visited.has(id)), []);
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
