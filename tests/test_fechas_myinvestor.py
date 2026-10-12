# -*- coding: utf-8 -*-
"""Importar MyInvestor: el valor de hoy cuadra y la fecha de entrada es coherente con coste y valor."""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import importar  # noqa: E402


def serie_lineal():
    """VL de 10 a 20 entre 2024-01-01 y 2026-01-01, un valor por día."""
    ini, fin = dt.date(2024, 1, 1), dt.date(2026, 1, 1)
    n = (fin - ini).days
    return {(ini + dt.timedelta(days=i)).isoformat(): 10 + 10 * i / n for i in range(n + 1)}


class Fechas(unittest.TestCase):
    def setUp(self):
        self.s = serie_lineal()
        self.vl_hoy = self.s["2026-01-01"]                              # 20

    def test_lote_coherente_conserva_su_fecha(self):
        vl = self.s["2024-10-17"]
        coste, valor = 100.0, 100.0 * self.vl_hoy / vl
        movs, _ = importar.myinvestor_a_movimientos("f", [("2024-10-17", coste, valor)], [], self.s)
        m = movs[0]
        self.assertEqual(m["fecha"], "2024-10-17")
        self.assertNotIn("fechaFiscal", m)
        self.assertAlmostEqual(m["unidades"] * self.vl_hoy, valor, places=2)     # el valor de hoy cuadra

    def test_lote_incoherente_se_recoloca_y_guarda_la_fecha_fiscal(self):
        # +25 % real, pero a su «fecha fiscal» el VL implicaría +54 %: el dinero no entró ese día.
        movs, deducidas = importar.myinvestor_a_movimientos("f", [("2024-10-17", 100.0, 125.0)], [], self.s)
        m = movs[0]
        self.assertEqual(deducidas, 1)
        self.assertEqual(m["fechaFiscal"], "2024-10-17")
        self.assertGreater(m["fecha"], "2025-01-01")                             # entra mucho después
        self.assertAlmostEqual(self.s[m["fecha"]], 16.0, delta=0.16)             # VL = 20 / 1,25
        self.assertAlmostEqual(m["unidades"] * self.vl_hoy, 125.0, places=2)

    def test_valor_de_hoy_siempre_cuadra_con_el_extracto(self):
        lotes = [("2024-10-17", 100.0, 125.0), ("2025-03-03", 50.0, 61.0), ("2024-02-01", 40.0, 80.0)]
        movs, _ = importar.myinvestor_a_movimientos("f", lotes, [], self.s)
        self.assertAlmostEqual(sum(m["unidades"] for m in movs) * self.vl_hoy, 125 + 61 + 80, places=1)

    def test_reembolsos_pasan_como_antes(self):
        movs, _ = importar.myinvestor_a_movimientos("f", [("2025-01-10", 10.0, 12.0)], [("2024-12-01", 7.5)], self.s)
        v = [m for m in movs if m["tipo"] == "venta"][0]
        self.assertEqual((v["unidades"], v["importe"]), (0, 7.5))

    def test_sin_serie_usa_el_comportamiento_anterior(self):
        movs, sin = importar.myinvestor_a_movimientos("f", [("2025-01-10", 10.0, 12.0)], [], {})
        self.assertEqual(len(movs), 1)
        self.assertEqual(movs[0]["fecha"], "2025-01-10")


if __name__ == "__main__":
    unittest.main()
