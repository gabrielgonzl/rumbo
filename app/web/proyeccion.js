/* proyeccion.js · Cálculo de «Si sigo así…» (sin DOM, para poder probarlo).
   Se carga en el navegador como window.Proyeccion y en Node con require(). */
(function (raiz) {
  "use strict";

  // Tipos que no crecen con la media de la cartera si no tienen objetivo propio.
  const QUIETOS = new Set(["efectivo", "deuda", "inmueble", "otro"]);

  /* Rentabilidad anual implícita de llevar un precio de 'hoy' a 'objetivo' en 'anos'. */
  function rentImplicita(hoy, objetivo, anos) {
    if (!(hoy > 0) || !(objetivo > 0) || !(anos > 0)) return null;
    return Math.pow(objetivo / hoy, 1 / anos) - 1;
  }

  /* Media de la cartera: solo cuentan los activos con objetivo, ponderados por su valor. */
  function mediaCartera(activos, anos) {
    let peso = 0, suma = 0;
    activos.forEach(a => {
      const r = rentImplicita(a.precio, a.objetivo, anos);
      if (r == null || !(a.valor > 0)) return;
      peso += a.valor; suma += a.valor * r;
    });
    return peso > 0 ? suma / peso : null;
  }

  /*
    entrada = {
      activos: [{id, valor, precio, objetivo, tipo}],   // objetivo = precio dentro de 'anos' (o null)
      anos, modo: "global" | "activo" | "mixto",
      rentGlobal,        // 0.07 = 7 %: modo global y respaldo de las aportaciones
      aportacion,        // € al mes, siempre global (no se atribuye a ningún activo)
      valorBase,         // lo que no son activos con precio (pasivos...): se mantiene fijo
      deuda              // opcional: deuda pendiente al final de cada mes [m0..mN] (se resta del total)
    }
    Devuelve {meses, total[], cartera[], aportaciones[], aportado[], porActivo{id:{rent, final}},
              media, rentAportaciones}
  */
  function simula(e) {
    const n = Math.round(e.anos * 12);
    const media = mediaCartera(e.activos, e.anos);
    // Las aportaciones crecen con la media de los objetivos; sin objetivos, con la global.
    const rentAport = e.modo === "global" || media == null ? e.rentGlobal : media;

    const porActivo = {};
    e.activos.forEach(a => {
      let r;
      const propia = rentImplicita(a.precio, a.objetivo, e.anos);
      if (e.modo === "global") r = a.valor > 0 && !QUIETOS.has(a.tipo) ? e.rentGlobal : 0;
      else if (propia != null) r = propia;
      else if (e.modo === "mixto" && media != null && a.valor > 0 && !QUIETOS.has(a.tipo)) r = media;
      else r = 0;
      porActivo[a.id] = { rent: r, valor: a.valor, propia: propia != null };
    });

    const mensual = r => Math.pow(1 + r, 1 / 12);
    const cartera = [], aportaciones = [], aportado = [], total = [];
    let ap = 0, acum = 0;
    const base = e.valorBase || 0;
    for (let m = 0; m <= n; m++) {
      let v = 0;
      e.activos.forEach(a => { v += a.valor * Math.pow(1 + porActivo[a.id].rent, m / 12); });
      cartera.push(v + base);
      aportaciones.push(ap);
      aportado.push(acum);
      total.push(v + base + ap - (e.deuda ? (e.deuda[m] || 0) : 0));
      ap = ap * mensual(rentAport) + e.aportacion;
      acum += e.aportacion;
    }
    e.activos.forEach(a => {
      porActivo[a.id].final = a.valor * Math.pow(1 + porActivo[a.id].rent, e.anos);
    });
    return { meses: n, total, cartera, aportaciones, aportado, porActivo, media, rentAportaciones: rentAport,
             deudaFinal: e.deuda ? (e.deuda[n] || 0) : 0 };
  }

  const api = { rentImplicita, mediaCartera, simula };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else raiz.Proyeccion = api;
})(typeof window !== "undefined" ? window : globalThis);
