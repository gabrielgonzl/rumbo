# -*- coding: utf-8 -*-
"""Carteras de fondos: modelo v4, validación, API, garantía efectiva y LTV efectivo."""
import contextlib
import datetime as dt
import io
import json
import os
import sys
import tempfile
import unittest

_TMP = tempfile.mkdtemp(prefix="rumbo_carteras_")
os.environ["PATRIMONIO_DATOS"] = _TMP
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import almacen, carteras as calc_carteras, exportar, motor, pignoracion, servidor  # noqa: E402

H = {"Sec-Fetch-Site": "same-origin", "Origin": "http://localhost"}


def cfg_base():
    """Tres fondos y ninguna cartera (esquema v4)."""
    cfg = json.loads(json.dumps(almacen.CARTERA_VACIA))
    cfg["productos"] = [
        {"id": f, "nombre": f"Fondo {f[-1].upper()}", "corto": f"Fondo {f[-1].upper()}", "tipo": "fondo",
         "fuente": "manual", "moneda": "EUR", "slot": i + 1}
        for i, f in enumerate(("fondo_a", "fondo_b", "fondo_c"))]
    cfg["valoraciones"] = [{"id": f"v{i}", "fecha": "2026-09-01", "producto": f, "valor": 1000.0 * (i + 1), "aportado": 900.0}
                           for i, f in enumerate(("fondo_a", "fondo_b", "fondo_c"))]
    return cfg


class Modelo(unittest.TestCase):
    def test_version_y_cartera_vacia(self):
        self.assertEqual(almacen.VERSION_ACTUAL, 4)
        self.assertEqual(almacen.CARTERA_VACIA["carteras"], [])

    def test_migra_v3_a_v4_es_aditiva_e_idempotente(self):
        v3 = {"version": 3, "titular": "X", "productos": [{"id": "a"}], "asignacion": {"objetivos": {"RV": 70}},
              "alertas": {"umbrales": {}}, "pignoraciones": []}
        copia = json.loads(json.dumps(v3))
        self.assertTrue(almacen.migra(v3))
        self.assertEqual(v3["version"], 4)
        self.assertEqual(v3["carteras"], [])
        for k in copia:
            if k != "version":
                self.assertEqual(v3[k], copia[k], k)
        self.assertFalse(almacen.migra(v3))

    def test_cartera_cargada_sin_el_campo_no_rompe(self):
        """Review Focus: una copia v3 sin `carteras` se carga y funciona."""
        ruta = os.path.join(_TMP, "v3.json")
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump({"version": 3, "productos": [], "movimientos": [], "valoraciones": []}, f)
        cfg = almacen.carga(ruta)
        self.assertEqual(cfg["carteras"], [])
        self.assertEqual(cfg["version"], almacen.VERSION_ACTUAL)


class Validacion(unittest.TestCase):
    def setUp(self):
        self.cfg = cfg_base()

    def test_crea_con_id_y_asigna_fondos(self):
        c = almacen.guarda_cartera(self.cfg, {"nombre": "Cartera Ejemplo", "entidad": "Entidad Ejemplo", "ltvMax": "50",
                                              "productos": ["fondo_a", "fondo_b"]})
        self.assertEqual(c, {"id": "c1", "nombre": "Cartera Ejemplo", "entidad": "Entidad Ejemplo", "ltvMax": 50.0})
        self.assertEqual([p.get("carteraId") for p in self.cfg["productos"]], ["c1", "c1", None])
        self.assertEqual(almacen.cartera(self.cfg, "c1")["nombre"], "Cartera Ejemplo")
        self.assertIsNone(almacen.cartera(self.cfg, "zz"))

    def test_nombre_obligatorio_unico_y_corto(self):
        for malo in ("", "   ", "x" * 81):
            with self.assertRaises(almacen.ErrorValidacion, msg=repr(malo)):
                almacen.guarda_cartera(self.cfg, {"nombre": malo})
        almacen.guarda_cartera(self.cfg, {"nombre": "Cartera Ejemplo"})
        with self.assertRaises(almacen.ErrorValidacion):
            almacen.guarda_cartera(self.cfg, {"nombre": "cartera EJEMPLO"})
        c = almacen.cartera(self.cfg, "c1")                       # editar la misma con su nombre no es un duplicado
        almacen.guarda_cartera(self.cfg, {"id": "c1", "nombre": "Cartera Ejemplo", "entidad": "Otra"})
        self.assertEqual(almacen.cartera(self.cfg, "c1")["entidad"], "Otra")

    def test_ltv_rango(self):
        for malo in (0, "0", 101, "x", float("nan"), float("inf"), -5):
            with self.assertRaises(almacen.ErrorValidacion, msg=repr(malo)):
                almacen.guarda_cartera(self.cfg, {"nombre": "A", "ltvMax": malo})
        self.assertEqual(almacen.guarda_cartera(self.cfg, {"nombre": "B", "ltvMax": "62,5"})["ltvMax"], 62.5)
        self.assertNotIn("ltvMax", almacen.guarda_cartera(self.cfg, {"nombre": "C"}))

    def test_nombre_hostil_sin_marcas(self):
        c = almacen.guarda_cartera(self.cfg, {"nombre": "<img src=x onerror=alert(1)>Mal", "entidad": "<b>X</b>"})
        self.assertNotRegex(json.dumps(c), r"[<>]")

    def test_asignar_mueve_el_fondo_de_cartera(self):
        almacen.guarda_cartera(self.cfg, {"nombre": "A", "productos": ["fondo_a"]})
        almacen.guarda_cartera(self.cfg, {"nombre": "B", "productos": ["fondo_a", "fondo_c"]})
        self.assertEqual([p.get("carteraId") for p in self.cfg["productos"]], ["c2", None, "c2"])

    def test_editar_quita_los_fondos_desmarcados(self):
        almacen.guarda_cartera(self.cfg, {"nombre": "A", "productos": ["fondo_a", "fondo_b"]})
        almacen.guarda_cartera(self.cfg, {"id": "c1", "nombre": "A", "productos": ["fondo_b"]})
        self.assertEqual([p.get("carteraId") for p in self.cfg["productos"]], [None, "c1", None])

    def test_productos_desconocidos_se_rechazan(self):
        with self.assertRaises(almacen.ErrorValidacion):
            almacen.guarda_cartera(self.cfg, {"nombre": "A", "productos": ["no_existe"]})

    def test_carteraid_inexistente_se_ignora_al_guardar_producto(self):
        datos = {"id": "fondo_a", "nombre": "Fondo A", "tipo": "fondo", "fuente": "manual", "carteraId": "c9"}
        prod, _ = almacen.guarda_producto(self.cfg, datos)
        self.assertNotIn("carteraId", prod)
        almacen.guarda_cartera(self.cfg, {"nombre": "A"})
        prod, _ = almacen.guarda_producto(self.cfg, dict(datos, carteraId="c1"))
        self.assertEqual(prod["carteraId"], "c1")
        prod, _ = almacen.guarda_producto(self.cfg, dict(datos, carteraId=""))
        self.assertNotIn("carteraId", prod)


