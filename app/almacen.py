# -*- coding: utf-8 -*-
"""
almacen.py  ·  Guarda y valida la cartera
=========================================
Todo lo que se escribe en mis_datos/cartera.json pasa por aquí: se comprueba
que tiene sentido y, antes de cada cambio, se guarda una copia automática.
"""

import datetime as dt
import json
import math
import os
import re
import unicodedata

from . import pignoracion, umbrales as umbrales_mod
from .motor import TIPOS, FUENTES, num_es

COPIAS_MAX = 20
TIPOS_MOV = {"compra": "Compra", "venta": "Venta", "dividendo": "Dividendo o cupón",
             "comision": "Comisión"}
SOLO_SALDO = ("efectivo", "deuda")   # tipos que se siguen solo con saldos anotados

VERSION_ACTUAL = 4   # v2: asignación objetivo y meta con fecha · v3: umbrales de las alertas · v4: carteras de fondos
UMBRALES_POR_DEFECTO = umbrales_mod.POR_DEFECTO

CARTERA_VACIA = {
    "version": VERSION_ACTUAL, "titular": "Mi patrimonio",
    "productos": [], "movimientos": [], "valoraciones": [], "pignoraciones": [],
    "comparador": [{"id": "real", "nombre": "Mi cartera real", "real": True}],
    "hitos": [10000, 25000, 50000, 100000, 250000, 500000, 1000000],
    "objetivo": {"activo": True, "importe": 100000, "etiqueta": "Próximo objetivo"},
    "asignacion": {"objetivos": {}},
    "alertas": {"umbrales": dict(UMBRALES_POR_DEFECTO)},
    "carteras": [],
}


class ErrorValidacion(Exception):
    def __init__(self, errores):
        super().__init__("; ".join(errores))
        self.errores = errores


# ---------------------------------------------------------------- disco

def migra(cfg):
    """
    Lleva una cartera de una versión anterior a la actual. Las migraciones solo AÑADEN campos
    opcionales: nunca borran ni reescriben lo que ya había. Devuelve True si cambió algo.
    """
    cambio = False
    v = cfg.get("version", 1)
    if v < 2:
        cfg.setdefault("asignacion", {"objetivos": {}})
        cfg.setdefault("pignoraciones", [])
        cfg["version"] = 2
        cambio = True
    if v < 3:
        cfg.setdefault("alertas", {"umbrales": dict(UMBRALES_POR_DEFECTO)})
        cfg["version"] = 3
        cambio = True
    if v < 4:
        cfg.setdefault("carteras", [])
        cfg["version"] = 4
        cambio = True
    return cambio


def umbrales(cfg):
    return umbrales_mod.de(cfg)


