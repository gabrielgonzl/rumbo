/* ============================================================
   carteras.js  ·  Totales por cartera de fondos (función pura, con test)
   Se usa en Posiciones: una línea por cartera con la suma de sus fondos.
   ============================================================ */
(function (raiz) {
  "use strict";

  const SIN = "sin-cartera";

  /* filas = filas de Posiciones ({p, valor, peso, plus, pct}, con p.carteraId); carteras = D.carteras.
     Devuelve [{id, nombre, entidad, ltvMax, filas, valor, peso, plus, pct, tir}], por valor descendente y con
     «Sin cartera» al final. La plusvalía y la rentabilidad de la línea solo se dan si TODOS sus fondos tienen plusvalía
     (si no, null: no se enseña un parcial como si fuera el total); es plusvalía / coste, con coste = valor - plusvalía. */
  function agrupa(filas, carteras) {
    const por = new Map((carteras || []).map(c => [c.id, c]));
    const grupos = new Map();
    (filas || []).forEach(f => {
      const id = f.p && por.has(f.p.carteraId) ? f.p.carteraId : SIN;
      if (!grupos.has(id)) {
        const c = por.get(id) || {};
        grupos.set(id, { id, nombre: id === SIN ? "Sin cartera" : c.nombre, entidad: c.entidad || "", ltvMax: c.ltvMax == null ? null : c.ltvMax,
          tirServidor: id !== SIN && c.tir != null ? c.tir : null, fondosTotal: id !== SIN ? c.fondos : null, filas: [] });
      }
      grupos.get(id).filas.push(f);
    });
    const out = [...grupos.values()].map(g => {
      const valor = g.filas.reduce((a, f) => a + f.valor, 0);
      const peso = g.filas.reduce((a, f) => a + (f.peso || 0), 0);
      const con = g.filas.filter(f => f.plus != null);
      const plus = con.length && con.length === g.filas.length ? con.reduce((a, f) => a + f.plus, 0) : null;   // todos o ninguno
      const coste = valor - (plus || 0);
      const pct = plus != null && con.length === g.filas.length && coste > 0 ? plus / coste : null;
      // La TIR combinada la calcula el servidor con TODOS los fondos: solo vale si están todos a la vista.
      const tir = g.tirServidor != null && g.fondosTotal === g.filas.length ? g.tirServidor : null;
      delete g.tirServidor; delete g.fondosTotal;
      return Object.assign(g, { valor, peso, plus, pct, tir });
    });
    return out.sort((a, b) => (a.id === SIN) - (b.id === SIN) || b.valor - a.valor);
  }

  /* LTV que se propone en el formulario del préstamo: el de las carteras en garantía si la garantía son SOLO
     carteras y todas tienen el mismo LTV; en otro caso null (espejo de pignoracion.ltv_sugerido). */
  function ltvSugerido(ids, nSueltos, carteras) {
    if (nSueltos > 0 || !ids || !ids.length) return null;
    const por = new Map((carteras || []).map(c => [c.id, c.ltvMax]));
    const v = ids.map(i => por.get(i));
    if (v.some(x => x == null) || new Set(v).size !== 1) return null;
    return Number(v[0]);
  }

  /* Texto (sin escapar) de la garantía de un préstamo resumido: «Cartera Ejemplo + 2 fondos sueltos». */
  function textoGarantia(x) {
    const nc = ((x && x.carterasDetalle) || []).map(c => c.nombre);
    const sueltos = ((x && x.activosSueltos) || []).length;
    if (!nc.length) { const n = ((x && x.activosDetalle) || []).length; return n + (n === 1 ? " activo" : " activos"); }
    const partes = [nc.join(" + ")];
    if (sueltos) partes.push(sueltos + (sueltos === 1 ? " fondo suelto" : " fondos sueltos"));
    return partes.join(" + ");
  }

  /* ¿La fila de Posiciones coincide con la búsqueda? Por fondo (nombre, identificador, clase) o por el nombre o la
     entidad de su cartera. Sin búsqueda, todo coincide. */
  function coincide(f, q, carteras) {
    const t = String(q || "").trim().toLowerCase();
    if (!t) return true;
    const p = (f && f.p) || {};
    if (((p.nombre || "") + " " + (p.identificador || "") + " " + ((f && f.clase) || "")).toLowerCase().includes(t)) return true;
    const c = (carteras || []).find(x => x.id === p.carteraId);
    return !!c && ((c.nombre || "") + " " + (c.entidad || "")).toLowerCase().includes(t);
  }

  const API = { agrupa, ltvSugerido, textoGarantia, coincide, SIN };
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  else raiz.Carteras = API;
})(typeof window !== "undefined" ? window : globalThis);