class Borrado(unittest.TestCase):
    def setUp(self):
        self.cfg = cfg_base()
        almacen.guarda_cartera(self.cfg, {"nombre": "Cartera Ejemplo", "productos": ["fondo_a", "fondo_b"]})

    def test_borrar_cartera_suelta_los_fondos_y_la_quita_de_los_prestamos(self):
        self.cfg["pignoraciones"] = [{"id": "pg1", "nombre": "Préstamo", "activos": ["fondo_c"], "carteraIds": ["c1"]}]
        almacen.borra_cartera(self.cfg, "c1")
        self.assertEqual(self.cfg["carteras"], [])
        self.assertTrue(all("carteraId" not in p for p in self.cfg["productos"]))
        self.assertNotIn("carteraIds", self.cfg["pignoraciones"][0])

    def test_borrar_cartera_rechazado_si_deja_un_prestamo_sin_garantia(self):
        self.cfg["pignoraciones"] = [{"id": "pg1", "nombre": "Mi préstamo", "activos": [], "carteraIds": ["c1"]}]
        with self.assertRaises(almacen.ErrorValidacion) as e:
            almacen.borra_cartera(self.cfg, "c1")
        self.assertIn("Mi préstamo", e.exception.errores[0])
        self.assertEqual(len(self.cfg["carteras"]), 1)                       # no se borró nada

    def test_borrar_cartera_inexistente(self):
        with self.assertRaises(almacen.ErrorValidacion):
            almacen.borra_cartera(self.cfg, "c9")

    def test_borrar_producto_lo_saca_de_su_cartera(self):
        """Review Focus 1: la cartera no lo cuenta y no lanza."""
        almacen.borra_producto(self.cfg, "fondo_a")
        fondos = [p["id"] for p in self.cfg["productos"] if p.get("carteraId") == "c1"]
        self.assertEqual(fondos, ["fondo_b"])


def prestamo(cfg, **kw):
    """Alta de un préstamo de 1.000 € por la validación real."""
    datos = {"nombre": "Préstamo", "entidad": "X", "activos": [], "principal": "1.000,00", "fecha": "2026-09-23",
             "interes": "5", "cuotas": 12, "primerPago": "2026-10-23"}
    datos.update(kw)
    return almacen.guarda_pignoracion(cfg, datos)


