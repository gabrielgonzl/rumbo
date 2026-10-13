# -*- coding: utf-8 -*-
"""
exposicion.py  ·  Qué tienes de verdad dentro de tus fondos («transparencia»)
=============================================================================
Cada fondo publica sus mayores posiciones. Sumando, ponderadas por lo que vale cada fondo
en tu cartera, las de todos tus fondos (y las acciones que tengas directamente), se ve la
exposición real a cada empresa: lo que un solo fondo no te enseña.

Solo se conocen las mayores posiciones de cada fondo (Morningstar publica las 10 primeras),
así que la cifra es un MÍNIMO: la exposición real nunca es menor que la que se calcula aquí.
"""

import json
import os
import re
import time
import unicodedata
import urllib.request
from concurrent.futures import ThreadPoolExecutor

DIAS_CACHE = 14
URL = ("https://lt.morningstar.com/api/rest.svc/klr5zyak8x/security_details/{id}"
       "?viewId=MFsnapshot&idtype=msid&responseViewFormat=json&languageId=es-ES&currencyId=EUR")
UA = {"User-Agent": "Mozilla/5.0 (rumbo)"}
ES_ISIN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}\d$")
SUFIJOS = re.compile(r"\b(inc|incorporated|corp|corporation|co|company|ltd|limited|plc|sa|s a|ag|se|nv|"
                     r"class [a-z]|cl [a-z]|clase [a-z]|ord|adr|holdings?|group|the|de|del)\b")


def clave(nombre, isin=None):
    """Identificador común de una empresa: el ISIN si lo hay; si no, el nombre sin sufijos."""
    if isin and ES_ISIN.match(isin.upper()):
        return isin.upper()
    t = unicodedata.normalize("NFKD", str(nombre or "")).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    t = SUFIJOS.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip() or str(nombre or "").lower()


# ---------------------------------------------------------------- lectura de Morningstar

def parsea(respuesta):
    """Respuesta de security_details -> {'fecha', 'posiciones': [{nombre, isin, pais, peso, tipo}]}."""
    o = respuesta[0] if isinstance(respuesta, list) and respuesta else respuesta
    if not isinstance(o, dict):
        return None
    mejor = None
    for pf in o.get("Portfolios") or []:
        hs = pf.get("PortfolioHoldings") or []
        if len(hs) > len((mejor or {}).get("PortfolioHoldings") or []):
            mejor = pf
    if not mejor:
        return None
    pos = []
    for h in mejor["PortfolioHoldings"]:
        peso = h.get("Weighting")
        if not isinstance(peso, (int, float)) or peso <= 0:
            continue
        pos.append({"nombre": h.get("SecurityName") or h.get("ExternalName") or "?",
                    "isin": h.get("ISIN") or "", "pais": h.get("CountryId") or "",
                    "peso": float(peso), "tipo": h.get("DetailHoldingTypeId") or ""})
    pos.sort(key=lambda p: -p["peso"])
    return {"fecha": str(mejor.get("ReleaseTopHoldingDate") or "")[:10], "posiciones": pos}


def _ruta(carpeta, codigo):
    return os.path.join(carpeta, "cache", "holdings_" + re.sub(r"[^A-Za-z0-9_.-]", "_", codigo) + ".json")


