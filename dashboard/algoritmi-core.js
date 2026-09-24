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

  function aifaLabel(code) {
    return AIFA_LABELS[code] || AIFA_LABELS.unknown;
  }

  return { currentNodeId, choose, proceed, rewind, pills, aifaLabel };
});