class Pignoracion(unittest.TestCase):
    HOY = dt.date(2026, 10, 1)

    def setUp(self):
        self.cfg = cfg_base()
        almacen.guarda_cartera(self.cfg, {"nombre": "Cartera Ejemplo", "ltvMax": 50, "productos": ["fondo_a", "fondo_b"]})

    def test_activos_efectivos_une_sueltos_y_carteras_sin_duplicados(self):
        p = prestamo(self.cfg, activos=["fondo_b", "fondo_c"], carteraIds=["c1"])
        self.assertEqual(pignoracion.activos_efectivos(self.cfg, p), ["fondo_b", "fondo_c", "fondo_a"])

    def test_prestamo_sin_carteras_conserva_sus_activos(self):
        p = prestamo(self.cfg, activos=["fondo_c", "fondo_a"])
        self.assertEqual(pignoracion.activos_efectivos(self.cfg, p), ["fondo_c", "fondo_a"])

    def test_fondo_anadido_despues_a_la_cartera_pasa_a_ser_garantia(self):
        p = prestamo(self.cfg, carteraIds=["c1"])
        self.assertEqual(pignoracion.activos_efectivos(self.cfg, p), ["fondo_a", "fondo_b"])
        almacen.guarda_cartera(self.cfg, {"id": "c1", "nombre": "Cartera Ejemplo", "productos": ["fondo_a", "fondo_b", "fondo_c"]})
        self.assertEqual(pignoracion.activos_efectivos(self.cfg, p), ["fondo_a", "fondo_b", "fondo_c"])

    def test_ltv_propio_manda(self):
        p = prestamo(self.cfg, carteraIds=["c1"], ltvMax="40")
        self.assertEqual(pignoracion.ltv_efectivo(self.cfg, p), 40.0)

    def test_ltv_de_cartera_unica_o_carteras_iguales(self):
        p = prestamo(self.cfg, carteraIds=["c1"])
        self.assertEqual(pignoracion.ltv_efectivo(self.cfg, p), 50.0)
        almacen.guarda_cartera(self.cfg, {"nombre": "Otra", "ltvMax": 50, "productos": ["fondo_c"]})
        p2 = prestamo(self.cfg, nombre="Dos", carteraIds=["c1", "c2"])
        self.assertEqual(pignoracion.ltv_efectivo(self.cfg, p2), 50.0)

    def test_ltv_distinto_entre_carteras_queda_sin_indicar(self):
        """Review Focus 3: ni media ni el menor: sin indicar."""
        almacen.guarda_cartera(self.cfg, {"nombre": "Otra", "ltvMax": 60, "productos": ["fondo_c"]})
        p = prestamo(self.cfg, carteraIds=["c1", "c2"])
        self.assertIsNone(pignoracion.ltv_efectivo(self.cfg, p))

    def test_garantia_mixta_o_cartera_sin_ltv_queda_sin_indicar(self):
        mixta = prestamo(self.cfg, activos=["fondo_c"], carteraIds=["c1"])
        self.assertIsNone(pignoracion.ltv_efectivo(self.cfg, mixta))
        almacen.guarda_cartera(self.cfg, {"nombre": "Sin LTV", "productos": ["fondo_c"]})
        sin = prestamo(self.cfg, nombre="S", carteraIds=["c2"])
        self.assertIsNone(pignoracion.ltv_efectivo(self.cfg, sin))
        suelto = prestamo(self.cfg, nombre="T", activos=["fondo_a"])
        self.assertIsNone(pignoracion.ltv_efectivo(self.cfg, suelto))

    def test_cartera_sin_fondos_como_garantia_se_rechaza(self):
        """Review Focus 2."""
        almacen.guarda_cartera(self.cfg, {"nombre": "Vacía"})
        with self.assertRaises(almacen.ErrorValidacion) as e:
            prestamo(self.cfg, carteraIds=["c2"])
        self.assertIn("sin fondos", " ".join(e.exception.errores))

    def test_cartera_inexistente_o_nada_se_rechaza(self):
        with self.assertRaises(almacen.ErrorValidacion) as e:             # con un fondo válido: falla solo por la cartera
            prestamo(self.cfg, activos=["fondo_c"], carteraIds=["c9"])
        self.assertIn("c9", " ".join(e.exception.errores))
        with self.assertRaises(almacen.ErrorValidacion):
            prestamo(self.cfg, activos=[], carteraIds=[])

    def test_carteraids_solo_se_guarda_si_no_esta_vacio(self):
        self.assertNotIn("carteraIds", prestamo(self.cfg, activos=["fondo_c"], carteraIds=[]))
        self.assertEqual(prestamo(self.cfg, nombre="C", carteraIds=["c1"])["carteraIds"], ["c1"])

    def test_bloquea_venta_y_marcas_incluyen_fondos_de_carteras(self):
        prestamo(self.cfg, carteraIds=["c1"])
        self.assertEqual(pignoracion.bloquea_venta(self.cfg, "fondo_a", "2026-10-01"), "Préstamo")
        self.assertIsNone(pignoracion.bloquea_venta(self.cfg, "fondo_c", "2026-10-01"))
        m = pignoracion.marcas(self.cfg, self.HOY)
        self.assertEqual(sorted(m), ["fondo_a", "fondo_b"])

    def test_resumen_garantia_margen_y_detalle_con_cartera(self):
        prestamo(self.cfg, carteraIds=["c1"])
        valores = {"fondo_a": 3000.0, "fondo_b": 2000.0, "fondo_c": 9999.0}
        e = pignoracion.resumen(self.cfg, valores, self.HOY)[0]
        self.assertEqual(e["activos"], ["fondo_a", "fondo_b"])
        self.assertEqual(e["garantia"], 5000.0)
        self.assertEqual(e["ltvMax"], 50.0)                       # el de la cartera
        self.assertEqual(e["ltvSugerido"], 50.0)
        self.assertEqual(e["carteraIds"], ["c1"])
        self.assertEqual(e["carterasDetalle"], [{"id": "c1", "nombre": "Cartera Ejemplo"}])
        self.assertAlmostEqual(e["ratio"], (e["saldo"] + e["devengado"]) / 5000.0, places=4)
        self.assertFalse(e["superaLimite"])

    def test_resumen_separa_los_fondos_sueltos_de_los_de_cartera(self):
        prestamo(self.cfg, carteraIds=["c1"])
        prestamo(self.cfg, nombre="Mixto", activos=["fondo_c"], carteraIds=["c1"])
        valores = {"fondo_a": 3000.0, "fondo_b": 2000.0, "fondo_c": 1000.0}
        solo, mixto = pignoracion.resumen(self.cfg, valores, self.HOY)
        self.assertEqual(solo["activosSueltos"], [])
        self.assertEqual(mixto["activosSueltos"], ["fondo_c"])
        self.assertEqual(mixto["activos"], ["fondo_c", "fondo_a", "fondo_b"])

    def test_prestamo_sin_carteras_da_las_mismas_cifras_que_antes(self):
        prestamo(self.cfg, activos=["fondo_a", "fondo_b"], ltvMax="50")
        e = pignoracion.resumen(self.cfg, {"fondo_a": 3000.0, "fondo_b": 2000.0}, self.HOY)[0]
        self.assertEqual((e["garantia"], e["ltvMax"], e["carterasDetalle"], e["ltvSugerido"]), (5000.0, 50.0, [], None))
        self.assertEqual(e["activosDetalle"][0]["id"], "fondo_a")


