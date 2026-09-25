/* Logica di navigazione degli algoritmi guidati: funzioni pure, nessun accesso al DOM.
   history = array di passi { nodeId, choice }, dove choice è l'indice della risposta
   (domanda) oppure "next" (raccomandazione proseguita alla linea successiva). */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.AlgoCore = api;
})(typeof self !== "undefined" ? self : this, function () {
  const AIFA_LABELS = {
    reimbursed: "Rimborsato AIFA",
    not_reimbursed: "Non rimborsato AIFA",
    unknown: "Da verificare",
    standard: "Standard",
  };

  function stepTarget(algo, step) {
    const node = algo.nodes[step.nodeId];
    return step.choice === "next" ? node.next.node : node.answers[step.choice].next;
  }

  function currentNodeId(algo, history) {
    return history.length ? stepTarget(algo, history[history.length - 1]) : algo.start;
  }

  function choose(algo, history, answerIndex) {
    const nodeId = currentNodeId(algo, history);
    const node = algo.nodes[nodeId];
    if (node.type !== "question" || !node.answers[answerIndex]) {
      throw new Error(`Risposta ${answerIndex} non valida per il nodo ${nodeId}`);
    }
    return [...history, { nodeId, choice: answerIndex }];
  }

  function proceed(algo, history) {
    const nodeId = currentNodeId(algo, history);
    const node = algo.nodes[nodeId];
    if (node.type !== "recommendation" || !node.next) {
      throw new Error(`Il nodo ${nodeId} non ha un seguito`);
    }
    return [...history, { nodeId, choice: "next" }];
  }

  function rewind(history, index) {
    return history.slice(0, index);
  }

  function pills(algo, history) {
    return history.map((step, index) => {
      const node = algo.nodes[step.nodeId];
      if (step.choice === "next") return { index, label: node.title };
      return { index, label: `${node.short || node.text}: ${node.answers[step.choice].label}` };
    });
  }

  // Percorso arricchito per la timeline: ogni passo è una risposta a una domanda
  // oppure una linea di terapia superata ("next"), con le opzioni che proponeva.
  function trail(algo, history) {
    return history.map((step, index) => {
      const node = algo.nodes[step.nodeId];
      if (step.choice === "next") {
        return { index, kind: "line", nodeId: step.nodeId, label: node.title, options: node.options.map(o => o.name) };
      }
      return { index, kind: "answer", nodeId: step.nodeId, label: node.short || node.text, value: node.answers[step.choice].label };
    });
  }

  // Dove porta un nodo: la prossima domanda oppure la terapia raccomandata.
  function preview(algo, nodeId) {
    const node = algo.nodes[nodeId];
    if (!node) return null;
    return node.type === "question"
      ? { kind: "question", label: node.short || node.text }
      : { kind: "recommendation", label: node.title, options: node.options.map(o => o.name) };
  }

  // Raccomandazioni raggiungibili da un nodo (visita in ampiezza), ordinate per distanza.
  function reachable(algo, fromId) {
    const seen = new Set([fromId]);
    const queue = [fromId];
    const out = [];
    while (queue.length) {
      const id = queue.shift();
      const node = algo.nodes[id];
      if (!node) continue;
      if (node.type === "recommendation") out.push(id);
      const targets = node.type === "question" ? node.answers.map(a => a.next) : (node.next ? [node.next.node] : []);
      for (const t of targets) if (!seen.has(t)) { seen.add(t); queue.push(t); }
    }
    return out;
  }

  // Linee di terapia successive raggruppate per livello: il livello è il numero di
  // raccomandazioni attraversate, così le alternative dello stesso passo stanno insieme.
  function upcomingLevels(algo, fromId, exclude) {
    const best = new Map([[fromId, 1]]);
    const queue = [fromId];
    while (queue.length) {
      const id = queue.shift();
      const node = algo.nodes[id];
      if (!node) continue;
      const level = best.get(id);
      const nextLevel = node.type === "recommendation" ? level + 1 : level;
      const targets = node.type === "question" ? node.answers.map(a => a.next) : (node.next ? [node.next.node] : []);
      for (const t of targets) {
        if (!best.has(t) || best.get(t) > nextLevel) { best.set(t, nextLevel); queue.push(t); }
      }
    }
    const levels = [];
    const seen = new Set(exclude);
    [...best.entries()]
      .filter(([id]) => algo.nodes[id] && algo.nodes[id].type === "recommendation")
      .sort((a, b) => a[1] - b[1])
      .forEach(([id, level]) => {
        const title = algo.nodes[id].title;
        if (seen.has(title)) return;
        seen.add(title);
        (levels[level - 1] = levels[level - 1] || []).push(title);
      });
    return levels.filter(Boolean);
  }

  // Sequenza delle linee di terapia sul ramo attuale: linee già superate, linea
  // corrente (se il nodo corrente è una raccomandazione) e passi successivi possibili,
  // ciascuno come elenco di alternative.
  function sequence(algo, history) {
    const done = history
      .map((step, index) => ({ step, index }))
      .filter(({ step }) => step.choice === "next")
      .map(({ step, index }) => ({ index, nodeId: step.nodeId, title: algo.nodes[step.nodeId].title }));
    const currentId = currentNodeId(algo, history);
    const node = algo.nodes[currentId];
    const current = node.type === "recommendation" ? { nodeId: currentId, title: node.title } : null;
    const from = current ? (node.next && node.next.node) : (done.length ? currentId : null);
    const upcoming = from ? upcomingLevels(algo, from, current ? [current.title] : []) : [];
    return { done, current, upcoming };
  }

  function aifaLabel(code) {
    return AIFA_LABELS[code] || AIFA_LABELS.unknown;
  }

  return { currentNodeId, choose, proceed, rewind, pills, trail, preview, reachable, sequence, aifaLabel };
});
