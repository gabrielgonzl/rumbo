# -*- coding: utf-8 -*-
"""
carteras.py  ·  Cifras de cada cartera de fondos (suma de sus fondos)
======================================================================
Función pura. Para cada cartera publica `fondos`, `valor`, `aportado`, `plusvalia`, `rentabilidad` y `tir`.

Regla de honestidad: el valor siempre se suma, pero el aportado, la plusvalía, la rentabilidad y la TIR solo se
dan si **todos** los fondos de la cartera tienen aportado y valor (y, para la TIR, flujos de caja). Si a uno le
falta, esas cifras son None: no se calculan con la mitad de los datos.
Un fondo vendido del todo (valor 0, con historia de flujos) cuenta como aportado 0: ya no tiene coste vivo, pero
sus compras y cobros siguen en los flujos de la TIR.
La TIR es la de todos los flujos de los fondos juntos más el valor de hoy (no la media de las TIR de cada fondo).
Los datos que no sean números o fechas válidos (un archivo editado a mano) dejan las cifras en None, no lanzan.
"""

import datetime as dt
import math


def _r4(x):
    return None if x is None else round(x, 4)


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _aportado(p):
    """Coste vivo del fondo, o None si no se puede saber."""
    a, v = p.get("aportado"), p.get("valor")
    if _num(a) and _num(v):
        return float(a)
    if _num(v) and v == 0 and p.get("flujos"):          # vendido del todo
        return 0.0
    return None


def _flujos(miembros):
    """Todos los flujos de los fondos como [(fecha, importe)], o None si algún fondo no los tiene o están mal formados."""
    salida = []
    for p in miembros:
        if not p.get("flujos"):
            return None
        for f, v in p["flujos"]:
            if not _num(v):
                return None
            salida.append((dt.date.fromisoformat(f), float(v)))
    return salida


def resumen(carteras, productos, fecha_extracto, xirr):
    """[{id, nombre, ..., fondos, valor, aportado, plusvalia, rentabilidad, tir}] en el orden de `carteras` (se saltan
    las que no sean un dict con id de texto). `productos` = productos ya calculados por el motor (con valor, aportado y
    flujos); `xirr` = motor.xirr."""
    salida = []
    for c in carteras or []:
        if not isinstance(c, dict) or not isinstance(c.get("id"), str) or not c["id"]:
            continue
        miembros = [p for p in productos if isinstance(p, dict) and p.get("carteraId") == c["id"]]
        valor = round(sum(p["valor"] for p in miembros if _num(p.get("valor"))), 2)
        aportes = [_aportado(p) for p in miembros]
        completos = bool(miembros) and all(a is not None for a in aportes)
        aportado = round(sum(aportes), 2) if completos else None
        plusvalia = round(valor - aportado, 2) if aportado is not None else None
        rentabilidad = _r4(plusvalia / aportado) if aportado else None
        tir = None
        if completos:
            try:
                flujos = _flujos(miembros)
                if flujos is not None:
                    tir = _r4(xirr(flujos + [(fecha_extracto, valor)]))
            except (TypeError, ValueError, OverflowError):
                tir = None
        salida.append(dict(c, fondos=len(miembros), valor=valor, aportado=aportado, plusvalia=plusvalia,
                           rentabilidad=rentabilidad, tir=tir))
    return salida
