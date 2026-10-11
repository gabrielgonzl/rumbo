# -*- coding: utf-8 -*-
"""
almacen.py  ·  Guarda y valida la cartera
=========================================
Todo lo que se escribe en mis_datos/cartera.json pasa por aquí: se comprueba
que tiene sentido y, antes de cada cambio, se guarda una copia automática.
"""

import datetime as dt
import json
import os
import re
import unicodedata

from . import pignoracion
from .motor import TIPOS, FUENTES, num_es

COPIAS_MAX = 20
TIPOS_MOV = {"compra": "Compra", "venta": "Venta", "dividendo": "Dividendo o cupón",
             "comision": "Comisión"}
SOLO_SALDO = ("efectivo", "deuda")   # tipos que se siguen solo con saldos anotados

CARTERA_VACIA = {
    "version": 1, "titular": "Mi patrimonio",
    "productos": [], "movimientos": [], "valoraciones": [], "pignoraciones": [],
    "comparador": [{"id": "real", "nombre": "Mi cartera real", "real": True}],
    "hitos": [10000, 25000, 50000, 100000, 250000, 500000, 1000000],
    "objetivo": {"activo": True, "importe": 100000, "etiqueta": "Próximo objetivo"},
}


class ErrorValidacion(Exception):
    def __init__(self, errores):
        super().__init__("; ".join(errores))
        self.errores = errores


# ---------------------------------------------------------------- disco

def carga(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def guarda(ruta, cfg):
    """Copia de seguridad automática de lo que había y escritura atómica de lo nuevo."""
    carpeta = os.path.dirname(ruta)
    copias = os.path.join(carpeta, "copias")
    if os.path.exists(ruta):
        os.makedirs(copias, exist_ok=True)
        sello = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        with open(ruta, "rb") as f, open(os.path.join(copias, f"auto_{sello}.json"), "wb") as g:
            g.write(f.read())
        viejas = sorted(n for n in os.listdir(copias) if n.startswith("auto_"))
        for n in viejas[:-COPIAS_MAX]:
            os.remove(os.path.join(copias, n))
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)
    os.replace(tmp, ruta)


# ---------------------------------------------------------------- ayudas

def fmt_fecha(iso):
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}"


def fmt_num(x):
    """12345.6 -> '12.345,6' (hasta 4 decimales, sin ceros de sobra)."""
    t = f"{x:,.4f}".rstrip("0").rstrip(".")
    return t.replace(",", "X").replace(".", ",").replace("X", ".")


def numero(valor, etiqueta, errores, obligatorio=True, minimo=None, mayor_que=None):
    """Acepta 1234.5, "1.234,56" o "1234,5". Devuelve float o None."""
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        if obligatorio:
            errores.append(f"Falta {etiqueta}.")
        return None
    if isinstance(valor, (int, float)):
        x = float(valor)
    else:
        t = valor.strip().replace("€", "").replace("%", "").replace(" ", "")
        if not re.fullmatch(r"-?[\d.,]+", t):
            errores.append(f"{etiqueta.capitalize()} no es un número: «{valor}».")
            return None
        x = num_es(t)
    if minimo is not None and x < minimo:
        errores.append(f"{etiqueta.capitalize()} no puede ser menor que {minimo:g}.")
    if mayor_que is not None and x <= mayor_que:
        errores.append(f"{etiqueta.capitalize()} tiene que ser mayor que {mayor_que:g}.")
    return x


def fecha(valor, errores):
    try:
        f = dt.date.fromisoformat(str(valor or "")[:10])
    except ValueError:
        errores.append("Falta la fecha o no es válida.")
        return None
    if f > dt.date.today():
        errores.append(f"La fecha {fmt_fecha(f.isoformat())} es futura.")
    elif f.year < 1950:
        errores.append(f"La fecha {fmt_fecha(f.isoformat())} parece un error.")
    return f.isoformat()


def slug(texto, existentes):
    base = unicodedata.normalize("NFKD", texto or "producto").encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "_", base.lower()).strip("_")[:30] or "producto"
    cand, i = base, 2
    while cand in existentes:
        cand, i = f"{base}_{i}", i + 1
    return cand


def siguiente_id(lista, prefijo):
    nums = [int(x["id"][1:]) for x in lista if re.fullmatch(prefijo + r"\d+", str(x.get("id", "")))]
    return f"{prefijo}{max(nums, default=0) + 1}"


