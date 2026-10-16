# -*- coding: utf-8 -*-
"""/api/vivo: cotización en vivo consultada por el servidor, con caché y sin tocar la cartera."""
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

_TMP = tempfile.mkdtemp(prefix="rumbo_vivo_")
os.environ["PATRIMONIO_DATOS"] = _TMP
os.environ.pop("PATRIMONIO_HOSTS", None)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import servidor  # noqa: E402


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Falso:
    """urlopen simulado: respuestas por fragmento de URL; None = error de red."""
    def __init__(self, tabla):
        self.tabla = tabla
        self.urls = []

    def __call__(self, req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else req
        self.urls.append(url)
        for frag, cuerpo in self.tabla.items():
            if frag in url:
                if cuerpo is None:
                    raise OSError("sin red")
                return _Resp(json.dumps(cuerpo).encode())
        raise OSError("desconocida")


class Vivo(unittest.TestCase):
    def setUp(self):
        servidor.DATOS = _TMP
        servidor._vivo_cache.clear()
        self.c = servidor.app.test_client()
        self.escribe({"vivo": {"productoId": "p", "coin": "bitcoin", "titulos": 1}})

    def escribe(self, datos):
        with open(servidor.ruta_calculado(), "w", encoding="utf-8") as f:
            json.dump(datos, f)

    def pide(self, falso, **h):
        with mock.patch.object(servidor.urllib.request, "urlopen", falso):
            return self.c.get("/api/vivo", headers=h)

    def test_coingecko(self):
        f = Falso({"coingecko": {"bitcoin": {"eur": 50000.5}}})
        r = self.pide(f)
        j = r.get_json()
        self.assertEqual(r.status_code, 200)
        self.assertTrue(j["ok"])
        self.assertEqual((j["precio"], j["fuente"]), (50000.5, "coingecko"))
        self.assertIn("ts", j)
        self.assertEqual(len(f.urls), 1)

    def test_fallback_binance(self):
        f = Falso({"coingecko": None, "binance": {"price": "49000.10"}})
        j = self.pide(f).get_json()
        self.assertTrue(j["ok"])
        self.assertEqual((j["precio"], j["fuente"]), (49000.10, "binance"))

    def test_ambos_fallan_502(self):
        f = Falso({"coingecko": None, "binance": None})
        r = self.pide(f)
        self.assertEqual(r.status_code, 502)
        self.assertFalse(r.get_json()["ok"])

    def test_otra_coin_no_usa_binance(self):
        self.escribe({"vivo": {"coin": "ethereum"}})
        f = Falso({"coingecko": None, "binance": {"price": "1"}})
        self.assertEqual(self.pide(f).status_code, 502)
        self.assertTrue(all("binance" not in u for u in f.urls))

    def test_cache_30s(self):
        f = Falso({"coingecko": {"bitcoin": {"eur": 10}}})
        for _ in range(3):
            self.assertEqual(self.pide(f).status_code, 200)
        self.assertEqual(len(f.urls), 1)
        # caducada: vuelve a consultar
        coin, (t, res) = next(iter(servidor._vivo_cache.items()))
        servidor._vivo_cache[coin] = (t - servidor.VIVO_TTL - 1, res)
        self.pide(f)
        self.assertEqual(len(f.urls), 2)

    def test_fallo_tambien_en_cache(self):
        f = Falso({"coingecko": None, "binance": None})
        self.pide(f)
        n = len(f.urls)
        self.pide(f)
        self.assertEqual(len(f.urls), n)

    def test_sin_vivo_404(self):
        self.escribe({"otra": 1})
        f = Falso({})
        r = self.pide(f)
        self.assertEqual(r.status_code, 404)
        self.assertFalse(r.get_json()["ok"])
        self.assertEqual(f.urls, [])

    def test_cross_site_403(self):
        f = Falso({"coingecko": {"bitcoin": {"eur": 1}}})
        r = self.pide(f, **{"Sec-Fetch-Site": "cross-site"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(f.urls, [])
        r = self.pide(f, **{"Sec-Fetch-Site": "same-origin"})
        self.assertEqual(r.status_code, 200)


if __name__ == "__main__":
    unittest.main()