class Publicacion(unittest.TestCase):
    def setUp(self):
        servidor.DATOS = _TMP
        for n in os.listdir(_TMP):
            q = os.path.join(_TMP, n)
            if os.path.isfile(q):
                os.remove(q)
        cfg = cfg_base()
        almacen.guarda_cartera(cfg, {"nombre": "Cartera Ejemplo", "entidad": "Entidad Ejemplo", "ltvMax": 50,
                                     "productos": ["fondo_a", "fondo_b"]})
        almacen.guarda(os.path.join(_TMP, "cartera.json"), cfg)
        self.c = servidor.app.test_client()

    def datos(self):
        t = self.c.get("/datos.js", headers={"Sec-Fetch-Site": "same-origin"}).get_data(as_text=True)
        return json.loads(t[t.index("{"):t.rindex("}") + 1])

    def test_datos_js_lleva_carteras_y_carteraid(self):
        d = self.datos()
        c = d["carteras"][0]
        self.assertEqual({k: c[k] for k in ("id", "nombre", "entidad", "ltvMax")},
                         {"id": "c1", "nombre": "Cartera Ejemplo", "entidad": "Entidad Ejemplo", "ltvMax": 50.0})
        self.assertEqual(c["fondos"], 2)
        por_id = {p["id"]: p.get("carteraId") for p in d["productos"]}
        self.assertEqual(por_id, {"fondo_a": "c1", "fondo_b": "c1", "fondo_c": None})

    def test_sin_carteras_publica_lista_vacia(self):
        almacen.guarda(os.path.join(_TMP, "cartera.json"), cfg_base())
        self.assertEqual(self.datos()["carteras"], [])

    def test_web_exportada_con_y_sin_importes_lleva_carteras_sin_importes(self):
        self.datos()                                   # calcula y guarda el panel, como al abrir la app
        for ocultar in ("", "?ocultar=1"):
            r = self.c.get("/api/exportar-web" + ocultar, headers={"Sec-Fetch-Site": "same-origin"})
            self.assertEqual(r.status_code, 200, ocultar)
            html = r.get_data(as_text=True)
            self.assertIn("Cartera Ejemplo", html, ocultar)
            self.assertIn('"carteraId":"c1"', html, ocultar)
        d = self.datos()
        self.assertEqual(set(d["carteras"][0]), {"id", "nombre", "entidad", "ltvMax", "fondos", "valor", "aportado",
                                                 "plusvalia", "rentabilidad", "tir"})


def _js(nombre):
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "web", nombre),
              encoding="utf-8") as f:
        return f.read()


class InterfazPosiciones(unittest.TestCase):
    """Comprobaciones estáticas; el comportamiento se verifica en la app real (Task 8)."""

    def test_modo_cartera_solo_si_hay_carteras(self):
        js = _js("app.js")
        self.assertIn('{ id: "cartera", et: "Cartera" }', js)
        self.assertIn("D.carteras", js)
        self.assertIn("Carteras.agrupa(", js)

    def test_linea_de_cartera_accesible_y_con_nombre_escapado(self):
        js = _js("app.js")
        bloque = js[js.index('tr class="grupo cartera"'):][:700]
        for pieza in ('role="button"', 'tabindex="0"', "aria-expanded", "esc(g.nombre)"):
            self.assertIn(pieza, bloque, pieza)

    def test_el_plegado_se_recuerda_y_la_busqueda_despliega(self):
        js = _js("app.js")
        self.assertIn('"patrimonio.carterasAbiertas"', js)
        self.assertIn("const buscando = !!q", js)

    def test_la_linea_de_cartera_enseña_su_tir(self):
        js = _js("app.js")
        self.assertIn("g.tir == null ? \"—\" : G.fmtPctSigno(g.tir, 1)", js)

    def test_nombres_largos_se_parten_y_la_busqueda_mira_la_cartera(self):
        css = _js("tema-carta.css")
        self.assertIn("tr.grupo.cartera td:first-child{white-space:normal;overflow-wrap:anywhere}", css)
        self.assertIn("Carteras.coincide(", _js("app.js"))

    def test_sin_estilos_en_linea_ni_nombres_sin_escapar(self):
        js = _js("app.js")
        self.assertIn("esc(String(g.ltvMax)", js)
        self.assertNotIn("${g.nombre}", js)
        self.assertNotIn("${g.entidad}", js)


class InterfazEditor(unittest.TestCase):
    def test_vista_carteras_y_acciones_registradas(self):
        ed = _js("editor.js")
        self.assertIn('["carteras", "Carteras"]', ed)
        for nombre in ("vistaCarteras", "formCartera", "borrarCartera"):
            self.assertIn(f"function {nombre}", ed, nombre)
        for acc in ("nuevaCartera: soloPropio(", "editarCartera: soloPropio(", "borrarCartera: soloPropio("):
            self.assertIn(acc, ed, acc)

    def test_ficha_del_producto_tiene_el_desplegable_de_cartera(self):
        ed = _js("editor.js")
        self.assertIn('name="carteraId"', ed)
        self.assertIn("Sin cartera", ed)

    def test_borrar_una_cartera_avisa_de_los_prestamos_que_respalda(self):
        """Antes no avisaba: quitarla de una garantía compartida cambiaba el LTV sugerido sin decirlo."""
        ed = _js("editor.js")
        trozo = ed[ed.index("async function borrarCartera"):][:1400]
        self.assertIn("carteraIds", trozo)
        self.assertIn("su garantía bajará", trozo)
        self.assertIn("LTV", trozo)

    def test_nombres_de_cartera_siempre_escapados(self):
        ed = _js("editor.js")
        trozo = ed[ed.index("function vistaCarteras"):ed.index("function vistaCarteras") + 2600]
        self.assertIn("esc(c.nombre)", trozo)
        self.assertNotIn("${c.nombre}", ed)
        self.assertNotIn("${c.entidad}", ed)