def producto(cfg, pid):
    return next((p for p in cfg.get("productos", []) if p["id"] == pid), None)


def texto(v, maximo=200):
    return str(v).strip()[:maximo] if v is not None else ""


# ---------------------------------------------------------------- productos

CAMPOS_TEXTO = ("nombre", "corto", "identificador", "codigo", "entidad", "clase", "gestora",
                "tipoDetalle", "respaldo", "respaldoMoneda", "vivo", "papel")


def guarda_producto(cfg, datos):
    """Crea o actualiza un producto. Devuelve (producto, cambió_la_fuente)."""
    errores = []
    nuevo = {k: texto(datos.get(k), 400 if k == "papel" else 200) for k in CAMPOS_TEXTO}
    if not nuevo["nombre"]:
        errores.append("Ponle un nombre al producto.")
    tipo = datos.get("tipo")
    if tipo not in TIPOS:
        errores.append("Elige de qué tipo es el producto.")
    fuente = "manual" if tipo in SOLO_SALDO else datos.get("fuente") or "manual"
    if fuente not in FUENTES:
        errores.append("Elige de dónde sale el precio.")
    if fuente != "manual" and not nuevo["codigo"]:
        errores.append(f"Falta el código del producto en {FUENTES.get(fuente, fuente)}. "
                       "Búscalo con el buscador o elige «a mano».")
    moneda = texto(datos.get("moneda")) or "EUR"
    moneda = moneda if moneda in ("GBp", "GBX") else moneda.upper()
    if not re.fullmatch(r"[A-Z]{3}|GBp|GBX", moneda):
        errores.append(f"La moneda «{moneda}» no es válida: usa un código de tres letras, como EUR o USD.")
    ter = numero(datos.get("ter"), "la comisión anual", errores, obligatorio=False, minimo=0)
    riesgo = numero(datos.get("riesgo"), "el nivel de riesgo", errores, obligatorio=False, minimo=1)
    if riesgo is not None and riesgo > 7:
        errores.append("El nivel de riesgo va de 1 a 7.")
    if errores:
        raise ErrorValidacion(errores)

    nuevo.update(tipo=tipo, fuente=fuente, moneda=moneda,
                 largoPlazo=bool(datos.get("largoPlazo", True)),
                 slot=int(datos["slot"]) if str(datos.get("slot") or "").isdigit() else None,
                 ter=ter / 100 if ter is not None else None,
                 riesgo=int(riesgo) if riesgo is not None else None)
    if fuente == "manual":
        nuevo.update(codigo="", respaldo="", respaldoMoneda="")
    nuevo["corto"] = nuevo["corto"] or nuevo["nombre"][:24]

    existente = producto(cfg, datos.get("id")) if datos.get("id") else None
    if existente:
        cambio = (existente.get("fuente"), existente.get("codigo")) != (fuente, nuevo["codigo"])
        destino = existente
        if nuevo["slot"] is None:
            nuevo.pop("slot")   # si no se dice color, se queda el que tenía
    else:
        cambio = fuente != "manual"
        destino = {"id": slug(nuevo["corto"], {p["id"] for p in cfg["productos"]})}
        if nuevo["slot"] is None:
            # Sin color elegido (por ejemplo, al importar): el que menos se use.
            usos = [sum(1 for p in cfg["productos"] if p.get("slot") == s) for s in range(1, 13)]
            nuevo["slot"] = usos.index(min(usos)) + 1
        cfg["productos"].append(destino)
    # Se conservan los campos que el formulario no toca (la exposición del índice, etc.).
    for k, v in nuevo.items():
        if v in ("", None):
            destino.pop(k, None)
        else:
            destino[k] = v
    return destino, cambio


def reparte_colores(cfg, orden=None):
    """Un color distinto para cada producto (los primeros de 'orden', los más grandes,
    se quedan los colores más fáciles de distinguir). Con más de 12, se repiten."""
    ids = [p["id"] for p in cfg["productos"]]
    orden = [i for i in (orden or []) if i in ids] + [i for i in ids if i not in (orden or [])]
    for n, pid in enumerate(orden):
        producto(cfg, pid)["slot"] = n % 12 + 1


