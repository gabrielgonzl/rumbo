// Ejecutar con:  node tests/graficos.test.js
// graficos.js cuelga de `window`; para las funciones puras basta un objeto vacío.
const assert = require("node:assert/strict");
global.window = {};
require("../app/web/graficos.js");
const G = window.G;

// 1. Resumen de serie temporal: rango, series y último valor.
let t = G.descSerie("Líneas", "2026-01", "2026-10", ["Fondo A", "Fondo B"], "1.000 €");
assert.equal(t, "Líneas, de ene 26 a oct 26. Series: Fondo A, Fondo B. Último valor: 1.000 €.");

// 1b. Las fechas completas salen legibles.
assert.ok(G.descSerie("Línea", "2026-09-02", "2026-09-13", null, null).includes("de 2 sep 2026 a 13 sep 2026"));

// 2. Sin rango ni series no inventa nada.
assert.equal(G.descSerie("Minigráfico", null, null, null, null), "Minigráfico.");

// 3. Un solo punto no dice «de X a X».
assert.equal(G.descSerie("Línea", "a", "a", null, null), "Línea (a).");

// 4. Reparto: porcentajes sobre el total, sin importes (vale también para la web «sin importes»).
t = G.descReparto([{ nombre: "Renta variable", valor: 750 }, { nombre: "Renta fija", valor: 250 }]);
assert.ok(t.includes("Renta variable 75 %") && t.includes("Renta fija 25 %"), t);
assert.ok(!/€/.test(t), "el reparto no debe llevar importes");

console.log("graficos.test.js: todo bien");
