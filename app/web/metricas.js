/* metricas.js · Métricas de un conjunto de componentes (sin DOM, para poder probarlo).
   Es la ÚNICA implementación del navegador: valor, aportado, plusvalía, TIR, ritmo, racha y caída.
   Se carga como window.Metricas y en Node con require(). */
(function (raiz) {
  "use strict";

  const ANO = 365 * 24 * 3600 * 1000;

  /* TIR (XIRR) de [{t: milisegundos, v: importe}]. Negativo = aportación, positivo = valor. */
  function xirr(flujos) {
    const f = flujos.filter(x => x.v);
    if (f.length < 2) return null;
    if (!(f.some(x => x.v < 0) && f.some(x => x.v > 0))) return null;
    const t0 = Math.min.apply(null, f.map(x => x.t));
    const van = tasa => {
      const base = 1 + tasa;
      if (base <= 1e-9) return Infinity;
      let s = 0;
      for (const x of f) s += x.v / Math.pow(base, (x.t - t0) / ANO);
      return s;
    };
    let lo = -0.9999, hi = 10, vlo = van(lo), vhi = van(hi);
    if (!isFinite(vlo) || !isFinite(vhi) || vlo * vhi > 0) return null;
    for (let i = 0; i < 200; i++) {
      const mid = (lo + hi) / 2, vm = van(mid);
      if (Math.abs(vm) < 1e-7) return mid;
      if (vlo * vm <= 0) hi = mid; else { lo = mid; vlo = vm; }
    }
    return (lo + hi) / 2;
  }

  /* Los 12 meses naturales que terminan en el mes de 'fechaIso' (YYYY-MM). */
  function ultimos12Meses(fechaIso) {
    let y = +fechaIso.slice(0, 4), m = +fechaIso.slice(5, 7);
    const out = [];
    for (let i = 0; i < 12; i++) {
      out.push(y + "-" + String(m).padStart(2, "0"));
      m--; if (m === 0) { m = 12; y--; }
    }
    return out;
  }

  /*
    D = los datos del servidor (window.DATOS); lista = componentes a medir;
    op.valorDe(p) = valor de un componente (por defecto p.valor; permite el precio en vivo).
  */
  function calcula(D, lista, op) {
    const valorDe = (op && op.valorDe) || (p => p.valor || 0);
    const n = D.fechas.length;
    const serie = new Array(n).fill(0);
    const serieAp = new Array(n).fill(0);
    let valor = 0, aportado = 0, valorConCoste = 0, valorTir = 0, nAp = 0;
    const flujos = [];

    lista.forEach(p => {
      const s = p.serie || [], sa = p.serieAportado || [];
      for (let i = 0; i < n; i++) {
        if (s[i] != null) serie[i] += s[i];
        if (sa[i] != null) serieAp[i] += sa[i];
      }
      valor += valorDe(p);
      if (p.aportado != null && p.aportado > 0) {
        aportado += p.aportado;
        valorConCoste += valorDe(p);
        nAp += (p.aportaciones || []).filter(a => a.importe).length;
      }
      // La TIR usa todo el dinero que entró y salió (compras, ventas, dividendos y
      // comisiones), y solo el valor de los productos que tienen esos movimientos.
      if (p.flujos && p.flujos.length) {
        p.flujos.forEach(([f, v]) => flujos.push({ t: Date.parse(f), v }));
        valorTir += valorDe(p);
      }
    });

    const plusvalia = aportado ? valorConCoste - aportado : null;
    const tir = flujos.length
      ? xirr(flujos.concat([{ t: Date.parse(D.fechaExtracto), v: valorTir }]))
      : null;

    // Aportaciones por mes natural de este conjunto de componentes.
    const am = D.aportacionesMensuales;
    const ids = new Set(lista.map(p => p.id));
    const porMes = {};
    am.meses.forEach((m, i) => {
      porMes[m] = Object.keys(am.porProducto)
        .reduce((a, id) => a + (ids.has(id) ? (am.porProducto[id][i] || 0) : 0), 0);
    });
    // Ritmo: lo aportado en los últimos 12 meses naturales entre 12 (un mes sin aportar cuenta como 0).
    const ritmo = ultimos12Meses(D.fechaExtracto).reduce((a, m) => a + (porMes[m] || 0), 0) / 12;

    const mesesConAp = am.meses.filter(m => porMes[m] > 0);
    let racha = 0;
    if (mesesConAp.length) {
      const set = new Set(mesesConAp);
      const ult = mesesConAp[mesesConAp.length - 1].split("-");
      let y = +ult[0], mo = +ult[1];
      while (set.has(y + "-" + String(mo).padStart(2, "0"))) {
        racha++; mo--; if (mo === 0) { mo = 12; y--; }
      }
    }

    // Caída del valor de ESTE conjunto (incluye aportaciones y ventas). La caída de la rentabilidad
    // (TWR) de toda la cartera la calcula el servidor: D.total.caidaMaximaTwr.
    let pico = 0, caida = 0, caidaFecha = null;
    for (let i = 0; i < n; i++) {
      pico = Math.max(pico, serie[i]);
      if (pico > 0) {
        const c = serie[i] / pico - 1;
        if (c < caida) { caida = c; caidaFecha = D.fechas[i]; }
      }
    }

    return {
      valor, aportado, valorConCoste, plusvalia,
      rentabilidad: aportado ? plusvalia / aportado : null,
      tir, numAportaciones: nAp, ritmo, racha, caida, caidaFecha,
      serie, serieAportado: serieAp,
    };
  }

  /*
    Grupos que no se pueden separar: una deuda y el dinero que recibiste con ella van juntos,
    porque si no la vista filtrada enseñaría un patrimonio inflado o hundido.
    Devuelve {id de componente: [ids del grupo]}.
  */
  function grupos(lista) {
    const g = {};
    const base = lista.filter(p => p.derivado);
    const clave = p => String(p.id).replace(/_efectivo$/, "");
    base.forEach(p => {
      const k = clave(p);
      g[k] = g[k] || [];
      g[k].push(p.id);
    });
    const out = {};
    Object.values(g).forEach(ids => ids.forEach(id => { out[id] = ids; }));
    return out;
  }

  const api = { xirr, calcula, ultimos12Meses, grupos };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else raiz.Metricas = api;
})(typeof window !== "undefined" ? window : globalThis);
