/* ============================================================
   app.js  ·  Dashboard de patrimonio
   ============================================================ */
(function () {
  "use strict";

  const D = window.DATOS;
  const $ = s => document.querySelector(s);
  const raiz = document.documentElement;

  const recuerda = {
    lee(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    guarda(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* da igual */ } },
  };

  // ?tab=rendimiento&tema=claro abre directamente esa pestaña con ese tema.
  const qs = new URLSearchParams(location.search);
  if (qs.get("tab")) recuerda.guarda("patrimonio.tab", qs.get("tab"));
  if (qs.get("tema")) recuerda.guarda("patrimonio.tema", qs.get("tema"));

  // El tema (claro u oscuro) se aplica siempre, también con la cartera vacía.
  const temaGuardado = recuerda.lee("patrimonio.tema");
  if (temaGuardado) raiz.dataset.tema = temaGuardado;
  else if (window.matchMedia && matchMedia("(prefers-color-scheme: light)").matches) raiz.dataset.tema = "claro";
  const cambiaTema = () => {
    raiz.dataset.tema = raiz.dataset.tema === "claro" ? "oscuro" : "claro";
    recuerda.guarda("patrimonio.tema", raiz.dataset.tema);
  };

  if (!D) {
    $("#btnTema").onclick = cambiaTema;
    // Cartera vacía: solo se enseña «Mis datos», para empezar a meter productos.
    document.body.classList.add("sinDatos");
    document.querySelectorAll("#tabs button").forEach(b =>
      b.setAttribute("aria-selected", String(b.dataset.tab === "datos")));
    document.querySelectorAll(".panel").forEach(p => { p.hidden = p.id !== "tab-datos"; });
    document.querySelectorAll(".aviso-legal, #bannerDemo").forEach(el => { el.hidden = true; });
    document.querySelectorAll("#tabs button").forEach(b => {
      b.onclick = () => {
        document.querySelectorAll("#tabs button").forEach(x => x.setAttribute("aria-selected", String(x === b)));
        document.querySelectorAll(".panel").forEach(p => { p.hidden = p.id !== "tab-" + b.dataset.tab; });
      };
    });
    return;
  }

  const estado = {
    tab: "patrimonio",
    rango: "todo",
    vista: "apilado",
    dist: "clase",
    fondo: null,
    serieDetalle: "posicion",
    mes: (D.resumenMensual || []).length - 1,
    anual: "mia",
    tablaFiltro: "todos",
    ordenTabla: { col: "fecha", desc: true },
    btcVivo: null,
    compRef: recuerda.lee("patrimonio.compRef") || "mundo",
    ocultos: new Set(),
    base: recuerda.lee("patrimonio.base") === "neto" ? "neto" : "activos",
  };

  /* ---------------------------------------------- ¿y si lo hubieras metido en un indexado? */
  function pintaComparacion() {
    const C = D.comparacion, sec = $("#seccionComparar");
    if (!sec) return;
    if (!C || !C.referencias.length) {
      // Sin el campo, los datos los calculó una versión anterior de la app (que sigue abierta).
      $("#compTitular").innerHTML = "comparacion" in D
        ? '<p class="vacio">Aparecerá cuando tengas compras anotadas.</p>'
        : '<p class="vacio">Cierra la ventana negra de la app y vuelve a abrirla para calcular esta sección.</p>';
      $("#compRef").innerHTML = "";
      $("#grafComparacion").innerHTML = "";
      return;
    }
    if (!C.referencias.some(r => r.id === estado.compRef)) estado.compRef = C.referencias[0].id;
    const r = C.referencias.find(x => x.id === estado.compRef);
    const segm = $("#compRef");
    segm.innerHTML = "";
    C.referencias.forEach(x => {
      const b = document.createElement("button");
      b.textContent = x.nombre;
      b.setAttribute("aria-pressed", String(x.id === r.id));
      b.onclick = () => { estado.compRef = x.id; recuerda.guarda("patrimonio.compRef", x.id); pintaComparacion(); };
      segm.appendChild(b);
    });
    const dif = C.tuValor - r.valor;
    const pct = r.valor ? dif / r.valor : 0;
    const igual = Math.abs(pct) < 0.005;
    const veredicto = igual ? `Vas prácticamente igual que el ${r.nombre}.`
      : dif > 0 ? `Vas ${G.fmtEur(Math.abs(dif), 0)} por delante del ${r.nombre} (${G.fmtPctSigno(pct, 1)}).`
      : `Con el ${r.nombre} tendrías ${G.fmtEur(Math.abs(dif), 0)} más (${G.fmtPctSigno(-dif / C.tuValor, 1)}).`;
    // Con un préstamo, «aportado» incluye el dinero prestado: de tu bolsillo es el capital propio.
    const puesto = C.aportado[C.aportado.length - 1];
    const cp = C.capitalPropio != null ? C.capitalPropio : D.total.capitalPropio;
    const propio = cp != null && Math.abs(cp - puesto) > 0.5;
    const bolsillo = propio ? cp : puesto;
    const caja = (et, v, extra, cls = "") => `<div class="compCaja ${cls}"><span>${et}</span><b>${v}</b>${extra ? `<small>${extra}</small>` : ""}</div>`;
    $("#compTitular").innerHTML =
      caja("Tú tienes hoy", G.fmtEur(C.tuValor, 0), `TIR ${G.fmtPctSigno(C.tuTir, 1)}`) +
      caja(`Con el ${r.nombre} tendrías`, G.fmtEur(r.valor, 0), `TIR ${G.fmtPctSigno(r.tir, 1)}`) +
      caja("Has puesto de tu bolsillo", G.fmtEur(bolsillo, 0),
        propio ? "compras menos ventas, sin el dinero prestado" : "compras menos ventas") +
      caja("Veredicto", veredicto, "", "veredicto");
    G.multiLinea($("#grafComparacion"), {
      fechas: D.fechas, alto: 300,
      series: [
        { nombre: "Tu cartera", valores: C.tuya, color: G.css("--s1"), destacado: true },
        { nombre: "Con el " + r.nombre, valores: r.serie, color: G.css("--s2") },
        { nombre: "Tu dinero puesto", valores: C.aportado, color: G.css("--tinta3") },
      ],
      formatoY: v => G.fmtEurCorto(v),
      formatoValor: v => G.fmtEur(v, 0),
      desdeCero: true,
    });
    const ley = (c, t) => `<span class="leyItem"><i data-st="background:${G.css(c)}"></i>${t}</span>`;
    $("#compNota").innerHTML = `<span class="leyComp">${ley("--s1", "Tu cartera")}${ley("--s2", "Con el " + r.nombre)}${ley("--tinta3", "Tu dinero puesto")}</span>
      ${r.detalle} Solo cuenta los productos con compras anotadas (no las cuentas ni lo
      que valoras a mano sin movimientos), desde el ${G.fmtFecha(C.desde)}. Sin impuestos ni comisiones de compra.
      ${r.aviso ? "<br>" + r.aviso : ""}`;
  }

  /* ---------------------------------------------- tema y colores */
  function temaOscuro() { return raiz.dataset.tema !== "claro"; }
  function color(p) {
    const c = p.slotColor || p.color || ["#2a78d6", "#3987e5"];
    return temaOscuro() ? c[1] : c[0];
  }
  function hex2rgb(h) {
    h = String(h).replace("#", "");
    if (h.length === 3) h = h.split("").map(c => c + c).join("");
    return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
  }
  function mezcla(a, b, t) {
    const A = hex2rgb(a), B = hex2rgb(b);
    return "#" + A.map((v, i) => Math.round(v + (B[i] - v) * t).toString(16).padStart(2, "0")).join("");
  }
  /** Tres tonos del propio color del producto: pequeña, habitual, extraordinaria. */
  function tonos(base) {
    return temaOscuro()
      ? [mezcla(base, "#1a1a19", 0.52), base, mezcla(base, "#ffffff", 0.42)]
      : [mezcla(base, "#fcfcfb", 0.58), base, mezcla(base, "#000000", 0.32)];
  }

  const TODOS = () => D.productos.concat(D.otrosActivos || [], D.pasivos || []);
  // Un derivado de pignoración ya a 0 € (p. ej. el dinero recibido, ya invertido) no se enseña en las
  // listas, pero sigue contando en los cálculos: si no, la deuda quedaría sin su contrapartida.
  const enseñable = p => !(p.derivado && !p.valor);
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  // Candado de los activos en garantía: no se pueden vender mientras dure la pignoración.
  const bloqueo = p => p.pignoradoEn && p.pignoradoEn.length
    ? `<span class="lock" title="Pignorado en «${esc(p.pignoradoEn.map(x => x.nombre).join("», «"))}»: ` +
      `no se puede vender hasta liquidar la pignoración">🔒</span>` : "";
  const visibles = () => TODOS().filter(p => !estado.ocultos.has(p.id));
  const filtrando = () => estado.ocultos.size > 0;
  const buscaProd = id => TODOS().find(p => p.id === id);

  /* ---------------------------------------------- precio en vivo */
  function precioVivo() {
    const v = D.vivo;
    if (!v || !estado.btcVivo) return null;
    return { id: v.productoId, titulos: v.titulos, precio: v.precioRef * (estado.btcVivo / v.btcRef) };
  }
  function valorDe(p) {
    const pv = precioVivo();
    if (pv && p.id === pv.id) return pv.titulos * pv.precio;
    return p.valor || 0;
  }

  /** Plusvalía calculada con el mismo valor que se enseña (en vivo si lo hay),
      para que valor, plusvalía y porcentaje siempre sumen entre sí. */
  function plusvaliaDe(p) {
    if (p.aportado == null || !(p.aportado > 0)) return null;
    const eur = valorDe(p) - p.aportado;
    return { eur, pct: eur / p.aportado };
  }

  /* ---------------------------------------------- métricas (módulo compartido y probado) */
  const metricas = lista => Metricas.calcula(D, lista, { valorDe });
  // Una deuda y el dinero que recibiste con ella se filtran siempre juntos.
  const GRUPOS = Metricas.grupos(TODOS());
  const grupoDe = id => GRUPOS[id] || [id];

  function agrupa(lista, campo) {
    const acc = new Map();
    lista.forEach(p => {
      const k = p[campo] || "Otros";
      const g = acc.get(k) || { nombre: k, valor: 0, color: color(p) };
      g.valor += valorDe(p);
      acc.set(k, g);
    });
    return [...acc.values()].filter(g => g.valor > 0).sort((a, b) => b.valor - a.valor);
  }

  /* ---------------------------------------------- rango temporal */
  const RANGOS = [
    { id: "1m", et: "1M", dias: 30 }, { id: "3m", et: "3M", dias: 91 },
    { id: "6m", et: "6M", dias: 182 }, { id: "ytd", et: "YTD", dias: null },
    { id: "1a", et: "1A", dias: 365 }, { id: "todo", et: "Todo", dias: null },
  ];
  function desdeIdx() {
    const n = D.fechas.length;
    const r = RANGOS.find(x => x.id === estado.rango);
    if (!r || r.id === "todo") return 0;
    if (r.id === "ytd") {
      const ini = D.fechaExtracto.slice(0, 4) + "-01-01";
      const i = D.fechas.findIndex(f => f >= ini);
      return i < 0 ? 0 : i;
    }
    return Math.max(0, n - 1 - r.dias);
  }
  const corta = arr => (arr || []).slice(desdeIdx());

  function pintaSegm(cont, opciones, activo, alPulsar) {
    if (!cont) return;
    cont.innerHTML = "";
    opciones.forEach(o => {
      const b = document.createElement("button");
      b.textContent = o.et;
      b.setAttribute("aria-pressed", String(o.id === activo));
      b.onclick = () => alPulsar(o.id);
      cont.appendChild(b);
    });
  }

  /* ================================================================
     PESTAÑA 1 · PATRIMONIO
     ================================================================ */
  const idsCorto = () => TODOS().filter(p => p.largoPlazo === false).map(p => p.id);

  function pintaFiltros() {
    const cont = $("#filtros");
    cont.innerHTML = "";
    const vistos = new Set();
    TODOS().filter(enseñable).forEach(p => {
      const ids = grupoDe(p.id);
      const clave = ids.join("|");
      if (vistos.has(clave)) return;       // un solo botón para la deuda y su dinero recibido
      vistos.add(clave);
      const on = !estado.ocultos.has(p.id);
      const b = document.createElement("button");
      b.className = "filtro";
      b.style.setProperty("--c", color(p));
      b.setAttribute("aria-pressed", String(on));
      b.title = on ? "Quitar del gráfico y de las métricas" : "Volver a incluirlo";
      b.innerHTML = `<i></i>${esc(p.corto || p.nombre)}<span class="im">${G.fmtEurCorto(valorDe(p))}</span>`;
      b.onclick = () => {
        if (on) {
          if (visibles().length <= ids.length) return;
          ids.forEach(id => estado.ocultos.add(id));
        } else ids.forEach(id => estado.ocultos.delete(id));
        pintaPatrimonio();
      };
      cont.appendChild(b);
    });
    const sep = document.createElement("span");
    sep.className = "filtroSep";
    cont.appendChild(sep);

    const cortos = idsCorto();
    const esLargo = cortos.length > 0 && cortos.length === estado.ocultos.size &&
      cortos.every(id => estado.ocultos.has(id));
    [
      { id: "todo", et: "Ver todo", act: !filtrando(), fn: () => estado.ocultos.clear() },
      { id: "largo", et: "Solo largo plazo", act: esLargo, fn: () => { estado.ocultos = new Set(cortos); } },
    ].forEach(pr => {
      if (pr.id === "largo" && !cortos.length) return;
      const b = document.createElement("button");
      b.className = "filtro preset";
      b.setAttribute("aria-pressed", String(pr.act));
      b.textContent = pr.et;
      b.title = pr.id === "largo"
        ? "Deja fuera el colchón y el efectivo: solo lo que tienes invertido a largo plazo"
        : "Vuelve a mostrar todos los componentes";
      b.onclick = () => { pr.fn(); pintaPatrimonio(); };
      cont.appendChild(b);
    });
  }

  function pintaHero(mVis, mTodo) {
    const filtro = filtrando();
    const m = filtro ? mVis : mTodo;
    $("#heroEtq").textContent = filtro ? "Vista filtrada" : "Patrimonio neto";
    $("#heroCifra").textContent = G.fmtEur(m.valor);

    const partes = [];
    if (m.plusvalia !== null) {
      const cl = m.plusvalia >= 0 ? "pos" : "neg";
      partes.push(`<span class="${cl} fuerte">${G.fmtEurSigno(m.plusvalia)}</span>
        <span class="${cl}">(${G.fmtPctSigno(m.rentabilidad)})</span> sobre lo aportado`);
    }
    if (m.tir !== null) partes.push(`TIR anualizada <span class="fuerte">${G.fmtPctSigno(m.tir)}</span>`);

    const pv = precioVivo();
    if (pv) {
      const p = D.productos.find(x => x.id === pv.id);
      if (p && !estado.ocultos.has(p.id)) {
        const delta = pv.titulos * pv.precio - p.valor;
        partes.push(`<span class="pill vivo"><span class="latido"></span>Bitcoin en vivo
          <span class="${delta >= 0 ? "pos" : "neg"}">${G.fmtEurSigno(delta)}</span></span>`);
      }
    } else if (D.vivo) {
      partes.push(`<span class="pill">Cotización a cierre del ${G.fmtFechaCorta(D.fechaExtracto)}</span>`);
    }
    if (filtro) {
      partes.push(`<button class="pill reset" id="btnReset" title="Volver a mostrarlo todo">
        de ${G.fmtEur(mTodo.valor, 0)} totales · ver todo</button>`);
    }
    $("#heroSub").innerHTML = partes.join('<span data-st="color:var(--tinta3)">·</span>');
    const reset = $("#btnReset");
    if (reset) reset.onclick = () => { estado.ocultos.clear(); pintaPatrimonio(); };

    if (filtro) { $("#progEnv").hidden = true; return; }

    // Progreso medido desde cero, que es como se lee de forma natural.
    const propio = (D.objetivo && D.objetivo.activo) ? D.objetivo.importe : null;
    const siguienteHito = (D.total.hitos.find(h => h.importe > m.valor) || {}).importe;
    const sig = (propio && propio > m.valor) ? propio : siguienteHito;
    if (!sig) { $("#progEnv").hidden = true; return; }
    const pct = Math.max(0, Math.min(1, m.valor / sig));
    $("#progEnv").hidden = false;
    $("#progRelleno").style.width = (pct * 100).toFixed(1) + "%";
    $("#progIzq").innerHTML =
      `<b data-st="color:var(--tinta)">${G.fmtPct(pct, 1)}</b> del camino hacia ${G.fmtEurCorto(sig)}`;
    $("#progDer").textContent = "Faltan " + G.fmtEur(sig - m.valor, 0);
  }

  function pintaKPIs(m) {
    const sinFiltro = !filtrando();
    const twr = sinFiltro && D.total.caidaMaximaTwr != null;
    const caida = twr ? D.total.caidaMaximaTwr : m.caida;
    const caidaFecha = twr ? D.total.caidaMaximaTwrFecha : m.caidaFecha;
    const prest = (D.pignoraciones || []).find(x => x.estado === "activa" && x.ratio != null);
    const kpis = [
      { e: "Aportado", v: G.fmtEur(m.aportado, 0),
        n: sinFiltro && D.total.dineroPrestado > 0 && D.total.capitalPropio != null
          ? `de tu bolsillo: ${G.fmtEur(D.total.capitalPropio, 0)} · prestado: ${G.fmtEur(D.total.dineroPrestado, 0)}`
          : `${m.numAportaciones} aportaciones` },
      {
        e: "Plusvalía latente", v: G.fmtEurSigno(m.plusvalia),
        n: m.rentabilidad != null ? G.fmtPctSigno(m.rentabilidad) + " sobre el coste" : "sin coste registrado",
        cl: m.plusvalia >= 0 ? "pos" : "neg"
      },
      { e: "TIR anualizada", v: G.fmtPctSigno(m.tir), n: "rentabilidad real del dinero", cl: m.tir >= 0 ? "pos" : "neg" },
    ];
    if (sinFiltro && D.total.tirCapitalPropio != null && D.total.deudaPignoraciones) {
      kpis.push({ e: "TIR de tu capital", v: G.fmtPctSigno(D.total.tirCapitalPropio), n: "descontando el préstamo y sus cuotas",
        cl: D.total.tirCapitalPropio >= 0 ? "pos" : "neg" });
    }
    kpis.push(
      { e: "Ritmo mensual", v: G.fmtEur(m.ritmo, 0), n: "últimos 12 meses naturales ÷ 12" },
      { e: "Racha", v: m.racha + (m.racha === 1 ? " mes" : " meses"), n: "aportando sin fallar" },
      { e: "Peor caída", v: G.fmtPctSigno(caida),
        n: caidaFecha ? (twr ? "de la rentabilidad, sin contar aportaciones · " : "del valor filtrado, el ") + G.fmtFecha(caidaFecha) : "", cl: "neg" });
    if (sinFiltro && prest) {
      kpis.push({ e: "Préstamo / garantía", v: G.fmtPct(prest.ratio, 1),
        n: prest.ltvMax ? "límite " + String(prest.ltvMax).replace(".", ",") + " %" : "límite sin indicar",
        cl: prest.nivel === "peligro" ? "neg" : "" });
    }
    $("#kpis").innerHTML = kpis.map(k =>
      `<div class="kpi"><div class="e">${k.e}</div>
       <div class="v ${k.cl || ""}">${k.v}</div><div class="n">${k.n}</div></div>`).join("");
    $("#kpisNota").textContent = filtrando()
      ? `Métricas de los ${visibles().length} componentes activos, no del patrimonio completo.` : "";
  }

  function pintaPrincipal(m) {
    const fechas = corta(D.fechas);
    const deudas = visibles().filter(p => p.tipoClave === "deuda");
    const hayDeuda = deudas.length > 0;
    const neto = hayDeuda && estado.base === "neto";
    // m.serie es el patrimonio NETO. La deuda es un recurso de financiación, no una pérdida: por
    // defecto el gráfico enseña los activos (para que pedir un préstamo no parezca una caída).
    const sinDeuda = m.serie.map((v, i) => v - deudas.reduce((a, p) => a + ((p.serie || [])[i] || 0), 0));
    const serieVista = neto ? m.serie : sinDeuda;
    const prods = visibles().filter(p => (p.serie || []).some(v => v) && (neto || p.tipoClave !== "deuda"));
    const cont = $("#grafPrincipal");
    let nota = "";

    // Selector «Activos | Neto de deuda» (solo si hay deuda).
    let seg = $("#segBase");
    if (!seg) {
      seg = document.createElement("div");
      seg.id = "segBase"; seg.className = "segm"; seg.setAttribute("role", "group"); seg.setAttribute("aria-label", "Qué valor enseñar");
      $("#segRango").parentNode.insertBefore(seg, $("#segRango"));
    }
    seg.hidden = !hayDeuda;
    if (hayDeuda) {
      pintaSegm(seg, [{ id: "activos", et: "Activos" }, { id: "neto", et: "Neto de deuda" }], neto ? "neto" : "activos",
        id => { estado.base = id; recuerda.guarda("patrimonio.base", id); pintaPrincipal(m); });
    }

    if (estado.vista === "total") {
      G.lineaConEventos(cont, {
        fechas, valores: corta(serieVista), color: G.css("--s1"), alto: 330,
        overlay: { nombre: "Aportado", valores: corta(m.serieAportado) },
      });
      if (hayDeuda) nota = neto ? "Neto: activos menos la deuda pendiente." : "Activos: no resta la deuda (ves el neto en la cifra de arriba).";
    } else if (estado.vista === "dinero") {
      // Lo que pusiste tú contra lo que ha puesto el mercado (siempre sobre activos).
      const tuyo = sinDeuda.map((v, i) => Math.min(m.serieAportado[i], v));
      const mercado = sinDeuda.map((v, i) => Math.max(0, v - m.serieAportado[i]));
      const bajoCoste = sinDeuda.some((v, i) => v > 0 && v < m.serieAportado[i] - 0.01);
      G.areaApilada(cont, {
        fechas, alto: 330,
        series: [
          { nombre: "Lo que pusiste tú", color: G.css("--tinta3"), valores: corta(tuyo) },
          { nombre: "Lo que puso el mercado", color: G.css("--s3"), valores: corta(mercado) },
        ],
      });
      nota = bajoCoste
        ? "Hubo días por debajo de lo aportado: ahí la banda verde desaparece."
        : "La banda verde es rentabilidad, no dinero tuyo.";
    } else if (estado.vista === "reparto") {
      const series = prods.filter(p => p.tipoClave !== "deuda")
        .map(p => ({ id: p.id, nombre: p.corto || p.nombre, color: color(p), valores: corta(p.serie) }));
      const tot = fechas.map((_, i) => series.reduce((a, s) => a + (s.valores[i] || 0), 0));
      series.forEach(s => { s.valores = s.valores.map((v, i) => tot[i] ? (v || 0) / tot[i] * 100 : 0); });
      G.areaApilada(cont, {
        fechas, series, alto: 330, maxForzado: 100,
        formatoY: v => Math.round(v) + " %",
        formatoValor: v => v.toFixed(1) + " %",
      });
    } else {
      G.areaApilada(cont, {
        fechas, alto: 330,
        series: prods.filter(p => p.tipoClave !== "deuda")
          .map(p => ({ id: p.id, nombre: p.corto || p.nombre, color: color(p), valores: corta(p.serie) })),
        overlay: { nombre: "Aportado", valores: corta(m.serieAportado) },
      });
      const tardios = visibles().filter(p => p.desde && p.desde > D.fechas[0] && p.aportado == null && p.tipoClave !== "deuda" && !p.derivado);
      if (tardios.length) {
        nota = tardios.map(p => p.corto).join(", ") + (tardios.length > 1 ? " entran" : " entra") +
          " en el seguimiento el " + G.fmtFecha(tardios[0].desde);
      } else if (hayDeuda) {
        nota = "Activos por producto; la deuda no se resta en este gráfico.";
      }
    }
    $("#evolNota").textContent = nota;
  }

  function pintaChips() {
    const cont = $("#chips");
    if (!cont) return;
    cont.innerHTML = "";
    TODOS().filter(enseñable).forEach(p => {
      const oculto = estado.ocultos.has(p.id);
      const b = document.createElement("button");
      b.className = "chip" + (oculto ? " apagado" : "");
      b.style.setProperty("--c", color(p));
      const plTarjeta = plusvaliaDe(p);
      const rent = plTarjeta ? plTarjeta.pct : null;
      b.innerHTML = `<span class="barra"></span>
        <div class="nm"><i></i>${p.corto || p.nombre}${bloqueo(p)}</div>
        <div class="vl">${G.fmtEur(valorDe(p))}</div>
        <div class="pi"><span>${oculto ? "fuera del gráfico" : G.fmtPct(p.peso, 1) + " del total"}</span>
          <span class="${rent == null ? "" : rent >= 0 ? "pos" : "neg"}">${rent == null ? "—" : G.fmtPctSigno(rent, 1)}</span></div>
        <div class="sp"></div>`;
      b.onclick = () => { estado.fondo = p.id; irA("fondos"); };
      cont.appendChild(b);
      G.mini(b.querySelector(".sp"), corta(p.serie), color(p));
    });
  }

  function pintaDistribucion() {
    const lista = visibles();
    const datos = estado.dist === "producto"
      ? lista.filter(p => valorDe(p) > 0)
        .map(p => ({ nombre: p.corto || p.nombre, valor: valorDe(p), color: color(p), id: p.id }))
        .sort((a, b) => b.valor - a.valor)
      : agrupa(lista, estado.dist);
    const total = datos.reduce((a, x) => a + x.valor, 0);
    G.donut($("#grafDonut"), {
      datos, alto: 236, tituloCentro: filtrando() ? "Filtrado" : "Total",
      valorCentro: G.fmtEurCorto(total),
      onClick: d => { if (d.id) { estado.fondo = d.id; irA("fondos"); } }
    });
    $("#leyendaDist").innerHTML = datos.map(d =>
      `<tr><td><i data-st="background:${d.color}"></i>${esc(d.nombre)}</td>
       <td>${G.fmtEur(d.valor)}</td><td>${G.fmtPct(d.valor / total, 1)}</td></tr>`).join("");
  }

  function pintaBarras() {
    const am = D.aportacionesMensuales;
    const desde = D.fechas[desdeIdx()].slice(0, 7);
    const idx = am.meses.findIndex(m => m >= desde);
    const i0 = idx < 0 ? am.meses.length : idx;
    const meses = am.meses.slice(i0);
    const series = visibles()
      .filter(p => (am.porProducto[p.id] || []).some(v => v))
      .map(p => ({ nombre: p.corto || p.nombre, color: color(p), valores: am.porProducto[p.id].slice(i0) }));
    G.barrasApiladas($("#grafBarras"), { categorias: meses, alto: 236, series });
    const suma = meses.reduce((a, _, i) => a + series.reduce((b, s) => b + (s.valores[i] || 0), 0), 0);
    $("#notaAport").textContent = meses.length
      ? `${G.fmtEur(suma, 0)} en ${meses.length} ${meses.length === 1 ? "mes" : "meses"}` : "";
  }

  function pintaHitos(mTodo) {
    // En la web con importes ocultos no hay hitos (delatarían cifras).
    $("#hitos").closest("section").hidden = !D.total.hitos.length;
    $("#hitos").innerHTML = D.total.hitos.map(h => {
      const hecho = !!h.fecha;
      return `<div class="hito ${hecho ? "hecho" : ""}">
        <div class="im">${G.fmtEurCorto(h.importe)}</div>
        <div class="fe">${hecho ? "✓ " + G.fmtFecha(h.fecha) : "faltan " + G.fmtEurCorto(h.importe - mTodo.valor)}</div>
      </div>`;
    }).join("");
  }

  /* ---- Si sigo así…: proyección global, por activo (precio objetivo) o mixta ---- */
  const proy = { modo: "global", objetivos: {}, clave: "" };   // los objetivos solo viven en esta sesión

  function activosProyeccion() {
    const lista = visibles(), activos = [];
    let valorBase = 0;
    lista.forEach(p => {
      const v = valorDe(p);
      if (!(v > 0)) {
        if (p.derivado && p.tipoClave === "deuda") return;   // la de un préstamo se amortiza con su cuadro
        valorBase += v;                                       // otras deudas: se mantienen fijas
        return;
      }
      activos.push({ id: p.id, nombre: p.corto || p.nombre, color: color(p), valor: v,
                     precio: (p.precioActual || p.nav) > 0 ? (p.precioActual || p.nav) : null, tipo: p.tipoClave || "" });
    });
    return { activos, valorBase };
  }

  /* ================================================================
     PLANIFICACIÓN · meta con fecha y asignación objetivo
     ================================================================ */
  const sumaMeses = (iso, n) => {
    const d = new Date(iso + "T00:00:00");
    d.setMonth(d.getMonth() + n);
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  };
  const numEs = t => {
    t = String(t == null ? "" : t).replace(/[€%\s]/g, "");
    if (t.includes(",") || /^-?\d{1,3}(\.\d{3})+$/.test(t)) t = t.replace(/\./g, "").replace(",", ".");
    return parseFloat(t);
  };
  async function enviaApi(url, cuerpo) {
    const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) });
    let j = {};
    try { j = await r.json(); } catch (e) { /* vacío */ }
    if (!r.ok || j.ok === false) throw new Error((j.errores || [j.error || "No he podido guardarlo."]).join("\n"));
    return j;
  }
  function recargaEnPlan() {
    recuerda.guarda("patrimonio.tab", "plan");
    location.reload();
  }

  function pintaMeta() {
    const el = $("#metaCuerpo");
    if (!el) return;
    const ob = D.objetivo && D.objetivo.activo ? D.objetivo : null;
    const neto = metricas(TODOS()).valor;
    const ritmo = D.total.ritmoMensual || 0;
    const escenarios = [["Prudente", 0.03], ["Medio", 0.06], ["Optimista", 0.09]];
    let cuerpo = "";
    if (!ob) {
      cuerpo = '<p class="vacio">Aún no has fijado una meta. Pon un importe (y, si quieres, una fecha) y verás cuándo llegas y cuánto aportar.</p>';
    } else {
      const filas = escenarios.map(([et, r]) => {
        const m = Asignacion.mesesHasta(neto, ob.importe, ritmo, r);
        const cuando = m == null ? "—" : G.fmtMes(sumaMeses(D.fechaExtracto, m).slice(0, 7));
        let nec = "";
        if (ob.fecha) {
          const n = Asignacion.mesesEntre(D.fechaExtracto, ob.fecha);
          const a = Asignacion.aportacionNecesaria(neto, ob.importe, n, r);
          nec = a == null ? "—" : G.fmtEur(a, 0) + "/mes";
        }
        return `<tr><td>${et} · ${Math.round(r * 100)} % anual</td><td>${cuando}</td>${ob.fecha ? `<td>${nec}</td>` : ""}</tr>`;
      }).join("");
      const falta = Math.max(0, ob.importe - neto);
      cuerpo = `<p>Meta: <b class="fuerte">${G.fmtEur(ob.importe, 0)}</b>${ob.fecha ? ` el <b class="fuerte">${G.fmtFecha(ob.fecha)}</b>` : ""}.
          Tienes ${G.fmtEur(neto, 0)} (${G.fmtPct(Math.min(1, neto / ob.importe), 0)}) y te faltan ${G.fmtEur(falta, 0)}.
          Con tu ritmo actual de <b>${G.fmtEur(ritmo, 0)}</b> al mes:</p>
        <div class="tablaEnv"><table class="dt"><thead><tr><th>Escenario</th><th>Llegarías en</th>${ob.fecha ? "<th>Para llegar a la fecha, aportando</th>" : ""}</tr></thead>
          <tbody>${filas}</tbody></table></div>`;
    }
    const editable = !window.ESTATICO;
    el.innerHTML = cuerpo + (editable ? `
      <form class="formMeta" id="formMeta" data-st="display:flex;gap:12px;flex-wrap:wrap;align-items:end;margin-top:16px">
        <label class="campo"><span class="et">Importe de la meta</span><input name="importe" inputmode="decimal" value="${ob ? String(ob.importe).replace(".", ",") : ""}" placeholder="100.000"></label>
        <label class="campo"><span class="et">Fecha <em>opcional</em></span><input type="date" name="fecha" value="${ob && ob.fecha ? ob.fecha : ""}"></label>
        <button class="btn prim" type="submit">Guardar meta</button><span class="subt" id="metaMsg" role="status"></span>
      </form>` : "");
    const f = $("#formMeta");
    if (f) f.onsubmit = async e => {
      e.preventDefault();
      try {
        await enviaApi("api/meta", { importe: f.elements.importe.value, fecha: f.elements.fecha.value, etiqueta: ob && ob.etiqueta });
        recargaEnPlan();
      } catch (x) { $("#metaMsg").textContent = x.message; }
    };
    $("#metaSubt").textContent = "Cuándo llegas y cuánto aportar";
  }

  const asig = { aport: null, edit: null, clave: "" };

  /* Grupo por defecto: algo más útil que la categoría fina de Morningstar. */
  function grupoAmplio(p) {
    const c = String(p.clase || ""), n = String(p.nombre || "");
    if (p.tipoClave === "cripto" || /bitcoin|btc|crypto|ether/i.test(n)) return "Criptoactivos";
    if (p.tipoClave === "efectivo") return "Efectivo";
    if (p.tipoClave === "accion") return "Acciones individuales";
    if (p.tipoClave === "bono" || /^RF/i.test(c)) return "Renta fija";
    if (/long\/short|alternativ|mixto|retorno absoluto/i.test(c)) return "Alternativos y mixtos";
    if (p.tipoClave === "commodity") return "Materias primas";
    if (p.tipoClave === "inmueble") return "Inmuebles";
    if (/^RV/i.test(c) || p.tipoClave === "fondo" || p.tipoClave === "etf") return "Fondos y ETF de renta variable";
    return "Otros";
  }

  function gruposAsignacion() {
    const m = new Map();
    TODOS().filter(enseñable).filter(p => valorDe(p) > 0 && !p.derivado).forEach(p => {
      const k = p.grupo || grupoAmplio(p);
      const g = m.get(k) || { id: k, valor: 0, n: 0, conGrupo: false };
      g.valor += valorDe(p); g.n++; g.conGrupo = g.conGrupo || !!p.grupo;
      m.set(k, g);
    });
    return [...m.values()].sort((a, b) => b.valor - a.valor);
  }

  function pintaAsignacion() {
    const el = $("#asigCuerpo");
    if (!el) return;
    const grupos = gruposAsignacion();
    const guardados = (D.asignacion && D.asignacion.objetivos) || {};
    if (asig.aport == null) asig.aport = Math.round((D.total.ritmoMensual || 0) / 10) * 10;
    if (!asig.edit) asig.edit = { ...guardados };
    const editable = !window.ESTATICO;
    const clave = grupos.map(g => g.id).join("|") + "|" + (editable ? "e" : "r");
    if (clave !== asig.clave) {
      asig.clave = clave;
      el.innerHTML = `
        <div class="subt" data-st="margin-bottom:14px"><div>El reparto <b>no vende nada</b>: la aportación del mes va a los grupos que están por debajo de su objetivo.
          Los grupos salen del campo «Grupo para la asignación» de cada producto (Datos → Productos); si está vacío, se agrupan por tipo de activo.
          ${gruposAsignacion().every(g => !g.conGrupo) ? "<b>Aún no has puesto grupos propios:</b> ponlos para definir un reparto como «Renta variable 80 % / Liquidez 20 %»." : ""}</div></div>
        <div data-st="display:flex;gap:12px;align-items:end;flex-wrap:wrap;margin-bottom:12px">
          <label class="campo"><span class="et">Aportación de este mes</span>
            <input id="asigAport" inputmode="decimal" value="${String(asig.aport).replace(".", ",")}" ${editable ? "" : "disabled"}></label>
          <span class="subt" id="asigSuma" role="status"></span>
        </div>
        <div class="tablaEnv"><table class="dt" id="tablaAsig"><thead><tr><th>Grupo</th><th>Vale hoy</th><th>Peso hoy</th>
          <th>Objetivo %</th><th>Desviación</th><th>Poner este mes</th></tr></thead>
          <tbody>${grupos.map(g => `<tr data-g="${esc(g.id)}"><td>${esc(g.id)} <small class="subt">· ${g.n}</small></td>
            <td>${G.fmtEur(g.valor, 0)}</td><td data-p>—</td>
            <td><input class="inObjAsig" inputmode="decimal" data-g="${esc(g.id)}" data-st="width:76px;text-align:right"
                value="${guardados[g.id] != null ? String(guardados[g.id]).replace(".", ",") : ""}" placeholder="—" ${editable ? "" : "disabled"}></td>
            <td data-d>—</td><td data-s>—</td></tr>`).join("")}</tbody></table></div>
        ${editable ? `<div data-st="margin-top:14px;display:flex;gap:12px;align-items:center;flex-wrap:wrap">
          <button class="btn prim" id="btnGuardaAsig">Guardar objetivos</button><span class="subt" id="asigMsg" role="status"></span></div>` : ""}`;
      asig.edit = { ...guardados };
      el.querySelectorAll(".inObjAsig").forEach(inp => inp.addEventListener("input", () => {
        const v = numEs(inp.value);
        if (v > 0) asig.edit[inp.dataset.g] = v; else delete asig.edit[inp.dataset.g];
        actualizaAsignacion();
      }));
      $("#asigAport").addEventListener("input", e => { const v = numEs(e.target.value); asig.aport = v >= 0 ? v : 0; actualizaAsignacion(); });
      const b = $("#btnGuardaAsig");
      if (b) b.onclick = async () => {
        try {
          await enviaApi("api/asignacion", { objetivos: asig.edit });
          recargaEnPlan();
        } catch (x) { $("#asigMsg").textContent = x.message; }
      };
    }
    actualizaAsignacion();
  }

  function actualizaAsignacion() {
    const grupos = gruposAsignacion();
    const filas = Asignacion.reparto(grupos.map(g => ({ id: g.id, valor: g.valor, objetivo: asig.edit[g.id] != null ? asig.edit[g.id] : null })), asig.aport || 0);
    const suma = Object.values(asig.edit).reduce((a, b) => a + b, 0);
    filas.forEach(f => {
      const tr = $("#tablaAsig") && $("#tablaAsig").querySelector(`tr[data-g="${CSS.escape(f.id)}"]`);
      if (!tr) return;
      tr.querySelector("[data-p]").textContent = G.fmtPct(f.pesoHoy, 1);
      const d = tr.querySelector("[data-d]");
      d.textContent = f.desviacion == null ? "—" : (f.desviacion >= 0 ? "+" : "") + f.desviacion.toFixed(1).replace(".", ",") + " pp";
      d.className = f.desviacion == null ? "" : Math.abs(f.desviacion) < 2 ? "" : f.desviacion > 0 ? "neg" : "pos";
      tr.querySelector("[data-s]").innerHTML = f.objetivo ? `<b>${G.fmtEur(f.sugerido, 0)}</b>` : "—";
    });
    const el = $("#asigSuma");
    if (el) {
      el.textContent = Object.keys(asig.edit).length
        ? `Objetivos: ${suma.toFixed(1).replace(".", ",")} %${Math.abs(suma - 100) > 0.5 ? " · deberían sumar 100 %" : ""} · máx. desviación ${Asignacion.maxDesviacion(filas).toFixed(1).replace(".", ",")} pp`
        : "Escribe el porcentaje objetivo de cada grupo.";
    }
  }

  /* ---- ¿Y si el mercado se mueve? Montecarlo con el riesgo del préstamo ---- */
  const mc = { volP: null, volG: null };

  function pintaMontecarlo() {
    const sec = $("#seccionMC");
    if (!sec) return;
    const anos = +$("#rAnos").value, mu = +$("#rRent").value / 100, apor = +$("#rApor").value;
    // Volatilidad histórica de tu cartera (del índice de rentabilidad), acotada a un rango razonable.
    if (mc.volP == null) {
      const h = Montecarlo.volatilidad(D.indiceCartera || []);
      mc.volP = Math.round(Math.min(35, Math.max(8, (h || 0.16) * 100)));
      mc.volG = Math.min(mc.volP, 18);
      $("#rVolP").value = mc.volP; $("#rVolG").value = mc.volG;
    }
    mc.volP = +$("#rVolP").value; mc.volG = +$("#rVolG").value;
    $("#vVolP").textContent = mc.volP + " %"; $("#vVolG").textContent = mc.volG + " %";

    const { activos } = activosProyeccion();
    const cartera = activos.reduce((a, x) => a + x.valor, 0);
    const prest = (D.pignoraciones || []).filter(x => x.estado === "activa" && !estado.ocultos.has("pignoracion_" + x.id));
    const garantia = prest.reduce((a, x) => a + (x.garantia || 0), 0);
    const ltv = prest.length && prest[0].ltvMax ? prest[0].ltvMax / 100 : null;
    const meses = Math.round(anos * 12);
    const deuda = deudaMensual(meses);
    const r = Montecarlo.simulaMemo({ cartera, garantia, deuda, aportacion: apor, anos, mu, sigma: mc.volP / 100,
      sigmaGarantia: mc.volG / 100, ltvMax: ltv, n: 1500, semilla: 20261012 });

    const base = new Date(D.fechaExtracto + "T00:00:00");
    const fechas = r.p50.map((_, i) => {
      const d = new Date(base.getFullYear(), base.getMonth() + i, 1);
      return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-01";
    });
    G.multiLinea($("#grafMC"), {
      fechas, alto: 260,
      series: [
        { nombre: "Bueno (1 de cada 10 acaba por encima)", valores: r.p90.map(Math.round), color: G.css("--s3") },
        { nombre: "Típico (mediana)", valores: r.p50.map(Math.round), color: G.css("--s1"), destacado: true },
        { nombre: "Malo (1 de cada 10 acaba por debajo)", valores: r.p10.map(Math.round), color: G.css("--s2") },
      ],
      formatoY: v => G.fmtEurCorto(v), formatoValor: v => G.fmtEur(v, 0),
    });

    const k = (e, v, n, cl) => `<div class="kpi"><div class="e">${e}</div><div class="v ${cl || ""}">${v}</div>${n ? `<div class="n">${n}</div>` : ""}</div>`;
    const tarjetas = [k(`Patrimonio neto en ${anos} años`, G.fmtEur(r.p50[meses], 0),
      `8 de cada 10 futuros acaban entre ${G.fmtEur(r.p10[meses], 0)} y ${G.fmtEur(r.p90[meses], 0)}`)];
    if (r.probDeudaMayor != null) {
      tarjetas.push(r.probLimite != null
        ? k("Probabilidad de tocar tu límite", G.fmtPct(r.probLimite, 0),
            `préstamo / garantía por encima del ${String(prest[0].ltvMax).replace(".", ",")} % en algún momento`, r.probLimite > 0.25 ? "neg" : "")
        : k("Probabilidad de tocar tu límite", "—", "indica el límite de tu entidad (LTV máximo) para calcularla"));
      tarjetas.push(k("Deuda mayor que la garantía", G.fmtPct(r.probDeudaMayor, 0),
        "probabilidad de que llegue a ocurrir en el plazo", r.probDeudaMayor > 0.1 ? "neg" : ""));
    }
    $("#mcResumen").className = "mcKpis";
    $("#mcResumen").innerHTML = tarjetas.join("");
    $("#mcNota").textContent = "Supone que la cartera y la garantía suben y bajan a la vez y que los rendimientos siguen una campana " +
      "con la rentabilidad y volatilidad de arriba. Los mercados reales tienen caídas más bruscas: tómalo como orden de magnitud, no como pronóstico.";
  }

  /* Deuda pendiente de los préstamos al final de cada mes de la proyección (según su cuadro). */
  function deudaMensual(meses) {
    const prest = (D.pignoraciones || []).filter(x => x.estado === "activa" && !estado.ocultos.has("pignoracion_" + x.id));
    if (!prest.length) return null;
    const base = new Date(D.fechaExtracto + "T00:00:00");
    return Array.from({ length: meses + 1 }, (_, m) => {
      const f = new Date(base.getFullYear(), base.getMonth() + m, base.getDate());
      const iso = f.getFullYear() + "-" + String(f.getMonth() + 1).padStart(2, "0") + "-" + String(f.getDate()).padStart(2, "0");
      return prest.reduce((a, x) => {
        let saldo = x.saldo;
        for (const r of ((x.calendario && x.calendario.futuro) || [])) {
          if (r.fecha <= iso) saldo = r.pendiente; else break;
        }
        return a + saldo;
      }, 0);
    });
  }

  function pintaProyeccion() {
    const anos = +$("#rAnos").value, rent = +$("#rRent").value / 100, apor = +$("#rApor").value;
    $("#vAnos").textContent = anos;
    $("#vRent").textContent = $("#rRent").value.replace(".", ",") + " %";
    $("#vApor").textContent = G.fmtEur(apor, 0);
    document.querySelectorAll("#segModoProy button").forEach(b =>
      b.setAttribute("aria-pressed", String(b.dataset.m === proy.modo)));
    const global = proy.modo === "global";
    $("#etqRent").textContent = global ? "Rentabilidad anual" : "Rentabilidad sin objetivos";
    $("#proyActivos").hidden = global;

    const { activos, valorBase } = activosProyeccion();
    const entrada = (a) => ({ ...a, objetivo: proy.objetivos[a.id] > 0 ? proy.objetivos[a.id] : null });
    const deuda = deudaMensual(Math.round(anos * 12));
    const sim = Proyeccion.simula({ activos: activos.map(entrada), anos, modo: proy.modo,
                                    rentGlobal: rent, aportacion: apor, valorBase, deuda });

    // La tabla se vuelve a dibujar solo si cambian los activos o el modo: así no pierdes el foco al escribir.
    const clave = proy.modo + "|" + activos.map(a => a.id).join(",");
    if (!global && clave !== proy.clave) {
      proy.clave = clave;
      $("#tablaProy").innerHTML =
        `<thead><tr><th>Activo</th><th>Vale hoy</th><th>Precio hoy</th>
          <th>Precio dentro de <span id="anosTabla"></span> años</th><th>Rentab. anual</th><th>Valdría</th></tr></thead>
         <tbody>${activos.map(a => `<tr>
          <td><i class="pt" data-st="background:${a.color}"></i>${esc(a.nombre)}</td>
          <td>${G.fmtEur(a.valor, 0)}</td>
          <td>${a.precio != null ? G.fmtEur(a.precio, a.precio < 10 ? 3 : 2) : "—"}</td>
          <td><input type="number" min="0" step="any" class="inObj" data-id="${a.id}" placeholder="vacío"
               value="${proy.objetivos[a.id] ?? ""}" ${a.precio == null ? "disabled title='Sin precio de mercado'" : ""}
               data-st="width:96px;text-align:right"></td>
          <td data-r="${a.id}">—</td><td data-f="${a.id}">—</td></tr>`).join("")}</tbody>`;
      $("#tablaProy").querySelectorAll("input.inObj").forEach(inp => {
        inp.addEventListener("input", () => {
          const v = parseFloat(inp.value.replace(",", "."));
          if (v > 0) proy.objetivos[inp.dataset.id] = v; else delete proy.objetivos[inp.dataset.id];
          pintaProyeccion();
        });
      });
    }
    if (!global) {
      $("#anosTabla").textContent = anos;
      activos.forEach(a => {
        const r = sim.porActivo[a.id];
        const rc = $("#tablaProy").querySelector(`[data-r="${a.id}"]`);
        const fc = $("#tablaProy").querySelector(`[data-f="${a.id}"]`);
        if (!rc) return;
        rc.textContent = G.fmtPctSigno(r.rent, 1) + (r.propia ? "" : r.rent ? " (media)" : " (quieto)");
        rc.className = r.rent >= 0 ? "pos" : "neg";
        fc.textContent = G.fmtEur(r.final, 0);
      });
    }

    const base = new Date(D.fechaExtracto);
    const fechas = sim.total.map((_, i) =>
      new Date(base.getFullYear(), base.getMonth() + i, 1).toISOString().slice(0, 10));
    G.lineaConEventos($("#grafProy"), {
      fechas, valores: sim.total.map(Math.round), color: G.css("--s3"), alto: 250,
      overlay: { nombre: "Habré aportado", valores: sim.aportado.map(Math.round) },
    });

    const m0 = sim.total[0], fin = sim.total[sim.total.length - 1], apFin = sim.aportado[sim.aportado.length - 1];
    $("#proyNota").hidden = global;
    if (!global) {
      const hay = sim.media != null;
      $("#proyNota").textContent = hay
        ? `Media de tus objetivos: ${G.fmtPctSigno(sim.media, 1)} anual (solo cuentan los activos con precio objetivo). ` +
          `Tus aportaciones mensuales crecen a ese ritmo y no se atribuyen a ningún activo.`
        : `Aún no has puesto ningún precio objetivo: los activos ${proy.modo === "mixto" ? "usan" : "se quedan sin crecer; las aportaciones usan"} ` +
          `la rentabilidad de ${$("#rRent").value.replace(".", ",")} %.`;
    }
    const amortizado = deuda ? deuda[0] - deuda[deuda.length - 1] : 0;
    $("#proyResumen").innerHTML =
      `Partiendo de ${G.fmtEur(m0, 0)}${filtrando() ? " (vista filtrada)" : ""},
       en <b class="fuerte">${anos} años</b> tendrías <b class="fuerte">${G.fmtEur(fin, 0)}</b>
       <span data-st="color:var(--tinta3)">·</span> habrías aportado ${G.fmtEur(apFin, 0)}
       <span data-st="color:var(--tinta3)">·</span> el mercado pondría
       <span class="pos fuerte">${G.fmtEur(fin - m0 - apFin - amortizado, 0)}</span>` +
      (amortizado > 0 ? ` <span data-st="color:var(--tinta3)">·</span> habrás amortizado
       <b class="fuerte">${G.fmtEur(amortizado, 0)}</b> del préstamo (sus cuotas salen de tu sueldo, no de la aportación)` : "");
  }

  /* ================================================================
     RESUMEN · la cabina: qué debo mirar ahora
     ================================================================ */
  const hoyIso = () => D.fechaExtracto;
  const diasHasta = iso => Math.round((Date.parse(iso) - Date.parse(hoyIso())) / 86400000);
  const ico = d => `<svg class="ico" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" ` +
    `stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
  const ICO_ALERTA = ico('<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18h.01"/>');
  const ICO_INFO = ico('<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5h.01"/>');
  // Rosa de los vientos (motivo de la dirección visual): marca los estados vacíos y siempre es decorativa.
  const ICO_ROSA = '<svg class="rosa" viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="9"/><path d="M12 3.5l2 6.5 6.5 2-6.5 2-2 6.5-2-6.5-6.5-2 6.5-2z"/></svg>';
  const ICO_LOCK = ico('<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 018 0v3"/>');
  const pctTxt = (x, d = 1) => x == null ? "—" : G.fmtPct(x, d);
  const NIVEL_ET = { bajo: "Holgado", medio: "Atención", alto: "Ajustado", peligro: "Por encima del límite" };
  const nivelEt = (n, limite) => n === "peligro" && !limite ? "Deuda mayor que la garantía" : (NIVEL_ET[n] || "Activa");
  const NIVEL_CL = { bajo: "ok", medio: "warn", alto: "warn", peligro: "danger" };

  /* ---- Avisos de datos en lenguaje llano ---- */
  const nombreDeCodigo = cod => {
    const c = String(cod).replace(/\.F$/, "");
    const p = D.productos.concat(D.otrosActivos || []).find(x => x.codigo === cod || x.codigo === c);
    return p ? (p.corto || p.nombre) : cod;
  };
  const diasEntre = (a, b) => Math.round((Date.parse(b) - Date.parse(a)) / 86400000);
  const lista = arr => arr.length > 2 ? arr.slice(0, -1).join(", ") + " y " + arr[arr.length - 1] : arr.join(" y ");

  /* ---- Alertas del Resumen: solo lo accionable, y descartables ---- */
  const ocultas = () => { try { return JSON.parse(recuerda.lee("patrimonio.alertasOcultas") || "{}"); } catch (e) { return {}; } };
  function descarta(clave) {
    const o = ocultas();
    o[clave] = Date.now();
    Object.keys(o).forEach(k => { if (Date.now() - o[k] > 90 * 86400000) delete o[k]; });   // se olvidan a los 90 días
    recuerda.guarda("patrimonio.alertasOcultas", JSON.stringify(o));
  }

  /* Texto de cada alerta (qué sale y cuándo lo decide Alertas.calcula, en alertas.js). */
  function textoAlerta(a) {
    const x = a.pig;
    switch (a.tipo) {
      case "ltv":
        if (a.sub === "limite") {
          return `<b>${esc(x.nombre)}:</b> el préstamo es el ${pctTxt(x.ratio)} de la garantía y tu límite es el ` +
            `${String(x.ltvMax).replace(".", ",")} %. Para volver al límite habría que amortizar ` +
            `<b>${G.fmtEur(x.amortizarParaLimite, 0)}</b> o añadir ${G.fmtEur(x.garantiaAnadirParaLimite, 0)} de garantía.`;
        }
        if (a.sub === "deuda") {
          return `<b>${esc(x.nombre)}:</b> la deuda (${G.fmtEur(x.saldo, 0)}) supera ya el valor de la garantía (${G.fmtEur(x.garantia, 0)}).`;
        }
        return `<b>${esc(x.nombre)}:</b> el préstamo es el ${pctTxt(x.ratio)} de la garantía. Si esos activos caen un ` +
          `${pctTxt(x.caidaHastaLimite != null ? x.caidaHastaLimite : x.caidaHastaIgualar)}, ` +
          `${x.caidaHastaLimite != null ? "tocarías el límite de tu entidad" : "la garantía igualaría la deuda"}.`;
      case "cuota":
        return `Cuota de <b>${esc(x.nombre)}</b> ${a.dias === 0 ? "hoy" : a.dias === 1 ? "mañana" : "en " + a.dias + " días"}: ` +
          `${G.fmtEur(x.proxima.cuota)} (${G.fmtFecha(x.proxima.fecha)}). Ten el saldo disponible.`;
      case "sinRed":
        return `No he podido descargar el precio de <b>${esc(lista(a.codigos.map(nombreDeCodigo)))}</b> (sin conexión con la fuente). ` +
          `Se usa el último valor guardado.`;
      case "viejo":
        return `Precio desactualizado: <b>${esc(lista(a.nombres))}</b>. El último que tengo es del ${G.fmtFecha(a.fecha)}` +
          (a.dias != null ? ` (hace ${a.dias} días).` : ".");
      case "desvio":
        return `Tu cartera se desvía <b>${String(a.pp.toFixed(1)).replace(".", ",")} puntos</b> de lo que querías` +
          `${a.grupo ? ` en <b>${esc(a.grupo)}</b>` : ""} (tu aviso salta a partir de ${String(a.umbral).replace(".", ",")}). Revisa cómo repartir tu próxima aportación.`;
      case "datosViejos":
        return `Los precios son de hace ${a.dias} días. Pulsa «Actualizar precios».`;
    }
    return "";
  }

  const UMBRALES_DEFECTO = { concentracionProducto: 15, concentracionValor: 5, desviacionAsignacion: 5, ltvAtencion: 75, ltvAlto: 90 };
  const umbralesAl = () => Object.assign({}, UMBRALES_DEFECTO, (D.alertas && D.alertas.umbrales) || {});

  // Mayor desvío (en puntos) entre lo que tienes y el objetivo de cada grupo; null si no hay objetivos.
  function desvioAsignacion() {
    const obj = (D.asignacion && D.asignacion.objetivos) || {};
    if (!Object.keys(obj).length) return { max: null, grupo: null };
    const filas = Asignacion.reparto(gruposAsignacion().map(g => ({ id: g.id, valor: g.valor, objetivo: obj[g.id] != null ? obj[g.id] : null })), 0);
    let max = null, grupo = null;
    filas.forEach(f => { if (f.desviacion != null && (max == null || Math.abs(f.desviacion) > max)) { max = Math.abs(f.desviacion); grupo = f.id; } });
    return { max, grupo };
  }

  function alertas() {
    const dv = desvioAsignacion();
    return Alertas.calcula({
      desvioMax: dv.max, desvioGrupo: dv.grupo, umbralDesvio: umbralesAl().desviacionAsignacion,
      pignoraciones: D.pignoraciones, avisos: D.avisos, preciosActualizados: D.preciosActualizados,
      ahora: Date.now(), fechaExtracto: D.fechaExtracto, estatico: !!window.ESTATICO, demo: D.modo === "demo",
      ocultas: ocultas(), filtrando: filtrando(),
    });
  }

  function pintaCockpit() {
    const el = $("#cockpit");
    if (!el) return;
    const todos = TODOS().filter(enseñable);
    const bruto = todos.filter(p => valorDe(p) > 0).reduce((a, p) => a + valorDe(p), 0);
    const deuda = -todos.filter(p => valorDe(p) < 0).reduce((a, p) => a + valorDe(p), 0);

    const idx = D.indiceCartera || [], n = idx.length;
    const var_ = dias => (n - 1 - dias >= 0 && idx[n - 1 - dias]) ? idx[n - 1] / idx[n - 1 - dias] - 1 : null;
    const ini = D.fechas.findIndex(f => f >= D.fechaExtracto.slice(0, 4) + "-01-01");
    const ytd = ini > 0 && idx[ini - 1] ? idx[n - 1] / idx[ini - 1] - 1 : (ini === 0 && idx[0] ? idx[n - 1] / idx[0] - 1 : null);
    const celda = (e, v, nota) => `<div class="c"><div class="e">${e}</div>
      <div class="v ${v == null ? "" : v >= 0 ? "pos" : "neg"}">${v == null ? "—" : G.fmtPctSigno(v, 2)}</div>
      <div class="n">${nota}</div></div>`;

    const { alertas: al, filtrada } = alertas();
    const esteMes = [];
    // La cuota que ya sale como alerta no se repite aquí.
    const cuotaAvisada = new Set(al.filter(a => a.tipo === "cuota").map(a => a.id));
    (D.pignoraciones || []).filter(x => x.estado === "activa" && x.proxima && !cuotaAvisada.has(x.id)).forEach(x =>
      esteMes.push({ cuando: G.fmtFechaCorta(x.proxima.fecha), t: `Cuota de ${esc(x.nombre)}: <b>${G.fmtEur(x.proxima.cuota)}</b>` }));
    const am = D.aportacionesMensuales || { meses: [], total: [] };
    const mesAct = D.fechaExtracto.slice(0, 7);
    const iMes = am.meses.indexOf(mesAct);
    const llevas = iMes >= 0 ? am.total[iMes] : 0;
    const ritmo = D.total.ritmoMensual || 0;
    if (ritmo) {
      esteMes.push({ cuando: "Este mes",
        t: llevas >= ritmo * 0.95 ? `Has aportado <b>${G.fmtEur(llevas, 0)}</b>: ya cubres tu ritmo habitual (${G.fmtEur(ritmo, 0)}).`
          : `Llevas <b>${G.fmtEur(llevas, 0)}</b> de tu ritmo habitual de ${G.fmtEur(ritmo, 0)}.` });
    }
    // Anotar el límite solo se puede en la app; la TIR del capital propio ya está en los indicadores.
    if (!window.ESTATICO) {
      (D.pignoraciones || []).filter(x => x.estado === "activa" && !x.ltvMax).forEach(x =>
        esteMes.push({ cuando: "Dato", t: `Anota el <b>límite de LTV</b> de «${esc(x.nombre)}» (en tu contrato) para medir tu margen real.` }));
    }

    el.innerHTML = `
      ${filtrada ? `<p class="subt" data-st="margin:0 0 10px">Vista filtrada: esta zona (avisos, patrimonio y rentabilidad reciente) es de toda la cartera.</p>` : ""}
      ${al.length ? `<div class="alertas">${al.map(a => `<div class="alerta ${a.cl}" role="${a.cl === "danger" ? "alert" : "status"}">
          ${a.cl === "info" ? ICO_INFO : ICO_ALERTA}<div class="txt">${textoAlerta(a)}</div>
          <div class="acciones">${a.ir ? `<button class="btn" data-ir="${a.ir}">${esc(a.irEt || "Ver riesgo")}</button>` : ""}
            ${a.accion === "actualizar" ? `<button class="btn" data-actualizar>Actualizar</button>` : ""}
            ${!a.descartable ? "" : `<button class="btn suave" data-cierra="${esc(a.clave)}" aria-label="Descartar este aviso" title="Descartar: volverá a salir si la situación cambia">✕</button>`}</div>
        </div>`).join("")}</div>` : ""}
      <div class="cockGrid">
        <div>
          <div class="patrim">
            <div class="c"><div class="e">Bruto (lo que tienes)</div><div class="v">${G.fmtEur(bruto, 0)}</div></div>
            <div class="c"><div class="e">Deuda</div><div class="v ${deuda ? "neg" : ""}">${deuda ? "−" + G.fmtEur(deuda, 0) : G.fmtEur(0, 0)}</div></div>
            <div class="c"><div class="e">Neto</div><div class="v">${G.fmtEur(bruto - deuda, 0)}</div></div>
          </div>
          <div class="variaciones" aria-label="Rentabilidad reciente de la cartera">
            ${celda("Hoy", var_(1), "rentabilidad de 1 día")}
            ${celda("Último mes", var_(30), "rentabilidad, sin aportaciones")}
            ${celda("En el año", ytd, "rentabilidad del año en curso")}
          </div>
        </div>
        <section class="tarjeta estaMes" aria-labelledby="estaMesTit">
          <header><h2 id="estaMesTit">Este mes</h2></header>
          ${esteMes.length ? `<ul>${esteMes.map(i => `<li><span class="cuando">${i.cuando}</span><span>${i.t}</span></li>`).join("")}</ul>`
            : `<p class="vacio">${ICO_ROSA}Nada pendiente: todo al día.</p>`}
        </section>
      </div>`;
    el.querySelectorAll("[data-ir]").forEach(b => { b.onclick = () => irA(b.dataset.ir); });
    el.querySelectorAll("[data-cierra]").forEach(b => { b.onclick = () => { descarta(b.dataset.cierra); pintaCockpit(); }; });
    el.querySelectorAll("[data-actualizar]").forEach(b => { b.onclick = () => actualizaPrecios(); });
  }

  /* ================================================================
     POSICIONES · tabla agrupable con panel de detalle
     ================================================================ */
  const pos = { agrupar: recuerda.lee("patrimonio.agrupar") || "tipo", orden: { col: "valor", desc: true }, q: "" };
  const AGRUPAR = [{ id: "tipo", et: "Tipo" }, { id: "garantia", et: "En garantía" }, { id: "clase", et: "Categoría" }, { id: "ninguno", et: "Sin agrupar" }];

  function badgeGarantia(p) {
    return p.pignoradoEn && p.pignoradoEn.length
      ? `<span class="badge lock" title="Pignorado en «${esc(p.pignoradoEn.map(x => x.nombre).join("», «"))}»: no se puede vender hasta liquidar">${ICO_LOCK} En garantía</span>` : "";
  }

  function filasPos() {
    const items = TODOS().filter(enseñable).filter(p => valorDe(p) >= 0 && !(p.derivado && p.tipoClave === "deuda"));
    const bruto = items.reduce((a, p) => a + valorDe(p), 0) || 1;
    return items.map(p => {
      const pl = plusvaliaDe(p);
      return { p, id: p.id, nombre: p.corto || p.nombre, clase: p.clase || "Otros", tipo: p.tipo || "Otros",
        valor: valorDe(p), peso: valorDe(p) / bruto, plus: pl ? pl.eur : null, pct: pl ? pl.pct : null,
        tir: p.tir != null ? p.tir : null, garantia: p.pignoradoEn && p.pignoradoEn.length ? "En garantía" : "Libre" };
    });
  }

  function pintaPosiciones() {
    const tabla = $("#tablaPos");
    if (!tabla) return;
    pintaSegm($("#segAgrupar"), AGRUPAR, pos.agrupar, id => { pos.agrupar = id; recuerda.guarda("patrimonio.agrupar", id); pintaPosiciones(); });
    const buscar = $("#posBuscar");
    if (buscar && buscar.value !== pos.q) buscar.value = pos.q;
    let filas = filasPos();
    const q = pos.q.trim().toLowerCase();
    if (q) filas = filas.filter(f => (f.p.nombre + " " + (f.p.identificador || "") + " " + f.clase).toLowerCase().includes(q));
    const o = pos.orden;
    const cmp = (a, b) => {
      const va = a[o.col], vb = b[o.col];
      const c = va == null ? -1 : vb == null ? 1 : typeof va === "string" ? va.localeCompare(vb, "es") : va - vb;
      return o.desc ? -c : c;
    };
    const cols = [["nombre", "Producto", false], ["clase", "Categoría", false], ["peso", "Peso", true], ["valor", "Valor", true],
      ["plus", "Plusvalía", true], ["pct", "Rentab.", true], ["tir", "TIR", true]];
    const cabecera = cols.map(([c, et]) => {
      const act = o.col === c;
      return `<th class="orden${c === "clase" ? " c-clase" : ""}" data-c="${c}" aria-sort="${act ? (o.desc ? "descending" : "ascending") : "none"}" tabindex="0">${et}${act ? (o.desc ? " ↓" : " ↑") : ""}</th>`;
    }).join("");
    const fila = f => `<tr class="fila" data-id="${esc(f.id)}" tabindex="0">
        <td class="nom"><i class="pt" data-st="background:${color(f.p)}"></i>${esc(f.nombre)} ${badgeGarantia(f.p)}</td>
        <td class="c-clase">${esc(f.clase)}</td><td>${G.fmtPct(f.peso, 1)}</td><td>${G.fmtEur(f.valor)}</td>
        <td class="${f.plus == null ? "" : f.plus >= 0 ? "pos" : "neg"}">${f.plus == null ? "—" : G.fmtEurSigno(f.plus)}</td>
        <td class="${f.pct == null ? "" : f.pct >= 0 ? "pos" : "neg"}">${f.pct == null ? "—" : G.fmtPctSigno(f.pct, 1)}</td>
        <td class="${f.tir == null ? "" : f.tir >= 0 ? "pos" : "neg"}">${f.tir == null ? "—" : G.fmtPctSigno(f.tir, 1)}</td></tr>`;
    let cuerpo = "";
    if (pos.agrupar === "ninguno") cuerpo = filas.sort(cmp).map(fila).join("");
    else {
      const g = new Map();
      filas.forEach(f => { const k = f[pos.agrupar]; (g.get(k) || g.set(k, []).get(k)).push(f); });
      [...g.entries()].sort((a, b) => b[1].reduce((s, f) => s + f.valor, 0) - a[1].reduce((s, f) => s + f.valor, 0))
        .forEach(([k, items]) => {
          const tot = items.reduce((s, f) => s + f.valor, 0), pes = items.reduce((s, f) => s + f.peso, 0);
          cuerpo += `<tr class="grupo"><td colspan="2">${esc(k)} · ${items.length}</td><td>${G.fmtPct(pes, 1)}</td><td>${G.fmtEur(tot)}</td><td colspan="3"></td></tr>`
            + items.sort(cmp).map(fila).join("");
        });
    }
    const total = filas.reduce((a, f) => a + f.valor, 0);
    tabla.innerHTML = `<thead><tr>${cabecera}</tr></thead><tbody>${cuerpo || '<tr><td colspan="7" class="vacio">Ningún producto coincide con la búsqueda.</td></tr>'}</tbody>
      <tfoot><tr class="filaTotal"><td colspan="3">Total ${filas.length} productos</td><td>${G.fmtEur(total)}</td><td colspan="3"></td></tr></tfoot>`;
    $("#posNota").textContent = pos.agrupar === "ninguno" ? "Pulsa una fila para ver su ficha" : "Agrupadas · pulsa una fila para ver su ficha";
    tabla.querySelectorAll("th.orden").forEach(th => {
      const act = () => { const c = th.dataset.c; pos.orden = { col: c, desc: pos.orden.col === c ? !pos.orden.desc : c !== "nombre" && c !== "clase" }; pintaPosiciones(); };
      th.onclick = act;
      th.onkeydown = e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); act(); } };
    });
    tabla.querySelectorAll("tr.fila").forEach(tr => {
      const abre = () => abreDetalle(tr.dataset.id);
      tr.onclick = abre;
      tr.onkeydown = e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); abre(); } };
    });
  }

  let ultimoFoco = null;
  function abreDetalle(id) {
    estado.fondo = id;
    ultimoFoco = document.activeElement;
    $("#drawer").hidden = false;
    $("#drawerVelo").hidden = false;
    pintaDetalle();
    $("#drawer").focus();
  }
  function cierraDetalle() {
    $("#drawer").hidden = true;
    $("#drawerVelo").hidden = true;
    if (ultimoFoco && ultimoFoco.focus) ultimoFoco.focus();
  }

  /* ================================================================
     RIESGO Y DEUDA · préstamos con garantía y concentración
     ================================================================ */
  function medidorLtv(x) {
    const r = Math.min(1, x.ratio || 0) * 100;
    const lim = x.ltvMax ? Math.min(100, x.ltvMax) : null;
    const zonas = Alertas.zonasLtv(x.ltvMax, umbralesAl());
    const num = v => String(v).replace(".", ",");
    const leyenda = zonas.map(z => `${z.et} desde ${num(z.en)} %`).join(" · ");
    return `<div class="medidor" role="img" aria-label="Préstamo sobre garantía: ${pctTxt(x.ratio)}${lim ? `, límite ${num(x.ltvMax)} %` : ""}. Zonas: ${leyenda}">
      <div class="pista"><div class="nivel ${x.nivel || ""}" data-st="width:${r.toFixed(1)}%"></div>
        ${zonas.map(z => `<i class="zonaLtv ${z.cl}" data-st="left:${z.en}%"></i>`).join("")}
        ${lim ? `<div class="marca" data-st="left:${lim}%"></div><span class="marcaEt" data-st="left:${Math.min(Math.max(lim, 12), 88)}%">límite ${num(x.ltvMax)} %</span>` : ""}</div>
      <div class="eje"><span>0 %</span><span>50 %</span><span>100 % de la garantía</span></div>
      <div class="zonasLey"><i class="zonaLtv warn"></i>atención desde ${num(zonas[0].en)} % <i class="zonaLtv danger"></i>riesgo alto desde ${num(zonas[1].en)} %</div></div>`;
  }

  function tarjetaPrestamo(x) {
    const activa = x.estado === "activa";
    const kpi = (e, v, n) => `<div class="kpi"><div class="e">${e}</div><div class="v">${v}</div>${n ? `<div class="n">${n}</div>` : ""}</div>`;
    let lectura = "";
    if (activa && x.ratio != null) {
      if (x.superaLimite) {
        lectura = `<p><b class="neg">Estás por encima del límite de tu entidad.</b> Para volver a él tendrías que amortizar
          <b>${G.fmtEur(x.amortizarParaLimite, 0)}</b> o añadir <b>${G.fmtEur(x.garantiaAnadirParaLimite, 0)}</b> de garantía.</p>`;
      } else if (x.caidaHastaLimite != null) {
        lectura = `<p>La garantía puede caer un <b>${pctTxt(x.caidaHastaLimite)}</b> (hasta ${G.fmtEur(x.garantiaMinima, 0)}) antes de tocar el
          límite del ${String(x.ltvMax).replace(".", ",")} %. Con una caída del ${pctTxt(x.caidaHastaIgualar)} valdría lo mismo que la deuda.</p>`;
      } else {
        lectura = `<p>Si la garantía cae un <b>${pctTxt(x.caidaHastaIgualar)}</b>, valdrá lo mismo que la deuda. Aún no has indicado el
          límite de tu entidad (LTV máximo): añádelo al editar la pignoración para medir tu margen real.</p>`;
      }
    }
    const stress = activa && x.stress && x.stress.length ? `
      <h3 class="sub">¿Y si el mercado cae?</h3>
      <div class="tablaEnv"><table class="dt stress"><thead><tr><th>Caída de la garantía</th><th>Garantía</th><th>Préstamo / garantía</th><th>Estado</th></tr></thead>
        <tbody>${x.stress.map(s => `<tr class="${s.nivel}"><td>−${Math.round(s.caida * 100)} %</td><td>${G.fmtEur(s.garantia, 0)}</td>
          <td>${pctTxt(s.ratio)}</td><td><span class="badge ${NIVEL_CL[s.nivel]}">${nivelEt(s.nivel, x.ltvMax)}</span></td></tr>`).join("")}</tbody></table></div>` : "";
    const cal = x.calendario || { proximas: [], saldoAnual: [] };
    const calend = activa && cal.proximas.length ? `
      <h3 class="sub">Próximas cuotas y deuda a final de año</h3>
      <div class="rejilla2" data-st="margin-top:8px">
        <div class="tablaEnv"><table class="dt"><thead><tr><th>Fecha</th><th>Cuota</th><th>Intereses</th><th>Amortizas</th><th>Queda</th></tr></thead>
          <tbody>${cal.proximas.slice(0, 6).map(r => `<tr><td>${G.fmtFecha(r.fecha)}</td><td>${G.fmtEur(r.cuota)}</td><td>${G.fmtEur(r.intereses)}</td>
            <td>${G.fmtEur(r.amortizado)}</td><td>${G.fmtEur(r.pendiente)}</td></tr>`).join("")}</tbody></table></div>
        <div class="tablaEnv"><table class="dt"><thead><tr><th>Cierre de año</th><th>Deuda pendiente</th></tr></thead>
          <tbody>${cal.saldoAnual.slice(0, 8).map(r => `<tr><td>${r.ano}</td><td>${G.fmtEur(r.saldo, 0)}</td></tr>`).join("")}</tbody></table></div>
      </div>` : "";
    return `<section class="tarjeta" data-st="margin-top:16px" aria-labelledby="pr-${esc(x.id)}">
      <header>
        <h2 id="pr-${esc(x.id)}">${esc(x.nombre)}</h2>
        ${activa ? `<span class="badge ${NIVEL_CL[x.nivel] || ""}">${nivelEt(x.nivel, x.ltvMax)}</span>` : '<span class="badge ok">Liquidada</span>'}
        ${x.entidad ? `<span class="subt">${esc(x.entidad)}</span>` : ""}
        <div class="sep"></div>
        ${window.ESTATICO ? "" : '<button class="btn" data-gestion>Gestionar en Datos</button>'}
      </header>
      ${activa ? `<div class="riesgoGrid">
          ${kpi("Préstamo / garantía", pctTxt(x.ratio), x.ltvMax ? "límite " + String(x.ltvMax).replace(".", ",") + " %" : "límite sin indicar")}
          ${kpi("Deuda pendiente", G.fmtEur(x.saldo), x.devengado ? "+" + G.fmtEur(x.devengado) + " de intereses devengados" : "")}
          ${kpi("Garantía hoy", G.fmtEur(x.garantia, 0), x.activosDetalle.length + (x.activosDetalle.length === 1 ? " activo" : " activos"))}
          ${kpi("Cuota", G.fmtEur(x.cuota), x.proxima ? "próxima: " + G.fmtFecha(x.proxima.fecha) : "")}
          ${kpi("Interés anual", String(x.interes).replace(".", ",") + " %", x.comisionApertura ? "apertura " + G.fmtEur(x.comisionApertura) : "sin comisión de apertura")}
          ${kpi("Intereses", G.fmtEur(x.interesesPagados, 0) + " pagados", G.fmtEur(x.interesesRestantes, 0) + " por pagar")}
        </div>
        ${medidorLtv(x)}${lectura}${stress}${calend}
        <h3 class="sub">Liquidarla</h3>
        <p>Cancelarla hoy costaría <b>${G.fmtEur(x.aLiquidar)}</b> (deuda ${G.fmtEur(x.saldo)} + intereses devengados ${G.fmtEur(x.devengado)}${x.penalizacion ? ` + comisión de cancelación ${G.fmtEur(x.penalizacion)}` : ""})
          y te ahorraría unos <b class="pos">${G.fmtEur(Math.max(0, x.ahorroSiLiquidas), 0)}</b> de intereses. Coste total del préstamo: ${G.fmtEur(x.costeTotal, 0)}.</p>
        <details class="faq"><summary>Qué implica tener activos pignorados</summary><div><ul>
          <li><b>Bloqueo:</b> no puedes vender ${x.activosDetalle.length > 1 ? "esos activos" : "ese activo"} hasta liquidar el préstamo.</li>
          <li><b>Liquidación forzosa:</b> si su valor baja demasiado, la entidad puede pedirte más garantía o vender por ti, aunque sea en mal momento.</li>
          <li><b>Coste:</b> pagas un ${String(x.interes).replace(".", ",")} % anual; lo que reinviertas debe rendir más que eso para compensar.</li>
          <li><b>Patrimonio neto:</b> la deuda se resta de tu patrimonio, así que no se infla con el dinero recibido.</li></ul></div></details>
        <div class="activos" data-st="margin-top:12px">${x.activosDetalle.map(a => `<span class="badge lock">${ICO_LOCK} ${esc(a.nombre)} · ${G.fmtEur(a.valor, 0)}</span>`).join(" ")}</div>`
      : `<p class="subt">Liquidada el ${G.fmtFecha(x.fechaLiquidacion)}. Recibiste ${G.fmtEur(x.recibido)} y has pagado ${G.fmtEur(x.interesesPagados)} de intereses.</p>`}
    </section>`;
  }

  function tarjetaTransparencia() {
    const T = D.transparencia;
    if (!T || !T.items || !T.items.length) return "";
    const top = T.items.slice(0, 10);
    const UMBRAL = umbralesAl().concentracionValor / 100;
    const cub = (T.cobertura || []).length;
    return `<section class="tarjeta" data-st="margin-top:16px" aria-labelledby="transpTit">
      <header><h2 id="transpTit">Qué tienes de verdad dentro</h2>
        <span class="subt">Mayores posiciones de tus fondos, sumadas, más tus acciones directas</span></header>
      <div class="conc">${top.map(i => `<div class="f ${i.peso > UMBRAL ? "alta" : ""}" title="${esc(i.fuentes.map(f => f.producto + ": " + G.fmtEur(f.valor, 0) + (f.directa ? " (directa)" : "")).join(" · "))}">
          <span>${esc(i.nombre)}${i.pais ? ` <small class="subt">${esc(i.pais)}</small>` : ""}</span>
          <span class="b"><i data-st="width:${Math.min(100, i.peso * 100 * 3).toFixed(1)}%"></i></span>
          <span class="p">${G.fmtPct(i.peso, 1)}</span></div>`).join("")}</div>
      <p class="subt" data-st="margin-top:12px">Es un <b>mínimo</b>: de cada fondo solo se conocen sus mayores posiciones
        (datos de ${cub} ${cub === 1 ? "fondo" : "fondos"}${T.fecha ? ", a " + G.fmtFecha(T.fecha) : ""}).
        ${(T.sinDatos || []).length ? "Sin datos: " + esc(T.sinDatos.slice(0, 6).join(", ")) + (T.sinDatos.length > 6 ? "…" : "") + "." : ""}
        ${(T.cobertura || []).filter(c => c.cubierto < 10).length ? "Casi sin datos (menos del 10 % del fondo): " +
          esc(T.cobertura.filter(c => c.cubierto < 10).map(c => c.nombre).join(", ")) + "." : ""}
        Pasa el ratón por una fila para ver de dónde sale.</p>
    </section>`;
  }

  /* ================================================================
     INGRESOS · dividendos e intereses cobrados (D.ingresos, ver ingresos.py)
     No viaja en la web exportada: sin importes no hay nada que enseñar.
     ================================================================ */
  function pintaIngresos() {
    const cont = $("#ingresos");
    if (!cont) return;
    const I = D.ingresos;
    if (!I || window.OCULTAR_IMPORTES || window.ESTATICO) { cont.innerHTML = ""; return; }
    if (!I.porMes.length) {
      cont.innerHTML = `<section class="tarjeta"><header><h2>Ingresos</h2></header>
        <p class="vacio">${ICO_ROSA}Aún no has anotado ningún dividendo ni interés cobrado.</p></section>`;
      return;
    }
    // Últimos 12 meses naturales, con los meses sin cobro a cero.
    const fin = (D.fechaExtracto || I.porMes[I.porMes.length - 1].mes).slice(0, 7);
    let [y, m] = fin.split("-").map(Number);
    const meses = [];
    for (let i = 0; i < 12; i++) { meses.unshift(`${y}-${String(m).padStart(2, "0")}`); if (--m === 0) { m = 12; y--; } }
    const porMes = Object.fromEntries(I.porMes.map(x => [x.mes, x.total]));
    const T = I.total;
    const kpi = (e, v, n) => `<div class="kpi"><div class="e">${e}</div><div class="v">${v}</div>${n ? `<div class="n">${n}</div>` : ""}</div>`;
    const filasProd = I.productos.map(p => `<tr><td>${esc(p.nombre)}</td><td>${G.fmtEur(p.ultimosDoce)}</td>
      <td>${G.fmtPct(p.yieldOnCost, 2)}</td><td>${G.fmtPct(p.yieldActual, 2)}</td><td>${G.fmtFecha(p.ultimaFecha)}</td></tr>`).join("");
    const filasAno = I.porAno.slice().reverse().map(a => `<tr><td>${a.ano}${a.ultimosDoce ? " (en curso)" : ""}</td><td>${G.fmtEur(a.total)}</td></tr>`).join("");
    cont.innerHTML = `
      <section class="tarjeta" aria-labelledby="ingTit">
        <header><h2 id="ingTit">Ingresos por dividendos</h2><span class="subt">Lo cobrado en los últimos 12 meses</span></header>
        <div class="riesgoGrid">
          ${kpi("Cobrado en 12 meses", G.fmtEur(T.ultimosDoce), "dividendos e intereses")}
          ${kpi("Sobre lo que pagaste", G.fmtPct(T.yieldOnCostCartera, 2), "yield on cost de la cartera")}
          ${kpi("Sobre su valor hoy", G.fmtPct(T.yieldActualCartera, 2), "rendimiento actual de la cartera")}
        </div>
        <div id="grafIngresos" data-titulo="Ingresos cobrados por mes"></div>
        <div class="tablaEnv"><table class="dt"><thead><tr><th>Producto</th><th>12 meses</th><th>Sobre coste</th><th>Sobre valor</th><th>Último cobro</th></tr></thead>
          <tbody>${filasProd}</tbody></table></div>
        <div class="tablaEnv" data-st="margin-top:16px"><table class="dt"><thead><tr><th>Año</th><th>Cobrado</th></tr></thead>
          <tbody>${filasAno}</tbody></table></div>
      </section>`;
    G.barrasSimples($("#grafIngresos"), {
      categorias: meses.map(G.fmtMes), valores: meses.map(k => porMes[k] || 0), formatoY: G.fmtEurCorto, formatoValor: v => v ? G.fmtEurCorto(v) : "", alto: 220, color: G.css("--s1"),
    });
  }

  /* ================================================================
     FISCALIDAD · orientación del ahorro (IRPF)
     ================================================================ */
  const fis = { ano: null };

  function pintaFiscal() {
    const cont = $("#fiscal");
    if (!cont) return;
    const F = D.fiscal;
    if (!F || window.OCULTAR_IMPORTES) {
      cont.innerHTML = `<section class="tarjeta"><header><h2>Fiscalidad</h2></header>
        <p class="vacio">${window.ESTATICO ? "Esta versión exportada no incluye la fiscalidad." : "Todavía no hay ventas ni dividendos anotados de los que calcular nada."}</p></section>`;
      return;
    }
    const anos = F.anos.map(a => a.ano);
    if (!anos.length) {
      cont.innerHTML = `<section class="tarjeta"><header><h2>Fiscalidad</h2></header>
        <p class="vacio">${ICO_ROSA}Aún no has anotado ninguna venta ni dividendo: no hay nada que declarar de momento.</p></section>${tarjeta720(F)}`;
      return;
    }
    if (fis.ano == null || !anos.includes(fis.ano)) fis.ano = anos[anos.length - 1];
    const a = F.anos.find(x => x.ano === fis.ano);
    const kpi = (e, v, n, cl) => `<div class="kpi"><div class="e">${e}</div><div class="v ${cl || ""}">${v}</div>${n ? `<div class="n">${n}</div>` : ""}</div>`;
    const filas = a.ventas.map(v => `<tr class="${v.diferida ? "alto" : ""}">
        <td>${G.fmtFecha(v.fecha)}</td><td>${esc(v.nombre)}</td>
        <td>${v.reembolso ? "—" : G.nfNum.format(v.unidades)}</td>
        <td>${v.reembolso ? "—" : G.fmtEur(v.importe)}</td><td>${v.reembolso ? "—" : G.fmtEur(v.coste)}</td>
        <td class="${v.resultado >= 0 ? "pos" : "neg"}">${G.fmtEurSigno(v.resultado)}</td>
        <td>${v.diferida ? `<span class="badge warn" title="Compraste valores homogéneos el ${G.fmtFecha(v.recompra)}, dentro del plazo de ${v.plazo}">Pérdida diferida · recompra ${G.fmtFecha(v.recompra)}</span>`
          : v.reembolso ? '<span class="badge">Plusvalía de reembolso</span>' : v.resultado < 0 ? '<span class="badge ok">Computa</span>' : ""}</td></tr>`).join("");
    cont.innerHTML = `
      <div class="alerta warn" role="note">${ICO_ALERTA}<div><b>Orientativo, no es tu declaración.</b> ${esc(F.aviso)}</div></div>
      <section class="tarjeta" data-st="margin-top:16px" aria-labelledby="fisTit">
        <header><h2 id="fisTit">Ahorro ${a.ano}</h2><div class="sep"></div>
          <div class="segm" id="segFiscalAno" role="group" aria-label="Año"></div></header>
        <div class="riesgoGrid">
          ${kpi("Ganancias", G.fmtEur(a.ganancias), "ventas con beneficio", "pos")}
          ${kpi("Pérdidas que computan", G.fmtEur(a.perdidas), a.diferidas ? G.fmtEur(a.diferidas) + " diferidas por recompra" : "", a.perdidas ? "neg" : "")}
          ${kpi("Dividendos e intereses", G.fmtEur(a.dividendos), "capital mobiliario")}
          ${kpi("Compensado", G.fmtEur(a.arrastreUsado + a.compensadoCruzada), a.arrastreUsado ? G.fmtEur(a.arrastreUsado) + " de años anteriores" : "")}
          ${kpi("Base del ahorro", G.fmtEur(a.base))}
          ${kpi("Cuota estimada", G.fmtEur(a.cuota), a.tipoMedio != null ? "tipo medio " + G.fmtPct(a.tipoMedio, 1) : "sin cuota", a.cuota ? "neg" : "")}
        </div>
        ${a.tramos.length ? `<div class="tablaEnv"><table class="dt"><thead><tr><th>Tramo de la base</th><th>Tipo</th><th>Parte</th><th>Cuota</th></tr></thead>
          <tbody>${a.tramos.map(t => `<tr><td>${G.fmtEur(t.desde, 0)} – ${t.hasta == null ? "en adelante" : G.fmtEur(t.hasta, 0)}</td><td>${G.fmtPct(t.tipo, 0)}</td><td>${G.fmtEur(t.parte)}</td><td>${G.fmtEur(t.cuota)}</td></tr>`).join("")}</tbody></table></div>` : ""}
      </section>
      <section class="tarjeta" data-st="margin-top:16px" aria-labelledby="fisVentas">
        <header><h2 id="fisVentas">Ventas de ${a.ano}</h2><span class="subt">Primeras compras, primeras ventas (FIFO) por producto</span></header>
        ${filas ? `<div class="tablaEnv"><table class="dt stress"><thead><tr><th>Fecha</th><th>Producto</th><th>Unidades</th><th>Importe</th><th>Coste</th><th>Resultado</th><th>Estado</th></tr></thead><tbody>${filas}</tbody></table></div>`
          : `<p class="vacio">${ICO_ROSA}No hay ventas anotadas este año.</p>`}
        ${a.arrastrePendiente.length ? `<p class="subt" data-st="margin-top:12px"><b>Pérdidas por compensar</b> (caducan a los ${F.anosArrastre} años): ${
          a.arrastrePendiente.map(x => `${G.fmtEur(x.importe)} de ${x.ano}`).join(" · ")}.</p>` : ""}
      </section>
      ${tarjeta720(F)}
      <section class="tarjeta" data-st="margin-top:16px"><header><h2>Lo que esta pantalla no sabe</h2></header>
        <ul class="notas"><li><b>Traspasos entre fondos:</b> no tributan y conservan coste y antigüedad; Rumbo los ve como venta y compra. Si has hecho alguno, el resultado de ese año no es fiable.</li>
          <li><b>Retenciones y comunidad autónoma:</b> la escala del ahorro es estatal y la misma en todo el territorio común, pero no se descuentan retenciones.</li>
          <li><b>Recompra:</b> el plazo es de 2 meses para valores cotizados (acciones, ETF) y de 1 año para los no cotizados (fondos). Se detecta por producto, sin mirar si el saldo posterior queda a cero.</li>
          <li><b>Reembolsos importados de MyInvestor:</b> su CSV da la plusvalía pero no la fecha de venta; se cuenta en la fecha del lote, que puede no ser el año en que se vendió. Revísalo con tu extracto fiscal.</li>
          <li><b>Divisas y gastos:</b> las comisiones que anotaste ya van en el importe; no se modelan gastos de custodia ni cambios de divisa.</li></ul>
      </section>`;
    pintaSegm($("#segFiscalAno"), anos.map(x => ({ id: x, et: String(x) })), fis.ano, id => { fis.ano = id; pintaFiscal(); });
  }

  function tarjeta720(F) {
    const m = F.modelo720;
    const cat = m.categorias;
    return `<section class="tarjeta" data-st="margin-top:16px" aria-labelledby="t720">
      <header><h2 id="t720">Modelos 720 y 721 · bienes en el extranjero</h2></header>
      <p>Solo cuentan los bienes <b>custodiados fuera de España</b> a 31 de diciembre: más de ${G.fmtEur(m.umbral, 0)} en una categoría
        (cuentas, valores, inmuebles), o en criptomonedas en conjunto. Marca cada producto en <b>Datos → Productos → «Dónde está custodiado»</b>.</p>
      ${m.productosMarcados ? `<div class="riesgoGrid">
          <div class="kpi"><div class="e">Valores en el extranjero</div><div class="v ${m.supera720 && cat.valores > m.umbral ? "neg" : ""}">${G.fmtEur(cat.valores, 0)}</div></div>
          <div class="kpi"><div class="e">Cuentas en el extranjero</div><div class="v ${cat.cuentas > m.umbral ? "neg" : ""}">${G.fmtEur(cat.cuentas, 0)}</div></div>
          <div class="kpi"><div class="e">Cripto en el extranjero</div><div class="v ${m.supera721 ? "neg" : ""}">${G.fmtEur(cat.cripto, 0)}</div></div></div>
        <p>${m.supera720 || m.supera721 ? "<b class='neg'>Superas el umbral en alguna categoría:</b> podrías tener que presentar el modelo " + (m.supera720 ? "720" : "") + (m.supera720 && m.supera721 ? " y el " : "") + (m.supera721 ? "721" : "") + " entre el 1 de enero y el 31 de marzo."
          : "Ninguna categoría supera el umbral con lo que has marcado."}</p>`
        : '<p class="subt">No has marcado ningún producto como custodiado en el extranjero, así que no se calcula nada. Si todo está en brókers españoles, no tienes que presentarlos.</p>'}
    </section>`;
  }

  function pintaRiesgo() {
    const cont = $("#riesgo");
    if (!cont) return;
    const lista = (D.pignoraciones || []).slice().sort((a, b) => (a.estado === "activa" ? 0 : 1) - (b.estado === "activa" ? 0 : 1));
    const activos = TODOS().filter(enseñable).filter(p => valorDe(p) > 0 && p.tipoClave !== "efectivo");
    const total = activos.reduce((a, p) => a + valorDe(p), 0) || 1;
    const top = activos.map(p => ({ p, peso: valorDe(p) / total })).sort((a, b) => b.peso - a.peso).slice(0, 8);
    const UMBRAL = umbralesAl().concentracionProducto / 100;
    cont.innerHTML = `
      ${lista.length ? lista.map(tarjetaPrestamo).join("") : `<section class="tarjeta"><header><h2>Préstamos con garantía</h2></header>
        <p class="vacio">${window.ESTATICO ? "Esta versión exportada no incluye los préstamos." : "No tienes ninguna pignoración anotada. Si pignoras activos para pedir un préstamo, anótala en Datos → Pignoraciones y aquí verás tu margen, el estrés de mercado y el calendario."}</p></section>`}
      ${tarjetaTransparencia()}
      <section class="tarjeta" data-st="margin-top:16px" aria-labelledby="concTit">
        <header><h2 id="concTit">Concentración</h2><span class="subt">Peso de cada producto sobre lo que tienes invertido (sin efectivo)</span></header>
        <div class="conc">${top.map(t => `<div class="f ${t.peso > UMBRAL ? "alta" : ""}"><span>${esc(t.p.corto || t.p.nombre)}</span>
          <span class="b"><i data-st="width:${(t.peso * 100).toFixed(1)}%"></i></span><span class="p">${G.fmtPct(t.peso, 1)}</span></div>`).join("")}</div>
        ${top.some(t => t.peso > UMBRAL) ? `<p class="subt" data-st="margin-top:12px">Marcados en ámbar los productos que pesan más del ${Math.round(UMBRAL * 100)} %.
          Los fondos indexados ya reparten el riesgo por dentro; una sola acción pequeña, no.</p>` : ""}
      </section>`;
    cont.querySelectorAll("[data-gestion]").forEach(b => {
      b.onclick = () => {
        try { localStorage.setItem("patrimonio.editor", "pignoraciones"); } catch (e) { /* da igual */ }
        irA("datos");
        if (window.Editor && window.Editor.vista) window.Editor.vista("pignoraciones");
      };
    });
  }

  function pintaTabla() {
    const filas = [];
    D.productos.forEach(p => (p.aportaciones || []).forEach(a => {
      if (!a.importe) return;
      filas.push({
        fecha: a.fecha, producto: p.corto || p.nombre, color: color(p), id: p.id,
        importe: a.importe, valor: a.valor,
        pl: a.valor != null ? a.valor - a.importe : null,
        rent: a.valor != null && a.importe ? (a.valor - a.importe) / a.importe : null,
      });
    }));
    const f = estado.tablaFiltro === "todos" ? filas : filas.filter(x => x.id === estado.tablaFiltro);
    const o = estado.ordenTabla;
    f.sort((a, b) => {
      const va = a[o.col], vb = b[o.col];
      const c = va == null ? -1 : vb == null ? 1 : va > vb ? 1 : va < vb ? -1 : 0;
      return o.desc ? -c : c;
    });
    const cols = [["fecha", "Fecha"], ["producto", "Producto"], ["importe", "Aportado"],
    ["valor", "Vale hoy"], ["pl", "Plusvalía"], ["rent", "Rentabilidad"]];
    $("#tablaMov").innerHTML =
      `<thead><tr>${cols.map(c => `<th class="orden" data-c="${c[0]}">${c[1]}${o.col === c[0] ? (o.desc ? " ↓" : " ↑") : ""}</th>`).join("")}</tr></thead>
       <tbody>${f.map(r => `<tr>
        <td>${G.fmtFecha(r.fecha)}</td>
        <td><i class="pt" data-st="background:${r.color}"></i>${r.producto}</td>
        <td>${G.fmtEur(r.importe)}</td>
        <td>${r.valor != null ? G.fmtEur(r.valor) : "—"}</td>
        <td class="${r.pl >= 0 ? "pos" : "neg"}">${r.pl != null ? G.fmtEurSigno(r.pl) : "—"}</td>
        <td class="${r.rent >= 0 ? "pos" : "neg"}">${r.rent != null ? G.fmtPctSigno(r.rent, 1) : "—"}</td>
      </tr>`).join("")}</tbody>`;
    $("#tablaMov").querySelectorAll("th.orden").forEach(th => {
      th.onclick = () => {
        const c = th.dataset.c;
        estado.ordenTabla = { col: c, desc: o.col === c ? !o.desc : true };
        pintaTabla();
      };
    });
    $("#notaTabla").textContent =
      `${f.length} movimientos · ${G.fmtEur(f.reduce((a, r) => a + r.importe, 0), 0)}`;
  }

  function pintaPatrimonio() {
    const mTodo = metricas(TODOS());
    const mVis = filtrando() ? metricas(visibles()) : mTodo;
    pintaFiltros();
    pintaHero(mVis, mTodo);
    pintaCockpit();
    pintaKPIs(mVis);
    pintaPrincipal(mVis);
    pintaChips();
    pintaDistribucion();
    pintaBarras();
    pintaHitos(mTodo);
    pintaTabla();
    pintaSegm($("#segRango"), RANGOS, estado.rango, id => { estado.rango = id; pintaPatrimonio(); });
    pintaSegm($("#segVista"), [
      { id: "apilado", et: "Por producto" }, { id: "total", et: "Total" },
      { id: "dinero", et: "Tu dinero vs mercado" }, { id: "reparto", et: "Reparto %" }
    ], estado.vista, id => { estado.vista = id; pintaPatrimonio(); });
    pintaSegm($("#segDist"), [
      { id: "clase", et: "Activo" }, { id: "producto", et: "Producto" },
      { id: "entidad", et: "Entidad" }, { id: "tipo", et: "Tipo" }
    ], estado.dist, id => { estado.dist = id; pintaDistribucion(); });
    pintaSegm($("#segTabla"), [{ id: "todos", et: "Todos" }].concat(
      D.productos.filter(p => (p.aportaciones || []).some(a => a.importe))
        .map(p => ({ id: p.id, et: p.corto || p.nombre }))),
      estado.tablaFiltro, id => { estado.tablaFiltro = id; pintaTabla(); });
  }

  /* ================================================================
     PESTAÑA 2 · EL MES
     ================================================================ */
  function pintaMes() {
    const rm = D.resumenMensual || [];
    if (!rm.length) { $("#mesCifra").textContent = "—"; return; }
    if (estado.mes == null || estado.mes < 0 || estado.mes >= rm.length) estado.mes = rm.length - 1;
    const r = rm[estado.mes];

    const sel = $("#mesSel");
    if (sel.options.length !== rm.length) {
      sel.innerHTML = rm.map((x, i) => `<option value="${i}">${G.fmtMes(x.mes)}</option>`).join("");
    }
    sel.value = String(estado.mes);
    $("#mesPrev").disabled = estado.mes === 0;
    $("#mesNext").disabled = estado.mes === rm.length - 1;

    const cambio = r.fin - r.inicio;
    // El titular es el cambio REAL: lo que aportaste mas lo que hizo el mercado.
    // Incorporar una cuenta al panel mueve el saldo pero no es dinero ganado,
    // asi que va aparte y no infla la cifra grande.
    const real = r.aportado + r.mercado;
    const ultimo = estado.mes === rm.length - 1;
    $("#mesEtq").textContent = ultimo ? "Cambio en lo que va de mes" : "Cambio del mes";
    $("#mesCifra").textContent = G.fmtEurSigno(real);
    $("#mesCifra").className = "hCifra " + (real >= 0 ? "pos" : "neg");
    $("#mesNota").textContent = ultimo
      ? "Mes en curso, con datos hasta el " + G.fmtFecha(D.fechaExtracto) : "";
    const trozos = [`De <span class="fuerte">${G.fmtEur(r.inicio)}</span> a <span class="fuerte">${G.fmtEur(r.fin)}</span>`];
    if (r.rentabilidad != null) {
      trozos.push(`rentabilidad de la cartera
        <span class="${r.rentabilidad >= 0 ? "pos" : "neg"} fuerte">${G.fmtPctSigno(r.rentabilidad)}</span>`);
    }
    $("#mesSub").innerHTML = trozos.join('<span data-st="color:var(--tinta3)">·</span>');

    const tarjetas = [
      { e: "Lo pusiste tú", v: G.fmtEur(r.aportado, 0), n: "aportaciones del mes", c: G.css("--s1") },
      {
        e: "Lo puso el mercado", v: G.fmtEurSigno(r.mercado), n: "revalorización, sin tocar nada",
        c: G.css("--s3"), cl: r.mercado >= 0 ? "pos" : "neg"
      },
    ];
    if (r.amortizacionPrestamo) tarjetas.push({
      e: "Deuda amortizada", v: G.fmtEur(r.amortizacionPrestamo, 0),
      n: "lo que has devuelto del préstamo: baja la deuda, no es mercado", c: G.css("--s4")
    });
    if (r.nuevo) tarjetas.push({
      e: "Nuevo en el panel", v: G.fmtEur(r.nuevo, 0),
      n: "no es dinero nuevo: es que empiezas a seguirlo", c: G.css("--s7")
    });
    $("#mesTarjetas").innerHTML = tarjetas.map(t =>
      `<div class="mesT" data-st="--c:${t.c}"><span class="barra"></span>
        <div class="e">${t.e}</div><div class="v ${t.cl || ""}">${t.v}</div><div class="n">${t.n}</div></div>`).join("");

    // tabla por componente
    const filas = TODOS().map(p => ({ p, d: r.porProducto[p.id] })).filter(x => x.d);
    const hayNuevo = filas.some(x => x.d.nuevo);
    const hayAmort = filas.some(x => x.d.amortizacionPrestamo);
    const colNuevo = (hayNuevo ? "<th>Entra al panel</th>" : "") + (hayAmort ? "<th>Deuda amortizada</th>" : "");
    $("#mesTabla").innerHTML =
      `<thead><tr><th>Componente</th><th>Al empezar</th><th>Aportaste</th>
        <th>Mercado</th>${colNuevo}<th>Al cerrar</th><th>Variación</th></tr></thead>
       <tbody>${filas.map(({ p, d }) => {
        const var_ = d.fin - d.inicio;
        return `<tr>
          <td><i class="pt" data-st="background:${color(p)}"></i>${esc(p.corto || p.nombre)}</td>
          <td>${G.fmtEur(d.inicio)}</td>
          <td>${d.aportado ? G.fmtEur(d.aportado) : "—"}</td>
          <td class="${d.mercado >= 0 ? "pos" : "neg"}">${G.fmtEurSigno(d.mercado)}</td>
          ${hayNuevo ? `<td>${d.nuevo ? G.fmtEur(d.nuevo) : "—"}</td>` : ""}
          ${hayAmort ? `<td>${d.amortizacionPrestamo ? G.fmtEur(d.amortizacionPrestamo) : "—"}</td>` : ""}
          <td>${G.fmtEur(d.fin)}</td>
          <td class="${var_ >= 0 ? "pos" : "neg"}">${G.fmtEurSigno(var_)}</td></tr>`;
      }).join("")}</tbody>
       <tfoot><tr><td>Total</td><td>${G.fmtEur(r.inicio)}</td><td>${G.fmtEur(r.aportado)}</td>
        <td class="${r.mercado >= 0 ? "pos" : "neg"}">${G.fmtEurSigno(r.mercado)}</td>
        ${hayNuevo ? `<td>${G.fmtEur(r.nuevo)}</td>` : ""}
        ${hayAmort ? `<td>${G.fmtEur(r.amortizacionPrestamo || 0)}</td>` : ""}
        <td>${G.fmtEur(r.fin)}</td>
        <td class="${cambio >= 0 ? "pos" : "neg"}">${G.fmtEurSigno(cambio)}</td></tr></tfoot>`;
    $("#mesTablaNota").textContent = "";

    // histórico de esfuerzo vs mercado
    const ult = rm.slice(-18);
    G.barrasAgrupadas($("#grafMesHist"), {
      categorias: ult.map(x => x.mes), alto: 250,
      formatoCat: G.fmtMes,
      series: [
        { nombre: "Lo pusiste tú", color: G.css("--s1"), valores: ult.map(x => x.aportado) },
        { nombre: "Lo puso el mercado", color: G.css("--s3"), valores: ult.map(x => x.mercado) },
      ],
    });
  }

  /* ================================================================
     PESTAÑA 3 · FONDOS
     ================================================================ */
  function pintaFondos() {
    pintaPosiciones();
    if (!$("#drawer").hidden) pintaDetalle();
  }

  function pintaDetalle() {
    const lista = TODOS().filter(enseñable);
    if (!lista.length) return;
    if (!estado.fondo || !buscaProd(estado.fondo)) estado.fondo = lista[0].id;
    const p = buscaProd(estado.fondo);
    $("#drawerTit").textContent = p.corto || p.nombre;
    pintaFichaFondo(p);
    pintaExposicion(p);
    pintaTablaFondo(p);
  }

  function pintaFichaFondo(p) {
    const sec = $("#fondoFicha");
    sec.style.setProperty("--c", color(p));
    const campos = [
      ["Tipo", p.tipo], ["ISIN", p.isin], ["Índice que replica", p.indice],
      ["Comisión anual (TER)", p.ter != null ? G.fmtPct(p.ter, 2) : null],
      ["Entidad", p.entidad], ["Gestora", p.gestora],
      ["Política", p.politica], ["Mercado", p.mercado],
      [p.origen ? "Primera aportación" : "Primer dato anotado", p.desde ? G.fmtFecha(p.desde) : null],
      [p.etqUnidades || "Participaciones",
        p.titulos != null ? G.nfNum.format(p.titulos)
          : p.participaciones != null ? G.nfNum.format(p.participaciones) : null],
      ["Precio medio de compra", p.precioMedio != null ? G.fmtEur(p.precioMedio) : null],
      [p.etqPrecio || "Valor liquidativo",
        p.nav != null ? G.fmtEur(p.nav) + (p.navFecha ? " · cierre del " + G.fmtFechaCorta(p.navFecha) : "") : null],
      ["Fuente del precio", p.fuenteTexto || p.fuentePrecio],
      ["Plusvalía ya materializada", p.realizado ? G.fmtEur(p.realizado) : null],
      ["Peso en el patrimonio", p.peso != null ? G.fmtPct(p.peso, 1) : null],
      ["Pignorado en", p.pignoradoEn && p.pignoradoEn.length
        ? "🔒 " + esc(p.pignoradoEn.map(x => x.nombre).join(", ")) + " · no se puede vender" : null],
    ].filter(c => c[0] && c[1]);

    const hayVL = !!(p.navSerie && p.navSerie.some(v => v));
    const etqVL = p.etqPrecio || "Valor liquidativo";
    const pocos = (p.serie || []).filter(v => v != null).length < 5;

    sec.innerHTML = `
      <header>
        <h2><span data-st="display:inline-block;width:10px;height:10px;border-radius:3px;background:${color(p)};margin-right:9px"></span>${esc(p.nombre)}</h2>
        <div class="sep"></div>
        ${hayVL ? '<div class="segm" id="segSerie"></div>' : ""}
      </header>
      ${p.papel ? `<div class="papel">${esc(p.papel)}</div>` : ""}
      ${p.indiceDetalle ? `<p data-st="color:var(--tinta2);font-size:13.5px;margin:0 0 16px">${esc(p.indiceDetalle)}</p>` : ""}
      <div class="ficha">${campos.map(c => `<div><dt>${c[0]}</dt><dd>${c[1]}</dd></div>`).join("")}</div>
      <div id="ventanas"></div>
      ${pocos ? '<p class="subt" data-st="margin:0 0 12px">Solo hay un valor anotado, así que aún no hay curva. Anota más en «Mis datos → Saldos y valores».</p>' : ""}
      <div class="envGraf" id="grafFondo"></div>
      <div class="tramos" id="tramosLey"></div>`;

    // "Al cierre" es la cifra comparable con MyInvestor, que fuera de horario
    // se queda en el último cierre. "En vivo" sigue al bitcoin a cualquier hora.
    const vivoAqui = !!(precioVivo() && precioVivo().id === p.id);
    const plCierre = p.aportado > 0 ? { eur: p.valor - p.aportado, pct: (p.valor - p.aportado) / p.aportado } : null;
    const res = [
      ["Aportado", p.aportado != null ? G.fmtEur(p.aportado) : "—"],
      [vivoAqui ? "Valor al cierre" : "Valor hoy", G.fmtEur(p.valor)],
      [vivoAqui ? "Plusvalía al cierre" : "Plusvalía",
        plCierre ? `${G.fmtEurSigno(plCierre.eur)} · ${G.fmtPctSigno(plCierre.pct, 2)}` : "—"],
    ];
    if (vivoAqui) {
      const plv = plusvaliaDe(p);
      res.push(["En vivo ahora", `${G.fmtEur(valorDe(p))} · ${G.fmtPctSigno(plv.pct, 2)}`]);
    }
    res.push(["TIR", p.tir != null ? G.fmtPctSigno(p.tir) : "—"]);
    // Tu posición y el comportamiento del producto van en filas separadas:
    // el "1 año" del bitcoin es del precio, no de tu dinero.
    let html = `<div class="ventanas"><span class="grupoEtq">Tu posición</span>` +
      res.map(r => `<div class="ventana"><div class="e">${r[0]}</div><div class="v">${r[1]}</div></div>`).join("") +
      `</div>`;
    if (p.ventanas) {
      const et = { "1m": "1 mes", "3m": "3 meses", "6m": "6 meses", ytd: "En el año", "1a": "1 año" };
      const celdas = ["1m", "3m", "6m", "ytd", "1a"].filter(k => p.ventanas[k] != null)
        .map(k => `<div class="ventana"><div class="e">${et[k]}</div>
          <div class="v ${p.ventanas[k] >= 0 ? "pos" : "neg"}">${G.fmtPctSigno(p.ventanas[k], 1)}</div></div>`).join("");
      if (celdas) {
        html += `<div class="ventanas"><span class="grupoEtq">${esc(p.etqVentanas || "El precio")}, lo tuvieras o no</span>${celdas}</div>`;
      }
    }
    $("#ventanas").innerHTML = html;

    if (hayVL) {
      pintaSegm($("#segSerie"),
        [{ id: "posicion", et: "Mi posición" }, { id: "vl", et: etqVL }],
        estado.serieDetalle, id => { estado.serieDetalle = id; pintaFichaFondo(p); });
    }

    const verVL = hayVL && estado.serieDetalle === "vl";
    const paleta = tonos(color(p));
    const fechas = corta(D.fechas);
    const eventos = (p.aportaciones || []).filter(a => a.importe).map(a => {
      const niv = a.nivel == null ? 1 : a.nivel;
      return {
        fecha: a.fecha, color: paleta[niv], aro: niv === 2, r: 5,
        texto: `${["Aportación pequeña", "Aportación habitual", "Aportación extraordinaria"][niv]}: ${G.fmtEur(a.importe)}`,
      };
    });
    G.lineaConEventos($("#grafFondo"), {
      fechas,
      valores: corta(verVL ? p.navSerie : p.serie),
      color: color(p), alto: 280, eventos, desdeCero: !verVL,
      overlay: verVL ? null : ((p.serieAportado || []).some(v => v)
        ? { nombre: "Aportado", valores: corta(p.serieAportado) } : null),
      formatoY: verVL ? (v => G.fmtEur(v, v > 500 ? 0 : 2)) : null,
      referencia: (verVL && p.precioMedio)
        ? { valor: p.precioMedio, etiqueta: "tu precio medio · " + G.fmtEur(p.precioMedio) } : null,
    });

    // leyenda de los tramos, con los importes reales de este producto
    const t = p.tramos;
    if (t && eventos.length) {
      const cuenta = [0, 0, 0];
      (p.aportaciones || []).forEach(a => { if (a.nivel != null) cuenta[a.nivel]++; });
      const medio = t.p33 != null && t.p67 != null
        ? (t.p33 === t.p67 ? G.fmtEur(t.p33, 0) : `${G.fmtEur(t.p33, 0)} – ${G.fmtEur(t.p67, 0)}`)
        : "";
      const et = t.p33 == null
        ? [["Aportaciones", ""]]
        : [["Pequeña", "menos de " + G.fmtEur(t.p33, 0)],
           ["Habitual", medio],
           ["Extraordinaria", "más de " + G.fmtEur(t.p67, 0)]];
      $("#tramosLey").innerHTML =
        `<span data-st="color:var(--tinta3)">Tamaño de cada aportación, medido con tu propio historial en este producto:</span>` +
        et.map((e, i) => `<span><i class="${i === 2 ? "aro" : ""}" data-st="background:${paleta[i]};color:${paleta[i]}"></i>
          ${e[0]} <span data-st="color:var(--tinta3)">${e[1]}${cuenta[i] ? " · " + cuenta[i] : ""}</span></span>`).join("");
    } else $("#tramosLey").innerHTML = "";
  }

  function pintaExposicion(p) {
    const sec = $("#fondoExpo");
    const e = p.exposicion;
    if (!e) { sec.hidden = true; return; }
    sec.hidden = false;
    const meses = (Date.parse(D.fechaExtracto) - Date.parse(e.actualizado)) / (30.44 * 864e5);
    const viejo = meses > 6;
    sec.innerHTML = `
      <header>
        <h2>Qué hay dentro</h2>
        <div class="sep"></div>
        <span class="expoNota ${viejo ? "viejo" : ""}">${viejo ? "⚠ " : ""}Datos a ${G.fmtFecha(e.actualizado)}${viejo ? " · conviene refrescarlos" : ""}</span>
      </header>
      <p class="subt" data-st="margin:0 0 18px">${e.constituyentes ? e.constituyentes.toLocaleString("es-ES") + " empresas. " : ""}${e.fuente}. Datos del índice a la fecha indicada.</p>
      <div class="expo">
        <div><h3>Por país</h3><div class="envGraf" id="expoPaises"></div></div>
        <div><h3>Por sector</h3><div class="envGraf" id="expoSectores"></div></div>
      </div>
      ${e.top10 ? `<h3 data-st="font-size:12px;text-transform:uppercase;letter-spacing:.07em;color:var(--tinta3);margin:24px 0 10px">
        Las 10 mayores posiciones · ${e.top10.reduce((a, x) => a + x[1], 0).toFixed(1)} % del fondo</h3>
        <div class="tablaEnv"><table class="dt"><tbody>${e.top10.map(x =>
          `<tr><td>${x[0]}</td><td>${x[1].toLocaleString("es-ES", { minimumFractionDigits: 2 })} %</td></tr>`).join("")}</tbody></table></div>` : ""}`;
    G.barrasHorizontales($("#expoPaises"), { datos: e.paises, color: color(p) });
    G.barrasHorizontales($("#expoSectores"), { datos: e.sectores, color: color(p) });
  }

  function pintaTablaFondo(p) {
    const sec = $("#fondoTabla");
    const filas = (p.aportaciones || []).filter(a => a.importe).slice().reverse();
    if (!filas.length) {
      sec.innerHTML = `<header><h2>Aportaciones</h2></header>
        <p class="vacio">Este componente no tiene aportaciones registradas: solo anotas su valor.</p>`;
      return;
    }
    const esFondo = p.tipoClave === "fondo" || p.tipoClave === "pension";
    const paleta = tonos(color(p));
    const hoy = new Date(D.fechaExtracto);
    const cab = ["Fecha", "Aportado", p.etqUnidades || "Participaciones",
      esFondo ? "VL de compra" : "Precio de compra", "Vale hoy", "Plusvalía", "Rent.", "Días"];
    sec.innerHTML = `<header><h2>Aportaciones a este producto</h2>
        <span class="subt">${filas.length} en total · ${G.fmtEur(p.aportado, 0)}</span></header>
      <div class="tablaEnv alto"><table class="dt">
        <thead><tr>${cab.map(c => `<th>${c}</th>`).join("")}</tr></thead>
        <tbody>${filas.map(a => {
          const pl = a.valor != null ? a.valor - a.importe : null;
          const rt = pl != null && a.importe ? pl / a.importe : null;
          const dias = Math.round((hoy - new Date(a.fecha)) / 864e5);
          const niv = a.nivel == null ? 1 : a.nivel;
          return `<tr><td>${G.fmtFecha(a.fecha)}</td>
            <td><i class="pt" data-st="background:${paleta[niv]}"></i>${G.fmtEur(a.importe)}</td>
            <td>${G.nfNum.format(a.participaciones || 0)}</td>
            <td>${a.precio != null ? G.fmtEur(a.precio) : "—"}</td>
            <td>${a.valor != null ? G.fmtEur(a.valor) : "—"}</td>
            <td class="${pl >= 0 ? "pos" : "neg"}">${pl != null ? G.fmtEurSigno(pl) : "—"}</td>
            <td class="${rt >= 0 ? "pos" : "neg"}">${rt != null ? G.fmtPctSigno(rt, 1) : "—"}</td>
            <td>${dias}</td></tr>`;
        }).join("")}</tbody></table></div>`;
  }

  /* ================================================================
     PESTAÑA 4 · RENDIMIENTO
     ================================================================ */
  function pintaRendimiento() {
    const ra = D.rentabilidadAnual;
    if (ra && ra.anos.length) {
      G.barrasSimples($("#grafAnual"), {
        categorias: ra.anos.map((a, i) => a + (ra.parcial[i] ? " *" : "")),
        valores: ra.cartera, alto: 240,
        color: G.css("--s1"),
        colores: ra.cartera.map(v => v >= 0 ? G.css("--s1") : G.css("--s2")),
      });
      $("#notaAnual").textContent =
        "Tu cartera completa, limpia del efecto de cuándo metiste el dinero. * año incompleto.";

      // Solo TU rentabilidad, por producto y año.
      $("#notaTablaAnual").textContent =
        "Tu rentabilidad en cada producto y año, desde el precio real al que compraste y con comisiones. "
        + "En un año completo coincide con la rentabilidad publicada del producto; el primer año cuenta desde tu primera compra.";
      const verProducto = false;
      const tabla = ra.porProducto;
      const desde = ra.desde || {};
      const MES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
      const corto = iso => { const q = iso.split("-"); return `${+q[2]} ${MES[+q[1] - 1]}`; };
      const celda = (v, d) => v == null
        ? `<td class="subt">${verProducto ? "—" : "aún no lo tenías"}</td>`
        : `<td class="${v >= 0 ? "pos" : "neg"}">${G.fmtPctSigno(v, 1)}` +
          `${d ? `<span class="subt" data-st="font-weight:400"> · desde ${corto(d)}</span>` : ""}</td>`;
      const prods = D.productos.filter(p => tabla[p.id]);
      $("#tablaAnual").innerHTML =
        `<thead><tr><th>Producto</th>${ra.anos.map((a, i) =>
          `<th>${a}${ra.parcial[i] ? " *" : ""}</th>`).join("")}</tr></thead>
         <tbody>${prods.map(p => `<tr>
           <td><i class="pt" data-st="background:${color(p)}"></i>${esc(p.corto)}</td>
           ${tabla[p.id].map((v, i) => celda(v, (desde[p.id] || [])[i])).join("")}
         </tr>`).join("")}</tbody>` +
        (verProducto ? "" : `<tfoot><tr><td>Tu cartera</td>${ra.cartera.map(v =>
          `<td class="${v == null ? "" : v >= 0 ? "pos" : "neg"}">${G.fmtPctSigno(v, 1)}</td>`).join("")}</tr></tfoot>`);
    }

    pintaComparacion();

    const comp = D.comparador || [];
    const detalles = $("#compDetalles");
    // Los detalles solo se dibujan al abrirlos: un SVG dentro de algo cerrado no tiene ancho.
    if (detalles && !detalles.dataset.conectado) {
      detalles.dataset.conectado = "1";
      detalles.addEventListener("toggle", () => { if (detalles.open) pintaRendimiento(); });
    }
    if (comp.length && (!detalles || detalles.open)) {
      const met0 = comp[0].metricas;
      const paleta = [G.css("--s1"), G.css("--s2"), G.css("--s3"), G.css("--s4"), G.css("--s5"), G.css("--s7"), G.css("--s6")];
      const series = comp.map((c, i) => ({
        nombre: c.nombre, valores: c.indice, destacado: c.real,
        color: c.real ? G.css("--tinta") : paleta[(i + 1) % paleta.length],
      }));
      G.multiLinea($("#grafComparador"), {
        fechas: D.fechas, series, alto: 320,
        formatoY: v => Math.round(v),
        formatoValor: v => v.toFixed(1),
      });
      $("#notaComparador").textContent =
        `Base 100 desde el ${G.fmtFecha(met0.desde)}. Las alternativas son comprar y mantener con pesos fijos.`;
      $("#tablaComparador").innerHTML =
        `<thead><tr><th>Cartera</th><th>Rentabilidad</th><th>Anualizada</th>
          <th>Volatilidad</th><th>Sharpe</th><th>Máx. caída</th></tr></thead>
         <tbody>${comp.map((c, i) => {
          const m = c.metricas;
          return `<tr class="${c.real ? "destacada" : ""}">
            <td><i class="pt" data-st="background:${series[i].color}"></i>${esc(c.nombre)}</td>
            <td class="${m.rentTotal >= 0 ? "pos" : "neg"}">${G.fmtPctSigno(m.rentTotal, 1)}</td>
            <td class="${m.cagr >= 0 ? "pos" : "neg"}">${G.fmtPctSigno(m.cagr, 1)}</td>
            <td>${G.fmtPct(m.vol, 1)}</td>
            <td>${m.sharpe == null ? "—" : m.sharpe.toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
            <td class="neg">${G.fmtPct(m.maxDD, 1)}</td></tr>`;
        }).join("")}</tbody>`;
      $("#notaRiesgo").innerHTML =
        `<b>Cómo leerlo.</b> La volatilidad mide cuánto se mueve la cartera; el Sharpe, cuánta rentabilidad
         sacas por cada unidad de ese meneo (más alto, mejor). El tipo sin riesgo sale de tu fondo
         monetario, si tienes uno. Ojo: son solo
         ${((Date.parse(met0.hasta) - Date.parse(met0.desde)) / 3.1536e10).toFixed(1)} años de datos,
         así que valen para comparar entre ellas, no como pronóstico. Tu cartera real cambia de pesos
         con el tiempo y cada producto solo cuenta desde que lo compraste; las alternativas son
         hipotéticas y llevan sus pesos fijos desde el primer día.`;
    }

    const c = D.comisiones;
    if (c && c.lineas.length) {
      $("#notaComisiones").textContent =
        `${G.fmtEur(c.anual)} al año · ${G.fmtPct(c.terPonderado, 3)} de lo invertido`;
      $("#tablaComisiones").innerHTML =
        `<thead><tr><th>Producto</th><th>Comisión</th><th>Sobre</th><th>Al año</th><th>Al mes</th></tr></thead>
         <tbody>${c.lineas.map(l => `<tr>
            <td><i class="pt" data-st="background:${temaOscuro() ? l.color[1] : l.color[0]}"></i>${esc(l.nombre)}</td>
            <td>${G.fmtPct(l.ter, 2)}</td><td>${G.fmtEur(l.valor, 0)}</td>
            <td>${G.fmtEur(l.anual)}</td><td>${G.fmtEur(l.anual / 12)}</td></tr>`).join("")}</tbody>
         <tfoot><tr><td>Total</td><td>${G.fmtPct(c.terPonderado, 3)}</td>
           <td>${G.fmtEur(c.base, 0)}</td><td>${G.fmtEur(c.anual)}</td>
           <td>${G.fmtEur(c.anual / 12)}</td></tr></tfoot>`;
    }
  }

  /* ---------------------------------------------- avisos y pie */
  function pintaComun() {
    // Los avisos de precio (sin conexión, desactualizado) ya salen como alerta en el Resumen, con su
    // botón; el pie solo guarda los avisos generales.
    $("#avisos").innerHTML = Alertas.clasificaAvisos(D.avisos).otros
      .map(a => `<div class="av"><span>⚠</span><span>${esc(a)}</span></div>`).join("");
    const pa = D.preciosActualizados;
    const fuentes = [...new Set(D.productos.map(p => p.fuentePrecio).filter(Boolean))];
    $("#pie").innerHTML =
      `${pa ? `Precios actualizados ${fechaHoraLocal(pa)}` : "Precios sin actualizar"} ·
       datos valorados a ${G.fmtFecha(D.fechaExtracto)} ·
       ${D.total.diasInvertido} días invertido.<br>
       Fuentes de precios: ${fuentes.join(", ") || "ninguna"}. En la pestaña Productos verás la de cada uno.<br>
       Los precios pueden llevar retraso.`;
    if ($("#bannerDemo")) $("#bannerDemo").hidden = D.modo !== "demo";
    const K = window.CANAL;
    if (K) {
      $("#pie").insertAdjacentHTML("beforeend", `<span class="creditoCanal">Herramienta gratuita hecha por
        ${K.autor} · ¿Te resulta útil? <a href="${K.suscribir}" target="_blank" rel="noopener">Suscríbete al canal ▶</a></span>`);
      document.querySelectorAll(".autorCanal").forEach(el => { el.textContent = K.autor; });
      document.querySelectorAll(".enlaceCanal").forEach(el => { el.href = K.canal; });
      document.querySelectorAll(".enlaceSuscribir").forEach(el => { el.href = K.suscribir; });
    }
  }

  /* ---------------------------------------------- avisos emergentes (toasts) */
  function toast(texto, op) {
    op = op || {};
    let cont = $("#toasts");
    if (!cont) {
      cont = document.createElement("div");
      cont.id = "toasts"; cont.className = "toasts"; cont.setAttribute("aria-live", "polite");
      document.body.appendChild(cont);
    }
    const t = document.createElement("div");
    t.className = "toast " + (op.tipo || "info");
    t.setAttribute("role", op.tipo === "danger" ? "alert" : "status");
    t.innerHTML = `<span>${esc(texto)}</span>`;
    if (op.accion) {
      const b = document.createElement("button");
      b.className = "btn"; b.textContent = op.accion.t;
      b.onclick = () => { t.remove(); op.accion.f(); };
      t.appendChild(b);
    }
    const x = document.createElement("button");
    x.className = "btn suave"; x.textContent = "✕"; x.setAttribute("aria-label", "Cerrar aviso");
    x.onclick = () => t.remove();
    t.appendChild(x);
    cont.appendChild(t);
    const ms = op.ms == null ? 6000 : op.ms;
    if (ms) setTimeout(() => t.remove(), ms);
    return t;
  }

  function haceCuanto(iso) {
    if (!/[+-]\d\d:\d\d$|Z$/.test(iso || "")) return null;          // sin zona horaria no se puede fiar
    const min = Math.round((Date.now() - Date.parse(iso)) / 60000);
    if (min < 2) return "hace un momento";
    if (min < 60) return `hace ${min} min`;
    if (min < 36 * 60) return `hace ${Math.round(min / 60)} h`;
    return `hace ${Math.round(min / 1440)} días`;
  }
  function fechaHoraLocal(iso) {
    if (!/[+-]\d\d:\d\d$|Z$/.test(iso || "")) return `el ${G.fmtFecha(iso.slice(0, 10))} a las ${iso.slice(11, 16)}`;
    const d = new Date(iso);
    const dd = String(d.getDate()).padStart(2, "0") + "/" + String(d.getMonth() + 1).padStart(2, "0") + "/" + d.getFullYear();
    return `el ${dd} a las ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  }
  function pintaMeta_() {
    const hace = haceCuanto(D.preciosActualizados);
    $("#metaFecha").textContent = "Datos a " + G.fmtFecha(D.fechaExtracto) + (hace ? " · precios " + hace : "");
  }

  async function actualizaPrecios() {
    const b = $("#btnPrecios");
    if (!b || b.disabled) return;
    const etq = b.querySelector(".lbl");
    b.disabled = true;
    b.classList.add("cargando");
    if (etq) etq.textContent = "Actualizando…";
    try {
      const r = await fetch("api/actualizar", { method: "POST" });
      let j = {};
      try { j = await r.json(); } catch (e) { /* vacío */ }
      if (r.status === 409) {
        toast(j.error || "Ya se están actualizando los precios.", { tipo: "info" });
      } else if (!r.ok || !j.ok) {
        throw new Error(j.error || "No he podido actualizar los precios.");
      } else {
        try { sessionStorage.setItem("rumbo.toast", JSON.stringify({ n: (j.avisos || []).length })); } catch (e) { /* da igual */ }
        location.reload();
        return;
      }
    } catch (e) {
      toast(e.message || "No he podido actualizar los precios. ¿Tienes conexión a internet?", { tipo: "danger", ms: 0 });
    }
    b.disabled = false;
    b.classList.remove("cargando");
    if (etq) etq.textContent = "Actualizar precios";
  }

  /* ---------------------------------------------- bitcoin en vivo */
  async function traeBtc() {
    // Lo consulta el servidor de la app (api/vivo): el navegador no habla con terceros.
    // En la web exportada o abierta como archivo no se consulta nada (cotización a cierre).
    if (window.ESTATICO || location.protocol === "file:") return null;
    try {
      const r = await fetch("api/vivo", { cache: "no-store" });
      if (!r.ok) return null;
      const j = await r.json();
      const v = Number(j && j.precio);
      return j && j.ok && v > 0 && isFinite(v) ? v : null;
    } catch (e) { return null; }
  }
  async function actualizaVivo() {
    if (!D.vivo) return;
    const v = await traeBtc();
    if (!v) return;
    estado.btcVivo = v;
    if (estado.tab !== "datos") pintarTab();     // no se repinta «Datos»: perdería lo que estés escribiendo
  }

  /* ---------------------------------------------- pestañas */
  function irA(tab) {
    // Si has cambiado datos en «Mis datos», el panel se recarga con las cifras nuevas.
    if (window.EDITOR_SUCIO && tab !== "datos") {
      recuerda.guarda("patrimonio.tab", tab);
      location.reload();
      return;
    }
    estado.tab = tab;
    document.querySelectorAll("#tabs button[data-tab]").forEach(b => {
      b.setAttribute("aria-selected", String(b.dataset.tab === tab));
      b.tabIndex = b.dataset.tab === tab ? 0 : -1;
    });
    $("#tabs").classList.remove("masAbierto");
    if ($("#tabMas")) $("#tabMas").setAttribute("aria-expanded", "false");
    if (tab !== "fondos" && $("#drawer")) cierraDetalle();
    document.querySelectorAll(".panel").forEach(p => { p.hidden = p.id !== "tab-" + tab; });
    recuerda.guarda("patrimonio.tab", tab);
    pintarTab();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function pintarTab() {
    // Cada pestaña se dibuja al mostrarse: un SVG dentro de un panel oculto
    // no tiene ancho, y saldria del tamano equivocado.
    if (estado.tab === "patrimonio") pintaPatrimonio();
    else if (estado.tab === "mes") pintaMes();
    else if (estado.tab === "fondos") pintaFondos();
    else if (estado.tab === "riesgo") pintaRiesgo();
    else if (estado.tab === "plan") { pintaMeta(); pintaAsignacion(); pintaProyeccion(); pintaMontecarlo(); }
    else if (estado.tab === "fiscal") { pintaIngresos(); pintaFiscal(); }
    else if (estado.tab === "rendimiento") pintaRendimiento();
    else if (estado.tab === "datos" && window.Editor) window.Editor.mostrar();
  }
  function pintar() { pintaComun(); pintarTab(); }

  /* ---------------------------------------------- arranque */
  document.title = "Rumbo · " + (D.titular || "Mi patrimonio");
  $("#marcaTexto").textContent = D.titular || "Mi patrimonio";
  pintaMeta_();
  setInterval(pintaMeta_, 60000);

  $("#btnTema").onclick = () => { cambiaTema(); pintar(); };
  if ($("#btnPrecios")) $("#btnPrecios").onclick = actualizaPrecios;
  if (location.protocol === "file:" && $("#btnPrecios")) $("#btnPrecios").hidden = true;
  $("#btnVideo").onclick = () => {
    document.body.classList.toggle("video");
    $("#btnVideo").classList.toggle("act");
    setTimeout(pintarTab, 60);
  };
  document.querySelectorAll("#tabs button[data-tab]").forEach(b => { b.onclick = () => irA(b.dataset.tab); });
  // Pestañas con teclado (patrón ARIA Tabs): flechas, Inicio y Fin.
  $("#tabs").addEventListener("keydown", e => {
    const bs = [...document.querySelectorAll("#tabs button[data-tab]")].filter(b => b.offsetParent !== null);
    const i = bs.indexOf(document.activeElement);
    if (i < 0) return;
    const sig = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[e.key];
    let j = sig ? (i + sig + bs.length) % bs.length : e.key === "Home" ? 0 : e.key === "End" ? bs.length - 1 : -1;
    if (j < 0) return;
    e.preventDefault();
    bs[j].focus();
    irA(bs[j].dataset.tab);
  });
  if ($("#tabMas")) $("#tabMas").onclick = () => {
    const abierto = $("#tabs").classList.toggle("masAbierto");
    $("#tabMas").setAttribute("aria-expanded", String(abierto));
  };
  if ($("#drawerCerrar")) {
    $("#drawerCerrar").onclick = cierraDetalle;
    $("#drawerVelo").onclick = cierraDetalle;
    $("#posBuscar").addEventListener("input", e => { pos.q = e.target.value; pintaPosiciones(); });
  }
  $("#mesSel").onchange = e => { estado.mes = +e.target.value; pintaMes(); };
  $("#mesPrev").onclick = () => { estado.mes = Math.max(0, estado.mes - 1); pintaMes(); };
  $("#mesNext").onclick = () => { estado.mes = Math.min(D.resumenMensual.length - 1, estado.mes + 1); pintaMes(); };
  ["rAnos", "rRent", "rApor"].forEach(id => $("#" + id).addEventListener("input", () => { pintaProyeccion(); pintaMontecarlo(); }));
  ["rVolP", "rVolG"].forEach(id => $("#" + id).addEventListener("input", pintaMontecarlo));
  document.querySelectorAll("#segModoProy button").forEach(b => {
    b.onclick = () => { proy.modo = b.dataset.m; proy.clave = ""; pintaProyeccion(); };
  });
  $("#rApor").value = Math.min(3000, Math.max(0, Math.round((D.total.ritmoMensual || 500) / 50) * 50));

  document.addEventListener("keydown", e => {
    // Solo se ignoran los atajos mientras escribes en un campo. Si el guardia
    // fuese "el foco esta en el body", dejarian de funcionar en cuanto pulsas
    // cualquier boton, que es justo cuando los quieres.
    const t = e.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable)) return;
    if (e.key === "Escape" && $("#drawer") && !$("#drawer").hidden) { cierraDetalle(); return; }
    if (e.key === "Escape" && filtrando()) { estado.ocultos.clear(); pintaPatrimonio(); }
    if (!e.altKey || e.metaKey || e.ctrlKey) return;
    if (e.code === "KeyV") $("#btnVideo").click();
    if (e.code === "KeyL" && estado.tab === "patrimonio") {
      estado.ocultos = filtrando() ? new Set() : new Set(idsCorto());
      pintaPatrimonio();
    }
    const n = "123456789".indexOf(e.key);
    const tab = ["patrimonio", "fondos", "rendimiento", "riesgo", "mes", "plan", "fiscal", "datos", "ayuda"][n];
    if (n >= 0 && document.getElementById("tab-" + tab)) irA(tab);
  });

  let t = null;
  window.addEventListener("resize", () => { clearTimeout(t); t = setTimeout(() => { if (estado.tab !== "datos") pintarTab(); }, 140); });

  const tabGuardada = recuerda.lee("patrimonio.tab");
  if (tabGuardada && document.getElementById("tab-" + tabGuardada)) {
    estado.tab = tabGuardada;
    document.querySelectorAll("#tabs button[data-tab]").forEach(b => {
      b.setAttribute("aria-selected", String(b.dataset.tab === estado.tab));
      b.tabIndex = b.dataset.tab === estado.tab ? 0 : -1;
    });
    document.querySelectorAll(".panel").forEach(p => { p.hidden = p.id !== "tab-" + estado.tab; });
  }

  try {
    pintar();
  } catch (e) {
    console.error(e);
    document.querySelector(".env").insertAdjacentHTML("afterbegin",
      '<div class="av" data-st="margin:20px 0"><span>⚠</span><span><b>Algo ha fallado al pintar el panel.</b> ' +
      String(e && e.message || e) + '<br>Cierra la app y vuelve a abrirla con «Iniciar»; si sigue igual, pulsa F12 y mira la consola del navegador.</span></div>');
  }
  // ?ir=seccionComparar pone esa sección la primera de su pestaña (para capturas y enlaces).
  const irA_ = qs.get("ir") && document.getElementById(qs.get("ir"));
  if (irA_) {
    irA_.parentNode.prepend(irA_);
    irA_.style.marginTop = "24px";
    pintarTab();
  }
  if (!window.ESTATICO && location.protocol !== "file:") {
    actualizaVivo();
    setInterval(actualizaVivo, 60000);
  }

  // Tras actualizar los precios la página se recarga: se confirma con un aviso.
  try {
    const t = JSON.parse(sessionStorage.getItem("rumbo.toast") || "null");
    if (t) {
      sessionStorage.removeItem("rumbo.toast");
      toast("Precios actualizados." + (t.n ? ` Con ${t.n} ${t.n === 1 ? "aviso" : "avisos"}: míralos en el Resumen y al pie de la página.` : ""),
        { tipo: "ok" });
    }
  } catch (e) { /* da igual */ }
  // Si la app actualiza sola (cada pocas horas) mientras la tienes abierta, avisa sin recargar de golpe.
  if (!window.ESTATICO && location.protocol !== "file:") {
    let avisado = null;
    setInterval(async () => {
      try {
        const r = await fetch("api/estado", { cache: "no-store" });
        const j = await r.json();
        if (j.generado && D.generado && j.generado > D.generado && j.generado !== avisado && estado.tab !== "datos") {
          avisado = j.generado;
          toast("Hay precios más recientes.", { ms: 0, accion: { t: "Ver", f: () => location.reload() } });
        }
      } catch (e) { /* sin red local: se reintenta */ }
    }, 180000);
  }
})();
