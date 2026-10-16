# -*- coding: utf-8 -*-
"""
umbrales.py  ·  Umbrales de las alertas (valores por defecto y lectura de lo guardado)
======================================================================================
Todo en %: pesos de concentración, puntos de desvío de la asignación y % del límite del préstamo
(LTV máximo) a partir del cual hay «atención» y «riesgo alto». Vive en su propio módulo para que
`almacen` (que valida y guarda) y `motor` (que lo publica) no se importen entre sí.
"""

POR_DEFECTO = {"concentracionProducto": 15, "concentracionValor": 5, "desviacionAsignacion": 5,
               "ltvAtencion": 75, "ltvAlto": 90}


def _numero(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def de(cfg):
    """Umbrales vigentes: los guardados sobre los de por defecto (claves que falten o sobren se ignoran)."""
    guardados = ((cfg or {}).get("alertas") or {}).get("umbrales") or {}
    return {k: (guardados[k] if _numero(guardados.get(k)) else v) for k, v in POR_DEFECTO.items()}
