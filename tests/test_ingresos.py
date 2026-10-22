# -*- coding: utf-8 -*-
"""Ingresos pasivos (dividendos): casos calculados a mano con cifras genéricas."""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import ingresos  # noqa: E402

HOY = dt.date(2026, 6, 15)


def cfg(movs, prods=("a",)):
    return {"productos": [{"id": p, "nombre": p.upper(), "corto": p.upper(), "tipo": "accion"} for p in prods],
            "movimientos": [dict(id=f"m{i}", **m) for i, m in enumerate(movs)]}


def c(f, u, imp, p="a"):
    return {"fecha": f, "producto": p, "tipo": "compra", "unidades": u, "importe": imp}


def v(f, u, imp, p="a"):
    return {"fecha": f, "producto": p, "tipo": "venta", "unidades": u, "importe": imp}


def dv(f, imp, p="a"):
    return {"fecha": f, "producto": p, "tipo": "dividendo", "importe": imp}


class Basico(unittest.TestCase):
    def setUp(self):
        self.r = ingresos.calcula(cfg([
            c("2024-01-10", 10, 1000), c("2025-01-10", 10, 2000),
            dv("2025-03-20", 30), dv("2025-07-01", 20),      # 2025: 50 (el de marzo cae fuera de 12 m)
            dv("2026-01-15", 40), dv("2026-03-15", 10),
        ]), {"a": 4000.0}, HOY)

    def test_por_mes_ordenado_y_sin_meses_vacios(self):
        self.assertEqual([m["mes"] for m in self.r["porMes"]], ["2025-03", "2025-07", "2026-01", "2026-03"])
        self.assertEqual(self.r["porMes"][2], {"mes": "2026-01", "total": 40.0, "porProducto": {"a": 40.0}})

    def test_por_ano(self):
        a = {x["ano"]: x for x in self.r["porAno"]}
        self.assertEqual(a[2025]["total"], 50.0)
        self.assertEqual(a[2026]["total"], 50.0)
        self.assertFalse(a[2025]["ultimosDoce"])
        self.assertTrue(a[2026]["ultimosDoce"])
        self.assertEqual(a[2026]["porProducto"], {"a": 50.0})

    def test_ultimos_doce_meses_naturales(self):
        # ventana 2025-07 .. 2026-06: 20 + 40 + 10
        self.assertEqual(self.r["ultimosDoce"], 70.0)

    def test_yields(self):
        p = self.r["productos"][0]
        self.assertEqual(p["id"], "a")
        self.assertEqual(p["ultimosDoce"], 70.0)
        self.assertEqual(p["yieldOnCost"], round(70 / 3000, 4))      # coste vivo 1.000 + 2.000
        self.assertEqual(p["yieldActual"], round(70 / 4000, 4))      # valor actual 4.000
        self.assertEqual(p["ultimaFecha"], "2026-03-15")
        self.assertEqual(self.r["total"], {"ultimosDoce": 70.0, "yieldOnCostCartera": round(70 / 3000, 4),
                                           "yieldActualCartera": round(70 / 4000, 4)})


class Limites(unittest.TestCase):
    def test_sin_dividendos(self):
        r = ingresos.calcula(cfg([c("2025-01-10", 10, 100)]), {"a": 120.0}, HOY)
        self.assertEqual((r["porMes"], r["porAno"], r["productos"]), ([], [], []))
        self.assertEqual(r["ultimosDoce"], 0.0)
        self.assertEqual(r["yieldOnCost"], {})
        self.assertEqual(r["total"]["ultimosDoce"], 0.0)
        self.assertEqual(r["total"]["yieldOnCostCartera"], 0.0)       # hay cartera, pero no paga
        self.assertEqual(r["total"]["yieldActualCartera"], 0.0)
        vacio = ingresos.calcula({}, {}, HOY)["total"]                 # sin cartera no hay rendimiento
        self.assertEqual(vacio, {"ultimosDoce": 0.0, "yieldOnCostCartera": None, "yieldActualCartera": None})

    def test_cfg_vacio_no_lanza(self):
        r = ingresos.calcula({}, {}, HOY)
        self.assertEqual(r["total"]["ultimosDoce"], 0.0)
        r = ingresos.calcula(cfg([dv("2026-01-01", 5, p="fantasma")]), {}, HOY)    # producto desconocido
        self.assertEqual(r["productos"][0]["nombre"], "fantasma")

    def test_producto_vendido_yield_on_cost_none(self):
        r = ingresos.calcula(cfg([c("2025-01-10", 10, 100), v("2026-01-10", 10, 150), dv("2025-12-01", 6)]),
                             {"a": 0.0}, HOY)
        p = r["productos"][0]
        self.assertEqual(p["ultimosDoce"], 6.0)
        self.assertIsNone(p["yieldOnCost"])
        self.assertIsNone(p["yieldActual"])
        self.assertIsNone(r["yieldOnCost"]["a"])
        self.assertIsNone(r["total"]["yieldOnCostCartera"])

    def test_coste_vivo_fifo_tras_venta_parcial(self):
        # compra 10 a 10 € y 10 a 20 €; vende 15 -> quedan 5 a 20 € = 100 € de coste vivo
        r = ingresos.calcula(cfg([c("2024-01-10", 10, 100), c("2024-06-10", 10, 200), v("2025-01-10", 15, 400),
                                  dv("2026-02-01", 5)]), {"a": 500.0}, HOY)
        self.assertEqual(r["productos"][0]["yieldOnCost"], 0.05)
        self.assertEqual(r["productos"][0]["yieldActual"], 0.01)

    def test_futuros_y_ceros_ignorados(self):
        r = ingresos.calcula(cfg([c("2025-01-10", 1, 100), dv("2026-09-01", 99), dv("2026-02-01", 0),
                                  dv("2026-03-01", 4)]), {"a": 100.0}, HOY)
        self.assertEqual([m["mes"] for m in r["porMes"]], ["2026-03"])
        self.assertEqual(r["ultimosDoce"], 4.0)

    def test_orden_por_ingresos_12m_y_varios_productos(self):
        r = ingresos.calcula(cfg([c("2025-01-10", 1, 100, "a"), c("2025-01-10", 1, 200, "b"),
                                  dv("2026-01-01", 3, "a"), dv("2026-01-02", 8, "b"), dv("2024-01-02", 99, "a")],
                                 ("a", "b")), {"a": 100.0, "b": 400.0}, HOY)
        self.assertEqual([p["id"] for p in r["productos"]], ["b", "a"])
        self.assertEqual(r["ultimosDoce"], 11.0)
        self.assertEqual(r["total"]["yieldOnCostCartera"], round(11 / 300, 4))
        self.assertEqual(r["total"]["yieldActualCartera"], round(11 / 500, 4))
        self.assertEqual(r["porMes"][0]["porProducto"], {"a": 99.0})


if __name__ == "__main__":
    unittest.main()
