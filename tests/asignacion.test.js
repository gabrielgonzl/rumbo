// Ejecutar con:  node tests/asignacion.test.js
const assert = require("node:assert/strict");
const A = require("../app/web/asignacion.js");
const cerca = (a, b, t = 0.011, et = "") => assert.ok(Math.abs(a - b) <= t, `${et} ${a} != ${b}`);
const suma = f => f.reduce((a, x) => a + x.sugerido, 0);

// 1. La suma de lo sugerido es SIEMPRE la aportación, al céntimo.
let f = A.reparto([{ id: "rv", valor: 7000, objetivo: 70 }, { id: "rf", valor: 3000, objetivo: 30 }], 1000);
cerca(suma(f), 1000);
// ya están en 70/30: la aportación se reparte 70/30
cerca(f[0].sugerido, 700); cerca(f[1].sugerido, 300);

// 2. Va primero a lo que está por debajo del objetivo.
f = A.reparto([{ id: "rv", valor: 8000, objetivo: 70 }, { id: "rf", valor: 2000, objetivo: 30 }], 1000);
// tras aportar: 11.000 -> RV debería tener 7.700 (ya tiene 8.000: no falta nada), RF 3.300 (faltan 1.300)
cerca(f[0].sugerido, 0); cerca(f[1].sugerido, 1000); cerca(suma(f), 1000);

// 3. Nunca sugiere vender: todos los grupos sobreponderados salvo uno.
f = A.reparto([{ id: "a", valor: 5000, objetivo: 20 }, { id: "b", valor: 5000, objetivo: 20 }, { id: "c", valor: 0, objetivo: 60 }], 600);
assert.ok(f.every(x => x.sugerido >= 0)); cerca(suma(f), 600);

// 4. Todas sobreponderadas: se reparte según el peso objetivo y la suma sigue cuadrando.
f = A.reparto([{ id: "a", valor: 9000, objetivo: 50 }, { id: "b", valor: 9000, objetivo: 50 }], 100);
cerca(suma(f), 100); cerca(f[0].sugerido, 50);

// 5. Grupos sin objetivo no reciben nada y la aportación 0 devuelve ceros.
f = A.reparto([{ id: "a", valor: 100, objetivo: 100 }, { id: "x", valor: 500, objetivo: null }], 0);
assert.ok(f.every(x => x.sugerido === 0));
f = A.reparto([{ id: "a", valor: 100, objetivo: 100 }, { id: "x", valor: 500, objetivo: null }], 50);
cerca(f[0].sugerido, 50); cerca(f[1].sugerido, 0);
assert.equal(f[1].desviacion, null);

// 6. Desviación en puntos y máxima.
f = A.reparto([{ id: "a", valor: 800, objetivo: 70 }, { id: "b", valor: 200, objetivo: 30 }], 0);
cerca(f[0].desviacion, 10, 1e-9); cerca(f[1].desviacion, -10, 1e-9); cerca(A.maxDesviacion(f), 10, 1e-9);

// 7. Meta: meses hasta llegar, y aportación necesaria (son inversas).
assert.equal(A.mesesHasta(100, 50, 10, 0.05), 0);
const m = A.mesesHasta(10000, 100000, 900, 0.07);
assert.ok(m > 60 && m < 100, `meses ${m}`);
const ap = A.aportacionNecesaria(10000, 100000, m, 0.07);
assert.ok(Math.abs(ap - 900) < 25, `aportación ${ap}`);
assert.equal(A.mesesHasta(0, 1e9, 0, 0), null);
assert.equal(A.aportacionNecesaria(100000, 50000, 12, 0.05), 0);
assert.equal(A.aportacionNecesaria(1000, 2000, 12, 0), 1000 / 12);

// 8. Meses naturales entre fechas.
assert.equal(A.mesesEntre("2026-10-12", "2030-12-31"), 50);
assert.equal(A.mesesEntre("2026-10-31", "2026-11-30"), 0);

console.log("asignacion.test.js: todo bien");
