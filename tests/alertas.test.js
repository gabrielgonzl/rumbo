// Ejecutar con:  node tests/alertas.test.js
const assert = require("node:assert/strict");
const A = require("../app/web/alertas.js");

const base = { fechaExtracto: "2026-10-13", ahora: Date.parse("2026-10-13T12:00:00Z"), estatico: false, demo: false, ocultas: {}, filtrando: false };
const pig = o => Object.assign({ id: "p1", nombre: "Préstamo", estado: "activa", nivel: "bajo", ratio: 0.3, ltvMax: 70, superaLimite: false }, o);
const run = (o) => A.calcula(Object.assign({}, base, o));
const tipos = r => r.alertas.map(a => a.tipo + (a.sub ? ":" + a.sub : ""));

// Holgado: no hay alerta.
assert.deepEqual(tipos(run({ pignoraciones: [pig()] })), []);

// Préstamo sin límite a 92 %: atención, sin ser «límite superado».
let r = run({ pignoraciones: [pig({ nivel: "alto", ratio: 0.92, ltvMax: null, caidaHastaIgualar: 0.08 })] });
assert.deepEqual(tipos(r), ["ltv:atencion"]);
assert.equal(r.alertas[0].cl, "warn");
assert.equal(r.alertas[0].ir, "riesgo");

// Con límite superado: peligro con importes.
r = run({ pignoraciones: [pig({ nivel: "peligro", superaLimite: true, ratio: 0.8, amortizarParaLimite: 500 })] });
assert.deepEqual(tipos(r), ["ltv:limite"]);
assert.equal(r.alertas[0].cl, "danger");

// Deuda mayor que la garantía.
r = run({ pignoraciones: [pig({ nivel: "peligro", superaLimite: false, ratio: 1.1, ltvMax: null })] });
assert.deepEqual(tipos(r), ["ltv:deuda"]);

// Una liquidada nunca avisa.
assert.deepEqual(tipos(run({ pignoraciones: [pig({ estado: "liquidada", nivel: "peligro", superaLimite: true })] })), []);

// Descartada: no sale; al cambiar de nivel la clave cambia y vuelve a salir.
const p92 = pig({ nivel: "alto", ratio: 0.92, ltvMax: null });
const clave = run({ pignoraciones: [p92] }).alertas[0].clave;
assert.deepEqual(tipos(run({ pignoraciones: [p92], ocultas: { [clave]: 1 } })), []);
const p100 = pig({ nivel: "peligro", ratio: 1.02, ltvMax: null });
r = run({ pignoraciones: [p100], ocultas: { [clave]: 1 } });
assert.deepEqual(tipos(r), ["ltv:deuda"]);
assert.notEqual(r.alertas[0].clave, clave);
// El mismo nivel con el ratio casi igual sigue descartado (misma clave).
assert.deepEqual(tipos(run({ pignoraciones: [pig({ nivel: "alto", ratio: 0.921, ltvMax: null })], ocultas: { [clave]: 1 } })), []);

// Cuota en 7 días: sale (hoy, 7); a 8 días o pasada, no.
const conCuota = f => pig({ proxima: { fecha: f, cuota: 300 } });
r = run({ pignoraciones: [conCuota("2026-10-20")] });
assert.deepEqual(tipos(r), ["cuota"]);
assert.equal(r.alertas[0].dias, 7);
assert.equal(run({ pignoraciones: [conCuota("2026-10-13")] }).alertas[0].dias, 0);
assert.deepEqual(tipos(run({ pignoraciones: [conCuota("2026-10-21")] })), []);
assert.deepEqual(tipos(run({ pignoraciones: [conCuota("2026-10-12")] })), []);