def carga(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    migra(cfg)       # en memoria; se escribe (con copia automática previa) la próxima vez que guardes
    return cfg


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
    if not math.isfinite(x):                       # NaN pasa todas las comparaciones: se rechaza aquí
        errores.append(f"{etiqueta.capitalize()} no es un número válido.")
        return None
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
    nums = [int(x["id"][len(prefijo):]) for x in lista if re.fullmatch(prefijo + r"\d+", str(x.get("id", "")))]
    return f"{prefijo}{max(nums, default=0) + 1}"


# ---------------------------------------------------------------- carteras de fondos

def cartera(cfg, cid):
    return next((c for c in cfg.get("carteras", []) if c.get("id") == cid), None)


def _exige_libre(cfg, cid, pid):
    """Un fondo no sale de una cartera que respalda un préstamo vivo: la garantía bajaría (y se desbloquearía su
    venta) sin que nadie lo note. Hay que cambiar antes la garantía del préstamo."""
    vivos = [p for p in cfg.get("pignoraciones", []) if cid in (p.get("carteraIds") or []) and p.get("estado") != "liquidada"]
    if vivos:
        c, f = cartera(cfg, cid) or {}, producto(cfg, pid) or {}
        raise ErrorValidacion([
            f"«{f.get('corto') or f.get('nombre') or pid}» forma parte de la cartera «{c.get('nombre', cid)}», que es garantía del "
            f"préstamo «{vivos[0].get('nombre')}». Cambia antes la garantía del préstamo (Datos → Pignoraciones)."])


def guarda_cartera(cfg, datos):
    """Crea o edita una cartera de fondos. `productos` (opcional) es la lista COMPLETA de fondos que la forman:
    los que no estén se sueltan y los que estén salen de la cartera que tuvieran. Devuelve la cartera."""
    errores = []
    cid = datos.get("id") or None
    existente = cartera(cfg, cid) if cid else None
    if cid and not existente:
        errores.append("Esa cartera ya no existe.")
    nombre = texto(datos.get("nombre"), 1000)
    if not nombre:
        errores.append("Ponle un nombre a la cartera (por ejemplo, «Cartera Ejemplo»).")
    elif len(nombre) > 80:
        errores.append("El nombre de la cartera no puede pasar de 80 caracteres.")
    elif any(str(c.get("nombre", "")).lower() == nombre.lower() for c in cfg.get("carteras", []) if c.get("id") != cid):
        errores.append(f"Ya tienes una cartera llamada «{nombre}».")
    ltv = numero(datos.get("ltvMax"), "el límite de préstamo sobre garantía de la cartera", errores,
                 obligatorio=False, mayor_que=0)
    if ltv is not None and ltv > 100:
        errores.append("El límite de préstamo sobre garantía va de 0 a 100 %.")
    ids = None
    if "productos" in datos:
        ids = [x for x in (datos.get("productos") or []) if isinstance(x, str)]
        desconocidos = [x for x in ids if not producto(cfg, x)]
        if desconocidos:
            errores.append("Hay fondos que ya no existen: " + ", ".join(desconocidos))
    if errores:
        raise ErrorValidacion(errores)

    if ids is not None:
        for p in cfg["productos"]:
            sale = p.get("carteraId") == cid and p["id"] not in ids                       # sale de esta cartera
            se_mueve = p["id"] in ids and p.get("carteraId") not in (None, cid)            # sale de otra para entrar aquí
            if sale and existente:
                _exige_libre(cfg, cid, p["id"])
            if se_mueve:
                _exige_libre(cfg, p["carteraId"], p["id"])
    carteras = cfg.setdefault("carteras", [])
    item = existente
    if item is None:
        item = {"id": siguiente_id(carteras, "c")}
        carteras.append(item)
    item["nombre"] = nombre
    for k, v in (("entidad", texto(datos.get("entidad"), 80)), ("ltvMax", ltv)):
        if v in ("", None):
            item.pop(k, None)
        else:
            item[k] = v
    if ids is not None:
        for p in cfg["productos"]:
            if p["id"] in ids:
                p["carteraId"] = item["id"]
            elif p.get("carteraId") == item["id"]:
                p.pop("carteraId", None)
    return dict(item)


def borra_cartera(cfg, cid):
    """Borra la cartera: sus fondos quedan sueltos y se quita de la garantía de los préstamos. Si un préstamo
    vivo se quedara sin garantía, no se borra."""
    c = cartera(cfg, cid)
    if not c:
        raise ErrorValidacion(["Esa cartera ya no existe."])
    for p in cfg.get("pignoraciones", []):
        if cid in (p.get("carteraIds") or []) and p.get("estado") != "liquidada":
            resto = [x for x in p["carteraIds"] if x != cid]
            if not resto and not p.get("activos"):
                raise ErrorValidacion([
                    f"No puedo borrar «{c['nombre']}»: el préstamo «{p.get('nombre')}» solo tiene esa cartera como "
                    "garantía. Cambia su garantía o liquídalo primero."])
    cfg["carteras"] = [x for x in cfg["carteras"] if x.get("id") != cid]
    for pr in cfg["productos"]:
        if pr.get("carteraId") == cid:
            pr.pop("carteraId", None)
    for p in cfg.get("pignoraciones", []):
        if cid in (p.get("carteraIds") or []):
            resto = [x for x in p["carteraIds"] if x != cid]
            if resto:
                p["carteraIds"] = resto
            else:
                p.pop("carteraIds", None)


def sanea_copia(cfg):
    """Limpia una cartera que llega de fuera (copia subida o recuperada): sin < ni > en ningún texto y con
    `slot` siempre entero 1-12. Una copia ajena no pasa por `texto()` y sus nombres acaban en HTML."""
    def limpia(v):
        if isinstance(v, str):
            return v.replace("<", "").replace(">", "")
        if isinstance(v, list):
            return [limpia(x) for x in v]
        if isinstance(v, dict):
            return {k: limpia(x) for k, x in v.items()}
        return v
    cfg = limpia(cfg)

    def lista(clave):                        # una copia ajena puede traer null, un número… donde esperamos una lista
        return cfg[clave] if isinstance(cfg.get(clave), list) else []

    ids_cartera = set()
    if "carteras" in cfg:
        limpias = []
        for c in lista("carteras"):
            if not isinstance(c, dict) or not isinstance(c.get("id"), str) or not c["id"] or c["id"] in ids_cartera:
                continue
            ids_cartera.add(c["id"])
            if not (isinstance(c.get("nombre"), str) and c["nombre"].strip()):
                c["nombre"] = c["id"]
            if not isinstance(c.get("entidad"), str):
                c.pop("entidad", None)
            v = c.get("ltvMax")
            try:
                x = None if isinstance(v, bool) else float(v.replace(",", ".")) if isinstance(v, str) else float(v)
            except (TypeError, ValueError, OverflowError):
                x = None
            if x is not None and math.isfinite(x) and 0 < x <= 100:
                c["ltvMax"] = x
            else:
                c.pop("ltvMax", None)
            limpias.append(c)
        cfg["carteras"] = limpias
    for p in lista("productos"):
        if isinstance(p, dict) and "carteraId" in p and not (isinstance(p["carteraId"], str) and p["carteraId"] in ids_cartera):
            p.pop("carteraId")
    for pg in lista("pignoraciones"):
        if isinstance(pg, dict) and "carteraIds" in pg:
            validas = [x for x in pg["carteraIds"] if isinstance(x, str) and x in ids_cartera] if isinstance(pg["carteraIds"], list) else []
            if validas:
                pg["carteraIds"] = validas
            else:
                pg.pop("carteraIds")
    for p in lista("productos"):
        if isinstance(p, dict) and "slot" in p:
            try:
                n = int(p["slot"])
            except (TypeError, ValueError, OverflowError):      # inf, nan, un entero enorme, una lista…
                n = 1
            p["slot"] = n if 1 <= n <= 12 else 1
    return cfg


def producto(cfg, pid):
    return next((p for p in cfg.get("productos", []) if p["id"] == pid), None)


def texto(v, maximo=200):
    """Texto de usuario: recortado y sin < ni >. Los nombres acaban en páginas HTML (también en la
    web exportada) y una importación con IA no es una fuente fiable."""
    if v is None:
        return ""
    return str(v).replace("<", "").replace(">", "").strip()[:maximo]


# ---------------------------------------------------------------- productos

CAMPOS_TEXTO = ("nombre", "corto", "identificador", "codigo", "entidad", "clase", "gestora",
                "tipoDetalle", "respaldo", "respaldoMoneda", "vivo", "papel", "grupo", "custodia")


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
    if "carteraId" in datos:        # sin la clave, la cartera del producto no se toca (p. ej. al importar)
        cid = texto(datos.get("carteraId"), 40)
        nuevo["carteraId"] = cid if cid and cartera(cfg, cid) else ""

    existente = producto(cfg, datos.get("id")) if datos.get("id") else None
    if existente and "carteraId" in nuevo and existente.get("carteraId") and existente["carteraId"] != (nuevo["carteraId"] or None):
        _exige_libre(cfg, existente["carteraId"], existente["id"])
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
    if producto(cfg, pid).get("carteraId"):
        _exige_libre(cfg, producto(cfg, pid)["carteraId"], pid)
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
            errores.append(f"«{p.get('corto') or p['nombre']}» está pignorado en «{bloquea}»: no se puede vender ni traspasar "
                           "hasta liquidar la pignoración (hazlo en Mis datos → Pignoraciones). En Rumbo un traspaso se anota "
                           "como una venta y una compra.")
    if errores:
        raise ErrorValidacion(errores)

    mov = {"fecha": f, "producto": p["id"], "tipo": tipo, "unidades": round(unidades, 8),
           "importe": round(importe, 2)}
    if comision:
        mov["comision"] = round(comision, 2)
    if texto(datos.get("nota")):
        mov["nota"] = texto(datos.get("nota"))
    ff = str(datos.get("fechaFiscal") or "")[:10]
    if ff and ff != f:
        try:
            mov["fechaFiscal"] = dt.date.fromisoformat(ff).isoformat()   # fecha fiscal si difiere de la real
        except ValueError:
            pass
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
    carteras_ids = []
    for c in (datos.get("carteraIds") or []):
        if isinstance(c, str) and c not in carteras_ids:
            carteras_ids.append(c)
    if not activos and not carteras_ids:
        errores.append("Marca qué activos o carteras has pignorado.")
    if desconocidos:
        errores.append("Hay activos que ya no existen: " + ", ".join(desconocidos))
    for c in carteras_ids:
        cartera_c = cartera(cfg, c)
        if not cartera_c:
            errores.append(f"Hay carteras que ya no existen: {c}")
        elif not any(p.get("carteraId") == c for p in cfg.get("productos", [])):
            errores.append(f"La cartera «{cartera_c['nombre']}» está sin fondos: no puede ser garantía de un préstamo. "
                           "Añade fondos a la cartera en Datos → Carteras.")
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
            **({"carteraIds": carteras_ids} if carteras_ids else {}),
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


# ---------------------------------------------------------------- asignación objetivo y meta

def guarda_asignacion(cfg, datos):
    """Porcentaje objetivo de cada grupo de la cartera. Los grupos sin objetivo no cuentan."""
    errores = []
    crudos = datos.get("objetivos")
    if not isinstance(crudos, dict):
        raise ErrorValidacion(["Faltan los porcentajes objetivo."])
    objetivos = {}
    for grupo, valor in crudos.items():
        g = texto(grupo, 80)
        if not g:
            continue
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            continue                       # vacío = sin objetivo
        x = numero(valor, f"el objetivo de «{g}»", errores, minimo=0)
        if x is not None and x > 100:
            errores.append(f"El objetivo de «{g}» no puede pasar del 100 %.")
        if x is not None and x > 0:
            objetivos[g] = round(x, 2)
    if sum(objetivos.values()) > 100.5:
        errores.append(f"Los objetivos suman {sum(objetivos.values()):g} %: no pueden pasar del 100 %.")
    if errores:
        raise ErrorValidacion(errores)
    cfg["asignacion"] = {"objetivos": objetivos}
    return cfg["asignacion"]


def guarda_alertas(cfg, datos):
    """Umbrales de las alertas. Lo que no se envíe se queda como estaba; vacío vuelve al valor de por defecto."""
    errores = []
    crudos = datos.get("umbrales")
    if not isinstance(crudos, dict):
        raise ErrorValidacion(["Faltan los umbrales de las alertas."])
    etiquetas = {"concentracionProducto": ("el peso máximo de un producto", 1, 100),
                 "concentracionValor": ("el peso máximo de un valor dentro de tus fondos", 1, 100),
                 "desviacionAsignacion": ("el desvío de la asignación", 0.5, 50),
                 "ltvAtencion": ("el nivel de atención del préstamo", 10, 99),
                 "ltvAlto": ("el nivel de riesgo alto del préstamo", 11, 100)}
    nuevos = umbrales(cfg)
    for k, (et, lo, hi) in etiquetas.items():
        if k not in crudos:
            continue
        v = crudos[k]
        if v is None or (isinstance(v, str) and not v.strip()):
            nuevos[k] = UMBRALES_POR_DEFECTO[k]
            continue
        x = numero(v, et, errores, minimo=lo)
        if x is not None and x > hi:
            errores.append(f"{et[0].upper() + et[1:]} no puede pasar de {hi:g}.")
        elif x is not None:
            nuevos[k] = round(x, 2)
    if nuevos["ltvAlto"] <= nuevos["ltvAtencion"]:
        errores.append("El nivel de riesgo alto tiene que ser mayor que el de atención.")
    if errores:
        raise ErrorValidacion(errores)
    cfg["alertas"] = {"umbrales": nuevos}
    return cfg["alertas"]


def guarda_meta(cfg, datos):
    """Meta de patrimonio: importe y, si quieres, fecha para calcular cuánto aportar."""
    errores = []
    importe = numero(datos.get("importe"), "el importe de la meta", errores, mayor_que=0)
    f = _fecha_libre(datos.get("fecha"), "la fecha de la meta", errores, obligatorio=False)
    if f and f <= dt.date.today().isoformat():
        errores.append("La fecha de la meta tiene que ser futura.")
    if errores:
        raise ErrorValidacion(errores)
    meta = {"activo": True, "importe": round(importe, 2),
            "etiqueta": texto(datos.get("etiqueta")) or "Mi meta"}
    if f:
        meta["fecha"] = f
    cfg["objetivo"] = meta
    return meta
