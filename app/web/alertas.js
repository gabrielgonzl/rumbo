/* alertas.js · Qué alertas salen en el Resumen y cuándo (sin DOM, para poder probarlo).
   Devuelve datos, no HTML: app.js pone los textos. Se carga como window.Alertas y en Node con require().

   Reglas:
     · Una alerta es algo accionable. La información permanente vive en su pantalla, no aquí.
     · La clave cambia cuando cambia la situación; una alerta descartada vuelve a salir con la clave nueva.
     · En la web exportada (estatico) no hay botones de acción de la app ni se puede descartar.
     · Con la vista filtrada las alertas siguen siendo de la cartera completa: se devuelve `filtrada`
       para que la pantalla lo diga.
*/
(function (raiz) {
  "use strict";

  const DIA = 86400000;
  const DIAS_CUOTA = 7;          // la cuota avisa en los 7 días previos
  const HORAS_PRECIOS = 36;      // precios generales con más de 36 h
  const DIAS_MS = 24 * 3600000;

  const diasEntre = (a, b) => Math.round((Date.parse(b) - Date.parse(a)) / DIA);

  /* Separa los avisos del servidor por tipo (el servidor los manda como texto). */
  function clasificaAvisos(avisos) {
    const sinRed = [], viejos = [], otros = [];
    (avisos || []).forEach(a => {
      let m;
      if ((m = /^(.+?): sin conexion y sin cache/.exec(a))) sinRed.push(m[1]);
      else if ((m = /^(.+?): el último precio que tengo es del (\d{4}-\d{2}-\d{2})/.exec(a))) viejos.push({ nombre: m[1], fecha: m[2] });
      else otros.push(a);
    });
    return { sinRed, viejos, otros };
  }

  function claveLtv(x) { return `ltv:${x.id}:${x.nivel}:${Math.round((x.ratio || 0) * 20)}`; }

  /*
    o = { pignoraciones, avisos, preciosActualizados, ahora (ms), fechaExtracto,
          estatico, demo, ocultas ({clave: ms}), filtrando }
    -> { alertas: [...visibles], filtrada: bool, descartables: bool }
  */
  function calcula(o) {
    const out = [];
    const estatico = !!o.estatico;
    (o.pignoraciones || []).filter(x => x.estado === "activa").forEach(x => {
      const clave = claveLtv(x);
      if (x.nivel === "peligro" && x.superaLimite) {
        out.push({ tipo: "ltv", sub: "limite", id: x.id, clave, cl: "danger", ir: "riesgo", pig: x });
      } else if (x.nivel === "peligro") {
        out.push({ tipo: "ltv", sub: "deuda", id: x.id, clave, cl: "danger", ir: "riesgo", pig: x });
      } else if (x.nivel === "alto" || x.nivel === "medio") {
        out.push({ tipo: "ltv", sub: "atencion", id: x.id, clave, cl: "warn", ir: "riesgo", pig: x });
      }
      if (x.proxima && x.proxima.fecha && o.fechaExtracto) {
        const d = diasEntre(o.fechaExtracto, x.proxima.fecha);
        if (d >= 0 && d <= DIAS_CUOTA) {
          out.push({ tipo: "cuota", id: x.id, clave: `cuota:${x.id}:${x.proxima.fecha}`, cl: "info", pig: x, dias: d });
        }
      }
    });

    const c = clasificaAvisos(o.avisos);
    let hayPrecios = false;
    if (c.sinRed.length) {
      hayPrecios = true;
      out.push({ tipo: "sinRed", clave: "sinRed:" + c.sinRed.join(","), cl: "info", codigos: c.sinRed,
        accion: estatico ? null : "actualizar" });
    }
    if (c.viejos.length) {
      hayPrecios = true;
      const peor = c.viejos.reduce((a, v) => v.fecha < a.fecha ? v : a, c.viejos[0]);
      out.push({ tipo: "viejo", clave: "viejo:" + c.viejos.map(v => v.nombre + v.fecha).join(","), cl: "info",
        nombres: c.viejos.map(v => v.nombre), fecha: peor.fecha, dias: diasEntre(peor.fecha, o.fechaExtracto),
        accion: estatico ? null : "actualizar" });
    }
    // «Precios de hace días» general: solo en la app real (en la web exportada no se puede actualizar,
    // y en la demo los precios son de ejemplo) y sin repetir lo que ya dicen los avisos por precio.
    const pa = o.preciosActualizados && /[+-]\d\d:\d\d$|Z$/.test(o.preciosActualizados) ? Date.parse(o.preciosActualizados) : null;
    if (pa && !estatico && !o.demo && !hayPrecios && o.ahora - pa > HORAS_PRECIOS * 3600000) {
      out.push({ tipo: "datosViejos", clave: "datosViejos:" + o.preciosActualizados.slice(0, 10), cl: "info",
        dias: Math.round((o.ahora - pa) / DIAS_MS), accion: "actualizar" });
    }

    const ocultas = estatico ? {} : (o.ocultas || {});
    const alertas = out.filter(a => !ocultas[a.clave]).map(a => Object.assign(a, { descartable: !estatico }));
    return { alertas, filtrada: !!o.filtrando, descartables: !estatico };
  }

  const API = { calcula, clasificaAvisos, claveLtv, DIAS_CUOTA, HORAS_PRECIOS };
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  else raiz.Alertas = API;
})(typeof window !== "undefined" ? window : globalThis);