def lee_cache(carpeta, codigo):
    try:
        with open(_ruta(carpeta, codigo), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def trae(codigo, carpeta, descargar, abre=None):
    """Composición de un fondo: de la caché si es reciente; si no, de Morningstar (si se permite)."""
    c = lee_cache(carpeta, codigo)
    fresco = c and (time.time() - c.get("ts", 0)) < DIAS_CACHE * 86400
    if fresco or not descargar:
        return c
    try:
        req = urllib.request.Request(URL.format(id=codigo), headers=UA)
        with (abre or urllib.request.urlopen)(req, timeout=10) as r:
            datos = parsea(json.loads(r.read().decode("utf-8", "replace")))
    except Exception:
        return c        # sin red o sin datos: lo último que hubiera
    if datos:
        datos["ts"] = time.time()
        os.makedirs(os.path.join(carpeta, "cache"), exist_ok=True)
        with open(_ruta(carpeta, codigo), "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False)
        return datos
    return c


# ---------------------------------------------------------------- agregación

def agrega(posiciones, composiciones):
    """
    posiciones = [{id, nombre, valor, tipo ('fondo'|'accion'|...), isin, codigo}]
    composiciones = {id de producto: {'posiciones': [...]}}  (solo fondos con datos)
    Devuelve {'items': [...], 'cobertura': [...], 'sinDatos': [...], 'total': float}.
    """
    total = sum(p["valor"] for p in posiciones if p["valor"] > 0) or 1.0
    acc = {}
    cobertura, sin = [], []

    def suma(k, nombre, isin, pais, eur, fuente, directa):
        a = acc.setdefault(k, {"nombre": nombre, "isin": isin, "pais": pais, "valor": 0.0, "fuentes": []})
        a["valor"] += eur
        a["fuentes"].append({"producto": fuente, "valor": round(eur, 2), "directa": directa})
        if directa:
            a["nombre"] = nombre

    for p in posiciones:
        if p["valor"] <= 0:
            continue
        comp = composiciones.get(p["id"])
        if comp and comp.get("posiciones"):
            cub = 0.0
            for h in comp["posiciones"]:
                eur = p["valor"] * h["peso"] / 100.0
                cub += h["peso"]
                suma(clave(h["nombre"], h.get("isin")), h["nombre"], h.get("isin") or "", h.get("pais") or "",
                     eur, p["nombre"], False)
            cobertura.append({"id": p["id"], "nombre": p["nombre"], "valor": round(p["valor"], 2),
                              "cubierto": round(min(cub, 100.0), 1)})
        elif p.get("tipo") in ("accion",):
            suma(clave(p["nombre"], p.get("isin")), p["nombre"], p.get("isin") or "", "", p["valor"], p["nombre"], True)
        elif p.get("tipo") in ("fondo", "etf"):
            sin.append(p["nombre"])
    items = [{"nombre": a["nombre"], "isin": a["isin"], "pais": a["pais"], "valor": round(a["valor"], 2),
              "peso": round(a["valor"] / total, 4),
              "fuentes": sorted(a["fuentes"], key=lambda f: -f["valor"])} for a in acc.values()]
    items.sort(key=lambda i: -i["valor"])
    return {"items": items[:25], "cobertura": cobertura, "sinDatos": sin, "total": round(total, 2)}


def calcula(productos, carpeta, descargar):
    """
    productos = lista de productos ya calculados por el motor (con valor, tipoClave, fuente, codigo).
    Baja (con caché de 14 días) la composición de los fondos de Morningstar y agrega.
    """
    fondos = [p for p in productos if p.get("fuente") == "morningstar" and p.get("codigo") and (p.get("valor") or 0) > 0]
    comps = {}
    if fondos:
        permitir = descargar is True or descargar == "faltan"
        with ThreadPoolExecutor(max_workers=4) as ex:
            for p, c in zip(fondos, ex.map(lambda p: trae(p["codigo"], carpeta, permitir), fondos)):
                if c and c.get("posiciones"):
                    comps[p["id"]] = c
    pos = [{"id": p["id"], "nombre": p.get("corto") or p.get("nombre"), "valor": float(p.get("valor") or 0),
            "tipo": p.get("tipoClave"), "isin": p.get("identificador") or "", "codigo": p.get("codigo")}
           for p in productos if (p.get("valor") or 0) > 0 and p.get("tipoClave") in ("fondo", "etf", "accion")]
    fechas = [c.get("fecha") for c in comps.values() if c.get("fecha")]
    out = agrega(pos, comps)
    out["fecha"] = max(fechas) if fechas else None
    return out
