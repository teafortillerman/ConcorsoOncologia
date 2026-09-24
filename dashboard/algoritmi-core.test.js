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
