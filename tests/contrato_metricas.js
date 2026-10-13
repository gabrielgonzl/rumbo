// Uso: node tests/contrato_metricas.js datos.json
// Comprueba que las métricas del navegador (metricas.js) coinciden con las del servidor (D.total).
const fs = require("node:fs");
const assert = require("node:assert/strict");
const M = require("../app/web/metricas.js");

const txt = fs.readFileSync(process.argv[2], "utf8");
const D = JSON.parse(txt);
const TODOS = D.productos.concat(D.otrosActivos || [], D.pasivos || []);
const cerca = (a, b, t, et) => assert.ok(Math.abs(a - b) <= t, `${et}: navegador ${a} != servidor ${b}`);

const m = M.calcula(D, TODOS);
cerca(m.valor, D.total.patrimonio, 0.01, "patrimonio");
cerca(m.aportado, D.total.aportado, 0.01, "aportado");
cerca(m.caida, D.total.caidaMaxima, 1e-4, "peor caída del valor");
cerca(m.ritmo, D.total.ritmoMensual, 0.01, "ritmo mensual");
assert.equal(m.racha, D.total.racha, "racha");
if (m.tir != null && D.total.tir != null) cerca(m.tir, D.total.tir, 1e-4, "TIR");

// Una deuda derivada y su dinero recibido se filtran siempre juntos.
const g = M.grupos(TODOS);
TODOS.filter(p => p.derivado).forEach(p => assert.ok(g[p.id] && g[p.id].includes(p.id)));
const deuda = TODOS.find(p => p.derivado && p.tipoClave === "deuda");
const efectivo = TODOS.find(p => p.derivado && p.tipoClave === "efectivo");
if (deuda && efectivo) assert.deepEqual(new Set(g[deuda.id]), new Set(g[efectivo.id]));

// Quitar la deuda SIN su contrapartida es justo lo que provocó la falsa caída del −18 %: el grupo lo evita.
if (deuda && efectivo) {
  const sinDeudaSola = TODOS.filter(p => !(g[deuda.id] || []).includes(p.id));
  const sinTodo = M.calcula(D, sinDeudaSola);
  const caidaIncoherente = M.calcula(D, TODOS.filter(p => p.id !== deuda.id));
  assert.ok(caidaIncoherente.caida <= sinTodo.caida + 1e-9, "quitar solo la deuda no debería mejorar la caída");
}
console.log("contrato_metricas.js: servidor y navegador coinciden");
