// Auditoría de contraste en la app real (V5). Uso: PATRIMONIO_DATOS=<demo> PATRIMONIO_PUERTO=8791 python -m app  y luego
//   NODE_PATH=$(npm root -g) node docs/auto/contraste_vivo.js
// Requiere Playwright. No va en CI.
const { chromium } = require("playwright");
const fn = () => {
  const parse = s => { const m = s.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
  const over = (f, b) => ({ r: f.r * f.a + b.r * (1 - f.a), g: f.g * f.a + b.g * (1 - f.a), b: f.b * f.a + b.b * (1 - f.a), a: 1 });
  const lin = c => { c /= 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
  const lum = c => 0.2126 * lin(c.r) + 0.7152 * lin(c.g) + 0.0722 * lin(c.b);
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const fondo = el => { const capas = []; for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c && c.a > 0) { capas.push(c); if (c.a >= 1) break; } } let b = parse(getComputedStyle(document.documentElement).backgroundColor) || { r: 255, g: 255, b: 255, a: 1 }; if (b.a < 1) b = over(b, { r: 255, g: 255, b: 255, a: 1 }); for (const c of capas.reverse()) b = over(c, b); return b; };
  const out = [];
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const vistos = new Set();
  while (w.nextNode()) {
    const t = w.currentNode; if (!t.textContent.trim()) continue;
    const e = t.parentElement; if (!e || vistos.has(e)) continue; vistos.add(e);
    const r = e.getBoundingClientRect(); if (r.width < 1 || r.height < 1) continue;
    const cs = getComputedStyle(e); if (cs.visibility === "hidden" || cs.display === "none") continue;
    let op = 1; for (let x = e; x; x = x.parentElement) op *= +getComputedStyle(x).opacity;
    const fg = parse(cs.color); if (!fg) continue;
    const bg = fondo(e); const f = over({ ...fg, a: fg.a * op }, bg);
    const px = parseFloat(cs.fontSize), gordo = px >= 24 || (px >= 18.66 && +cs.fontWeight >= 700);
    const min = gordo ? 3 : 4.5, rr = ratio(f, bg);
    if (rr < min) out.push({ txt: t.textContent.trim().slice(0, 30), cls: e.className && e.className.baseVal === undefined ? e.className : "", tag: e.tagName, ratio: +rr.toFixed(2), min });
  }
  return out;
};
(async () => {
  const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" });
  const todos = {};
  for (const tema of ["oscuro", "claro"]) {
    const p = await (await b.newContext({ viewport: { width: 1280, height: 900 } })).newPage();
    await p.goto("http://127.0.0.1:8791/"); await p.waitForTimeout(1200);
    await p.evaluate(t => { if (t === "claro") document.documentElement.setAttribute("data-tema", "claro"); else document.documentElement.removeAttribute("data-tema"); }, tema);
    await p.evaluate(() => { document.querySelector(".filtro:not(.preset)")?.click(); });
    await p.waitForTimeout(300);
    for (const tab of ["Resumen","Posiciones","Rendimiento","Riesgo y deuda","Mes a mes","Planificación","Fiscalidad","Datos","Ayuda"]) {
      await p.evaluate(t => [...document.querySelectorAll("[role=tab],button,a")].find(x => x.textContent.trim() === t)?.click(), tab);
      await p.waitForTimeout(500);
      const f = await p.evaluate(fn);
      f.forEach(x => { const k = `${tema}|${x.tag}.${x.cls}|${x.min}`; (todos[k] = todos[k] || { n: 0, peor: 99, ej: x.txt, tabs: new Set() }); todos[k].n++; todos[k].peor = Math.min(todos[k].peor, x.ratio); todos[k].tabs.add(tab); });
    }
  }
  for (const [k, v] of Object.entries(todos).sort((a, b) => a[1].peor - b[1].peor)) console.log(k, "n=" + v.n, "peor=" + v.peor, "«" + v.ej + "»", [...v.tabs].join(","));
  console.log("grupos con fallo:", Object.keys(todos).length);
  await b.close();
})();
