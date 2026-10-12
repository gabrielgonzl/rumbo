# -*- coding: utf-8 -*-
"""
fiscal.py  ·  Orientación fiscal del ahorro (IRPF, España, régimen común)
=========================================================================
AVISO: es una estimación orientativa a partir de los movimientos que has anotado. No sustituye a
tu declaración ni a un asesor: no conoce tus retenciones, tu comunidad autónoma, los traspasos
entre fondos (que no tributan y conservan antigüedad), las deducciones ni tu situación personal.

Reglas que aplica (verificadas en la Ley 35/2006 del IRPF y en la Ley 7/2024):
  · Valores homogéneos: FIFO por producto (art. 37.2). Las distintas clases de un fondo, con ISIN
    distinto, no son homogéneas.
  · Escala del ahorro (art. 66): 19 % hasta 6.000 €, 21 % hasta 50.000 €, 23 % hasta 200.000 €,
    27 % hasta 300.000 € y 30 % por encima (el 30 % rige desde 2025).
  · Integración y compensación (art. 49): rendimientos del capital mobiliario y ganancias/pérdidas
    patrimoniales se compensan primero entre sí; un saldo negativo compensa al otro hasta el 25 %
    de su saldo positivo; lo que sobra se arrastra cuatro años.
  · Pérdidas no computables por recompra (art. 33.5 f y g): si recompras valores homogéneos en los
    2 meses anteriores o posteriores (cotizados) o en el año anterior o posterior (no cotizados,
    como los fondos), la pérdida no se computa hasta que se vendan los que sigas teniendo.
  · Modelos 720 y 721: umbral de 50.000 € por categoría (cuentas, valores, inmuebles) o, para
    criptomonedas, en conjunto, solo para bienes custodiados en el extranjero a 31 de diciembre.
"""

import datetime as dt

ESCALA_AHORRO = [(6000.0, 0.19), (44000.0, 0.21), (150000.0, 0.23), (100000.0, 0.27), (float("inf"), 0.30)]
COMPENSACION_CRUZADA = 0.25
ANOS_ARRASTRE = 4
UMBRAL_720 = 50000.0
COTIZADOS = ("accion", "etf")          # 2 meses; el resto (fondos, planes…) se trata como no cotizado: 1 año


def cuota_ahorro(base):
    """Cuota íntegra de la base liquidada del ahorro con la escala vigente."""
    if base <= 0:
        return 0.0
    cuota, resto = 0.0, base
    for ancho, tipo in ESCALA_AHORRO:
        parte = min(resto, ancho)
        cuota += parte * tipo
        resto -= parte
        if resto <= 0:
            break
    return round(cuota, 2)


def tramos(base):
    """Desglose por tramo de una base: [(desde, hasta, tipo, parte)] solo con partes > 0."""
    out, desde, resto = [], 0.0, max(base, 0.0)
    for ancho, tipo in ESCALA_AHORRO:
        parte = min(resto, ancho)
        if parte > 0:
            out.append({"desde": desde, "hasta": None if ancho == float("inf") else desde + ancho,
                        "tipo": tipo, "parte": round(parte, 2), "cuota": round(parte * tipo, 2)})
        desde += ancho
        resto -= parte
        if resto <= 0:
            break
    return out


def _f(iso):
    return dt.date.fromisoformat(str(iso)[:10])