class InterfazPrestamo(unittest.TestCase):
    def test_formulario_con_carteras_en_garantia_y_ltv_sugerido(self):
        ed = _js("editor.js")
        self.assertIn('name="cartera"', ed)
        self.assertIn("d.carteraIds =", ed)
        self.assertIn("Carteras.ltvSugerido(", ed)
        self.assertIn("Carteras en garantía", ed)

    def test_la_lista_y_la_tarjeta_resumen_la_garantia_con_texto_escapado(self):
        self.assertIn("Carteras.textoGarantia(", _js("app.js"))
        self.assertIn("esc(Carteras.textoGarantia(", _js("app.js"))
        ed = _js("editor.js")
        self.assertIn("Carteras.textoGarantia(", ed)
        self.assertIn("esc(Carteras.textoGarantia(", ed)


class Proteccion(unittest.TestCase):
    """Una cartera que respalda un préstamo vivo no pierde fondos en silencio (hallazgo de la revisión)."""

    def setUp(self):
        self.cfg = cfg_base()
        almacen.guarda_cartera(self.cfg, {"nombre": "Cartera Ejemplo", "ltvMax": 50, "productos": ["fondo_a", "fondo_b"]})
        self.pg = prestamo(self.cfg, nombre="Mi préstamo", carteraIds=["c1"])

    def fondos(self):
        return [p["id"] for p in self.cfg["productos"] if p.get("carteraId") == "c1"]

    def test_sacar_un_fondo_de_la_cartera_pignorada_se_rechaza(self):
        with self.assertRaises(almacen.ErrorValidacion) as e:
            almacen.guarda_cartera(self.cfg, {"id": "c1", "nombre": "Cartera Ejemplo", "productos": ["fondo_a"]})
        self.assertIn("Mi préstamo", e.exception.errores[0])
        self.assertEqual(self.fondos(), ["fondo_a", "fondo_b"])               # nada cambió

    def test_vaciar_una_cartera_pignorada_se_rechaza(self):
        with self.assertRaises(almacen.ErrorValidacion):
            almacen.guarda_cartera(self.cfg, {"id": "c1", "nombre": "Cartera Ejemplo", "productos": []})
        self.assertEqual(self.fondos(), ["fondo_a", "fondo_b"])

    def test_anadir_fondos_o_editar_otros_datos_si_se_permite(self):
        almacen.guarda_cartera(self.cfg, {"id": "c1", "nombre": "Cartera Ejemplo", "productos": ["fondo_a", "fondo_b", "fondo_c"]})
        self.assertEqual(self.fondos(), ["fondo_a", "fondo_b", "fondo_c"])
        almacen.guarda_cartera(self.cfg, {"id": "c1", "nombre": "Renombrada", "entidad": "Otra"})      # sin tocar los fondos
        self.assertEqual(self.fondos(), ["fondo_a", "fondo_b", "fondo_c"])

    def test_mover_o_soltar_un_fondo_desde_su_ficha_se_rechaza(self):
        base = {"id": "fondo_a", "nombre": "Fondo A", "tipo": "fondo", "fuente": "manual"}
        for destino in ("", "c2"):
            almacen.guarda_cartera(self.cfg, {"nombre": "Otra %s" % destino, "productos": ["fondo_c"]}) if destino else None
            with self.assertRaises(almacen.ErrorValidacion, msg=repr(destino)):
                almacen.guarda_producto(self.cfg, dict(base, carteraId=destino))
        self.assertEqual(self.fondos(), ["fondo_a", "fondo_b"])
        almacen.guarda_producto(self.cfg, dict(base, carteraId="c1"))              # dejarlo donde está, sí

    def test_meter_un_fondo_suelto_en_la_cartera_desde_su_ficha_si_se_permite(self):
        almacen.guarda_producto(self.cfg, {"id": "fondo_c", "nombre": "Fondo C", "tipo": "fondo", "fuente": "manual", "carteraId": "c1"})
        self.assertEqual(self.fondos(), ["fondo_a", "fondo_b", "fondo_c"])

    def test_borrar_un_fondo_de_una_cartera_pignorada_se_rechaza(self):
        with self.assertRaises(almacen.ErrorValidacion):
            almacen.borra_producto(self.cfg, "fondo_a")
        self.assertIsNotNone(almacen.producto(self.cfg, "fondo_a"))
        almacen.borra_producto(self.cfg, "fondo_c")                                  # uno suelto y libre, sí

    def test_con_el_prestamo_liquidado_vuelve_a_poderse(self):
        self.pg["estado"] = "liquidada"
        almacen.guarda_cartera(self.cfg, {"id": "c1", "nombre": "Cartera Ejemplo", "productos": []})
        self.assertEqual(self.fondos(), [])


