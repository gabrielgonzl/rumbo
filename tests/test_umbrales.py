# -*- coding: utf-8 -*-
"""Q9: umbrales de las alertas guardados en la cartera (migración v3)."""
import json
import os
import sys
import tempfile
import unittest

_TMP = tempfile.mkdtemp(prefix="rumbo_umb_")
os.environ["PATRIMONIO_DATOS"] = _TMP
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import almacen, pignoracion, servidor, umbrales  # noqa: E402

H = {"Sec-Fetch-Site": "same-origin", "Origin": "http://localhost"}


class Migracion(unittest.TestCase):
    def test_v2_pasa_a_v3_con_los_valores_por_defecto_y_sin_tocar_nada(self):
        v2 = {"version": 2, "titular": "X", "productos": [{"id": "a"}], "asignacion": {"objetivos": {"RV": 70}},
              "pignoraciones": []}
        copia = json.loads(json.dumps(v2))
        self.assertTrue(almacen.migra(v2))
        self.assertEqual(v2["version"], almacen.VERSION_ACTUAL)      # la cadena de migraciones llega hasta la última
        self.assertEqual(v2["alertas"], {"umbrales": umbrales.POR_DEFECTO})
        for k in copia:
            if k != "version":
                self.assertEqual(v2[k], copia[k], k)
        self.assertFalse(almacen.migra(v2))

    def test_los_valores_por_defecto_son_los_de_siempre(self):
        self.assertEqual(umbrales.de({}), {"concentracionProducto": 15, "concentracionValor": 5,
                                           "desviacionAsignacion": 5, "ltvAtencion": 75, "ltvAlto": 90})

    def test_basura_guardada_se_ignora(self):
        u = umbrales.de({"alertas": {"umbrales": {"ltvAlto": "mucho", "concentracionProducto": True, "otra": 1,
                                                  "desviacionAsignacion": 8}}})
        self.assertEqual((u["ltvAlto"], u["concentracionProducto"], u["desviacionAsignacion"]), (90, 15, 8))
        self.assertNotIn("otra", u)


class Validacion(unittest.TestCase):
    def test_guarda_y_valida(self):
        cfg = {}
        r = almacen.guarda_alertas(cfg, {"umbrales": {"concentracionProducto": "20", "ltvAtencion": "60,5", "ltvAlto": 80}})
        self.assertEqual(r["umbrales"]["concentracionProducto"], 20)
        self.assertEqual(r["umbrales"]["ltvAtencion"], 60.5)
        self.assertEqual(r["umbrales"]["desviacionAsignacion"], 5)               # lo no enviado se queda
        r = almacen.guarda_alertas(cfg, {"umbrales": {"concentracionProducto": ""}})
        self.assertEqual(r["umbrales"]["concentracionProducto"], 15)             # vacío = por defecto

    def test_nan_e_infinito_se_rechazan(self):
        for malo in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(almacen.ErrorValidacion, msg=str(malo)):
                almacen.guarda_alertas({}, {"umbrales": {"ltvAlto": malo}})

    def test_rechaza_lo_absurdo(self):
        for malo in ({"concentracionProducto": 0}, {"concentracionProducto": 150}, {"desviacionAsignacion": "x"},
                     {"ltvAtencion": 95, "ltvAlto": 90}, {"ltvAlto": 70}):
            with self.assertRaises(almacen.ErrorValidacion, msg=str(malo)):
                almacen.guarda_alertas({}, {"umbrales": malo})
        with self.assertRaises(almacen.ErrorValidacion):
            almacen.guarda_alertas({}, {})


class Niveles(unittest.TestCase):
    def test_por_defecto_igual_que_antes(self):
        self.assertEqual([pignoracion.nivel_riesgo(r, 0.7) for r in (0.50, 0.53, 0.64, 0.69, 0.71)],
                         ["bajo", "medio", "alto", "alto", "peligro"])

    def test_niveles_configurados(self):
        cfg = {"alertas": {"umbrales": {"ltvAtencion": 50, "ltvAlto": 60}}}
        a, b = pignoracion.niveles_de(cfg)
        self.assertEqual((a, b), (0.5, 0.6))
        self.assertEqual(pignoracion.nivel_riesgo(0.38, 0.7, a, b), "medio")      # 38/70 = 54 % del límite
        self.assertEqual(pignoracion.nivel_riesgo(0.45, 0.7, a, b), "alto")       # 64 %
        self.assertEqual(pignoracion.nivel_riesgo(0.30, 0.7, a, b), "bajo")

    def test_umbrales_incoherentes_vuelven_al_defecto(self):
        cfg = {"alertas": {"umbrales": {"ltvAtencion": 90, "ltvAlto": 80}}}
        self.assertEqual(pignoracion.niveles_de(cfg), (0.75, 0.9))


