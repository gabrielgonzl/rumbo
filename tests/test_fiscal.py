# -*- coding: utf-8 -*-
"""Fiscalidad del ahorro: escala, FIFO, compensación y regla de recompra (casos calculados a mano)."""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import fiscal as fs  # noqa: E402


def cfg(movs, tipo="accion", extra=None):
    prod = {"id": "a", "nombre": "A", "corto": "A", "tipo": tipo}
    prod.update(extra or {})
    return {"productos": [prod], "movimientos": [dict(id=f"m{i}", producto="a", **m) for i, m in enumerate(movs)]}


def c(f, u, imp):
    return {"fecha": f, "tipo": "compra", "unidades": u, "importe": imp}


def v(f, u, imp):
    return {"fecha": f, "tipo": "venta", "unidades": u, "importe": imp}


class Escala(unittest.TestCase):
    def test_tramos(self):
        self.assertEqual(fs.cuota_ahorro(0), 0)
        self.assertEqual(fs.cuota_ahorro(6000), 1140.0)
        self.assertEqual(fs.cuota_ahorro(15000), 3030.0)                     # ejemplo de fondos: 1.140 + 21 % de 9.000
        self.assertEqual(fs.cuota_ahorro(50000), 10380.0)
        self.assertEqual(fs.cuota_ahorro(200000), 44880.0)
        self.assertEqual(fs.cuota_ahorro(300000), 71880.0)
        self.assertEqual(fs.cuota_ahorro(400000), 71880.0 + 30000)          # el 30 % rige desde 2025

    def test_desglose_suma_la_cuota(self):
        t = fs.tramos(70000)
        self.assertEqual(round(sum(x["cuota"] for x in t), 2), fs.cuota_ahorro(70000))
        self.assertEqual([x["tipo"] for x in t], [0.19, 0.21, 0.23])


class Fifo(unittest.TestCase):
    def test_vende_primero_lo_mas_antiguo(self):
        r = fs.ventas_realizadas(cfg([c("2023-01-10", 10, 100), c("2023-06-10", 10, 200), v("2024-03-01", 15, 300)]))
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["coste"], 100 + 5 * 20)                         # 10 a 10 € + 5 a 20 €
        self.assertEqual(r[0]["resultado"], 100.0)

    def test_reembolso_importado_cuenta_como_resultado(self):
        r = fs.ventas_realizadas(cfg([{"fecha": "2025-05-05", "tipo": "venta", "unidades": 0, "importe": 42.5}]))
        self.assertEqual(r[0]["resultado"], 42.5)
        self.assertTrue(r[0]["reembolso"])


class Recompra(unittest.TestCase):
    def test_accion_cotizada_dos_meses(self):
        m = [c("2024-01-02", 10, 100), v("2024-06-10", 10, 60), c("2024-07-20", 5, 40)]   # pérdida y recompra a 40 días
        r = fs.calcula(cfg(m, "accion"))
        a = r["anos"][0]
        self.assertTrue(a["ventas"][0]["diferida"])
        self.assertEqual(a["perdidas"], 0.0)                                  # no computa
        self.assertEqual(a["diferidas"], 40.0)

    def test_fuera_de_plazo_si_computa(self):
        m = [c("2024-01-02", 10, 100), v("2024-06-10", 10, 60), c("2024-09-20", 5, 40)]   # 3 meses: fuera de los 2
        a = fs.calcula(cfg(m, "accion"))["anos"][0]
        self.assertFalse(a["ventas"][0]["diferida"])
        self.assertEqual(a["perdidas"], 40.0)

    def test_fondo_no_cotizado_un_ano(self):
        m = [c("2024-01-02", 10, 100), v("2024-06-10", 10, 60), c("2024-12-20", 5, 40)]   # 6 meses: dentro del año
        a = fs.calcula(cfg(m, "fondo"))["anos"][0]
        self.assertTrue(a["ventas"][0]["diferida"])
        self.assertEqual(a["ventas"][0]["plazo"], "1 año")

    def test_la_compra_que_se_vende_no_cuenta_como_recompra(self):
        m = [c("2024-05-20", 10, 100), v("2024-06-10", 10, 60)]               # comprada 3 semanas antes y vendida
        a = fs.calcula(cfg(m, "accion"))["anos"][0]
        self.assertFalse(a["ventas"][0]["diferida"])


class Compensacion(unittest.TestCase):
    def test_perdidas_compensan_ganancias_del_mismo_ano(self):
        m = [c("2024-01-02", 10, 100), v("2024-02-10", 10, 400),             # +300
             {"id": "x", "fecha": "2024-03-01", "tipo": "compra", "unidades": 1, "importe": 50}]
        a = fs.calcula(cfg([c("2024-01-02", 10, 100), v("2024-08-10", 10, 400)]))["anos"][0]
        self.assertEqual((a["ganancias"], a["perdidas"], a["patrimoniales"]), (300.0, 0.0, 300.0))
        self.assertEqual(a["base"], 300.0)
        self.assertEqual(a["cuota"], 57.0)

    def test_perdida_compensa_dividendos_solo_un_25_por_ciento(self):
        movs = [c("2024-01-02", 10, 1000), v("2024-08-10", 10, 200),          # −800
                {"fecha": "2024-09-01", "tipo": "dividendo", "unidades": 0, "importe": 1000}]
        a = fs.calcula(cfg(movs, "accion"))["anos"][0]
        self.assertEqual(a["compensadoCruzada"], 250.0)                       # 25 % de 1.000
        self.assertEqual(a["base"], 750.0)
        self.assertEqual(a["arrastrePendiente"], [{"ano": 2024, "importe": 550.0}])

    def test_arrastre_se_aplica_al_ano_siguiente_y_caduca_a_los_cuatro(self):
        movs = [c("2020-01-02", 10, 1000), v("2020-08-10", 10, 200),          # −800 en 2020
                c("2021-01-02", 10, 100), v("2021-08-10", 10, 600),           # +500 en 2021
                c("2026-01-02", 10, 100), v("2026-08-10", 10, 600)]           # +500 en 2026 (el resto ya caducó)
        r = {a["ano"]: a for a in fs.calcula(cfg(movs, "accion"))["anos"]}
        self.assertEqual(r[2021]["arrastreUsado"], 500.0)
        self.assertEqual(r[2021]["base"], 0.0)
        self.assertEqual(r[2026]["arrastreUsado"], 0.0)                       # 2020 + 4 = 2024: caducó
        self.assertEqual(r[2026]["base"], 500.0)


class Modelo720(unittest.TestCase):
    def test_solo_cuenta_lo_marcado_en_el_extranjero(self):
        c1 = {"productos": [{"id": "a", "tipo": "fondo", "custodia": "extranjero"},
                            {"id": "b", "tipo": "fondo"},
                            {"id": "c", "tipo": "cripto", "custodia": "extranjero"}], "movimientos": []}
        r = fs.modelo_720(c1, {"a": 60000.0, "b": 999999.0, "c": 20000.0})
        self.assertTrue(r["supera720"])
        self.assertFalse(r["supera721"])
        self.assertEqual(r["categorias"]["valores"], 60000.0)
        self.assertEqual(r["productosMarcados"], 2)


if __name__ == "__main__":
    unittest.main()
