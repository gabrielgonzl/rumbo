# -*- coding: utf-8 -*-
"""Actualización de precios: estado, exclusión mutua y control de origen."""
import json
import os
import sys
import tempfile
import unittest

_TMP = tempfile.mkdtemp(prefix="rumbo_act_")
os.environ["PATRIMONIO_DATOS"] = _TMP
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import almacen, servidor  # noqa: E402

H = {"Sec-Fetch-Site": "same-origin", "Origin": "http://localhost"}


class Actualizacion(unittest.TestCase):
    def setUp(self):
        servidor.DATOS = _TMP
        cfg = json.loads(json.dumps(almacen.CARTERA_VACIA))
        cfg["productos"] = [{"id": "a", "nombre": "A", "corto": "A", "tipo": "fondo", "fuente": "manual", "moneda": "EUR", "slot": 1}]
        cfg["valoraciones"] = [{"id": "v1", "fecha": "2026-09-01", "producto": "a", "valor": 100.0}]
        almacen.guarda(os.path.join(_TMP, "cartera.json"), cfg)
        self.c = servidor.app.test_client()

    def test_estado_tras_calcular(self):
        servidor.recalcula(descargar=False)
        j = self.c.get("/api/estado", headers=H).get_json()
        self.assertIsNotNone(j["generado"])
        self.assertFalse(j["actualizando"])

    def test_actualizar_devuelve_generado(self):
        r = self.c.post("/api/actualizar", headers=H)
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        self.assertIsNotNone(r.get_json()["generado"])

    def test_no_se_solapan_dos_actualizaciones(self):
        self.assertTrue(servidor.cerrojo_act.acquire(blocking=False))     # simula una en curso
        try:
            r = self.c.post("/api/actualizar", headers=H)
            self.assertEqual(r.status_code, 409)
            self.assertIn("espera", r.get_json()["error"])
        finally:
            servidor.cerrojo_act.release()
        self.assertEqual(self.c.post("/api/actualizar", headers=H).status_code, 200)

    def test_estado_y_actualizar_respetan_el_control_de_origen(self):
        mal = {"Sec-Fetch-Site": "cross-site"}
        self.assertEqual(self.c.get("/api/estado", headers=mal).status_code, 403)
        self.assertEqual(self.c.post("/api/actualizar", headers=mal).status_code, 403)


if __name__ == "__main__":
    unittest.main()