class CopiasAjenasConCarteras(unittest.TestCase):
    def test_sanea_copia_normaliza_las_carteras(self):
        cfg = {"productos": [{"id": "a", "carteraId": "c1"}, {"id": "b", "carteraId": "zz"}, {"id": "c", "carteraId": 7}],
               "movimientos": [], "valoraciones": [],
               "carteras": [{"id": "c1", "nombre": "Buena", "ltvMax": "abc"}, {"id": "c1", "nombre": "Duplicada"},
                            {"nombre": "Sin id"}, "basura", {"id": "c2", "ltvMax": 150, "entidad": 5},
                            {"id": "c3", "nombre": "Ok", "ltvMax": "62,5"}, {"id": "c4", "nombre": "N", "ltvMax": float("nan")}],
               "pignoraciones": [{"id": "pg1", "carteraIds": "c1"}, {"id": "pg2", "carteraIds": ["c1", 3, "zz"]}]}
        limpia = almacen.sanea_copia(cfg)
        ids = [c["id"] for c in limpia["carteras"]]
        self.assertEqual(ids, ["c1", "c2", "c3", "c4"])                           # sin duplicados, sin basura, sin id
        por = {c["id"]: c for c in limpia["carteras"]}
        self.assertNotIn("ltvMax", por["c1"])                                     # «abc» fuera
        self.assertEqual(por["c2"]["nombre"], "c2")                               # nombre por defecto
        self.assertNotIn("ltvMax", por["c2"]); self.assertNotIn("entidad", por["c2"])
        self.assertEqual(por["c3"]["ltvMax"], 62.5)                               # texto numérico válido -> número
        self.assertNotIn("ltvMax", por["c4"])
        self.assertEqual([p.get("carteraId") for p in limpia["productos"]], ["c1", None, None])
        self.assertNotIn("carteraIds", limpia["pignoraciones"][0])
        self.assertEqual(limpia["pignoraciones"][1]["carteraIds"], ["c1"])

    def test_un_ltv_corrupto_no_tumba_el_calculo(self):
        cfg = cfg_base()
        almacen.guarda_cartera(cfg, {"nombre": "A", "productos": ["fondo_a"]})
        cfg["carteras"][0]["ltvMax"] = "abc"                                      # editado a mano, sin pasar por la validación
        p = prestamo(cfg, carteraIds=["c1"])
        self.assertIsNone(pignoracion.ltv_sugerido(cfg, p))
        e = pignoracion.resumen(cfg, {"fondo_a": 1000.0}, dt.date(2026, 10, 1))[0]
        self.assertIsNone(e["ltvMax"])

    def test_cartera_sin_nombre_no_rompe_el_duplicado(self):
        cfg = cfg_base()
        cfg["carteras"] = [{"id": "c1"}]
        almacen.guarda_cartera(cfg, {"nombre": "Nueva"})


class Robustez(unittest.TestCase):
    """Reservas de la segunda revisión de seguridad: ni una copia hostil ni un archivo editado a mano lanzan excepciones."""

    def test_sanea_copia_con_tipos_raros_no_lanza(self):
        cfg = {"productos": [{"id": "a", "carteraId": ["c1"]}, {"id": "b", "carteraId": {"x": 1}}, None, "x", {"id": "c", "carteraId": "c1"}],
               "movimientos": [], "valoraciones": [],
               "carteras": [{"id": "c1", "nombre": "A", "ltvMax": 10 ** 400}, {"id": "c2", "nombre": "B", "ltvMax": float("inf")}],
               "pignoraciones": None}
        limpia = almacen.sanea_copia(cfg)
        self.assertEqual([p.get("carteraId") for p in limpia["productos"] if isinstance(p, dict)], [None, None, "c1"])
        self.assertTrue(all("ltvMax" not in c for c in limpia["carteras"]))
        for raro in (None, 5, "texto", {"a": 1}):
            almacen.sanea_copia({"productos": raro, "movimientos": [], "valoraciones": [], "carteras": raro, "pignoraciones": raro})
        almacen.sanea_copia({"productos": [], "movimientos": [], "valoraciones": [],
                             "pignoraciones": [None, "x", {"id": "pg", "carteraIds": None}, {"id": "p2", "carteraIds": [["c1"], {"a": 1}]}]})

    def test_ltv_sugerido_y_efectivo_con_valores_corruptos(self):
        cfg = cfg_base()
        almacen.guarda_cartera(cfg, {"nombre": "A", "productos": ["fondo_a"]})
        p = prestamo(cfg, carteraIds=["c1"])
        for malo in (float("nan"), float("inf"), 10 ** 400, "abc", True, None, [1]):
            cfg["carteras"][0]["ltvMax"] = malo
            self.assertIsNone(pignoracion.ltv_sugerido(cfg, p), repr(malo))
        p["ltvMax"] = 10 ** 400                                       # préstamo editado a mano
        cfg["carteras"][0]["ltvMax"] = 50.0
        self.assertEqual(pignoracion.ltv_efectivo(cfg, p), 50.0)       # cae a lo sugerido, no lanza
        p["ltvMax"] = float("nan")
        self.assertEqual(pignoracion.ltv_efectivo(cfg, p), 50.0)

    def test_sanea_copia_con_slot_infinito_o_enorme_no_lanza(self):
        for raro in (float("inf"), float("-inf"), float("nan"), 10 ** 400, 1e999, "9" * 500, [1], {"a": 1}):
            limpia = almacen.sanea_copia({"productos": [{"id": "a", "slot": raro}], "movimientos": [], "valoraciones": []})
            self.assertEqual(limpia["productos"][0]["slot"], 1, repr(raro)[:30])

    def test_placeholder_de_entidad_del_formulario_es_generico(self):
        ed = _js("editor.js")
        self.assertNotIn('name="entidad" placeholder="MyInvestor"', ed)


class TextosDeBloqueo(unittest.TestCase):
    """Un activo pignorado no se puede vender NI TRASPASAR hasta liquidar la pignoración (en Rumbo, un traspaso es venta + compra)."""

    def test_el_rechazo_de_la_venta_dice_que_tampoco_se_traspasa(self):
        cfg = cfg_base()
        prestamo(cfg, activos=["fondo_a"])
        with self.assertRaises(almacen.ErrorValidacion) as e:
            almacen.guarda_movimiento(cfg, {"fecha": "2026-10-10", "producto": "fondo_a", "tipo": "venta",
                                            "unidades": "1", "importe": "100"})
        msg = e.exception.errores[0]
        self.assertIn("vender ni traspasar", msg)
        self.assertIn("venta y una compra", msg)                         # cómo se anota un traspaso en Rumbo
        self.assertIn("Pignoraciones", msg)                              # qué hacer

    def test_la_interfaz_nunca_dice_solo_vender(self):
        for nombre in ("app.js", "editor.js"):
            js = _js(nombre)
            for viejo in ("no se puede vender hasta", "no puedes vender ${", "no se pueden vender mientras", "no se puede vender\""):
                self.assertNotIn(viejo, js, f"{nombre}: {viejo}")
        self.assertIn("vender ni traspasar", _js("app.js"))
        self.assertIn("vender ni traspasar", _js("editor.js"))

    def test_glosario_y_readme_lo_explican(self):
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for ruta in ("docs/GLOSARIO.md", "README.md"):
            with open(os.path.join(raiz, ruta), encoding="utf-8") as f:
                self.assertIn("traspasar", f.read(), ruta)


