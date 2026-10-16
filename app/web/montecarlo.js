/* montecarlo.js · Simulación de trayectorias del patrimonio y del riesgo del préstamo
   (sin DOM, con semilla, probada con Node). window.Montecarlo / require().

   Modelo (a propósito simple y declarado): cada mes, la cartera y la garantía rinden
   exp(mu − σ²/2 + σ·Z) con Z normal, la MISMA Z para las dos (se mueven juntas); la aportación
   mensual entra en la cartera pero no en la garantía; la deuda sigue su cuadro.
   No es una predicción: enseña el orden de magnitud del riesgo, no un pronóstico. */
(function (raiz) {
  "use strict";

  // Generador reproducible (mulberry32) y normal estándar (Box-Muller).
  function rng(semilla) {
    let a = semilla >>> 0;
    return () => {
      a = (a + 0x6D2B79F5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function normal(u) {
    let x = 0, y = 0;
    while (x === 0) x = u();
    y = u();
    return Math.sqrt(-2 * Math.log(x)) * Math.cos(2 * Math.PI * y);
  }
  function percentil(ordenado, p) {
    if (!ordenado.length) return 0;
    const i = (ordenado.length - 1) * p;
    const lo = Math.floor(i), hi = Math.ceil(i);
    return ordenado[lo] + (ordenado[hi] - ordenado[lo]) * (i - lo);
  }

  /*
    e = {
      cartera,           // valor bruto invertido hoy
      garantia,          // valor hoy de los activos pignorados (≤ cartera)
      deuda,             // [saldo al final de cada mes 0..N] (puede ser null/[] si no hay préstamo)
      aportacion,        // € al mes (a la cartera)
      anos, mu, sigma,   // rentabilidad anual esperada y volatilidad anual de la cartera
      sigmaGarantia,     // volatilidad anual de la garantía (por defecto = sigma)
      muGarantia,        // por defecto = mu
      ltvMax,            // 0-1, límite de la entidad (opcional)
      n, semilla
    }
    Devuelve {meses, p10[], p50[], p90[] (patrimonio neto), probLimite, probDeudaMayor, peorLtv: {p50,p90}}
  */
  function simula(e) {
    const N = Math.round(e.anos * 12);
    const n = e.n || 2000;
    const u = rng(e.semilla == null ? 12345 : e.semilla);
    const mu = e.mu, sg = e.sigma, sgG = e.sigmaGarantia != null ? e.sigmaGarantia : e.sigma;
    const muG = e.muGarantia != null ? e.muGarantia : e.mu;
    const mP = mu / 12 - (sg * sg) / 24, vP = sg / Math.sqrt(12);
    const mG = muG / 12 - (sgG * sgG) / 24, vG = sgG / Math.sqrt(12);
    const deuda = e.deuda || null;
    const porMes = Array.from({ length: N + 1 }, () => new Float64Array(n));
    let tocaLimite = 0, deudaMayor = 0;
    const peor = new Float64Array(n);

    for (let k = 0; k < n; k++) {
      let P = e.cartera, G = e.garantia, hitL = false, hitD = false, maxLtv = 0;
      porMes[0][k] = P - (deuda ? deuda[0] : 0);
      for (let m = 1; m <= N; m++) {
        const z = normal(u);
        P = P * Math.exp(mP + vP * z) + e.aportacion;
        G = G * Math.exp(mG + vG * z);
        const d = deuda ? (deuda[m] || 0) : 0;
        porMes[m][k] = P - d;
        if (d > 0 && G > 0) {
          const ltv = d / G;
          if (ltv > maxLtv) maxLtv = ltv;
          if (e.ltvMax && ltv > e.ltvMax) hitL = true;
          if (ltv >= 1) hitD = true;
        } else if (d > 0 && G <= 0) { hitD = true; hitL = true; maxLtv = Infinity; }
      }
      if (hitL) tocaLimite++;
      if (hitD) deudaMayor++;
      peor[k] = maxLtv;
    }
    const p10 = [], p50 = [], p90 = [];
    for (let m = 0; m <= N; m++) {
      const arr = Array.from(porMes[m]).sort((a, b) => a - b);
      p10.push(percentil(arr, 0.10)); p50.push(percentil(arr, 0.50)); p90.push(percentil(arr, 0.90));
    }
    const ps = Array.from(peor).sort((a, b) => a - b);
    return { meses: N, p10, p50, p90, probLimite: e.ltvMax ? tocaLimite / n : null, probDeudaMayor: deuda ? deudaMayor / n : null,
      peorLtv: { p50: percentil(ps, 0.5), p90: percentil(ps, 0.9) } };
  }

  /* Volatilidad anual a partir de un índice diario (nivel base 100): desviación típica de los
     rendimientos diarios × √252. Ignora saltos absurdos (> ±25 % en un día). */
  function volatilidad(indice) {
    const r = [];
    for (let i = 1; i < indice.length; i++) {
      if (indice[i - 1] > 0 && indice[i] > 0) {
        const x = indice[i] / indice[i - 1] - 1;
        if (Math.abs(x) < 0.25) r.push(x);
      }
    }
    if (r.length < 20) return null;
    const m = r.reduce((a, b) => a + b, 0) / r.length;
    const v = r.reduce((a, b) => a + (b - m) * (b - m), 0) / (r.length - 1);
    return Math.sqrt(v) * Math.sqrt(252);
  }

  /* La simulación es determinista (semilla fija): con los mismos datos de entrada el resultado es el mismo,
     así que al volver a la pestaña o repintar no se vuelve a calcular. Guarda solo la última. */
  let ultima = { clave: null, res: null };
  function simulaMemo(e) {
    const clave = JSON.stringify(e);
    if (ultima.clave !== clave) ultima = { clave, res: simula(e) };
    return ultima.res;
  }

  const api = { simula, simulaMemo, volatilidad, rng };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else raiz.Montecarlo = api;
})(typeof window !== "undefined" ? window : globalThis);
