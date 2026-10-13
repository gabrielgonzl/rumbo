// Ejecutar con:  node tests/montecarlo.test.js
const assert = require("node:assert/strict");
const M = require("../app/web/montecarlo.js");
const cerca = (a, b, t, et = "") => assert.ok(Math.abs(a - b) <= t, `${et} ${a} != ${b}`);

const base = { cartera: 10000, garantia: 6000, deuda: null, aportacion: 0, anos: 5, mu: 0.06, sigma: 0.15, n: 3000, semilla: 7 };

// 1. Sin volatilidad la trayectoria es determinista y coincide con el interés compuesto.
const d = M.simula({ ...base, sigma: 0, aportacion: 100, n: 50 });
const esperado = (() => { let v = 10000; const i = Math.exp(0.06 / 12); for (let m = 0; m < 60; m++) v = v * i + 100; return v; })();
cerca(d.p50[60], esperado, 1, "determinista");
cerca(d.p10[60], d.p90[60], 1e-6, "sin dispersión");

// 2. Reproducible con semilla; distinta con otra.
const a = M.simula(base), b = M.simula(base), c = M.simula({ ...base, semilla: 99 });
assert.deepEqual(a.p50, b.p50);
assert.notDeepEqual(a.p50, c.p50);

// 3. Orden de percentiles y apertura creciente en el tiempo.
for (let m = 0; m <= 60; m++) assert.ok(a.p10[m] <= a.p50[m] && a.p50[m] <= a.p90[m]);
assert.ok(a.p90[60] - a.p10[60] > a.p90[12] - a.p10[12]);

// 4. La mediana está cerca de e^(mu·t) (con la corrección -σ²/2 la mediana del precio no se mueve de ahí).
cerca(a.p50[60] / 10000, Math.exp(0.06 * 5 - 0.5 * 0.15 * 0.15 * 5 * 0) , 0.2, "orden de magnitud");

// 5. Riesgo del préstamo: más volatilidad → más probabilidad de tocar el límite; sin deuda → null.
const deuda = Array.from({ length: 61 }, (_, m) => 5000 - 50 * m);
const r1 = M.simula({ ...base, deuda, ltvMax: 0.9, sigma: 0.10, sigmaGarantia: 0.10 });
const r2 = M.simula({ ...base, deuda, ltvMax: 0.9, sigma: 0.30, sigmaGarantia: 0.30 });
assert.ok(r2.probLimite > r1.probLimite, `${r2.probLimite} <= ${r1.probLimite}`);
assert.ok(r1.probLimite >= 0 && r2.probLimite <= 1);
assert.equal(M.simula({ ...base, ltvMax: 0.9 }).probDeudaMayor, null);
assert.equal(M.simula(base).probLimite, null);

// 6. Con la garantía holgada nunca se toca el límite.
const holgada = M.simula({ ...base, garantia: 100000, deuda, ltvMax: 0.8, sigma: 0.2, sigmaGarantia: 0.2 });
assert.equal(holgada.probLimite, 0);
assert.equal(holgada.probDeudaMayor, 0);

// 7. Volatilidad de un índice sintético: ±1 % alterno diario ≈ 15,9 % anual; datos escasos → null.
const idx = [100]; for (let i = 0; i < 300; i++) idx.push(idx[i] * (i % 2 ? 0.99 : 1.01));
cerca(M.volatilidad(idx), 0.01 * Math.sqrt(252), 0.01, "volatilidad");
assert.equal(M.volatilidad([100, 101]), null);

console.log("montecarlo.test.js: todo bien");
