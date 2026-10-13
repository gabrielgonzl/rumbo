# -*- coding: utf-8 -*-
"""
ingresos.py  ·  Dividendos e ingresos pasivos
=============================================
Función pura: a partir de los movimientos `dividendo` resume lo cobrado por mes, por año y por
producto, y calcula el rendimiento sobre coste (yield on cost) y sobre valor actual.

Definiciones:
  · «Últimos 12 meses» = los 12 meses naturales que terminan en el mes de `hoy` (el mes en curso
    cuenta entero hasta `hoy`). Los movimientos con fecha posterior a `hoy` se ignoran.
  · Coste vivo = coste, por FIFO y por producto, de las unidades que siguen en cartera
    (misma regla que `fiscal.ventas_realizadas`: orden por fecha fiscal, compras con unidades > 0).
  · yieldOnCost  = ingresos 12 m / coste vivo      (None si el coste vivo es 0).
  · yieldActual  = ingresos 12 m / valor actual    (None si el valor es 0).
  · Cartera: solo suma los productos con denominador > 0 (un producto vendido no distorsiona).
Todos los rendimientos van en tanto por uno, redondeados a 4 decimales.
"""

import datetime as dt

_ORDEN = {"compra": 0, "comision": 1, "dividendo": 2, "venta": 3}


def _fecha(iso):
    try:
        return dt.date.fromisoformat(str(iso)[:10])
    except (TypeError, ValueError):
        return None


def _num(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def _coste_vivo(movs):
    """Coste de los lotes que siguen en cartera (FIFO)."""
    movs = sorted(movs, key=lambda m: (str(m.get("fechaFiscal") or m.get("fecha")), _ORDEN.get(m.get("tipo"), 9)))
    lotes = []                                   # [unidades restantes, coste por unidad]
    for m in movs:
        u, imp = _num(m.get("unidades")), _num(m.get("importe"))
        if m.get("tipo") == "compra" and u > 0:
            lotes.append([u, imp / u])
        elif m.get("tipo") == "venta" and u > 0:
            falta = u
            while falta > 1e-9 and lotes:
                t = min(falta, lotes[0][0])
                lotes[0][0] -= t
                falta -= t
                if lotes[0][0] <= 1e-9:
                    lotes.pop(0)
    return sum(u * c for u, c in lotes)


def _ratio(num, den):
    return round(num / den, 4) if den and den > 1e-9 else None


def calcula(cfg, valores_hoy, hoy):
    cfg = cfg or {}
    valores_hoy = valores_hoy or {}
    hoy = hoy if isinstance(hoy, dt.date) else (_fecha(hoy) or dt.date.today())
    nombres = {p.get("id"): (p.get("corto") or p.get("nombre") or p.get("id")) for p in cfg.get("productos", [])}
    ini_mes = hoy.year * 12 + hoy.month - 1 - 11           # primer mes de la ventana de 12 meses
    ref = hoy.year * 12 + hoy.month - 1

    por_mes, por_ano, por_prod = {}, {}, {}
    movs_prod = {}
    for m in cfg.get("movimientos", []):
        f = _fecha(m.get("fecha"))
        if f is None or f > hoy:
            continue
        movs_prod.setdefault(m.get("producto"), []).append(m)
        if m.get("tipo") != "dividendo":
            continue
        imp = _num(m.get("importe"))
        if imp == 0:
            continue
        pid = m.get("producto")
        mes = f"{f.year:04d}-{f.month:02d}"
        d = por_mes.setdefault(mes, {})
        d[pid] = d.get(pid, 0.0) + imp
        a = por_ano.setdefault(f.year, {})
        a[pid] = a.get(pid, 0.0) + imp
        pr = por_prod.setdefault(pid, {"doce": 0.0, "ultima": None})
        if ini_mes <= f.year * 12 + f.month - 1 <= ref:
            pr["doce"] += imp
        if pr["ultima"] is None or f.isoformat() > pr["ultima"]:
            pr["ultima"] = f.isoformat()

    def _red(d):
        return {k: round(v, 2) for k, v in d.items()}

    out_mes = [{"mes": mes, "total": round(sum(d.values()), 2), "porProducto": _red(d)}
               for mes, d in sorted(por_mes.items())]
    out_ano = [{"ano": a, "total": round(sum(d.values()), 2), "ultimosDoce": a == hoy.year,
                "porProducto": _red(d)} for a, d in sorted(por_ano.items())]
    ultimos = round(sum(p["doce"] for p in por_prod.values()), 2)

    productos, yoc = [], {}
    num_c = den_c = num_a = den_a = 0.0
    for pid, pr in por_prod.items():
        coste = _coste_vivo(movs_prod.get(pid, []))
        valor = _num(valores_hoy.get(pid))
        yc, ya = _ratio(pr["doce"], coste), _ratio(pr["doce"], valor)
        yoc[pid] = yc
        productos.append({"id": pid, "nombre": nombres.get(pid, pid), "ultimosDoce": round(pr["doce"], 2),
                          "yieldOnCost": yc, "yieldActual": ya, "ultimaFecha": pr["ultima"]})
        if coste > 1e-9:
            num_c += pr["doce"]
        if valor > 1e-9:
            num_a += pr["doce"]
    for pid, movs in movs_prod.items():                    # denominador: toda la cartera, no solo los que pagan
        den_c += max(_coste_vivo(movs), 0.0)
    den_a = sum(_num(v) for v in valores_hoy.values() if _num(v) > 0)
    productos.sort(key=lambda p: (-p["ultimosDoce"], str(p["nombre"])))
    return {
        "porMes": out_mes, "porAno": out_ano, "ultimosDoce": ultimos, "yieldOnCost": yoc,
        "yieldActual": {p["id"]: p["yieldActual"] for p in productos},
        "productos": productos,
        "total": {"ultimosDoce": ultimos, "yieldOnCostCartera": _ratio(num_c, den_c),
                  "yieldActualCartera": _ratio(num_a, den_a)},
    }
