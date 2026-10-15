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

// 5. Etiquetas directas: no se pisan, respetan los límites y conservan el orden de entrada.
let ys = G.separaEtiquetas([100, 102, 104], 14, 10, 300);
assert.ok(ys[1] - ys[0] >= 14 - 1e-9 && ys[2] - ys[1] >= 14 - 1e-9, String(ys));
assert.ok(ys.every(v => v >= 10 && v <= 300));
ys = G.separaEtiquetas([295, 298, 300], 14, 10, 300);          // pegadas al borde de abajo: se empujan hacia arriba
assert.ok(ys.every(v => v <= 300) && ys[2] - ys[1] >= 14 - 1e-9 && ys[1] - ys[0] >= 14 - 1e-9, String(ys));
ys = G.separaEtiquetas([200, 50], 14, 10, 300);                 // el orden de salida es el de entrada, no el de altura
assert.deepEqual(ys, [200, 50]);
assert.deepEqual(G.separaEtiquetas([], 14, 0, 100), []);

// 6. Nombre corto: sin paréntesis y con tope.
assert.equal(G.nombreCorto("Bueno (1 de cada 10 acaba por encima)", 17), "Bueno");
assert.equal(G.nombreCorto("Un nombre larguísimo de serie", 12), "Un nombre l…");

// 7. Tabla alternativa: muestreo (primera y última siempre, sin repetidos, tope) y formatos de las celdas.
assert.deepEqual(G.indicesMuestra(3, 24), [0, 1, 2]);
let ix = G.indicesMuestra(100, 24);
assert.ok(ix.length <= 24 && ix[0] === 0 && ix[ix.length - 1] === 99, String(ix));
assert.ok(ix.every((v, k) => k === 0 || v > ix[k - 1]));
assert.deepEqual(G.indicesMuestra(0, 24), []);
let tb = G.tSerie(["2026-01-05", "2026-02-05"], [{ nombre: "A", valores: [1, null] }, { nombre: "B", valores: [2, 3] }], v => v + " €", [3, 3]);
assert.deepEqual(tb.cab, ["Fecha", "A", "B", "Total"]);
assert.deepEqual(tb.filas[0], ["5 ene 2026", "1 €", "2 €", "3 €"]);
assert.equal(tb.filas[1][1], "—");                       // hueco, no «null» ni «undefined»
assert.equal(tb.nota, "");
tb = G.tSerie(Array.from({ length: 100 }, (_, i) => "2026-01-" + String(1 + (i % 28)).padStart(2, "0")), [{ nombre: "A", valores: new Array(100).fill(1) }], v => String(v));
assert.ok(tb.filas.length <= 24 && /de 100 fechas/.test(tb.nota), tb.nota);
tb = G.tReparto([{ nombre: "RV", valor: 750 }, { nombre: "RF", valor: 250 }]);
assert.deepEqual(tb.filas.map(f => f[2]), ["75,0 %", "25,0 %"]);
tb = G.tPares(["Categoría", "Valor"], ["2025", "2026"], [0.1, null], v => v * 100 + " %");
assert.deepEqual(tb.filas, [["2025", "10 %"], ["2026", "—"]]);
// Con «ocultar importes» las celdas de dinero no enseñan cantidades.
global.window.OCULTAR_IMPORTES = true;
assert.equal(G.tReparto([{ nombre: "RV", valor: 750 }]).filas[0][1], "•••");
global.window.OCULTAR_IMPORTES = false;

// 8. Nada que se redondee a cero lleva signo: ni «-0,00 %» ni «+-0,00 %».
assert.equal(G.fmtPctSigno(-0), "+0,00 %");
assert.equal(G.fmtPctSigno(-0.00001), "+0,00 %");
assert.equal(G.fmtPct(-0.00001, 2), "0,00 %");
assert.equal(G.fmtPctSigno(0.1234, 1), "+12,3 %");
assert.equal(G.fmtPctSigno(-0.0234, 1), "-2,3 %");
assert.equal(G.fmtPctSigno(-0.00004, 1), "+0,0 %");
assert.ok(!/-0,0/.test(G.fmtEur(-0.001)), G.fmtEur(-0.001));
assert.ok(!/-0/.test(G.fmtEur(-0.4, 0)), G.fmtEur(-0.4, 0));
assert.equal(G.fmtEurSigno(-0.001).startsWith("+"), true);
assert.ok(G.fmtEurSigno(-12.5).startsWith("-"));
assert.equal(G.fmtPct(null), "—");

console.log("graficos.test.js: todo bien");
