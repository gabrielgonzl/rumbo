# -*- coding: utf-8 -*-
"""Contrato servidor <-> navegador: metricas.js (Node) debe dar las mismas cifras que motor.construir."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

_TMP = tempfile.mkdtemp(prefix="rumbo_contrato_")
os.environ["PATRIMONIO_DATOS"] = _TMP
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import almacen, servidor  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cartera(con_prestamo):
    cfg = json.loads(json.dumps(almacen.CARTERA_VACIA))
    cfg["productos"] = [
        {"id": "a", "nombre": "Fondo A", "corto": "Fondo A", "tipo": "fondo", "fuente": "manual", "moneda": "EUR", "slot": 1},
        {"id": "b", "nombre": "Fondo B", "corto": "Fondo B", "tipo": "fondo", "fuente": "manual", "moneda": "EUR", "slot": 2}]
    val = []
    for i, (f, a, b) in enumerate([("2025-01-31", 1000, 500), ("2025-06-30", 1700, 800), ("2025-12-31", 2300, 1250),
                                   ("2026-06-30", 3100, 1700), ("2026-09-30", 3400, 1900)]):
        val += [{"id": f"va{i}", "fecha": f, "producto": "a", "valor": float(a), "aportado": float(a) * 0.8},
                {"id": f"vb{i}", "fecha": f, "producto": "b", "valor": float(b), "aportado": float(b) * 0.85}]
    cfg["valoraciones"] = val
    cfg["movimientos"] = [
        {"id": f"m{i}", "fecha": f, "producto": p, "tipo": "compra", "unidades": 0, "importe": imp}
        for i, (f, p, imp) in enumerate([("2025-01-15", "a", 800.0), ("2025-02-15", "b", 400.0),
                                         ("2025-09-10", "a", 500.0), ("2026-03-05", "b", 300.0),
                                         ("2026-08-20", "a", 450.0)])]
    if con_prestamo:
        cfg["pignoraciones"] = [{
            "id": "pg1", "nombre": "Préstamo de prueba", "estado": "activa", "activos": ["a", "b"],
            "principal": 2000.0, "fecha": "2026-08-01", "interes": 5.0, "cuotas": 60,
            "primerPago": "2026-09-01", "efectivoHasta": "2026-08-20"}]
    return cfg


@unittest.skipUnless(shutil.which("node"), "Node no está instalado")
class Contrato(unittest.TestCase):
    def comprueba(self, con_prestamo):
        servidor.DATOS = _TMP
        almacen.guarda(os.path.join(_TMP, "cartera.json"), cartera(con_prestamo))
        for n in ("calculado_propio.json", "estado.json"):
            p = os.path.join(_TMP, n)
            if os.path.exists(p):
                os.remove(p)
        datos = servidor.recalcula(descargar=False)
        ruta = os.path.join(_TMP, f"datos_{con_prestamo}.json")
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False)
        r = subprocess.run(["node", os.path.join(RAIZ, "tests", "contrato_metricas.js"), ruta],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return datos

    def test_sin_prestamo(self):
        self.comprueba(False)

    def test_con_prestamo_y_efectivo_derivado(self):
        d = self.comprueba(True)
        self.assertEqual(len(d["pasivos"]), 1)
        self.assertIsNotNone(d["total"].get("tirCapitalPropio") if d["total"].get("tir") else True)

    def test_el_servidor_calcula_la_caida_sobre_la_rentabilidad(self):
        d = self.comprueba(True)
        self.assertIn("caidaMaximaTwr", d["total"])
        self.assertLessEqual(d["total"]["caidaMaximaTwr"], 0)


if __name__ == "__main__":
    unittest.main()
