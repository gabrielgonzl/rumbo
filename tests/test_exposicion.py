# -*- coding: utf-8 -*-
"""Transparencia: composición de fondos agregada por empresa."""
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import exposicion as ex  # noqa: E402


def resp(holdings, fecha="2026-09-30T00:00:00"):
    return [{"Portfolios": [{"ReleaseTopHoldingDate": fecha, "PortfolioHoldings": holdings}]}]


def h(nombre, peso, isin="", pais="USA", tipo="E"):
    return {"SecurityName": nombre, "ISIN": isin, "Weighting": peso, "CountryId": pais, "DetailHoldingTypeId": tipo}


class Parseo(unittest.TestCase):
    def test_extrae_posiciones_ordenadas_y_descarta_ceros(self):
        d = ex.parsea(resp([h("B", 3.0), h("A", 10.5, "US0378331005"), h("Cero", 0)]))
        self.assertEqual([p["nombre"] for p in d["posiciones"]], ["A", "B"])
        self.assertEqual(d["fecha"], "2026-09-30")

    def test_elige_la_cartera_con_mas_posiciones(self):
        r = [{"Portfolios": [{"PortfolioHoldings": [h("Bono", 4, tipo="B")]},
                             {"PortfolioHoldings": [h("A", 5), h("B", 4), h("C", 3)]}]}]
        self.assertEqual(len(ex.parsea(r)["posiciones"]), 3)

    def test_respuesta_vacia(self):
        self.assertIsNone(ex.parsea([{"Portfolios": []}]))
        self.assertIsNone(ex.parsea("x"))


class Clave(unittest.TestCase):
    def test_isin_manda_y_los_nombres_se_normalizan(self):
        self.assertEqual(ex.clave("Apple Inc", "us0378331005"), "US0378331005")
        self.assertEqual(ex.clave("Berkshire Hathaway Inc Class B"), ex.clave("BERKSHIRE HATHAWAY INC"))
        self.assertEqual(ex.clave("Nestlé S.A."), ex.clave("Nestle SA"))


class Agregacion(unittest.TestCase):
    def test_suma_entre_fondos_y_acciones_directas(self):
        pos = [{"id": "f1", "nombre": "Fondo 1", "valor": 1000.0, "tipo": "fondo"},
               {"id": "f2", "nombre": "Fondo 2", "valor": 3000.0, "tipo": "fondo"},
               {"id": "ac", "nombre": "Apple Inc", "valor": 500.0, "tipo": "accion", "isin": "US0378331005"},
               {"id": "f3", "nombre": "Sin datos", "valor": 100.0, "tipo": "fondo"}]
        comps = {"f1": {"posiciones": [{"nombre": "Apple Inc", "isin": "US0378331005", "peso": 10.0, "pais": "USA"}]},
                 "f2": {"posiciones": [{"nombre": "APPLE INC", "isin": "US0378331005", "peso": 5.0, "pais": "USA"},
                                       {"nombre": "Otra", "isin": "", "peso": 2.0, "pais": "FRA"}]}}
        r = ex.agrega(pos, comps)
        apple = r["items"][0]
        self.assertEqual(apple["valor"], 100 + 150 + 500)            # 10 % de 1.000 + 5 % de 3.000 + directa
        self.assertEqual(len(apple["fuentes"]), 3)
        self.assertAlmostEqual(apple["peso"], 750 / 4600, places=4)
        self.assertEqual(r["sinDatos"], ["Sin datos"])
        self.assertEqual({c["id"]: c["cubierto"] for c in r["cobertura"]}, {"f1": 10.0, "f2": 7.0})

    def test_sin_composiciones_solo_cuentan_las_acciones(self):
        r = ex.agrega([{"id": "a", "nombre": "X", "valor": 10.0, "tipo": "accion"}], {})
        self.assertEqual(len(r["items"]), 1)


class Cache(unittest.TestCase):
    def test_baja_guarda_y_reutiliza_sin_red(self):
        carpeta = tempfile.mkdtemp(prefix="rumbo_ex_")
        cuerpo = json.dumps(resp([h("A", 10.0)])).encode()

        class R(io.BytesIO):
            def __enter__(s): return s
            def __exit__(s, *a): return False
        llamadas = []

        def abre(req, timeout=0):
            llamadas.append(1)
            return R(cuerpo)
        d = ex.trae("F000TEST", carpeta, True, abre=abre)
        self.assertEqual(d["posiciones"][0]["nombre"], "A")
        ex.trae("F000TEST", carpeta, True, abre=abre)                # fresca: no vuelve a descargar
        self.assertEqual(len(llamadas), 1)
        self.assertIsNotNone(ex.trae("F000TEST", carpeta, False))     # sin permiso de red: de la caché

    def test_sin_red_devuelve_lo_que_hubiera(self):
        carpeta = tempfile.mkdtemp(prefix="rumbo_ex_")

        def falla(req, timeout=0):
            raise OSError("sin red")
        self.assertIsNone(ex.trae("F000NADA", carpeta, True, abre=falla))


if __name__ == "__main__":
    unittest.main()
