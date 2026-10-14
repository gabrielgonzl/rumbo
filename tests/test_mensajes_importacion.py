# -*- coding: utf-8 -*-
"""Q5: cada error de importación dice qué hacer (no solo qué falla)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import almacen, importar  # noqa: E402

BASE = {"fecha": "2026-03-10", "tipo_movimiento": "compra", "identificador": "XX", "importe": "100"}


def errores_de(**cambios):
    fila = dict(BASE, **cambios)
    cfg = almacen.CARTERA_VACIA
    plan = importar.preparar_tabla(cfg, [(2, fila)], tempfile.mkdtemp())
    return [e["mensaje"] for e in plan.errores]


class MensajesAccionables(unittest.TestCase):
    def assertAccion(self, msgs, *palabras):
        self.assertTrue(msgs, "se esperaba un error")
        txt = " ".join(msgs).lower()
        self.assertTrue(any(p in txt for p in palabras), msgs)

    def test_fecha(self):
        self.assertAccion(errores_de(fecha="ayer"), "usa el formato")

    def test_tipo(self):
        self.assertAccion(errores_de(tipo_movimiento="regalo"), "usa compra")

    def test_numero_ilegible(self):
        self.assertAccion(errores_de(importe="cien euros"), "escríbelo", "sin €")

    def test_sin_importe(self):
        self.assertAccion(errores_de(importe=""), "rellena")

    def test_sin_identificador(self):
        self.assertAccion(errores_de(identificador=""), "pon el isin", "rellena")


if __name__ == "__main__":
    unittest.main()
