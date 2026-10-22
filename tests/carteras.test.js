// Ejecutar con:  node tests/carteras.test.js
const assert = require("node:assert/strict");
const C = require("../app/web/carteras.js");

const fila = (id, carteraId, valor, plus, peso = 0) => ({ id, p: { carteraId }, valor, plus, peso, pct: null });
const carteras = [{ id: "c1", nombre: "Cartera Ejemplo", entidad: "Entidad Ejemplo", ltvMax: 50 }, { id: "c2", nombre: "Otra" }];

// 1. Suma de valor, peso y plusvalía; rentabilidad = plusvalía / coste cuando todos los fondos tienen coste.
let g = C.agrupa([fila("a", "c1", 600, 100, 0.3), fila("b", "c1", 400, -50, 0.2)], carteras);
assert.equal(g.length, 1);
assert.equal(g[0].id, "c1"); assert.equal(g[0].nombre, "Cartera Ejemplo"); assert.equal(g[0].ltvMax, 50);
assert.equal(g[0].valor, 1000); assert.equal(g[0].peso, 0.5); assert.equal(g[0].plus, 50);
assert.ok(Math.abs(g[0].pct - 50 / 950) < 1e-12, String(g[0].pct));      // coste = 1000 - 50
assert.equal(g[0].filas.length, 2);

// 2. Si a algún fondo le falta la plusvalía, la de la línea y su rentabilidad son null: no se enseña un parcial como si fuera el total.
g = C.agrupa([fila("a", "c1", 600, 100), fila("b", "c1", 400, null)], carteras);
assert.equal(g[0].pct, null); assert.equal(g[0].plus, null);
// ...y si ninguno la tiene, plus es null.
g = C.agrupa([fila("a", "c1", 600, null)], carteras);
assert.equal(g[0].plus, null); assert.equal(g[0].pct, null);

// 3. Sin cartera, o con una cartera desconocida, va a «Sin cartera».
g = C.agrupa([fila("a", undefined, 10, 1), fila("b", "zz", 20, 2)], carteras);
assert.equal(g.length, 1); assert.equal(g[0].id, C.SIN); assert.equal(g[0].nombre, "Sin cartera"); assert.equal(g[0].valor, 30);

// 4. Una cartera sin filas no aparece; el orden es por valor descendente y «Sin cartera» siempre al final.
g = C.agrupa([fila("a", "c2", 100, 0), fila("b", undefined, 5000, 0), fila("c", "c1", 300, 0)], carteras);
assert.deepEqual(g.map(x => x.id), ["c1", "c2", C.SIN]);

// 5. Entrada vacía o sin lista de carteras.
assert.deepEqual(C.agrupa([], carteras), []);
assert.deepEqual(C.agrupa([fila("a", "c1", 1, 0)], undefined).map(x => x.id), [C.SIN]);

// 6. No muta la entrada y tolera un coste no positivo (valor - plus <= 0 → pct null).
const entrada = [fila("a", "c1", 100, 100)];
g = C.agrupa(entrada, carteras);
assert.equal(g[0].pct, null);
assert.equal(entrada[0].p.carteraId, "c1");

// 7. LTV sugerido en el formulario del préstamo: espejo de pignoracion.ltv_sugerido (solo carteras, todas con el mismo LTV).
const cs = [{ id: "c1", ltvMax: 50 }, { id: "c2", ltvMax: 50 }, { id: "c3", ltvMax: 60 }, { id: "c4" }];
assert.equal(C.ltvSugerido(["c1"], 0, cs), 50);
assert.equal(C.ltvSugerido(["c1", "c2"], 0, cs), 50);
assert.equal(C.ltvSugerido(["c1", "c3"], 0, cs), null);          // distintos: ni media ni el menor
assert.equal(C.ltvSugerido(["c1"], 2, cs), null);                // con fondos sueltos: sin indicar
assert.equal(C.ltvSugerido(["c4"], 0, cs), null);                // cartera sin LTV
assert.equal(C.ltvSugerido(["c1", "c4"], 0, cs), null);
assert.equal(C.ltvSugerido([], 0, cs), null);
assert.equal(C.ltvSugerido(["zz"], 0, cs), null);
assert.equal(C.ltvSugerido(["c1"], 0, undefined), null);

