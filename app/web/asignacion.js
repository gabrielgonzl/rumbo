/* asignacion.js · Asignación objetivo, reparto de la aportación y metas (sin DOM, probado con Node).
   Se carga como window.Asignacion y en Node con require(). */
(function (raiz) {
  "use strict";

  const r2 = x => Math.round(x * 100) / 100;

  /*
    grupos = [{id, valor, objetivo}]  (objetivo en %, null = sin objetivo)
    aportacion = € a repartir este mes (sin vender nada).
    Devuelve [{id, valor, objetivo, pesoHoy, desviacion, sugerido}] y garantiza que
    la suma de lo sugerido es exactamente la aportación.
  */
  function reparto(grupos, aportacion) {
    const total = grupos.reduce((a, g) => a + Math.max(0, g.valor), 0);
    const conObj = grupos.filter(g => g.objetivo != null && g.objetivo > 0);
    const sumObj = conObj.reduce((a, g) => a + g.objetivo, 0);
    const despues = total + aportacion;

    // Lo que le falta a cada grupo para llegar a su objetivo tras aportar (nunca negativo: no se vende).
    const falta = {};
    conObj.forEach(g => { falta[g.id] = Math.max(0, (g.objetivo / 100) * despues - g.valor); });
    const faltaTotal = Object.values(falta).reduce((a, b) => a + b, 0);

    const sugerido = {};
    grupos.forEach(g => { sugerido[g.id] = 0; });
    if (aportacion > 0 && conObj.length) {
      if (faltaTotal >= aportacion && faltaTotal > 0) {
        // No llega para todos: se reparte en proporción a lo que le falta a cada uno.
        conObj.forEach(g => { sugerido[g.id] = aportacion * falta[g.id] / faltaTotal; });
      } else {
        // Sobra: primero se cubre lo que falta y el resto, según el peso objetivo.
        const resto = aportacion - faltaTotal;
        conObj.forEach(g => { sugerido[g.id] = falta[g.id] + (sumObj ? resto * g.objetivo / sumObj : 0); });
      }
      // Redondeo a céntimos sin perder ninguno: el último absorbe la diferencia.
      let acum = 0;
      conObj.forEach((g, i) => {
        if (i === conObj.length - 1) sugerido[g.id] = r2(aportacion - acum);
        else { sugerido[g.id] = r2(sugerido[g.id]); acum += sugerido[g.id]; }
      });
    }

    return grupos.map(g => {
      const pesoHoy = total ? g.valor / total : 0;
      return { id: g.id, valor: g.valor, objetivo: g.objetivo, pesoHoy,
        desviacion: g.objetivo != null ? pesoHoy * 100 - g.objetivo : null,   // puntos porcentuales
        sugerido: sugerido[g.id] };
    });
  }

  /* Mayor desviación absoluta (en puntos) de los grupos con objetivo. */
  function maxDesviacion(filas) {
    return filas.reduce((m, f) => f.desviacion == null ? m : Math.max(m, Math.abs(f.desviacion)), 0);
  }

  /*
    Meses hasta llegar a 'meta' desde 'valor' aportando 'aport' al mes con una rentabilidad anual 'rent'.
    null si no se llega en 100 años.
  */
  function mesesHasta(valor, meta, aport, rent) {
    if (valor >= meta) return 0;
    const i = Math.pow(1 + rent, 1 / 12) - 1;
    let v = valor;
    for (let m = 1; m <= 1200; m++) {
      v = v * (1 + i) + aport;
      if (v >= meta) return m;
    }
    return null;
  }

  /* Aportación mensual necesaria para llegar a 'meta' en 'meses' meses (rentabilidad anual 'rent'). */
  function aportacionNecesaria(valor, meta, meses, rent) {
    if (meses <= 0) return null;
    const i = Math.pow(1 + rent, 1 / 12) - 1;
    const g = Math.pow(1 + i, meses);
    const faltante = meta - valor * g;
    if (faltante <= 0) return 0;
    return i === 0 ? faltante / meses : faltante * i / (g - 1);
  }

  /* Meses naturales entre dos fechas ISO (la segunda posterior). */
  function mesesEntre(desdeIso, hastaIso) {
    const a = new Date(desdeIso + "T00:00:00"), b = new Date(hastaIso + "T00:00:00");
    return (b.getFullYear() - a.getFullYear()) * 12 + (b.getMonth() - a.getMonth()) - (b.getDate() < a.getDate() ? 1 : 0);
  }

  const api = { reparto, maxDesviacion, mesesHasta, aportacionNecesaria, mesesEntre };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else raiz.Asignacion = api;
})(typeof window !== "undefined" ? window : globalThis);
