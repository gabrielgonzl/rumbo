# -*- coding: utf-8 -*-
"""Pignoraciones: cuadro, deuda pendiente, coste, garantía y bloqueo de ventas."""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import pignoracion as pg  # noqa: E402

D = dt.date


def prestamo(**kw):
    base = {"id": "p1", "nombre": "Préstamo cartera", "entidad": "MyInvestor", "estado": "activa",
            "activos": ["a", "b"], "principal": 10000.0, "fecha": "2026-09-23", "interes": 5.0,
            "cuotas": 120, "primerPago": "2026-10-23", "comisionApertura": 0, "comisionCancelacion": 0}
    base.update(kw)
    return base


class Cuadro(unittest.TestCase):
    def test_cuadro_frances_de_referencia(self):
        c = pg.cuadro(prestamo())
        self.assertEqual(len(c), 120)
        self.assertEqual(c[0]["cuota"], 106.07)
        self.assertEqual(c[0]["intereses"], 41.67)
        self.assertEqual(c[0]["pendiente"], 9935.60)
        self.assertEqual(c[0]["fecha"], "2026-10-23")
        self.assertEqual(c[-1]["fecha"], "2036-09-23")
        self.assertEqual(c[-1]["pendiente"], 0.0)
        self.assertAlmostEqual(c[-1]["cuota"], 105.37, delta=0.15)

    def test_ultimo_dia_de_mes_corto(self):
        self.assertEqual(pg.suma_meses(D(2026, 1, 31), 1), D(2026, 2, 28))

    def test_cuadro_importado_manda(self):
        p = prestamo(cuadro=[{"fecha": "2026-10-23", "cuota": 10, "intereses": 1, "amortizado": 9, "pendiente": 5491}])
        self.assertEqual(len(pg.cuadro(p)), 1)


class Estado(unittest.TestCase):
    def test_hoy_aun_sin_cuotas(self):
        e = pg.estado(prestamo(), D(2026, 10, 12))
        self.assertEqual(e["saldo"], 10000.0)
        self.assertEqual(e["cuotasPagadas"], 0)
        self.assertEqual(e["proxima"], {"fecha": "2026-10-23", "cuota": 106.07})
        self.assertAlmostEqual(e["costeTotal"], 2727.71, delta=3)

    def test_tras_dos_cuotas(self):
        e = pg.estado(prestamo(), D(2026, 11, 24))
        self.assertEqual(e["saldo"], 9870.92)
        self.assertEqual(e["cuotasPagadas"], 2)
        self.assertAlmostEqual(e["interesesPagados"], 41.67 + 41.40, delta=0.02)

    def test_liquidar_hoy_con_penalizacion(self):
        e = pg.estado(prestamo(comisionCancelacion=1.0), D(2026, 11, 24))
        self.assertEqual(e["penalizacion"], round(9870.92 * 0.01, 2))
        self.assertGreater(e["aLiquidar"], e["saldo"])
        self.assertGreater(e["ahorroSiLiquidas"], 2000)

    def test_liquidada(self):
        p = prestamo(estado="liquidada", fechaLiquidacion="2026-12-01", importeLiquidacion=9900)
        self.assertEqual(pg.saldo_a(p, D(2026, 11, 30)), 9870.92)
        self.assertEqual(pg.saldo_a(p, D(2026, 12, 1)), 0.0)
        e = pg.estado(p, D(2027, 3, 1))
        self.assertEqual((e["estado"], e["saldo"], e["aLiquidar"], e["cuotasPagadas"]), ("liquidada", 0.0, 0.0, 2))


class Garantia(unittest.TestCase):
    CFG = {"productos": [{"id": "a", "corto": "A"}, {"id": "b", "corto": "B"}], "pignoraciones": [prestamo(ltvMax=95)]}

    def test_colchon(self):
        r = pg.resumen(self.CFG, {"a": 6000, "b": 5000}, D(2026, 10, 12))[0]
        self.assertEqual(r["garantia"], 11000.0)
        deuda = 10000 + r["devengado"]                                  # capital + intereses devengados
        self.assertAlmostEqual(r["ratio"], deuda / 11000, places=3)
        self.assertAlmostEqual(r["caidaHastaIgualar"], 1 - deuda / 11000, places=3)
        self.assertLess(r["caidaHastaLimite"], r["caidaHastaIgualar"])      # el límite salta antes
        self.assertAlmostEqual(r["garantiaMinima"], deuda / 0.95, delta=0.05)

    def test_marcas_y_bloqueo_de_ventas(self):
        self.assertEqual(list(pg.marcas(self.CFG, D(2026, 10, 12))), ["a", "b"])
        self.assertEqual(pg.bloquea_venta(self.CFG, "a", "2026-10-01"), "Préstamo cartera")
        self.assertIsNone(pg.bloquea_venta(self.CFG, "a", "2026-09-01"))      # antes de pignorar
        self.assertIsNone(pg.bloquea_venta(self.CFG, "zzz", "2026-10-01"))


class Derivados(unittest.TestCase):
    def test_deuda_con_saldos_en_cada_pago(self):
        cfg = {"pignoraciones": [prestamo()]}
        prods, vals = pg.derivados(cfg, D(2026, 12, 31))
        self.assertEqual([p["tipo"] for p in prods], ["deuda"])
        self.assertEqual([(v["fecha"], v["valor"]) for v in vals],
                         [("2026-09-23", 10000.0), ("2026-10-23", 9935.6), ("2026-11-23", 9870.92),
                          ("2026-12-23", 9805.98)])

    def test_efectivo_recibido_hasta_que_se_invierte(self):
        cfg = {"pignoraciones": [prestamo(efectivoHasta="2026-09-28")]}
        prods, vals = pg.derivados(cfg, D(2026, 10, 12))
        self.assertEqual({p["tipo"] for p in prods}, {"deuda", "efectivo"})
        cash = [(v["fecha"], v["valor"]) for v in vals if v["producto"].endswith("_efectivo")]
        self.assertEqual(cash, [("2026-09-23", 10000.0), ("2026-09-28", 0.0)])

    def test_no_aparece_antes_de_empezar(self):
        self.assertEqual(pg.derivados({"pignoraciones": [prestamo()]}, D(2026, 9, 1)), ([], []))


if __name__ == "__main__":
    unittest.main()
