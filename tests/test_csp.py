# -*- coding: utf-8 -*-
"""Q7: Content-Security-Policy estricta, sin scripts en línea en la app servida."""
import os
import re
import sys
import tempfile
import unittest

_TMP = tempfile.mkdtemp(prefix="rumbo_csp_")
os.environ["PATRIMONIO_DATOS"] = _TMP
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import exportar, servidor  # noqa: E402

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "web")


class Csp(unittest.TestCase):
    def setUp(self):
        servidor.DATOS = _TMP
        self.c = servidor.app.test_client()

    def test_cabecera_en_la_pagina_y_en_la_api(self):
        for ruta in ("/", "/api/estado", "/cargador.js"):
            csp = self.c.get(ruta, headers={"Sec-Fetch-Site": "same-origin"}).headers.get("Content-Security-Policy", "")
            self.assertIn("script-src 'self'", csp, ruta)
            self.assertIn("default-src 'none'", csp, ruta)
            self.assertIn("frame-ancestors 'none'", csp, ruta)

    def test_la_politica_no_permite_codigo_en_linea_ni_terceros(self):
        csp = servidor.CSP
        script = re.search(r"script-src ([^;]*)", csp).group(1)
        self.assertNotIn("unsafe-inline", script)
        self.assertNotIn("unsafe-eval", script)
        self.assertNotRegex(csp, r"https?:")
        self.assertIn("connect-src 'self'", csp)

    def test_index_no_tiene_scripts_en_linea_ni_manejadores(self):
        html = open(os.path.join(WEB, "index.html"), encoding="utf-8").read()
        for m in re.finditer(r"<script\b([^>]*)>(.*?)</script>", html, re.S):
            self.assertIn("src=", m.group(1))
            self.assertEqual(m.group(2).strip(), "")
        self.assertNotRegex(html, r"\son[a-z]+\s*=")
        self.assertNotIn("javascript:", html)

    def test_la_web_exportada_sigue_llevando_los_scripts(self):
        html = exportar.pagina(WEB, {"total": {"patrimonio": 0, "serie": [], "hitos": []}, "productos": []})
        self.assertNotIn("cargador.js", html)
        self.assertIn("window.ESTATICO = true", html)


if __name__ == "__main__":
    unittest.main()
