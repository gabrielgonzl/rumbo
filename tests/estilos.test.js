// Ejecutar con:  node tests/estilos.test.js
const assert = require("node:assert/strict");
const { filtra } = require("../app/web/estilos.js");
const k = t => filtra(t).map(d => d[0]);

// Lo que la interfaz usa pasa tal cual.
assert.deepEqual(filtra("margin-top:12px; text-align:left"), [["margin-top", "12px"], ["text-align", "left"]]);
assert.deepEqual(filtra("background:var(--s3)"), [["background", "var(--s3)"]]);
assert.deepEqual(filtra("--c:var(--s2)"), [["--c", "var(--s2)"]]);
assert.deepEqual(filtra("width:42.5%"), [["width", "42.5%"]]);
assert.deepEqual(filtra("display:flex;gap:8px;flex-wrap:wrap;align-items:center"), [["display", "flex"], ["gap", "8px"], ["flex-wrap", "wrap"], ["align-items", "center"]]);

// Lo que permitiría suplantar o mover la interfaz, no.
assert.deepEqual(k("position:fixed;inset:0;z-index:9999;top:0;margin-top:4px"), ["margin-top"]);
assert.deepEqual(k("transform:scale(9);opacity:0;pointer-events:none;visibility:hidden"), []);
assert.deepEqual(k("POSITION : fixed"), []);                                   // sin importar mayúsculas ni espacios

// Valores que cargan recursos o escapan, no.
assert.deepEqual(k("background:url(https://malo.example/x.png)"), []);
assert.deepEqual(k("background: URL( data:image/png;base64,AAA )"), []);
assert.deepEqual(k("color:expression(alert(1))"), []);
assert.deepEqual(k("background:\\75rl(x)"), []);
assert.deepEqual(k("color:red @import"), []);

// Basura: sin dos puntos, valor vacío, undefined.
assert.deepEqual(filtra("color"), []);
assert.deepEqual(filtra("color:"), []);
assert.deepEqual(filtra(undefined), []);
assert.deepEqual(filtra(""), []);
console.log("estilos.test.js: todo bien");