def _mas_meses(d, n):
    m = d.month - 1 + n
    a, m = d.year + m // 12, m % 12 + 1
    dias = [31, 29 if a % 4 == 0 and (a % 100 or a % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return dt.date(a, m, min(d.day, dias))


# ---------------------------------------------------------------- ventas realizadas (FIFO)

def ventas_realizadas(cfg):
    """
    Ventas con su resultado, por FIFO y por producto. Devuelve una lista ordenada por fecha:
    {fecha, producto, nombre, tipo, unidades, importe, coste, resultado, compras_consumidas}.
    Las «ventas de 0 unidades» (plusvalía de un reembolso importada del extracto) cuentan su importe
    como resultado, porque ya es la ganancia y no el precio de venta.
    """
    prods = {p["id"]: p for p in cfg.get("productos", [])}
    por = {}
    for m in cfg.get("movimientos", []):
        por.setdefault(m.get("producto"), []).append(m)
    out = []
    for pid, movs in por.items():
        p = prods.get(pid)
        if not p:
            continue
        orden = {"compra": 0, "comision": 1, "dividendo": 2, "venta": 3}
        movs = sorted(movs, key=lambda m: (m["fecha"], orden.get(m.get("tipo"), 9)))
        lotes = []                                    # [fecha, unidades restantes, coste por unidad, id]
        for m in movs:
            u, imp = float(m.get("unidades") or 0), float(m.get("importe") or 0)
            if m.get("tipo") == "compra" and u > 0:
                lotes.append([m["fecha"], u, imp / u, m.get("id")])
            elif m.get("tipo") == "venta":
                if u <= 0:
                    out.append({"fecha": m["fecha"], "producto": pid, "nombre": p.get("corto") or p.get("nombre"),
                                "tipo": p.get("tipo"), "unidades": 0.0, "importe": imp, "coste": 0.0,
                                "resultado": imp, "consumidas": [], "reembolso": True})
                    continue
                falta, coste, usadas = u, 0.0, []
                while falta > 1e-9 and lotes:
                    lote = lotes[0]
                    t = min(falta, lote[1])
                    coste += t * lote[2]
                    usadas.append(lote[3])
                    lote[1] -= t
                    falta -= t
                    if lote[1] <= 1e-9:
                        lotes.pop(0)
                out.append({"fecha": m["fecha"], "producto": pid, "nombre": p.get("corto") or p.get("nombre"),
                            "tipo": p.get("tipo"), "unidades": u, "importe": imp, "coste": round(coste, 2),
                            "resultado": round(imp - coste, 2), "consumidas": usadas, "reembolso": False})
    out.sort(key=lambda v: v["fecha"])
    return out


def marca_recompra(cfg, ventas):
    """
    Añade a cada venta con pérdida si se ve afectada por la regla de recompra: compras de valores
    homogéneos (mismo producto) dentro del plazo (2 meses los cotizados, 1 año el resto) que no
    sean las que se venden. Es aproximado: no mira si el saldo posterior queda a cero.
    """
    compras = {}
    for m in cfg.get("movimientos", []):
        if m.get("tipo") == "compra" and float(m.get("unidades") or 0) > 0:
            compras.setdefault(m.get("producto"), []).append(m)
    for v in ventas:
        v["diferida"] = False
        v["plazo"] = "2 meses" if v["tipo"] in COTIZADOS else "1 año"
        if v["resultado"] >= 0 or v.get("reembolso"):
            continue
        d = _f(v["fecha"])
        meses = 2 if v["tipo"] in COTIZADOS else 12
        ini, fin = _mas_meses(d, -meses), _mas_meses(d, meses)
        for c in compras.get(v["producto"], []):
            if c.get("id") in v["consumidas"]:
                continue
            if ini <= _f(c["fecha"]) <= fin:
                v["diferida"] = True
                v["recompra"] = c["fecha"]
                break


# ---------------------------------------------------------------- año a año

def _dividendos(cfg):
    out = {}
    for m in cfg.get("movimientos", []):
        if m.get("tipo") == "dividendo":
            a = int(str(m["fecha"])[:4])
            out[a] = out.get(a, 0.0) + float(m.get("importe") or 0)
    return out


def calcula(cfg, hoy=None, valores=None):
    """
    Resumen fiscal por año: ventas, dividendos, compensaciones, base, cuota y estimación del 720/721.
    valores = {id de producto: valor actual}; solo para el indicador del 720.
    """
    hoy = hoy or dt.date.today()
    ventas = ventas_realizadas(cfg)
    marca_recompra(cfg, ventas)
    div = _dividendos(cfg)
    anos = sorted({int(v["fecha"][:4]) for v in ventas} | set(div))
    arrastre = []                                     # [año de origen, importe pendiente] de pérdidas patrimoniales
    por_ano = []
    for a in anos:
        vs = [v for v in ventas if int(v["fecha"][:4]) == a]
        computables = [v for v in vs if not v["diferida"]]
        diferidas = [v for v in vs if v["diferida"]]
        ganancias = round(sum(v["resultado"] for v in computables if v["resultado"] > 0), 2)
        perdidas = round(-sum(v["resultado"] for v in computables if v["resultado"] < 0), 2)
        pat = round(ganancias - perdidas, 2)
        rcm = round(div.get(a, 0.0), 2)

        # 1) Pérdidas de años anteriores (caducan a los 4 años) contra ganancias patrimoniales.
        arrastre = [x for x in arrastre if a - x[0] <= ANOS_ARRASTRE]
        usado_arr = 0.0
        if pat > 0:
            for x in arrastre:
                t = min(x[1], pat - usado_arr)
                x[1] -= t
                usado_arr += t
        pat_tras_arr = round(pat - usado_arr, 2)
        arrastre = [x for x in arrastre if x[1] > 0.005]

        # 2) Compensación cruzada con límite del 25 % del saldo positivo del otro bloque.
        comp_pat_con_rcm = comp_rcm_con_pat = 0.0
        if pat_tras_arr < 0 and rcm > 0:
            comp_pat_con_rcm = round(min(-pat_tras_arr, rcm * COMPENSACION_CRUZADA), 2)
        elif rcm < 0 and pat_tras_arr > 0:
            comp_rcm_con_pat = round(min(-rcm, pat_tras_arr * COMPENSACION_CRUZADA), 2)
        pat_final = pat_tras_arr + (comp_pat_con_rcm if pat_tras_arr < 0 else -comp_rcm_con_pat)
        rcm_final = rcm - comp_pat_con_rcm if rcm > 0 else rcm + comp_rcm_con_pat
        # Lo que queda negativo se arrastra cuatro años.
        if pat_final < -0.005:
            arrastre.append([a, round(-pat_final, 2)])
        base = round(max(pat_final, 0.0) + max(rcm_final, 0.0), 2)
        cuota = cuota_ahorro(base)
        por_ano.append({
            "ano": a, "ventas": vs, "ganancias": ganancias, "perdidas": perdidas, "patrimoniales": pat,
            "dividendos": rcm, "diferidas": round(-sum(v["resultado"] for v in diferidas), 2),
            "arrastreUsado": round(usado_arr, 2), "compensadoCruzada": round(comp_pat_con_rcm + comp_rcm_con_pat, 2),
            "base": base, "cuota": cuota, "tipoMedio": round(cuota / base, 4) if base else None,
            "tramos": tramos(base), "arrastrePendiente": [{"ano": o, "importe": round(i, 2)} for o, i in arrastre],
        })
    return {
        "anos": por_ano, "escala": [{"hasta": None if t == float("inf") else t, "tipo": r} for t, r in ESCALA_AHORRO],
        "compensacionCruzada": COMPENSACION_CRUZADA, "anosArrastre": ANOS_ARRASTRE,
        "modelo720": modelo_720(cfg, valores or {}),
        "aviso": ("Estimación orientativa con los movimientos que has anotado. No conoce tus retenciones, tu "
                  "comunidad autónoma, los traspasos entre fondos (no tributan) ni tus deducciones. Consulta "
                  "con un asesor o con la AEAT antes de presentar nada."),
    }


def modelo_720(cfg, valores):
    """Suma por categoría de lo que marcas como custodiado en el extranjero (campo `custodia`)."""
    cat = {"valores": 0.0, "cripto": 0.0, "cuentas": 0.0}
    n = 0
    for p in cfg.get("productos", []):
        if str(p.get("custodia") or "").lower() not in ("extranjero", "exterior", "fuera"):
            continue
        v = float(valores.get(p["id"], 0) or 0)
        n += 1
        k = "cripto" if p.get("tipo") == "cripto" else "cuentas" if p.get("tipo") == "efectivo" else "valores"
        cat[k] += v
    return {"categorias": {k: round(v, 2) for k, v in cat.items()}, "productosMarcados": n,
            "umbral": UMBRAL_720,
            "supera720": any(cat[k] > UMBRAL_720 for k in ("valores", "cuentas")),
            "supera721": cat["cripto"] > UMBRAL_720}
