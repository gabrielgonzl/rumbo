# -*- coding: utf-8 -*-
"""Q2/Q3: el préstamo no se cuenta como mercado ni como capital propio."""
import json
import os
import sys
import tempfile
import unittest

_TMP = tempfile.mkdtemp(prefix="rumbo_prestamo_")
os.environ["PATRIMONIO_DATOS"] = _TMP
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import almacen, servidor  # noqa: E402


def cartera(prestamo=True, efectivo_hasta="2026-08-15"):
    """Un fondo con valor constante entre agosto y septiembre; el único cambio es la deuda."""
    cfg = json.loads(json.dumps(almacen.CARTERA_VACIA))
    cfg["productos"] = [{"id": "a", "nombre": "Fondo A", "corto": "Fondo A", "tipo": "fondo",
                         "fuente": "manual", "moneda": "EUR", "slot": 1}]
    cfg["valoraciones"] = [
        {"id": f"v{i}", "fecha": f, "producto": "a", "valor": v, "aportado": ap}
        for i, (f, v, ap) in enumerate([("2026-07-31", 1000.0, 1000.0), ("2026-08-31", 3000.0, 3000.0),
                                        ("2026-09-30", 3000.0, 3000.0)])]
    cfg["movimientos"] = [
        {"id": "m0", "fecha": "2026-07-01", "producto": "a", "tipo": "compra", "unidades": 0, "importe": 1000.0},
        {"id": "m1", "fecha": "2026-08-15", "producto": "a", "tipo": "compra", "unidades": 0, "importe": 2000.0}]
    if prestamo:
        p = {"id": "pg1", "nombre": "Préstamo de prueba", "estado": "activa", "activos": ["a"],
             "principal": 2000.0, "fecha": "2026-08-01", "interes": 5.0, "cuotas": 60,
             "primerPago": "2026-09-01"}
        if efectivo_hasta:
            p["efectivoHasta"] = efectivo_hasta
        cfg["pignoraciones"] = [p]
    return cfg


def calcula(cfg):
    servidor.DATOS = _TMP
    almacen.guarda(os.path.join(_TMP, "cartera.json"), cfg)
    for n in ("calculado_propio.json", "estado.json"):
        r = os.path.join(_TMP, n)
        if os.path.exists(r):
            os.remove(r)
    return servidor.recalcula(descargar=False)


class AmortizacionNoEsMercado(unittest.TestCase):
    def test_septiembre_el_mercado_no_incluye_la_amortizacion(self):
        d = calcula(cartera())
        sep = next(m for m in d["resumenMensual"] if m["mes"] == "2026-09")
        # El fondo no se mueve y no hay aportaciones: el mercado es 0 aunque la deuda baje.
        self.assertEqual(sep["aportado"], 0)
        self.assertAlmostEqual(sep["mercado"], 0.0, places=2)
        # La deuda baja en la cuota capital del primer pago (cuadro francés, 5 % a 60 meses).
        self.assertGreater(sep["amortizacionPrestamo"], 0)
        self.assertLess(sep["amortizacionPrestamo"], 100)
        # El desglose cierra: inicio + aportado + nuevo + mercado + amortización = fin.
        suma = sep["inicio"] + sep["aportado"] + sep["nuevo"] + sep["mercado"] + sep["amortizacionPrestamo"]
        self.assertAlmostEqual(suma, sep["fin"], places=1)

    def test_el_efectivo_del_prestamo_que_se_gasta_despues_no_es_amortizacion(self):
        # El efectivo recibido baja a 0 en septiembre (compra el 15-ago, efectivo «hasta» el 10-sep):
        # esa caída NO es deuda devuelta; la amortización sigue siendo solo la cuota capital.
        d = calcula(cartera(efectivo_hasta="2026-09-10"))
        sep = next(m for m in d["resumenMensual"] if m["mes"] == "2026-09")
        self.assertGreater(sep["amortizacionPrestamo"], 0)
        self.assertLess(sep["amortizacionPrestamo"], 100)
        efectivo = [v for k, v in sep["porProducto"].items() if k.endswith("_efectivo")]
        self.assertTrue(all(v["amortizacionPrestamo"] == 0 for v in efectivo))
        suma = sep["inicio"] + sep["aportado"] + sep["nuevo"] + sep["mercado"] + sep["amortizacionPrestamo"]
        self.assertAlmostEqual(suma, sep["fin"], places=1)

    def test_sin_prestamo_el_campo_es_cero(self):
        d = calcula(cartera(prestamo=False))
        for m in d["resumenMensual"]:
            self.assertEqual(m["amortizacionPrestamo"], 0)


class CapitalPropio(unittest.TestCase):
    def test_capital_propio_resta_el_principal_invertido(self):
        d = calcula(cartera())
        t = d["total"]
        self.assertEqual(t["aportado"], 3000.0)              # no cambia
        self.assertEqual(t["dineroPrestado"], 2000.0)
        self.assertEqual(t["capitalPropio"], 1000.0)

    def test_sin_prestamo_todo_es_propio(self):
        t = calcula(cartera(prestamo=False))["total"]
        self.assertEqual(t["dineroPrestado"], 0.0)
        self.assertEqual(t["capitalPropio"], t["aportado"])

    def test_prestamo_no_invertido_no_resta(self):
        # sin «efectivoHasta» no se sabe que se invirtiera: no se resta
        t = calcula(cartera(efectivo_hasta=None))["total"]
        self.assertEqual(t["dineroPrestado"], 0.0)
        self.assertEqual(t["capitalPropio"], t["aportado"])

    def test_prestamo_liquidado_no_resta(self):
        cfg = cartera()
        cfg["pignoraciones"][0].update({"estado": "liquidada", "fechaLiquidacion": "2026-09-15",
                                        "importeLiquidacion": 2000.0})
        t = calcula(cfg)["total"]
        self.assertEqual(t["dineroPrestado"], 0.0)


if __name__ == "__main__":
    unittest.main()
