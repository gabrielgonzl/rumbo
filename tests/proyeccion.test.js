// Ejecutar con:  node tests/proyeccion.test.js
const assert = require("node:assert/strict");
const P = require("../app/web/proyeccion.js");
const cerca = (a, b, t = 1e-6) => assert.ok(Math.abs(a - b) <= t, `${a} != ${b}`);

// 1. Rentabilidad implícita: duplicar en 7 años ≈ 10,41 % anual.
cerca(P.rentImplicita(10, 20, 7), Math.pow(2, 1 / 7) - 1);
assert.equal(P.rentImplicita(10, null, 7), null);
assert.equal(P.rentImplicita(0, 20, 7), null);

// 2. La media solo cuenta los activos con objetivo, ponderados por valor.
const A = [
  { id: "a", valor: 1000, precio: 10, objetivo: 20, tipo: "accion" },   // x2 en 1 año = +100 %
  { id: "b", valor: 3000, precio: 10, objetivo: 11, tipo: "accion" },   // +10 %
  { id: "c", valor: 6000, precio: 5, objetivo: null, tipo: "fondo" },   // vacío: no cuenta
];
cerca(P.mediaCartera(A, 1), (1000 * 1 + 3000 * 0.1) / 4000);
assert.equal(P.mediaCartera([A[2]], 1), null);

// 3. El precio objetivo se cumple justo al final del plazo.
const r = P.simula({ activos: A, anos: 3, modo: "activo", rentGlobal: 0.05, aportacion: 0 });
cerca(r.porActivo.a.final, 1000 * 2);
cerca(r.porActivo.b.final, 3000 * 1.1);
cerca(r.porActivo.c.final, 6000);                 // modo activo: el vacío se queda quieto
assert.equal(r.total.length, 3 * 12 + 1);

// 4. Mixto: el vacío usa la media de la cartera.
const x = P.simula({ activos: A, anos: 1, modo: "mixto", rentGlobal: 0.05, aportacion: 0 });
cerca(x.porActivo.c.rent, x.media);

// 5. Global: todos a la misma rentabilidad, objetivos ignorados.
const g = P.simula({ activos: A, anos: 2, modo: "global", rentGlobal: 0.07, aportacion: 0 });
cerca(g.cartera[24], 10000 * 1.07 ** 2);

// 6. Aportaciones: aparte, nunca atribuidas a un activo.
const ap = P.simula({ activos: A, anos: 1, modo: "activo", rentGlobal: 0, aportacion: 100 });
cerca(ap.porActivo.a.final, 2000);                // no cambian por aportar
cerca(ap.aportado[12], 1200);
cerca(ap.total[12], ap.cartera[12] + ap.aportaciones[12]);
assert.ok(ap.aportaciones[12] > 1200);             // crecen con la media (> 0 %)
cerca(ap.rentAportaciones, ap.media);

// 7. Sin ningún objetivo, las aportaciones usan la rentabilidad global.
const s = P.simula({ activos: [A[2]], anos: 1, modo: "mixto", rentGlobal: 0.06, aportacion: 100 });
assert.equal(s.media, null);
cerca(s.rentAportaciones, 0.06);

// 8. Efectivo sin objetivo no crece con la media.
const c = P.simula({ activos: [A[0], { id: "e", valor: 500, precio: 0, objetivo: null, tipo: "efectivo" }],
  anos: 1, modo: "mixto", rentGlobal: 0.05, aportacion: 0 });
cerca(c.porActivo.e.final, 500);
console.log("proyeccion.test.js: todo bien");