def borra_producto(cfg, pid):
    """Borra el producto con sus movimientos y valores anotados."""
    if not producto(cfg, pid):
        raise ErrorValidacion(["Ese producto ya no existe."])
    cfg["productos"] = [p for p in cfg["productos"] if p["id"] != pid]
    cfg["movimientos"] = [m for m in cfg.get("movimientos", []) if m.get("producto") != pid]
    cfg["valoraciones"] = [v for v in cfg.get("valoraciones", []) if v.get("producto") != pid]
    for c in cfg.get("comparador", []):
        if c.get("pesos"):
            c["pesos"].pop(pid, None)
    cfg["comparador"] = [c for c in cfg.get("comparador", []) if c.get("real") or c.get("pesos")]


# ---------------------------------------------------------------- movimientos

def unidades_a(cfg, pid, fecha_iso, excluir=None):
    """Unidades que tenías de un producto al final de ese día."""
    total = 0.0
    for m in cfg.get("movimientos", []):
        if m.get("producto") != pid or m.get("id") == excluir or m["fecha"] > fecha_iso:
            continue
        u = float(m.get("unidades") or 0)
        total += u if m.get("tipo") == "compra" else -u if m.get("tipo") == "venta" else 0
    return total


def guarda_movimiento(cfg, datos):
    errores = []
    p = producto(cfg, datos.get("producto"))
    if not p:
        errores.append("Elige el producto.")
    elif p.get("tipo") in SOLO_SALDO:
        errores.append(f"«{p.get('corto') or p['nombre']}» se sigue con saldos, no con movimientos: "
                       "anótalo en «Saldos y valores».")
    tipo = datos.get("tipo")
    if tipo not in TIPOS_MOV:
        errores.append("Elige el tipo de movimiento: compra, venta, dividendo o comisión.")
    f = fecha(datos.get("fecha"), errores)
    importe = numero(datos.get("importe"), "el importe", errores, mayor_que=0)
    cotiza = bool(p and p.get("fuente") != "manual")
    unidades = 0.0
    if tipo == "compra":
        unidades = numero(datos.get("unidades"), "cuántas unidades compraste", errores,
                          obligatorio=cotiza, mayor_que=0 if cotiza else None) or 0.0
    elif tipo == "venta":
        unidades = numero(datos.get("unidades"), "cuántas unidades vendiste", errores,
                          obligatorio=cotiza, minimo=0) or 0.0
    comision = numero(datos.get("comision"), "la comisión", errores, obligatorio=False, minimo=0)
    if comision and importe and comision >= importe:
        errores.append("La comisión no puede ser mayor que el importe total.")
    if not errores and tipo == "venta" and cotiza and unidades:
        tenias = unidades_a(cfg, p["id"], f, excluir=datos.get("id"))
        if unidades > tenias + 1e-6:
            errores.append(f"El {fmt_fecha(f)} solo tenías {fmt_num(tenias)} unidades de "
                           f"«{p.get('corto') or p['nombre']}» y estás vendiendo {fmt_num(unidades)}.")
    if not errores and tipo == "venta":
        bloquea = pignoracion.bloquea_venta(cfg, p["id"], f)
        if bloquea:
            errores.append(f"«{p.get('corto') or p['nombre']}» está pignorado en «{bloquea}»: no se puede vender "
                           "hasta liquidar la pignoración (hazlo en Mis datos → Pignoraciones).")
    if errores:
        raise ErrorValidacion(errores)

    mov = {"fecha": f, "producto": p["id"], "tipo": tipo, "unidades": round(unidades, 8),
           "importe": round(importe, 2)}
    if comision:
        mov["comision"] = round(comision, 2)
    if texto(datos.get("nota")):
        mov["nota"] = texto(datos.get("nota"))
    lista = cfg.setdefault("movimientos", [])
    existente = next((m for m in lista if m.get("id") == datos.get("id")), None) if datos.get("id") else None
    if existente:
        existente.clear()
        existente.update(id=datos["id"], **mov)
        return existente
    mov = {"id": siguiente_id(lista, "m"), **mov}
    lista.append(mov)
    lista.sort(key=lambda m: m["fecha"])
    return mov


