// Verificación en la app real de las carteras de fondos (pignorar una cartera). Requiere Playwright y una carpeta de datos
// con una cartera «Cartera Ejemplo» (LTV 50) que agrupe 3 fondos con valor manual; ver docs/superpowers/plans/2026-10-15-carteras-de-fondos.md.
//   PATRIMONIO_DATOS=<carpeta> PATRIMONIO_PUERTO=8791 python -m app   y luego   NODE_PATH=$(npm root -g) node docs/auto/carteras_vivo.js
const { chromium } = require("playwright");
(async () => {
  const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" });
  const p = await b.newPage({ viewport: { width: 1280, height: 1000 } }); const errs = [];
  p.on("console", m => m.type() === "error" && errs.push(m.text())); p.on("pageerror", e => errs.push(String(e)));
  p.on("dialog", d => { errs.push("DIALOG " + d.message()); d.accept(); });
  await p.addInitScript(() => document.addEventListener("securitypolicyviolation", e => console.error("CSP:", e.violatedDirective)));
  await p.goto("http://127.0.0.1:8791/"); await p.waitForTimeout(1500);
  const tab = n => p.evaluate(n => [...document.querySelectorAll("[role=tab]")].find(x => x.textContent.trim() === n).click(), n);
  const vista = n => p.evaluate(n => [...document.querySelectorAll("#edVistas button")].find(x => x.textContent.trim() === n).click(), n);
  await tab("Datos"); await p.waitForTimeout(500); await vista("Pignoraciones"); await p.waitForTimeout(300);
  await p.click("[data-acc=nuevaPig]"); await p.waitForTimeout(500);
  console.log("secciones:", await p.$$eval("dialog .secc", e => e.map(x => x.textContent)));
  console.log("placeholder inicial:", await p.$eval("dialog input[name=ltvMax]", e => e.placeholder));
  await p.locator("dialog input[name=cartera]").first().check(); await p.waitForTimeout(200);
  console.log("placeholder con cartera:", await p.$eval("dialog input[name=ltvMax]", e => e.placeholder));
  await p.locator("dialog input[name=activo]").last().check(); await p.waitForTimeout(200);
  console.log("placeholder con cartera + suelto:", await p.$eval("dialog input[name=ltvMax]", e => e.placeholder));
  await p.locator("dialog input[name=activo]").last().uncheck();
  await p.fill("dialog input[name=nombre]", "Préstamo con la cartera"); await p.fill("dialog input[name=principal]", "1.000,00"); await p.fill("dialog input[name=interes]", "5");
  await p.fill("dialog input[name=cuotas]", "12"); await p.fill("dialog input[name=fecha]", "2026-09-01"); await p.fill("dialog input[name=primerPago]", "2026-10-23");
  await p.click("dialog .btn.prim"); await p.waitForTimeout(9000);
  await tab("Datos"); await p.waitForTimeout(400); await vista("Pignoraciones"); await p.waitForTimeout(300);
  console.log("lista:", await p.$$eval("#edCuerpo tbody tr", e => e.map(r => r.innerText.replace(/\s+/g, " ").slice(0, 110))));
  await tab("Riesgo y deuda"); await p.waitForTimeout(600);
  const t = await p.evaluate(() => document.querySelector("#tab-riesgo").innerText.replace(/\s+/g, " "));
  console.log("riesgo:", (t.match(/Garantía hoy[^]{0,120}/) || [""])[0]);
  console.log("LTV/límite:", (t.match(/límite[^.]{0,90}/i) || [""])[0], "| zonas:", (t.match(/atención desde[^]{0,60}/) || [""])[0]);
  console.log("bloqueo:", /Bloqueo/.test(t), "insignias:", (await p.$$eval("#tab-riesgo .badge.lock", e => e.map(x => x.innerText.replace(/\s+/g, " ")))));
  await tab("Posiciones"); await p.waitForTimeout(400);
  console.log("🔒 en posiciones:", await p.$$eval("#tablaPos .badge.lock", e => e.length));
  console.log("data-st:", await p.evaluate(() => document.querySelectorAll("[data-st]").length), "ov:", await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "errores:", errs);
  await b.close();
})();
