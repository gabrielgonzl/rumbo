# -*- coding: utf-8 -*-
"""
pignoracion.py  ·  Préstamos con garantía de tus activos
========================================================
Una pignoración es un préstamo que te da el broker dejando en garantía (pignorados)
uno o varios de tus activos. Aquí se calcula todo lo que implica: el cuadro de
amortización, la deuda pendiente, el coste, el colchón frente a una caída del
mercado y lo que habría que pagar para liquidarla hoy.

El préstamo entra en el patrimonio como una deuda (pasivo) derivada: no hace falta
anotar saldos a mano.
"""

import calendar
import datetime as dt
from decimal import ROUND_HALF_UP, Decimal

REDONDEO = 2


def r2(x):
    """Redondeo comercial a 2 decimales (0,625 -> 0,63), como hacen los bancos."""
    return float(Decimal(repr(float(x))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _fecha(v):
    return v if isinstance(v, dt.date) else dt.date.fromisoformat(str(v)[:10])


def suma_meses(f, n):
    """Mismo día, n meses después (si el mes es más corto, el último día)."""
    m = f.month - 1 + n
    a, m = f.year + m // 12, m % 12 + 1
    return dt.date(a, m, min(f.day, calendar.monthrange(a, m)[1]))


def cuota_francesa(principal, tin, n):
    """Cuota fija mensual del sistema francés. tin en % anual."""
    i = tin / 100 / 12
    if n <= 0:
        return 0.0
    if i == 0:
        return principal / n
    return principal * i / (1 - (1 + i) ** -n)


def cuadro(p):
    """
    Calendario de pagos: [{fecha, cuota, intereses, amortizado, pendiente}].
    Si la pignoración trae su cuadro (importado del broker) se usa tal cual; si no,
    se calcula con el sistema francés a partir de principal, interés y número de cuotas.
    """
    if p.get("cuadro"):
        return [dict(fecha=str(r["fecha"])[:10], cuota=float(r["cuota"]), intereses=float(r["intereses"]),
                     amortizado=float(r["amortizado"]), pendiente=float(r["pendiente"])) for r in p["cuadro"]]
    principal, tin, n = float(p["principal"]), float(p.get("interes") or 0), int(p.get("cuotas") or 0)
    if n <= 0:
        return []
    cuota = float(p.get("cuota") or 0) or r2(cuota_francesa(principal, tin, n))
    primero = _fecha(p.get("primerPago") or suma_meses(_fecha(p["fecha"]), 1))
    i = tin / 100 / 12
    saldo, filas = principal, []          # el saldo se arrastra sin redondear; solo se redondea al enseñarlo
    for k in range(n):
        inter = saldo * i
        pago = cuota if k < n - 1 else saldo + inter           # la última cierra el préstamo
        saldo = saldo - (pago - inter) if k < n - 1 else 0.0
        filas.append({"fecha": suma_meses(primero, k).isoformat(), "cuota": r2(pago),
                      "intereses": r2(inter), "amortizado": r2(pago - inter), "pendiente": max(r2(saldo), 0.0)})
    return filas


def vigente(p, hoy):
    """¿Sigue en pie en esa fecha? (empezada y no liquidada todavía)."""
    if _fecha(p["fecha"]) > hoy:
        return False
    liq = p.get("fechaLiquidacion")
    return not (p.get("estado") == "liquidada" and liq and _fecha(liq) <= hoy)


def saldo_a(p, hoy):
    """Deuda pendiente en esa fecha (capital, sin intereses devengados)."""
    if not vigente(p, hoy):
        return 0.0
    saldo = float(p["principal"])
    for r in cuadro(p):
        if _fecha(r["fecha"]) <= hoy:
            saldo = r["pendiente"]
    return round(saldo, REDONDEO)


def estado(p, hoy):
    """Todas las cifras que enseña el panel de una pignoración."""
    filas = cuadro(p)
    liquidada = p.get("estado") == "liquidada"
    corte = _fecha(p["fechaLiquidacion"]) if liquidada and p.get("fechaLiquidacion") else hoy
    corte = min(corte, hoy)
    pagadas = [r for r in filas if _fecha(r["fecha"]) <= corte]
    pendientes = [r for r in filas if _fecha(r["fecha"]) > corte]
    saldo = 0.0 if liquidada else (pagadas[-1]["pendiente"] if pagadas else float(p["principal"]))
    ultima = _fecha(pagadas[-1]["fecha"]) if pagadas else _fecha(p["fecha"])
    tin = float(p.get("interes") or 0)
    dias = max((hoy - ultima).days, 0)
    devengado = 0.0 if liquidada else round(saldo * tin / 100 * dias / 365, 2)
    interes_pagado = round(sum(r["intereses"] for r in pagadas), 2)
    interes_restante = 0.0 if liquidada else round(sum(r["intereses"] for r in pendientes), 2)
    cancel = float(p.get("comisionCancelacion") or 0)
    penalizacion = 0.0 if liquidada else round(saldo * cancel / 100, 2)
    a_liquidar = 0.0 if liquidada else round(saldo + devengado + penalizacion, 2)
    apertura = float(p.get("comisionApertura") or 0)
    sig = pendientes[0] if pendientes and not liquidada else None
    return {
        "id": p["id"], "nombre": p.get("nombre"), "entidad": p.get("entidad") or "",
        "estado": "liquidada" if liquidada else ("activa" if vigente(p, hoy) else "pendiente"),
        "fecha": p["fecha"], "fechaLiquidacion": p.get("fechaLiquidacion"),
        "principal": r2(p["principal"]), "recibido": round(float(p.get("recibido") or p["principal"]), 2),
        "interes": tin, "cuota": filas[0]["cuota"] if filas else 0.0,
        "cuotasTotal": len(filas), "cuotasPagadas": len(pagadas),
        "saldo": round(saldo, 2), "devengado": devengado,
        "interesesPagados": interes_pagado, "interesesRestantes": interes_restante,
        "comisionApertura": apertura, "comisionCancelacion": cancel,
        "costeTotal": round(sum(r["intereses"] for r in filas) + apertura, 2),
        "costePagado": round(interes_pagado + apertura, 2),
        "proxima": {"fecha": sig["fecha"], "cuota": sig["cuota"]} if sig else None,
        "fin": filas[-1]["fecha"] if filas else None,
        "penalizacion": penalizacion, "aLiquidar": a_liquidar,
        # Lo que te ahorras en intereses si la liquidas hoy en vez de mantenerla hasta el final.
        "ahorroSiLiquidas": round(interes_restante - devengado - penalizacion, 2) if not liquidada else 0.0,
        "ltvMax": p.get("ltvMax"), "activos": list(p.get("activos") or []),
        "efectivoHasta": p.get("efectivoHasta"), "importeLiquidacion": p.get("importeLiquidacion"),
    }


def resumen(cfg, valores, hoy):
    """
    Lista para el panel. 'valores' = {id de producto: valor actual en €}.
    Añade la garantía: lo que valen hoy los activos pignorados y cuánto margen hay.
    """
    nombres = {p["id"]: (p.get("corto") or p.get("nombre")) for p in cfg.get("productos", [])}
    salida = []
    for p in cfg.get("pignoraciones", []):
        if _fecha(p["fecha"]) > hoy:
            continue
        e = estado(p, hoy)
        garantia = round(sum(valores.get(a, 0.0) for a in e["activos"]), 2)
        deuda = e["saldo"] + e["devengado"]
        e["garantia"] = garantia
        e["activosDetalle"] = [{"id": a, "nombre": nombres.get(a, a), "valor": round(valores.get(a, 0.0), 2)}
                               for a in e["activos"]]
        if e["estado"] == "activa" and garantia > 0:
            e["ratio"] = round(deuda / garantia, 4)                   # préstamo / garantía
            # Caída de la garantía que la deja justo igual a la deuda…
            e["caidaHastaIgualar"] = round(1 - deuda / garantia, 4)
            # …y, si conoces el límite de la entidad (LTV máximo), hasta ese límite.
            ltv = float(e["ltvMax"]) / 100 if e.get("ltvMax") else None
            e["caidaHastaLimite"] = round(max(0.0, 1 - deuda / (ltv * garantia)), 4) if ltv else None
            e["garantiaMinima"] = round(deuda / ltv, 2) if ltv else None
        else:
            e["ratio"] = e["caidaHastaIgualar"] = e["caidaHastaLimite"] = e["garantiaMinima"] = None
        salida.append(e)
    return salida


def marcas(cfg, hoy):
    """{id de producto: [{id, nombre}]} de los activos pignorados ahora mismo."""
    m = {}
    for p in cfg.get("pignoraciones", []):
        if vigente(p, hoy):
            for a in p.get("activos") or []:
                m.setdefault(a, []).append({"id": p["id"], "nombre": p.get("nombre")})
    return m


def bloquea_venta(cfg, producto, fecha):
    """Nombre de la pignoración que impide vender 'producto' en 'fecha', o None."""
    f = _fecha(fecha)
    for p in cfg.get("pignoraciones", []):
        if producto in (p.get("activos") or []) and vigente(p, f):
            return p.get("nombre") or "una pignoración"
    return None


def derivados(cfg, hoy):
    """
    Productos y valores que el motor necesita para que la deuda cuente en el patrimonio:
    una deuda (con su saldo en cada pago) y, si lo pides, el dinero recibido como efectivo
    hasta que lo inviertas. No se guardan: se recalculan siempre desde la pignoración.
    """
    productos, valoraciones = [], []
    for p in cfg.get("pignoraciones", []):
        ini = _fecha(p["fecha"])
        if ini > hoy:
            continue
        pid = f"pignoracion_{p['id']}"
        nom = p.get("nombre") or "Pignoración"
        nom = nom if nom.lower().startswith("préstamo") else f"Préstamo · {nom}"
        productos.append({"id": pid, "nombre": nom, "corto": nom[:24],
                          "tipo": "deuda", "fuente": "manual", "moneda": "EUR", "clase": "Deudas",
                          "entidad": p.get("entidad") or "", "largoPlazo": False, "slot": 11,
                          "derivado": "pignoracion"})
        snaps = [(ini, float(p["principal"]))]
        for r in cuadro(p):
            f = _fecha(r["fecha"])
            if ini < f <= hoy:
                snaps.append((f, float(r["pendiente"])))
        if p.get("estado") == "liquidada" and p.get("fechaLiquidacion"):
            lq = _fecha(p["fechaLiquidacion"])
            snaps = [s for s in snaps if s[0] < lq] + [(lq, 0.0)]
        valoraciones += [{"id": f"{pid}_{i}", "fecha": f.isoformat(), "producto": pid, "valor": round(v, 2)}
                         for i, (f, v) in enumerate(snaps) if f <= hoy]
        if p.get("efectivoHasta"):
            hasta = _fecha(p["efectivoHasta"])
            eid = f"{pid}_efectivo"
            productos.append({"id": eid, "nombre": f"Dinero recibido · {p.get('nombre') or 'pignoración'}",
                              "corto": "Dinero del préstamo", "tipo": "efectivo", "fuente": "manual",
                              "moneda": "EUR", "clase": "Efectivo", "largoPlazo": False, "slot": 12,
                              "derivado": "pignoracion"})
            recibido = float(p.get("recibido") or p["principal"])
            valoraciones.append({"id": f"{eid}_0", "fecha": ini.isoformat(), "producto": eid,
                                 "valor": round(recibido, 2)})
            if hasta <= hoy:
                valoraciones.append({"id": f"{eid}_1", "fecha": hasta.isoformat(), "producto": eid, "valor": 0.0})
    return productos, valoraciones
