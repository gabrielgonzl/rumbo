/* ============================================================
   estilos.js  ·  Estilos en línea compatibles con una CSP estricta
   La CSP no admite atributos style="…" (ni setAttribute("style")), pero sí asignar `el.style`
   desde un script. La interfaz escribe `data-st="color:red"` donde antes ponía `style="…"` y
   este archivo lo aplica a cada nodo que entra en la página (y a los que ya estaban).
   ============================================================ */
(function () {
  "use strict";
  function aplica(n) {
    if (!n || n.nodeType !== 1) return;
    if (n.hasAttribute("data-st")) {
      n.style.cssText = n.getAttribute("data-st");
      n.removeAttribute("data-st");
    }
    if (n.querySelectorAll) n.querySelectorAll("[data-st]").forEach(aplica);
  }
  aplica(document.documentElement);
  new MutationObserver(ms => ms.forEach(m => {
    if (m.type === "attributes") aplica(m.target);
    else m.addedNodes.forEach(aplica);
  })).observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ["data-st"] });
})();