def borra_movimiento(cfg, mid):
    antes = len(cfg.get("movimientos", []))
    cfg["movimientos"] = [m for m in cfg.get("movimientos", []) if m.get("id") != mid]
    if len(cfg["movimientos"]) == antes:
        raise ErrorValidacion(["Ese movimiento ya no existe."])


# ---------------------------------------------------------------- valores anotados

def guarda_valoracion(cfg, datos):
    errores = []
    p = producto(cfg, datos.get("producto"))
    if not p:
        errores.append("Elige el producto.")
    f = fecha(datos.get("fecha"), errores)
    valor = numero(datos.get("valor"), "el valor", errores, minimo=0)
    aportado = numero(datos.get("aportado"), "lo aportado", errores, obligatorio=False, minimo=0)
    if errores:
        raise ErrorValidacion(errores)
    val = {"fecha": f, "producto": p["id"], "valor": round(valor, 2)}
    if aportado is not None and p.get("tipo") not in SOLO_SALDO:
        val["aportado"] = round(aportado, 2)
    lista = cfg.setdefault("valoraciones", [])
    # Un solo valor por producto y día: si ya había uno, se sustituye.
    existente = next((v for v in lista if v.get("id") == datos.get("id")), None) if datos.get("id") else None
    existente = existente or next((v for v in lista if v["producto"] == p["id"] and v["fecha"] == f), None)
    if existente:
        vid = existente["id"]
        existente.clear()
        existente.update(id=vid, **val)
        return existente
    val = {"id": siguiente_id(lista, "v"), **val}
    lista.append(val)
    lista.sort(key=lambda v: (v["producto"], v["fecha"]))
    return val


def borra_valoracion(cfg, vid):
    antes = len(cfg.get("valoraciones", []))
    cfg["valoraciones"] = [v for v in cfg.get("valoraciones", []) if v.get("id") != vid]
    if len(cfg["valoraciones"]) == antes:
        raise ErrorValidacion(["Ese valor ya no existe."])


# ---------------------------------------------------------------- pignoraciones

def _fecha_libre(valor, etiqueta, errores, obligatorio=True):
    """Como fecha(), pero admite fechas futuras (el primer pago o el cuadro lo son)."""
    if valor is None or not str(valor).strip():
        if obligatorio:
            errores.append(f"Falta {etiqueta}.")
        return None
    try:
        return dt.date.fromisoformat(str(valor)[:10]).isoformat()
    except ValueError:
        errores.append(f"{etiqueta.capitalize()} no es una fecha válida.")
        return None


def _valida_cuadro(cuadro, errores):
    if not isinstance(cuadro, list) or not cuadro:
        return None
    filas = []
    for i, r in enumerate(cuadro, start=1):
        try:
            f = dt.date.fromisoformat(str(r["fecha"])[:10]).isoformat()
            filas.append({"fecha": f, "cuota": round(float(r["cuota"]), 2),
                          "intereses": round(float(r["intereses"]), 2),
                          "amortizado": round(float(r["amortizado"]), 2),
                          "pendiente": round(float(r["pendiente"]), 2)})
        except (KeyError, TypeError, ValueError):
            errores.append(f"La fila {i} del cuadro de amortización no es válida.")
            return None
    filas.sort(key=lambda r: r["fecha"])
    return filas