class Api(unittest.TestCase):
    def setUp(self):
        servidor.DATOS = _TMP
        for n in os.listdir(_TMP):
            p = os.path.join(_TMP, n)
            if os.path.isfile(p):
                os.remove(p)
        cfg = json.loads(json.dumps(almacen.CARTERA_VACIA))
        cfg["productos"] = [{"id": "fondo_a", "nombre": "Fondo A", "corto": "Fondo A", "tipo": "fondo",
                             "fuente": "manual", "moneda": "EUR", "slot": 1}]
        cfg["valoraciones"] = [{"id": "v1", "fecha": "2026-09-01", "producto": "fondo_a", "valor": 3000.0,
                                "aportado": 2500.0}]
        almacen.guarda(os.path.join(_TMP, "cartera.json"), cfg)
        self.c = servidor.app.test_client()

    def test_guardar_y_publicar_en_datos(self):
        r = self.c.post("/api/alertas", json={"umbrales": {"concentracionProducto": 25}}, headers=H)
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        t = self.c.get("/datos.js", headers={"Sec-Fetch-Site": "same-origin"}).get_data(as_text=True)
        self.assertIn('"alertas":{"umbrales":{"concentracionProducto":25', t)

    def test_cross_site_no_puede_cambiar_los_umbrales(self):
        r = self.c.post("/api/alertas", json={"umbrales": {"concentracionProducto": 25}},
                        headers={"Sec-Fetch-Site": "cross-site", "Origin": "http://malo.example"})
        self.assertEqual(r.status_code, 403)


class Interfaz(unittest.TestCase):
    def test_editor_tiene_la_vista_y_la_accion(self):
        web = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "web")
        with open(os.path.join(web, "editor.js"), encoding="utf-8") as f:
            ed = f.read()
        with open(os.path.join(web, "app.js"), encoding="utf-8") as f:
            app = f.read()
        self.assertIn('value="${esc(String(u[k])', ed)          # el valor guardado se escapa
        self.assertIn('["alertas", "Alertas"]', ed)
        self.assertIn("guardarAlertas", ed)
        for k in umbrales.POR_DEFECTO:
            self.assertIn(k, ed, k)
        self.assertIn("umbralesAl().concentracionProducto", app)
        self.assertIn("umbralesAl().concentracionValor", app)


class CopiasAjenas(unittest.TestCase):
    """Reservas de la revisión: una copia de seguridad ajena no puede colar HTML ni un `slot` que rompa una plantilla."""

    def test_sanea_copia_quita_marcas_y_fuerza_el_slot(self):
        cfg = {"productos": [{"id": "a", "nombre": "<img src=x onerror=alert(1)>Fondo", "corto": "A>B",
                              "slot": '1" data-st="position:fixed'}, {"id": "b", "slot": 99}, {"id": "c", "slot": "7"}],
               "movimientos": [{"id": "m1", "nota": "<b>hola</b>"}], "valoraciones": [], "otro": {"x": ["<i>"]}}
        limpia = almacen.sanea_copia(cfg)
        self.assertNotRegex(json.dumps(limpia, ensure_ascii=False), r"[<>]")
        self.assertEqual([p["slot"] for p in limpia["productos"]], [1, 1, 7])
        self.assertEqual(limpia["movimientos"][0]["nota"], "bhola/b")           # el texto queda, sin etiquetas
        self.assertEqual(cfg["productos"][0]["slot"], '1" data-st="position:fixed')   # no muta la entrada

    def test_valida_copia_sanea(self):
        cfg = servidor.valida_copia({"productos": [{"id": "a", "nombre": "<script>", "slot": "x"}],
                                     "movimientos": [], "valoraciones": []})
        self.assertEqual(cfg["productos"][0]["nombre"], "script")
        self.assertEqual(cfg["productos"][0]["slot"], 1)


class Identificadores(unittest.TestCase):
    def test_siguiente_id_con_prefijo_de_dos_letras(self):
        """Antes: int(id[1:]) rompía con «pg1» y la segunda pignoración daba error 500."""
        self.assertEqual(almacen.siguiente_id([], "pg"), "pg1")
        self.assertEqual(almacen.siguiente_id([{"id": "pg1"}], "pg"), "pg2")
        self.assertEqual(almacen.siguiente_id([{"id": "pg3"}, {"id": "pg10"}, {"id": "x"}], "pg"), "pg11")
        self.assertEqual(almacen.siguiente_id([{"id": "m7"}], "m"), "m8")

    def test_dos_pignoraciones_seguidas_por_la_api(self):
        c = servidor.app.test_client()
        servidor.DATOS = _TMP
        for n in os.listdir(_TMP):
            p = os.path.join(_TMP, n)
            if os.path.isfile(p):
                os.remove(p)
        cfg = json.loads(json.dumps(almacen.CARTERA_VACIA))
        cfg["productos"] = [{"id": "fondo_a", "nombre": "Fondo A", "corto": "Fondo A", "tipo": "fondo",
                             "fuente": "manual", "moneda": "EUR", "slot": 1}]
        cfg["valoraciones"] = [{"id": "v1", "fecha": "2026-09-01", "producto": "fondo_a", "valor": 3000.0,
                                "aportado": 2500.0}]
        almacen.guarda(os.path.join(_TMP, "cartera.json"), cfg)
        alta = {"nombre": "Préstamo", "entidad": "X", "activos": ["fondo_a"], "principal": "1.000,00",
                "fecha": "2026-09-23", "interes": "5", "cuotas": 12, "primerPago": "2026-10-23"}
        r1 = c.post("/api/pignoraciones", json=alta, headers=H)
        r2 = c.post("/api/pignoraciones", json=dict(alta, nombre="Otro", activos=[]), headers=H)
        self.assertEqual(r1.status_code, 200, r1.get_data(as_text=True))
        self.assertNotEqual(r2.status_code, 500, r2.get_data(as_text=True))     # 200 o un error de validación, nunca 500


if __name__ == "__main__":
    unittest.main()