def datos_de(cfg):
    """Calcula el panel de una cartera de prueba (sin red) y devuelve `datos`."""
    servidor.DATOS = _TMP
    for n in os.listdir(_TMP):
        q = os.path.join(_TMP, n)
        if os.path.isfile(q):
            os.remove(q)
    almacen.guarda(os.path.join(_TMP, "cartera.json"), cfg)
    with contextlib.redirect_stdout(io.StringIO()):
        return servidor.recalcula(descargar=False)


def cfg_con_compras():
    """Dos fondos con compras en fechas distintas y valor manual a 2026-09-01; ambos en «Cartera Ejemplo»."""
    cfg = json.loads(json.dumps(almacen.CARTERA_VACIA))
    cfg["productos"] = [{"id": f, "nombre": f, "corto": f, "tipo": "fondo", "fuente": "manual", "moneda": "EUR", "slot": i + 1}
                        for i, f in enumerate(("fa", "fb"))]
    cfg["movimientos"] = [
        {"id": "m1", "fecha": "2026-01-10", "producto": "fa", "tipo": "compra", "unidades": 10, "importe": 1000.0},
        {"id": "m2", "fecha": "2026-04-10", "producto": "fa", "tipo": "compra", "unidades": 5, "importe": 500.0},
        {"id": "m3", "fecha": "2026-03-01", "producto": "fb", "tipo": "compra", "unidades": 20, "importe": 2000.0}]
    cfg["valoraciones"] = [{"id": "v1", "fecha": "2026-09-01", "producto": "fa", "valor": 1700.0, "aportado": None},
                           {"id": "v2", "fecha": "2026-09-01", "producto": "fb", "valor": 2300.0, "aportado": None}]
    almacen.guarda_cartera(cfg, {"nombre": "Cartera Ejemplo", "productos": ["fa", "fb"]})
    return cfg


class RendimientoDeCartera(unittest.TestCase):
    """Valor, aportado, plusvalía, rentabilidad y TIR combinada de cada cartera (se publican en datos.carteras)."""

    def test_cifras_de_la_cartera_son_la_suma_de_sus_fondos(self):
        d = datos_de(cfg_con_compras())
        c = d["carteras"][0]
        self.assertEqual((c["valor"], c["aportado"], c["plusvalia"], c["fondos"]), (4000.0, 3500.0, 500.0, 2))
        self.assertEqual(c["rentabilidad"], round(500.0 / 3500.0, 4))

    def test_la_tir_es_la_de_todos_los_flujos_juntos(self):
        d = datos_de(cfg_con_compras())
        hoy = dt.date.fromisoformat(d["fechaExtracto"])
        flujos = [(dt.date.fromisoformat(f), v) for p in d["productos"] for f, v in p["flujos"]]
        esperado = round(motor.xirr(flujos + [(hoy, 4000.0)]), 4)
        self.assertEqual(d["carteras"][0]["tir"], esperado)
        sueltas = [p["tir"] for p in d["productos"]]
        self.assertNotIn(d["carteras"][0]["tir"], sueltas)                  # no es la de ninguno de los fondos

    def test_si_a_un_fondo_le_faltan_datos_no_se_inventa(self):
        cfg = cfg_con_compras()
        cfg["productos"].append({"id": "fc", "nombre": "fc", "corto": "fc", "tipo": "fondo", "fuente": "manual",
                                 "moneda": "EUR", "slot": 3})
        cfg["valoraciones"].append({"id": "v3", "fecha": "2026-09-01", "producto": "fc", "valor": 500.0, "aportado": None})
        almacen.guarda_cartera(cfg, {"id": "c1", "nombre": "Cartera Ejemplo", "productos": ["fa", "fb", "fc"]})
        c = datos_de(cfg)["carteras"][0]
        self.assertEqual(c["valor"], 4500.0)                                  # el valor sí se suma
        self.assertEqual((c["aportado"], c["plusvalia"], c["rentabilidad"], c["tir"]), (None, None, None, None))

    def test_cartera_sin_fondos(self):
        cfg = cfg_con_compras()
        almacen.guarda_cartera(cfg, {"nombre": "Vacía"})
        c = datos_de(cfg)["carteras"][1]
        self.assertEqual((c["fondos"], c["valor"], c["aportado"], c["tir"]), (0, 0.0, None, None))

    def test_sin_importes_escala_el_dinero_y_deja_los_porcentajes(self):
        d = datos_de(cfg_con_compras())
        real = d["carteras"][0]
        oculto = exportar.sin_importes(d)["carteras"][0]
        self.assertNotEqual(oculto["valor"], real["valor"])
        self.assertAlmostEqual(oculto["valor"] / oculto["aportado"], real["valor"] / real["aportado"], places=3)   # el factor es aleatorio y se redondea a céntimos
        self.assertEqual((oculto["tir"], oculto["rentabilidad"], oculto["fondos"]), (real["tir"], real["rentabilidad"], real["fondos"]))
        self.assertNotIn("4000.0", json.dumps(exportar.sin_importes(d)["carteras"]))


