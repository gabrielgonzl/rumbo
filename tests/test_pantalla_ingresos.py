# -*- coding: utf-8 -*-
"""La pantalla de Ingresos vive en la pestaña Fiscalidad y no viaja en la web exportada."""
import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from app import exportar  # noqa: E402

WEB = os.path.join(RAIZ, "app", "web")


def lee(n):
    return open(os.path.join(WEB, n), encoding="utf-8").read()


class PantallaIngresos(unittest.TestCase):
    def test_contenedor_y_pintado(self):
        self.assertIn('id="ingresos"', lee("index.html"))
        js = lee("app.js")
        self.assertIn("function pintaIngresos()", js)
        self.assertIn("pintaIngresos(); pintaFiscal();", js)

    def test_se_oculta_si_no_hay_datos_o_es_estatica(self):
        js = lee("app.js")
        cuerpo = js[js.index("function pintaIngresos()"):js.index("function pintaFiscal()")]
        self.assertIn("!I ||", cuerpo)
        self.assertIn("window.ESTATICO", cuerpo)
        self.assertIn("OCULTAR_IMPORTES", cuerpo)

    def test_la_web_exportada_con_importes_tampoco_lleva_ingresos(self):
        datos = {"total": {"patrimonio": 1, "serie": [], "hitos": []}, "productos": [],
                 "ingresos": {"ultimosDoce": 99.5, "porMes": [], "porAno": [], "productos": [], "total": {}}}
        self.assertNotIn("99.5", exportar.pagina(WEB, datos))

    def test_la_web_sin_importes_no_lleva_ingresos(self):
        datos = {"total": {"patrimonio": 1, "serie": [], "hitos": []}, "productos": [],
                 "ingresos": {"ultimosDoce": 99.5, "porMes": [], "porAno": [], "productos": [], "total": {}}}
        self.assertNotIn("ingresos", exportar.sin_importes(datos))


if __name__ == "__main__":
    unittest.main()