def guarda_pignoracion(cfg, datos):
    """Crea o actualiza una pignoración (préstamo con garantía de activos)."""
    errores = []
    nombre = texto(datos.get("nombre"))
    if not nombre:
        errores.append("Ponle un nombre a la pignoración (por ejemplo, «Préstamo con mi cartera»).")
    activos = [a for a in (datos.get("activos") or []) if isinstance(a, str)]
    desconocidos = [a for a in activos if not producto(cfg, a)]
    if not activos:
        errores.append("Marca qué activos has pignorado.")
    if desconocidos:
        errores.append("Hay activos que ya no existen: " + ", ".join(desconocidos))
    principal = numero(datos.get("principal"), "el dinero recibido", errores, mayor_que=0)
    f = _fecha_libre(datos.get("fecha"), "la fecha en que recibiste el dinero", errores)
    interes = numero(datos.get("interes"), "el interés anual", errores, minimo=0)
    cuadro = _valida_cuadro(datos.get("cuadro"), errores)
    cuotas = numero(datos.get("cuotas"), "el número de cuotas", errores, obligatorio=not cuadro, mayor_que=0)
    if cuotas is not None and cuotas != int(cuotas):
        errores.append("El número de cuotas tiene que ser entero.")
    cuota = numero(datos.get("cuota"), "la cuota mensual", errores, obligatorio=False, mayor_que=0)
    primer = _fecha_libre(datos.get("primerPago"), "la fecha de la primera cuota", errores, obligatorio=not cuadro)
    apertura = numero(datos.get("comisionApertura"), "la comisión de apertura", errores, obligatorio=False, minimo=0)
    cancel = numero(datos.get("comisionCancelacion"), "la comisión de cancelación", errores,
                    obligatorio=False, minimo=0)
    ltv = numero(datos.get("ltvMax"), "el límite de préstamo sobre garantía", errores, obligatorio=False,
                 mayor_que=0)
    if ltv is not None and ltv > 100:
        errores.append("El límite de préstamo sobre garantía va de 0 a 100 %.")
    recibido = numero(datos.get("recibido"), "lo que te ingresaron", errores, obligatorio=False, mayor_que=0)
    hasta = _fecha_libre(datos.get("efectivoHasta"), "la fecha hasta la que tuviste el dinero", errores,
                         obligatorio=False)
    if f and hasta and hasta < f:
        errores.append("El dinero no puede haberse invertido antes de recibirlo.")
    if errores:
        raise ErrorValidacion(errores)

    item = {"nombre": nombre, "entidad": texto(datos.get("entidad")), "activos": activos,
            "principal": round(principal, 2), "fecha": f, "interes": interes,
            "comisionApertura": round(apertura or 0, 2), "comisionCancelacion": cancel or 0,
            "nota": texto(datos.get("nota"), 400)}
    if cuadro:
        item.update(cuadro=cuadro, cuotas=len(cuadro), primerPago=cuadro[0]["fecha"], cuota=cuadro[0]["cuota"])
    else:
        item.update(cuotas=int(cuotas), primerPago=primer)
        if cuota:
            item["cuota"] = round(cuota, 2)
    if ltv is not None:
        item["ltvMax"] = ltv
    if recibido is not None:
        item["recibido"] = round(recibido, 2)
    if hasta:
        item["efectivoHasta"] = hasta

    lista = cfg.setdefault("pignoraciones", [])
    existente = next((x for x in lista if x.get("id") == datos.get("id")), None) if datos.get("id") else None
    if existente:
        for k in ("estado", "fechaLiquidacion", "importeLiquidacion"):
            if k in existente:
                item[k] = existente[k]
        existente.clear()
        existente.update(id=datos["id"], **item)
        return existente
    item = {"id": siguiente_id(lista, "pg"), "estado": "activa", **item}
    lista.append(item)
    return item


def borra_pignoracion(cfg, pid):
    antes = len(cfg.get("pignoraciones", []))
    cfg["pignoraciones"] = [x for x in cfg.get("pignoraciones", []) if x.get("id") != pid]
    if len(cfg["pignoraciones"]) == antes:
        raise ErrorValidacion(["Esa pignoración ya no existe."])


def liquida_pignoracion(cfg, pid, datos):
    """Marca la pignoración como liquidada: la deuda desaparece y los activos quedan libres."""
    errores = []
    x = next((x for x in cfg.get("pignoraciones", []) if x.get("id") == pid), None)
    if not x:
        raise ErrorValidacion(["Esa pignoración ya no existe."])
    f = fecha(datos.get("fecha"), errores)
    importe = numero(datos.get("importe"), "lo que pagaste para liquidarla", errores, obligatorio=False, minimo=0)
    if f and f < x["fecha"]:
        errores.append("No se puede liquidar antes de haberla recibido.")
    if errores:
        raise ErrorValidacion(errores)
    x.update(estado="liquidada", fechaLiquidacion=f)
    if importe is not None:
        x["importeLiquidacion"] = round(importe, 2)
    return x


def reabre_pignoracion(cfg, pid):
    x = next((x for x in cfg.get("pignoraciones", []) if x.get("id") == pid), None)
    if not x:
        raise ErrorValidacion(["Esa pignoración ya no existe."])
    for k in ("fechaLiquidacion", "importeLiquidacion"):
        x.pop(k, None)
    x["estado"] = "activa"
    return x
