# -*- coding: utf-8 -*-
"""Migración del formato, asignación objetivo y meta con fecha."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest

_TMP = tempfile.mkdtemp(prefix="rumbo_f3_")
os.environ["PATRIMONIO_DATOS"] = _TMP
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import almacen, servidor  # noqa: E402

H = {"Sec-Fetch-Site": "same-origin", "Origin": "http://localhost"}


class Migracion(unittest.TestCase):
    def test_v1_pasa_a_la_version_actual_sin_perder_nada(self):
        v1 = {"version": 1, "titular": "X", "productos": [{"id": "a", "nombre": "A", "tipo": "fondo"}],
              "movimientos": [{"id": "m1"}], "valoraciones": [], "objetivo": {"activo": True, "importe": 5000}}
        copia = json.loads(json.dumps(v1))
        self.assertTrue(almacen.migra(v1))
        self.assertEqual(v1["version"], almacen.VERSION_ACTUAL)
        self.assertEqual(v1["asignacion"], {"objetivos": {}})
        for k in copia:
            if k != "version":
                self.assertEqual(v1[k], copia[k], k)          # lo que había queda intacto
        self.assertFalse(almacen.migra(v1))                   # idempotente

    def test_carga_migra_en_memoria_y_el_archivo_no_cambia_hasta_guardar(self):
        ruta = os.path.join(_TMP, "v1.json")
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "productos": [], "movimientos": [], "valoraciones": []}, f)
        self.assertEqual(almacen.carga(ruta)["version"], almacen.VERSION_ACTUAL)
        self.assertEqual(json.load(open(ruta, encoding="utf-8"))["version"], 1)


class Asignacion(unittest.TestCase):
    def test_guarda_y_valida(self):
        cfg = {}
        r = almacen.guarda_asignacion(cfg, {"objetivos": {"Renta variable": "70", "Renta fija": "20,5", "Vacío": ""}})
        self.assertEqual(r, {"objetivos": {"Renta variable": 70.0, "Renta fija": 20.5}})
        with self.assertRaises(almacen.ErrorValidacion):
            almacen.guarda_asignacion({}, {"objetivos": {"A": 80, "B": 40}})        # suma 120 %
        with self.assertRaises(almacen.ErrorValidacion):
            almacen.guarda_asignacion({}, {"objetivos": {"A": -5}})
        with self.assertRaises(almacen.ErrorValidacion):
            almacen.guarda_asignacion({}, {})

    def test_el_nombre_del_grupo_no_admite_html(self):
        r = almacen.guarda_asignacion({}, {"objetivos": {"<img src=x onerror=1>": 10}})
        self.assertNotIn("<", list(r["objetivos"])[0])


class Meta(unittest.TestCase):
    def test_meta_con_fecha(self):
        futura = (dt.date.today() + dt.timedelta(days=400)).isoformat()
        cfg = {}
        m = almacen.guarda_meta(cfg, {"importe": "100.000", "fecha": futura, "etiqueta": "Libertad"})
        self.assertEqual((m["importe"], m["fecha"], m["etiqueta"]), (100000.0, futura, "Libertad"))
        self.assertEqual(cfg["objetivo"], m)

    def test_fecha_pasada_y_sin_importe(self):
        with self.assertRaises(almacen.ErrorValidacion):
            almacen.guarda_meta({}, {"importe": 1000, "fecha": "2020-01-01"})
        with self.assertRaises(almacen.ErrorValidacion):
            almacen.guarda_meta({}, {"importe": ""})


class Api(unittest.TestCase):
    def setUp(self):
        servidor.DATOS = _TMP
        cfg = json.loads(json.dumps(almacen.CARTERA_VACIA))
        cfg["productos"] = [{"id": "a", "nombre": "A", "corto": "A", "tipo": "fondo", "fuente": "manual",
                             "moneda": "EUR", "slot": 1, "grupo": "Renta variable"}]
        cfg["valoraciones"] = [{"id": "v1", "fecha": "2026-09-01", "producto": "a", "valor": 1000.0, "aportado": 900.0}]
        almacen.guarda(os.path.join(_TMP, "cartera.json"), cfg)
        self.c = servidor.app.test_client()

    def test_asignacion_y_meta_por_api(self):
        r = self.c.post("/api/asignacion", json={"objetivos": {"Renta variable": 100}}, headers=H)
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        futura = (dt.date.today() + dt.timedelta(days=800)).isoformat()
        r = self.c.post("/api/meta", json={"importe": 50000, "fecha": futura}, headers=H)
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        datos = servidor.recalcula(descargar=False)
        self.assertEqual(datos["asignacion"]["objetivos"], {"Renta variable": 100.0})
        self.assertEqual(datos["objetivo"]["fecha"], futura)
        self.assertEqual(datos["productos"][0]["grupo"], "Renta variable")

    def test_otra_web_no_puede_cambiar_la_asignacion(self):
        r = self.c.post("/api/asignacion", json={"objetivos": {"A": 10}}, headers={"Sec-Fetch-Site": "cross-site"})
        self.assertEqual(r.status_code, 403)


if __name__ == "__main__":
    unittest.main()
