/* Logica di navigazione degli algoritmi guidati: funzioni pure, nessun accesso al DOM.
   history = array di passi { nodeId, choice }, dove choice è l'indice della risposta
   (domanda), "next" (raccomandazione proseguita alla linea successiva) oppure "opt"
   con { option } (terapia scelta in una raccomandazione con "select": true).

   Trattamenti ricevuti: un'opzione scelta (o una risposta) può dichiarare "gives", le classi
   di farmaco ricevute (es. "io", "platino"). Le opzioni successive possono avere "requires"
   ed "excludes" ([{ tag, reason }]): se non sono soddisfatte l'opzione resta visibile ma
   non indicata, con il motivo. Una risposta con "expire" annulla l'effetto limitante di
   quelle classi (es. recidiva oltre 12 mesi dalla fine della terapia perioperatoria).
   Una domanda con "only_if_any" viene saltata (verso "skip_to") se nessuna di quelle
   classi è attiva. */
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
    if (step.choice === "next") return node.next.node;
    if (step.choice === "opt") {
      const option = node.options[step.option];
      return (option.next && option.next.node) || node.next.node;
    }
    return node.answers[step.choice].next;
  }

  // Classi di farmaco ricevute lungo il percorso e trattamenti effettuati, in ordine.
  function exposures(algo, history) {
    const active = new Set();
    const treatments = [];
    const add = (entry, tags) => {
      (tags || []).forEach(t => active.add(t));
      treatments.push({ ...entry, gives: [...(tags || [])], expired: null });
    };
    history.forEach((step, index) => {
      const node = algo.nodes[step.nodeId];
      if (step.choice === "opt") {
        const option = node.options[step.option];
        add({ index, line: node.title, name: option.name }, option.gives);
      } else if (typeof step.choice === "number") {
        const answer = node.answers[step.choice];
        if (answer.gives) add({ index, line: node.short || node.text, name: answer.treatment || answer.label }, answer.gives);
        (answer.expire || []).forEach(tag => {
          if (!active.delete(tag)) return;
          treatments.forEach(t => { if (t.gives.includes(tag) && !t.expired) t.expired = answer.label; });
        });
      }
    });
    return { active, treatments };
  }

  // Salta le domande che non si applicano ai trattamenti ricevuti ("only_if_any").
  function resolve(algo, history, nodeId) {
    let id = nodeId;
    for (let guard = 0; guard < 50; guard++) {
      const node = algo.nodes[id];
      if (!node || node.type !== "question" || !node.only_if_any) return id;
      const { active } = exposures(algo, history);
      if (node.only_if_any.some(t => active.has(t))) return id;
      id = node.skip_to;
    }
    return id;
  }

  function currentNodeId(algo, history) {
    return resolve(algo, history, history.length ? stepTarget(algo, history[history.length - 1]) : algo.start);
  }

  // Un'opzione è indicata se ha tutte le classi richieste e nessuna di quelle escluse.
  function optionStatus(algo, history, option) {
    const { active } = exposures(algo, history);
    const blocked = (option.excludes || []).find(r => active.has(r.tag)) || (option.requires || []).find(r => !active.has(r.tag));
    return blocked ? { available: false, reason: blocked.reason } : { available: true, reason: null };
  }

  function pick(algo, history, optionIndex) {
    const nodeId = currentNodeId(algo, history);
    const node = algo.nodes[nodeId];
    const option = node.type === "recommendation" && node.select ? node.options[optionIndex] : null;
    if (!option) throw new Error(`Terapia ${optionIndex} non selezionabile nel nodo ${nodeId}`);
    if (!optionStatus(algo, history, option).available) throw new Error(`Terapia non indicata: ${option.name}`);
    if (!(option.next || node.next)) throw new Error(`Il nodo ${nodeId} non ha un seguito`);
    return [...history, { nodeId, choice: "opt", option: optionIndex }];
  }

  function nodeTargets(node) {
    if (node.type === "question") return [...node.answers.map(a => a.next), ...(node.skip_to ? [node.skip_to] : [])];
    return [...(node.next ? [node.next.node] : []), ...node.options.filter(o => o.next).map(o => o.next.node)];
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
      if (step.choice === "opt") return { index, label: `${node.title}: ${node.options[step.option].name}` };
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
      if (step.choice === "opt") {
        return { index, kind: "line", nodeId: step.nodeId, label: node.title, chosen: node.options[step.option].name, options: [node.options[step.option].name] };
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
      const targets = nodeTargets(node);
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
      const targets = nodeTargets(node);
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
      .filter(({ step }) => step.choice === "next" || step.choice === "opt")
      .map(({ step, index }) => {
        const node = algo.nodes[step.nodeId];
        const entry = { index, nodeId: step.nodeId, title: node.title };
        if (step.choice === "opt") entry.chosen = node.options[step.option].name;
        return entry;
      });
    const currentId = currentNodeId(algo, history);
    const node = algo.nodes[currentId];
    const current = node.type === "recommendation" ? { nodeId: currentId, title: node.title } : null;
    const from = current ? ((node.next && node.next.node) || (node.options.find(o => o.next) || {}).next?.node) : (done.length ? currentId : null);
    const upcoming = from ? upcomingLevels(algo, from, current ? [current.title] : []) : [];
    return { done, current, upcoming };
  }

  function aifaLabel(code) {
    return AIFA_LABELS[code] || AIFA_LABELS.unknown;
  }

  return { currentNodeId, choose, proceed, pick, rewind, pills, trail, preview, reachable, sequence, aifaLabel, exposures, optionStatus };
});