// 8. Texto de la garantía de un préstamo (sin escapar: quien lo pinta lo escapa).
const g1 = (nc, sueltos, total) => ({ carterasDetalle: nc.map(n => ({ nombre: n })), activosSueltos: new Array(sueltos).fill("x"), activosDetalle: new Array(total).fill({}) });
assert.equal(C.textoGarantia(g1([], 0, 1)), "1 activo");
assert.equal(C.textoGarantia(g1([], 0, 3)), "3 activos");
assert.equal(C.textoGarantia(g1(["Cartera Ejemplo"], 0, 3)), "Cartera Ejemplo");
assert.equal(C.textoGarantia(g1(["A", "B"], 0, 4)), "A + B");
assert.equal(C.textoGarantia(g1(["Cartera Ejemplo"], 1, 4)), "Cartera Ejemplo + 1 fondo suelto");
assert.equal(C.textoGarantia(g1(["Cartera Ejemplo"], 2, 5)), "Cartera Ejemplo + 2 fondos sueltos");
assert.equal(C.textoGarantia({ activosDetalle: [{}] }), "1 activo");   // datos antiguos, sin los campos nuevos

// 9. Búsqueda en Posiciones: por fondo (nombre, identificador, clase) y también por nombre o entidad de su cartera.
const bf = (nombre, carteraId, extra = {}) => ({ p: Object.assign({ nombre, carteraId }, extra), clase: extra.clase || "" });
const cc = [{ id: "c1", nombre: "Cartera Ejemplo", entidad: "Entidad Ejemplo" }];
assert.equal(C.coincide(bf("MSCI World", "c1"), "world", cc), true);
assert.equal(C.coincide(bf("MSCI World", "c1"), "ejemplo", cc), true);          // por la cartera
assert.equal(C.coincide(bf("MSCI World", "c1"), "entidad", cc), true);          // por la entidad de la cartera
assert.equal(C.coincide(bf("MSCI World", undefined), "ejemplo", cc), false);    // suelto: la cartera no cuenta
assert.equal(C.coincide(bf("MSCI World", "c1", { identificador: "IE00BYX5NX33" }), "ie00byx5", cc), true);
assert.equal(C.coincide(bf("MSCI World", "c1", { clase: "Renta variable" }), "renta", cc), true);
assert.equal(C.coincide(bf("MSCI World", "c1"), "bitcoin", cc), false);
assert.equal(C.coincide(bf("MSCI World", "c1"), "", cc), true);                  // sin búsqueda, todo
assert.equal(C.coincide(bf("MSCI World", "zz"), "ejemplo", cc), false);          // cartera desconocida
assert.equal(C.coincide(bf("MSCI World", "c1"), "ejemplo", undefined), false);

// 10. TIR de la línea: la combinada que calcula el servidor, solo si están a la vista TODOS los fondos de la cartera
// (con un filtro activo no es la de lo que se ve, así que null) y nunca para «Sin cartera».
const ct = [{ id: "c1", nombre: "A", fondos: 2, tir: 0.0875 }, { id: "c2", nombre: "B", fondos: 1, tir: null }];
g = C.agrupa([fila("a", "c1", 600, 100), fila("b", "c1", 400, 50)], ct);
assert.equal(g[0].tir, 0.0875);
g = C.agrupa([fila("a", "c1", 600, 100)], ct);                       // un fondo filtrado: faltan datos
assert.equal(g[0].tir, null);
g = C.agrupa([fila("a", "c2", 600, 100)], ct);                       // el servidor no pudo calcularla
assert.equal(g[0].tir, null);
g = C.agrupa([fila("a", undefined, 600, 100)], ct);
assert.equal(g[0].tir, null);
g = C.agrupa([fila("a", "c1", 600, 100), fila("b", "c1", 400, 50)], [{ id: "c1", nombre: "A" }]);   // datos sin los campos nuevos
assert.equal(g[0].tir, null);

console.log("carteras.test.js: todo bien");
