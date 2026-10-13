# -*- coding: utf-8 -*-
"""Todo SVG que dibuja graficos.js debe llevar role="img" y aria-label (V3)."""
import os
import re
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTE = os.path.join(RAIZ, "app", "web", "graficos.js")


class GraficosAccesibles(unittest.TestCase):
    def setUp(self):
        self.js = open(FUENTE, encoding="utf-8").read()

    def test_cada_svg_se_etiqueta(self):
        creados = len(re.findall(r'el\("svg"', self.js))
        etiquetados = len(re.findall(r"(?<!function )\betiquetar\(svg,", self.js))
        self.assertGreaterEqual(creados, 9)
        self.assertEqual(creados, etiquetados, "hay un SVG sin etiquetar")

    def test_la_etiqueta_pone_role_y_aria_label(self):
        cuerpo = re.search(r"function etiquetar\(.*?\n  }\n", self.js, re.S).group(0)
        self.assertIn('"role", "img"', cuerpo)
        self.assertIn('"aria-label"', cuerpo)


if __name__ == "__main__":
    unittest.main()
