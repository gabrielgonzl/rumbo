# -*- coding: utf-8 -*-
"""El tema «Carta de navegación» se enlaza en index.html y viaja dentro de la web exportada."""
import os
import re
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from app import exportar  # noqa: E402

WEB = os.path.join(RAIZ, "app", "web")


class TemaCarta(unittest.TestCase):
    def test_se_carga_despues_de_rediseno(self):
        html = open(os.path.join(WEB, "index.html"), encoding="utf-8").read()
        self.assertLess(html.index('href="rediseno.css"'), html.index('href="tema-carta.css"'))

    def test_la_web_exportada_lleva_el_css_en_linea(self):
        css = open(os.path.join(WEB, "tema-carta.css"), encoding="utf-8").read()
        html = exportar.pagina(WEB, {"total": {"patrimonio": 0, "serie": [], "hitos": []}, "productos": []})
        self.assertIn(css.strip()[:200], html)
        self.assertNotIn('href="tema-carta.css"', html)

    def test_sin_degradados_ni_recursos_externos(self):
        css = open(os.path.join(WEB, "tema-carta.css"), encoding="utf-8").read()
        self.assertNotRegex(css, r"(?i)url\(|@import|https?://")
        self.assertNotIn("linear-gradient", re.sub(r"/\*.*?\*/", "", css, flags=re.S))


if __name__ == "__main__":
    unittest.main()