class ResumenPuro(unittest.TestCase):
    """app/carteras.resumen con datos a mano: robustez y casos límite (revisión del verificador y de seguridad)."""
    HOY = dt.date(2026, 9, 1)

    def prod(self, pid, cid="c1", valor=1000.0, aportado=900.0, flujos=(("2026-01-10", -900.0),)):
        return {"id": pid, "carteraId": cid, "valor": valor, "aportado": aportado, "flujos": [list(f) for f in flujos]}

    def resumen(self, productos, carteras=({"id": "c1", "nombre": "A"},)):
        return calc_carteras.resumen(list(carteras), productos, self.HOY, motor.xirr)

    def test_carteras_sin_id_o_que_no_son_dict_se_saltan(self):
        r = self.resumen([self.prod("a", cid=None)], carteras=[{"nombre": "Sin id"}, "basura", None, {"id": "", "nombre": "x"},
                                                              {"id": "c1", "nombre": "A"}])
        self.assertEqual([c["id"] for c in r], ["c1"])
        self.assertEqual(r[0]["fondos"], 0)                       # el fondo sin cartera no se cuela en una cartera sin id

    def test_datos_raros_no_lanzan_y_dejan_las_cifras_en_none(self):
        for malo in ({"aportado": "abc"}, {"aportado": float("nan")}, {"aportado": [1]}):        # sin aportado fiable
            r = self.resumen([self.prod("a", **malo)])[0]
            self.assertEqual((r["aportado"], r["plusvalia"], r["rentabilidad"], r["tir"]), (None,) * 4, repr(malo))
        for malo in ({"valor": None}, {"valor": "x"}, {"valor": float("inf")}):                   # sin valor fiable
            r = self.resumen([self.prod("a", **malo)])[0]
            self.assertEqual((r["aportado"], r["rentabilidad"], r["tir"]), (None,) * 3, repr(malo))
        for malo in ({"flujos": [["no es fecha", -900.0]]}, {"flujos": [["2026-01-10", "abc"]]}, {"flujos": [[None, 1]]},
                     {"flujos": [["2026-01-10"]]}, {"flujos": "texto"}):                          # flujos ilegibles: solo la TIR
            r = self.resumen([self.prod("a", **malo)])[0]
            self.assertIsNone(r["tir"], repr(malo))
            self.assertEqual(r["aportado"], 900.0, repr(malo))                                    # lo demás sigue valiendo

    def test_un_fondo_sin_valor_no_da_una_rentabilidad_de_menos_100(self):
        r = self.resumen([self.prod("a"), self.prod("b", valor=None)])[0]
        self.assertEqual(r["valor"], 1000.0)
        self.assertEqual((r["aportado"], r["plusvalia"], r["rentabilidad"], r["tir"]), (None, None, None, None))

    def test_un_fondo_vendido_del_todo_no_hace_perder_la_tir_de_la_cartera(self):
        vendido = self.prod("v", valor=0.0, aportado=None, flujos=(("2026-01-10", -2000.0), ("2026-05-10", 2100.0)))
        vivo = self.prod("a", valor=1000.0, aportado=900.0, flujos=(("2026-02-10", -900.0),))
        r = self.resumen([vivo, vendido])[0]
        self.assertEqual((r["valor"], r["aportado"], r["plusvalia"]), (1000.0, 900.0, 100.0))
        flujos = [(dt.date(2026, 2, 10), -900.0), (dt.date(2026, 1, 10), -2000.0), (dt.date(2026, 5, 10), 2100.0), (self.HOY, 1000.0)]
        self.assertEqual(r["tir"], round(motor.xirr(flujos), 4))
        sin_flujos = self.prod("w", valor=0.0, aportado=None, flujos=())
        self.assertIsNone(self.resumen([vivo, sin_flujos])[0]["aportado"])        # valor 0 sin historia: no hay de dónde sacarlo

    def test_xirr_con_todos_los_flujos_el_mismo_dia_no_inventa_una_tir(self):
        mismo = dt.date(2026, 1, 1)
        self.assertIsNone(motor.xirr([(mismo, -100.0), (mismo, 100.0)]))
        r = calc_carteras.resumen([{"id": "c"}], [{"carteraId": "c", "valor": 100.0, "aportado": 100.0, "flujos": [["2026-01-01", -100.0]]}],
                                  mismo, motor.xirr)[0]
        self.assertIsNone(r["tir"])
        self.assertIsNotNone(motor.xirr([(dt.date(2026, 1, 1), -100.0), (dt.date(2027, 1, 1), 110.0)]))   # lo normal sigue igual


class Api(unittest.TestCase):
    def setUp(self):
        servidor.DATOS = _TMP
        for n in os.listdir(_TMP):
            p = os.path.join(_TMP, n)
            if os.path.isfile(p):
                os.remove(p)
        almacen.guarda(os.path.join(_TMP, "cartera.json"), cfg_base())
        self.c = servidor.app.test_client()

    def test_crear_editar_y_borrar_por_la_api(self):
        r = self.c.post("/api/carteras", json={"nombre": "Cartera Ejemplo", "ltvMax": 50, "productos": ["fondo_a"]}, headers=H)
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        self.assertEqual(r.get_json()["item"]["id"], "c1")
        self.assertEqual(r.get_json()["cartera"]["carteras"][0]["nombre"], "Cartera Ejemplo")
        r = self.c.delete("/api/carteras/c1", headers=H)
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        self.assertEqual(r.get_json()["cartera"]["carteras"], [])

    def test_error_de_validacion_es_400_con_mensaje(self):
        r = self.c.post("/api/carteras", json={"nombre": ""}, headers=H)
        self.assertEqual(r.status_code, 400)
        self.assertTrue(r.get_json()["errores"])

    def test_origen_cruzado_403(self):
        cab = {"Sec-Fetch-Site": "cross-site", "Origin": "http://malo.example"}
        self.assertEqual(self.c.post("/api/carteras", json={"nombre": "X"}, headers=cab).status_code, 403)
        self.assertEqual(self.c.delete("/api/carteras/c1", headers=cab).status_code, 403)


if __name__ == "__main__":
    unittest.main()
