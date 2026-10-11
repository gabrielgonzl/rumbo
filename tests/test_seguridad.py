# -*- coding: utf-8 -*-
"""Pruebas del control de origen: ninguna web ajena puede leer ni cambiar tu cartera."""
import os
import sys
import tempfile
import unittest

_TMP = tempfile.mkdtemp(prefix="rumbo_test_")
os.environ["PATRIMONIO_DATOS"] = _TMP
os.environ.pop("PATRIMONIO_HOSTS", None)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import servidor  # noqa: E402


class ControlDeOrigen(unittest.TestCase):
    def setUp(self):
        self.c = servidor.app.test_client()

    # --- lectura (cross-site script inclusion)
    def test_datos_js_mismo_origen(self):
        r = self.c.get("/datos.js", headers={"Sec-Fetch-Site": "same-origin"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_data(as_text=True).startswith("window.DATOS = "))

    def test_datos_js_otra_web_rechazado(self):
        for site in ("cross-site", "same-site"):
            r = self.c.get("/datos.js", headers={"Sec-Fetch-Site": site})
            self.assertEqual(r.status_code, 403, site)
            self.assertNotIn("window.DATOS", r.get_data(as_text=True))

    def test_datos_js_sin_cabeceras_de_navegador(self):
        # curl, el healthcheck y ya_abierta() no mandan Sec-Fetch-*
        self.assertEqual(self.c.get("/datos.js").status_code, 200)

    def test_datos_js_referer_ajeno_rechazado(self):
        r = self.c.get("/datos.js", headers={"Referer": "https://malvada.example/x"})
        self.assertEqual(r.status_code, 403)

    # --- escritura (CSRF)
    def test_post_otra_web_rechazado(self):
        r = self.c.post("/api/actualizar", headers={"Sec-Fetch-Site": "cross-site"})
        self.assertEqual(r.status_code, 403)
        r = self.c.post("/api/copia/subir", headers={"Origin": "https://malvada.example"})
        self.assertEqual(r.status_code, 403)
        r = self.c.delete("/api/productos/x", headers={"Sec-Fetch-Site": "same-site"})
        self.assertEqual(r.status_code, 403)

    def test_post_mismo_origen_llega_a_la_ruta(self):
        r = self.c.post("/api/copia/subir", headers={"Sec-Fetch-Site": "same-origin",
                                                     "Origin": "http://localhost"})
        self.assertEqual(r.status_code, 400)   # «elige el archivo»: pasó el control

    # --- DNS rebinding
    def test_host_desconocido_rechazado(self):
        r = self.c.get("/datos.js", headers={"Host": "rebind.malvada.example:8765"})
        self.assertEqual(r.status_code, 403)

    def test_hosts_locales_aceptados(self):
        for h in ("127.0.0.1:8765", "localhost:8765", "[::1]:8765"):
            self.assertEqual(self.c.get("/api/ping", headers={"Host": h}).status_code, 200, h)

    # --- casos límite
    def test_origin_null_rechazado(self):
        self.assertEqual(self.c.post("/api/actualizar", headers={"Origin": "null"}).status_code, 403)
        self.assertEqual(self.c.get("/datos.js", headers={"Origin": "null"}).status_code, 403)

    def test_post_sin_origen_rechazado(self):
        self.assertEqual(self.c.post("/api/actualizar").status_code, 403)

    def test_post_con_sec_fetch_none_rechazado(self):
        r = self.c.post("/api/actualizar", headers={"Sec-Fetch-Site": "none"})
        self.assertEqual(r.status_code, 403)

    def test_multipart_otra_web_rechazado(self):
        r = self.c.post("/api/copia/subir", data={"archivo": (__import__("io").BytesIO(b"{}"), "c.json")},
                        content_type="multipart/form-data", headers={"Sec-Fetch-Site": "cross-site"})
        self.assertEqual(r.status_code, 403)

    def test_head_options_y_estaticos_otra_web_rechazados(self):
        h = {"Sec-Fetch-Site": "cross-site"}
        self.assertEqual(self.c.head("/datos.js", headers=h).status_code, 403)
        self.assertEqual(self.c.options("/api/cartera", headers=h).status_code, 403)
        self.assertEqual(self.c.get("/app.js", headers=h).status_code, 403)

    def test_hosts_raros_rechazados(self):
        for host in ("0.0.0.0:8765", "127.0.0.1.:8765", "127.0.0.1.evil.example"):
            self.assertEqual(self.c.get("/datos.js", headers={"Host": host}).status_code, 403, host)

    # --- defensa en profundidad
    def test_cabeceras_de_proteccion(self):
        r = self.c.get("/datos.js")
        self.assertEqual(r.headers.get("Cross-Origin-Resource-Policy"), "same-origin")
        self.assertEqual(r.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(r.headers.get("X-Frame-Options"), "DENY")


if __name__ == "__main__":
    unittest.main()