// S2: en la app real la cuota se mide contra HOY, no contra la fecha de la valoración (que puede ser antigua).
const hoyReal = Date.parse("2026-10-18T12:00:00Z");
assert.deepEqual(tipos(run({ fechaExtracto: "2026-09-01", ahora: hoyReal, pignoraciones: [conCuota("2026-10-20")] })), ["cuota"]);
assert.equal(run({ fechaExtracto: "2026-09-01", ahora: hoyReal, pignoraciones: [conCuota("2026-10-20")] }).alertas[0].dias, 2);
// Con valoración antigua y cuota lejana de hoy, no avisa aunque esté cerca de la valoración.
assert.deepEqual(tipos(run({ fechaExtracto: "2026-10-15", ahora: hoyReal, pignoraciones: [conCuota("2026-10-20")] })), ["cuota"]);
assert.deepEqual(tipos(run({ fechaExtracto: "2026-10-15", ahora: Date.parse("2026-10-01T12:00:00Z"), pignoraciones: [conCuota("2026-10-20")] })), []);
// En la web exportada (una foto) manda la fecha de la valoración.
assert.deepEqual(tipos(run({ estatico: true, fechaExtracto: "2026-10-15", ahora: hoyReal, pignoraciones: [conCuota("2026-10-20")] })), ["cuota"]);
assert.deepEqual(tipos(run({ estatico: true, fechaExtracto: "2026-09-01", ahora: hoyReal, pignoraciones: [conCuota("2026-10-20")] })), []);

// S1: sin fechaExtracto no hay «NaN días».
r = run({ fechaExtracto: undefined, avisos: ["MSCI World: el último precio que tengo es del 2026-09-20 (hace 23 días)"] });
assert.equal(r.alertas.find(a => a.tipo === "viejo").dias, 23);
r = run({ fechaExtracto: undefined, ahora: undefined, avisos: ["MSCI World: el último precio que tengo es del 2026-09-20 (hace 23 días)"] });
assert.equal(r.alertas.find(a => a.tipo === "viejo").dias, null);
assert.deepEqual(tipos(run({ fechaExtracto: undefined, ahora: undefined, pignoraciones: [conCuota("2026-10-20")] })), []);

// Precio desactualizado y sin conexión.
const avisos = [
  "MSCI World: el último precio que tengo es del 2026-09-20 (hace 23 días)",
  "BTC-EUR: sin conexion y sin cache",
  "Otra cosa general",
];
r = run({ avisos });
assert.deepEqual(tipos(r).sort(), ["sinRed", "viejo"]);
const viejo = r.alertas.find(a => a.tipo === "viejo");
assert.equal(viejo.dias, 23);
assert.equal(viejo.accion, "actualizar");
assert.deepEqual(A.clasificaAvisos(avisos).otros, ["Otra cosa general"]);

// Precios generales de hace días: una sola alerta, y no si ya hay avisos por precio.
const antiguo = "2026-10-10T08:00:00+00:00";
assert.deepEqual(tipos(run({ preciosActualizados: antiguo })), ["datosViejos"]);
assert.deepEqual(tipos(run({ preciosActualizados: antiguo, avisos })).sort(), ["sinRed", "viejo"]);
assert.deepEqual(tipos(run({ preciosActualizados: "2026-10-13T08:00:00+00:00" })), []);
// En la demo no se pide actualizar.
assert.deepEqual(tipos(run({ preciosActualizados: antiguo, demo: true })), []);

// Vista filtrada: las alertas son de la cartera completa y se avisa de ello.
r = run({ pignoraciones: [p92], filtrando: true });
assert.equal(r.filtrada, true);
assert.equal(r.alertas.length, 1);
assert.equal(run({ pignoraciones: [p92] }).filtrada, false);

// Exportación estática: sin acciones de la app, sin descartar, sin «precios de hace días»,
// y las descartadas en el navegador del autor no se aplican.
r = run({ estatico: true, avisos, preciosActualizados: antiguo, pignoraciones: [p92, conCuota("2026-10-15")], ocultas: { [clave]: 1 } });
assert.ok(r.alertas.length >= 3);
assert.ok(r.alertas.every(a => !a.accion && a.descartable === false));
assert.ok(!r.alertas.some(a => a.tipo === "datosViejos"));
assert.ok(r.alertas.some(a => a.clave === clave));
assert.equal(r.descartables, false);

console.log("alertas.test.js: todo en orden");
