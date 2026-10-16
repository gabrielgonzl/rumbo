# -*- coding: utf-8 -*-
"""La web exportada sin importes no puede dejar cifras sin escalar que delaten el factor secreto."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import exportar  # noqa: E402


class SinImportes(unittest.TestCase):
    def datos(self):
        return {"total": {"patrimonio": 1000.0, "hitos": [10000], "serie": [900.0, 1000.0]},
                "productos": [{"id": "a", "nombre": "A", "valor": 1000.0, "serie": [900.0, 1000.0]}],
                "pasivos": [{"id": "d", "nombre": "Deuda", "valor": -500.0, "serie": [-500.0, -500.0]}],
                "aportacionesMensuales": {"meses": [], "porProducto": {}, "total": []},
                "objetivo": {"importe": 100000},
                "pignoraciones": [{"id": "pg1", "saldo": 500.0, "garantia": 1000.0, "cuota": 10.0}]}

    def test_no_viaja_ninguna_pignoracion(self):
        out = exportar.sin_importes(self.datos())
        self.assertNotIn("pignoraciones", out)

    def test_la_transparencia_no_lleva_el_total_absoluto(self):
        d = self.datos()
        d["transparencia"] = {"total": 1234.5, "items": [{"nombre": "X", "valor": 100.0, "peso": 0.08, "fuentes": [{"valor": 100.0}]}],
                              "cobertura": [{"id": "a", "valor": 1000.0, "cubierto": 40}]}
        out = exportar.sin_importes(d)
        self.assertNotIn("total", out["transparencia"])
        k = out["total"]["patrimonio"] / 1000.0
        self.assertAlmostEqual(out["transparencia"]["items"][0]["valor"], 100.0 * k, places=1)

    def test_cifras_del_prestamo_se_escalan_con_el_mismo_factor(self):
        d = self.datos()
        d["total"].update(aportado=3000.0, capitalPropio=1000.0, dineroPrestado=2000.0, deudaPignoraciones=1800.0)
        d["resumenMensual"] = [{"mes": "2026-09", "inicio": 100.0, "fin": 90.0, "aportado": 0.0, "nuevo": 0.0,
                                "mercado": 0.0, "amortizacionPrestamo": 10.0,
                                "porProducto": {"d": {"inicio": 100.0, "fin": 90.0, "amortizacionPrestamo": 10.0}}}]
        out = exportar.sin_importes(d)
        k = out["total"]["aportado"] / 3000.0
        t = out["total"]
        self.assertAlmostEqual(t["capitalPropio"], 1000.0 * k, places=1)
        self.assertAlmostEqual(t["dineroPrestado"], 2000.0 * k, places=1)
        self.assertAlmostEqual(t["deudaPignoraciones"], 1800.0 * k, places=1)
        m = out["resumenMensual"][0]
        self.assertAlmostEqual(m["amortizacionPrestamo"], 10.0 * k, places=1)
        self.assertAlmostEqual(m["porProducto"]["d"]["amortizacionPrestamo"], 10.0 * k, places=1)
        # y nada queda con su valor real (salvo que el factor sea casi 1)
        if abs(k - 1) > 0.05:
            self.assertNotAlmostEqual(t["dineroPrestado"], 2000.0, places=0)

    def test_la_fiscalidad_no_viaja_en_la_web_sin_importes(self):
        d = self.datos()
        d["fiscal"] = {"anos": [{"ano": 2025, "base": 1234.0, "cuota": 234.0}]}
        self.assertNotIn("fiscal", exportar.sin_importes(d))

    def test_los_ingresos_no_viajan_en_la_web_sin_importes(self):
        d = self.datos()
        d["ingresos"] = {"porMes": [{"mes": "2026-01", "total": 40.0, "porProducto": {"a": 40.0}}],
                         "ultimosDoce": 40.0, "total": {"ultimosDoce": 40.0}}
        self.assertNotIn("ingresos", exportar.sin_importes(d))
        self.assertIn("ingresos", d)           # el original no se toca

    def test_los_importes_salen_escalados(self):
        out = exportar.sin_importes(self.datos())
        self.assertNotEqual(out["total"]["patrimonio"], 1000.0)
        # la deuda se escala con el mismo factor que el resto: su proporción se conserva
        k = out["total"]["patrimonio"] / 1000.0
        self.assertAlmostEqual(out["pasivos"][0]["valor"], -500.0 * k, places=1)


if __name__ == "__main__":
    unittest.main()
