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

    def test_s3_la_x_sola_no_ocupa_una_linea(self):
        css = open(os.path.join(WEB, "tema-carta.css"), encoding="utf-8").read()
        self.assertIn(".alerta .acciones:has(> .btn:only-child)", css)

    def test_s4_medidor_con_marcas_de_zona_sin_degradado(self):
        css = open(os.path.join(WEB, "tema-carta.css"), encoding="utf-8").read()
        self.assertIn(".medidor .zonaLtv", css)
        js = open(os.path.join(WEB, "app.js"), encoding="utf-8").read()
        self.assertIn("Alertas.zonasLtv", js)

    def test_s5_el_aviso_legal_solo_dice_lo_de_la_exactitud_una_vez(self):
        html = open(os.path.join(WEB, "index.html"), encoding="utf-8").read()
        js = open(os.path.join(WEB, "app.js"), encoding="utf-8").read()
        self.assertEqual((html + js).count("no se garantiza"), 0)
        self.assertEqual(html.count("No se garantiza la exactitud"), 1)

    def test_q4_glosario_un_termino_por_concepto(self):
        """«Posición» solo queda como nombre de pestaña, en «mayores posiciones» de un fondo y en «Mi posición»."""
        js = open(os.path.join(WEB, "app.js"), encoding="utf-8").read()
        html = open(os.path.join(WEB, "index.html"), encoding="utf-8").read()
        permitido = ("mayores posiciones", "Mi posición")
        sin_comentarios = lambda t: re.sub(r"(?m)^\s*//.*$|/\*.*?\*/|<!--.*?-->", "", t, flags=re.S)
        for texto in (sin_comentarios(js), sin_comentarios(html)):
            for m in re.finditer(r"[Pp]osici[oó]n(es)?", texto):
                ctx = texto[max(0, m.start() - 12):m.end() + 3]
                self.assertTrue(any(p in ctx for p in permitido) or 'id="posiciones"' in ctx or "Posiciones" in ctx
                                or "posicion" in ctx, ctx)
        self.assertTrue(os.path.exists(os.path.join(RAIZ, "docs", "GLOSARIO.md")))

    def test_v4_el_grafico_sube_y_los_kpis_secundarios_bajan(self):
        html = open(os.path.join(WEB, "index.html"), encoding="utf-8").read()
        i = lambda t: html.index(t)
        self.assertLess(i('id="cockpit"'), i('id="grafPrincipal"'))
        self.assertLess(i('id="grafPrincipal"'), i('id="filtros"'))      # filtros como leyenda, bajo el gráfico
        self.assertLess(i('id="filtros"'), i('id="kpis"'))

    def test_v4_estados_vacios_con_rosa_de_los_vientos(self):
        js = open(os.path.join(WEB, "app.js"), encoding="utf-8").read()
        self.assertIn("const ICO_ROSA", js)
        self.assertIn('aria-hidden="true"', js[js.index("const ICO_ROSA"):js.index("const ICO_ROSA") + 300])
        self.assertGreaterEqual(js.count("${ICO_ROSA}"), 4)


if __name__ == "__main__":
    unittest.main()
