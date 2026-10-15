/* ============================================================
   estilos.js  ·  Estilos en línea compatibles con una CSP estricta
   La CSP no admite el atributo de estilo en línea (ni crearlo con setAttribute), pero sí asignar
   `el.style` desde un script. La interfaz escribe `data-st="color:red"` donde antes iba ese atributo y
   este archivo lo aplica a cada nodo que entra en la página (y a los que ya estaban).

   Defensa en profundidad: solo se aplican las propiedades que la interfaz usa (más variables
   `--x`), y se descarta cualquier valor con url(), @, \ o expression. Así, aunque un dato ajeno
   consiguiera colar un `data-st`, no podría superponer ni mover elementos (position, inset,
   z-index… no están permitidos) ni cargar nada.
   ============================================================ */
(function (raiz) {
  "use strict";

  const PERMITIDAS = /^(--[a-z0-9-]+|margin(-(top|right|bottom|left))?|padding(-(top|right|bottom|left))?|background(-color)?|color|text-align|text-transform|width|height|display|left|gap|flex-wrap|align-items|cursor|font-size|font-weight|letter-spacing|border-radius)$/;
  const PELIGROSO = /url\s*\(|expression|@|\\|javascript:|<|>/i;

  /* "a:b; c:d" -> [["a","b"],["c","d"]] solo con lo permitido. Pura (con test). */
  function filtra(texto) {
    return String(texto || "").split(";").map(d => {
      const k = d.indexOf(":");
      return k < 0 ? null : [d.slice(0, k).trim().toLowerCase(), d.slice(k + 1).trim()];
    }).filter(d => d && PERMITIDAS.test(d[0]) && d[1] && !PELIGROSO.test(d[1]));
  }

  const API = { filtra };
  if (typeof module !== "undefined" && module.exports) { module.exports = API; return; }
  raiz.Estilos = API;

  function aplica(n) {
    if (!n || n.nodeType !== 1) return;
    if (n.hasAttribute("data-st")) {
      filtra(n.getAttribute("data-st")).forEach(([k, v]) => n.style.setProperty(k, v));
      n.removeAttribute("data-st");
    }
    if (n.querySelectorAll) n.querySelectorAll("[data-st]").forEach(aplica);
  }
  aplica(document.documentElement);
  new MutationObserver(ms => ms.forEach(m => {
    if (m.type === "attributes") aplica(m.target);
    else m.addedNodes.forEach(aplica);
  })).observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ["data-st"] });
})(typeof window !== "undefined" ? window : globalThis);
