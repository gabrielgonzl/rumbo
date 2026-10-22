# Carteras de fondos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que Rumbo conozca las carteras de fondos (p. ej. una cartera indexada gestionada por una entidad): verlas como una línea plegable en Posiciones y pignorarlas, con un LTV máximo sugerido por cartera.

**Architecture:** Nueva entidad `carteras` en el archivo de datos (v4, migración aditiva) y un `carteraId` opcional en cada producto. La garantía de una pignoración se resuelve al leer (`activos_efectivos`) y el LTV efectivo con una regla fija (`ltv_efectivo`); las cifras de deuda no cambian. Los totales por cartera se calculan en el navegador con una función pura (`carteras.js`), como el resto de agrupaciones de Posiciones.

**Tech Stack:** Python 3 + Flask (`app/*.py`), JS vanilla (`app/web/*.js`), `unittest` y `node` para pruebas, Playwright (Chromium en `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`) para la comprobación en la app real. Sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-10-15-carteras-de-fondos-design.md`

## Global Constraints

- Rama `auto/mejora-continua`; nunca `main`, nunca `--force`, nunca fusionar el PR #5. Commits pequeños con los trailers `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` y `Claude-Session: https://claude.ai/code/session_01LbWos3XYyC62C6HzdkAsP5`.
- Datos personales: ninguno en commits ni tests (nombres genéricos: «Cartera Ejemplo», «Entidad Ejemplo», «Fondo A»; nunca el producto o la entidad reales del usuario). No tocar `mis_datos`, `.env`, CSV/Excel reales.
- `VERSION_ACTUAL = 4`; la migración solo añade `carteras: []` y es idempotente. `test_fase3` sigue comparando con `almacen.VERSION_ACTUAL`.
- Cartera: `nombre` obligatorio, ≤ 80 caracteres, único sin distinguir mayúsculas; `entidad` ≤ 80; `ltvMax` opcional, numérico finito, `0 < ltvMax ≤ 100`. Los ids salen de `almacen.siguiente_id(lista, "c")`.
- Regla de LTV efectivo: (1) `ltvMax` escrito en el préstamo; (2) si no, garantía = solo carteras, todas con `ltvMax` y todas iguales → ese valor; (3) en otro caso `None`.
- Un fondo solo puede estar en una cartera. Borrar una cartera deja sus fondos sueltos y la quita de los préstamos; si un préstamo se quedara sin garantía, el borrado se rechaza.
- Interfaz: todo texto de usuario por `esc()` (`app.js`/`editor.js`) o `escH()` (`graficos.js`); nada de atributos de estilo en línea (usar `data-st` con propiedades de la lista de `estilos.js`); sin recursos externos; la web exportada debe seguir funcionando y no lleva importes nuevos.
- Una cifra no cambia por estilo: deuda, intereses, cuotas y rentabilidades existentes deben dar lo mismo antes y después.
- Antes de cada commit: `python -m unittest discover -s tests` y `for f in tests/*.test.js; do node $f; done` en verde. Si hay `pip` roto: `pip install --ignore-installed blinker flask openpyxl`.

## Review Focus

1. **Producto borrado que pertenecía a una cartera**: la cartera lo pierde sin error y la garantía de los préstamos se recalcula sin él (Task 1 y 2).
2. **Cartera sin fondos usada como garantía**: se rechaza con un mensaje que dice qué hacer, no una garantía vacía silenciosa (Task 2).
3. **Dos carteras con LTV distinto y préstamo sin LTV propio**: queda «sin indicar»; nunca se promedia ni se coge el menor sin avisar (Task 2).
4. **Nombre de cartera hostil** (`<img src=x onerror=alert(1)>`, comillas, 200 caracteres) en tabla, formulario, desplegables y tooltips: sin HTML inyectado y recortado (Task 1, 5, 6, 7).
5. **Búsqueda con las líneas de cartera plegadas**: si un fondo coincide con la búsqueda, su cartera aparece desplegada y solo con las filas que coinciden; sin coincidencias, no aparece (Task 5).

---

### Task 1: Modelo de datos, migración v4 y API de carteras

**Files:**
- Modify: `app/almacen.py` (`VERSION_ACTUAL`, `CARTERA_VACIA`, `migra`, `guarda_producto`, `borra_producto`; funciones nuevas)
- Modify: `app/servidor.py` (registros `GUARDAR` y `BORRAR`)
- Test: `tests/test_carteras.py` (nuevo)

**Interfaces:**
- Produces:
  - `almacen.VERSION_ACTUAL == 4`; `CARTERA_VACIA["carteras"] == []`.
  - `almacen.cartera(cfg, cid) -> dict | None`.
  - `almacen.guarda_cartera(cfg, datos) -> dict`: `datos` = `{id?, nombre, entidad?, ltvMax?, productos: [ids]}`; crea (id `c1`, `c2`…) o edita; asigna `carteraId` a los productos indicados y lo quita de los que ya no estén en la lista; devuelve la cartera `{id, nombre, entidad, ltvMax?}`. Lanza `ErrorValidacion` con mensajes en español.
  - `almacen.borra_cartera(cfg, cid) -> None`.
  - `guarda_producto` acepta `carteraId` (cadena); si no existe en `cfg["carteras"]` se ignora.
  - `servidor.GUARDAR["carteras"] = almacen.guarda_cartera`, `servidor.BORRAR["carteras"] = almacen.borra_cartera`.

- [ ] **Step 1: Write the failing tests** en `tests/test_carteras.py`: `test_migra_v3_a_v4_es_aditiva_e_idempotente` (un dict v3 con `productos` y `asignacion` queda igual salvo `version == 4` y `carteras == []`; segunda llamada devuelve `False`), `test_nombre_obligatorio_unico_y_corto` (vacío, repetido en distinta capitalización, 81 caracteres → `ErrorValidacion`), `test_ltv_rango` (`0`, `101`, `float("nan")`, `"x"` rechazados; `"50"` y `"62,5"` aceptados), `test_asignar_mueve_el_fondo_de_cartera` (un fondo en la cartera A pasa a B al guardar B con él), `test_editar_quita_los_fondos_desmarcados`, `test_borrar_cartera_suelta_los_fondos_y_la_quita_de_los_prestamos`, `test_borrar_cartera_rechazado_si_deja_un_prestamo_sin_garantia` (mensaje contiene el nombre del préstamo), `test_borrar_producto_lo_saca_de_su_cartera` (Review Focus 1: tras `borra_producto` la cartera no lo cuenta y no lanza), `test_carteraid_inexistente_se_ignora_al_guardar_producto`, `test_api_crear_y_borrar_y_origen_cruzado_403` (cliente Flask como `test_umbrales.Api`: 200 al crear con cabeceras `H`, 403 con `Sec-Fetch-Site: cross-site`), `test_nombre_hostil_sin_marcas` (`"<img src=x onerror=alert(1)>Mal"` se guarda sin `<` ni `>`).
- [ ] **Step 2: Run** `python -m unittest tests.test_carteras -v` → Expected: FAIL (`AttributeError: guarda_cartera`).
- [ ] **Step 3: Implement** lo descrito en Interfaces. `guarda_cartera` valida con `texto()` y `numero()` (ya rechaza no finitos); `borra_producto` limpia `carteraId` implícitamente (el producto desaparece) y no necesita más que un test; `borra_cartera` falla con `ErrorValidacion(["No puedo borrar «X»: el préstamo «Y» solo tiene esa cartera como garantía. Cambia su garantía o liquídalo primero."])` cuando algún préstamo tenga `carteraIds == [id]` y `activos` vacío. Migración: `if v < 4: cfg.setdefault("carteras", []); cfg["version"] = 4`.
- [ ] **Step 4: Run** `python -m unittest discover -s tests` → Expected: OK (incluidos `test_fase3` y `test_umbrales`, que comparan con `VERSION_ACTUAL`).
- [ ] **Step 5: Commit** `git add app/almacen.py app/servidor.py tests/test_carteras.py && git commit -m "Carteras de fondos: modelo v4, validación y API"`.

### Task 2: Garantía efectiva y LTV efectivo en las pignoraciones

**Files:**
- Modify: `app/pignoracion.py` (`resumen`, `marcas`, `bloquea_venta`; funciones nuevas)
- Modify: `app/almacen.py` (`guarda_pignoracion`)
- Test: `tests/test_carteras.py` (clase `Pignoracion`) y `tests/test_pignoracion.py` si algún test existente depende del orden de `activos`

**Interfaces:**
- Consumes: `cfg["carteras"]`, `producto["carteraId"]` (Task 1).
- Produces:
  - `pignoracion.activos_efectivos(cfg, p) -> list[str]`: `p["activos"]` más los ids de productos con `carteraId` en `p["carteraIds"]`, sin duplicados, orden estable (sueltos primero, luego por orden de `cfg["productos"]`).
  - `pignoracion.ltv_efectivo(cfg, p) -> float | None` (regla de Global Constraints).
  - `resumen()` devuelve, además de lo actual: `activos` = efectivos, `ltvMax` = efectivo, `ltvSugerido` (resultado de la regla 2 aunque el préstamo tenga LTV propio, o `None`), `carteraIds` y `carterasDetalle: [{"id", "nombre"}]`.
  - `almacen.guarda_pignoracion` acepta `carteraIds: [str]`: exige que existan, y que la garantía efectiva (activos + fondos de esas carteras) no esté vacía; guarda `carteraIds` solo si no está vacío.

- [ ] **Step 1: Write the failing tests**: `test_activos_efectivos_une_sueltos_y_carteras_sin_duplicados`, `test_fondo_anadido_despues_a_la_cartera_pasa_a_ser_garantia`, `test_ltv_propio_manda`, `test_ltv_de_cartera_unica_o_carteras_iguales`, `test_ltv_distinto_entre_carteras_queda_sin_indicar` (Review Focus 3; assert `None`), `test_garantia_mixta_sin_ltv_propio_queda_sin_indicar`, `test_cartera_sin_fondos_como_garantia_se_rechaza` (Review Focus 2; mensaje contiene «sin fondos»), `test_cartera_inexistente_se_rechaza`, `test_bloquea_venta_de_un_fondo_de_cartera_pignorada` (`bloquea_venta(cfg, "fondo_a", "2026-10-01")` devuelve el nombre del préstamo), `test_marcas_incluye_fondos_de_carteras`, `test_resumen_garantia_y_margen_con_cartera` (valor de garantía = suma de los fondos de la cartera; `ratio` = deuda/garantía), `test_prestamo_sin_carteras_da_lo_mismo_que_antes` (mismas cifras que con `activos` solo).
- [ ] **Step 2: Run** `python -m unittest tests.test_carteras.Pignoracion -v` → Expected: FAIL.
- [ ] **Step 3: Implement**. `resumen()` llama a `estado(p, hoy)` como hoy y después sustituye `e["activos"]` y `e["ltvMax"]` por los efectivos antes de calcular garantía/margen; `marcas()` y `bloquea_venta()` iteran `activos_efectivos(cfg, p)`. No tocar `estado()`.
- [ ] **Step 4: Run** `python -m unittest discover -s tests` → Expected: OK.
- [ ] **Step 5: Commit** `git add app/pignoracion.py app/almacen.py tests/ && git commit -m "Carteras: garantía efectiva y LTV efectivo en las pignoraciones"`.

### Task 3: Publicar carteras en `datos.js` y en la web exportada

**Files:**
- Modify: `app/motor.py` (resultado de `construir`, junto a `"alertas"`)
- Modify: `app/exportar.py` solo si algún test demuestra que hace falta
- Test: `tests/test_carteras.py` (clase `Publicacion`)

**Interfaces:**
- Consumes: Task 1.
- Produces: `datos["carteras"] = [{"id", "nombre", "entidad", "ltvMax"?}]` (lista, posiblemente vacía) y `carteraId` en cada producto publicado (ya viaja si el motor copia el dict del producto; el test lo confirma).

- [ ] **Step 1: Write the failing tests**: `test_datos_js_lleva_carteras_y_carteraid` (cartera temporal con un fondo asignado; `/datos.js` contiene `"carteras":[{"id":"c1"` y el producto lleva `"carteraId":"c1"`), `test_web_exportada_con_y_sin_importes_lleva_carteras_sin_importes` (`exportar.pagina` con `ocultar=True` contiene el nombre de la cartera y ninguna clave nueva con importes).
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** `"carteras": cfg.get("carteras") or []` en `motor.construir`. **Step 4: Run** `python -m unittest discover -s tests` → OK.
- [ ] **Step 5: Commit** `git commit -m "Carteras: publicar en datos.js y en la exportación"`.

### Task 4: Totales por cartera (JS puro) y carga del script

**Files:**
- Create: `app/web/carteras.js`
- Modify: `app/web/cargador.js` (lista de scripts: `"carteras.js"` tras `"alertas.js"`), `app/exportar.py` (misma lista, mismo orden)
- Test: `tests/carteras.test.js` (nuevo) y `tests/test_csp.py` (que `carteras.js` está en ambas listas)

**Interfaces:**
- Produces: `Carteras.agrupa(filas, carteras) -> [{id, nombre, entidad, ltvMax, filas, valor, peso, plus, pct}]` y `Carteras.SIN = "sin-cartera"`. `filas` son los objetos de `filasPos()` (`{p, valor, peso, plus, pct}`; `p.carteraId`). Orden: por `valor` descendente; «Sin cartera» (id `Carteras.SIN`, nombre «Sin cartera») siempre al final y solo si tiene filas; una cartera sin filas no aparece. `plus` = suma de `plus` de las filas que lo tienen (`null` si ninguna); `pct` = `plus / (valor - plus)` solo si **todas** las filas tienen `plus != null` y `valor - plus > 0`, si no `null`; `peso` = suma de pesos. Exporta por `module.exports` en Node y `window.Carteras` en el navegador.

- [ ] **Step 1: Write the failing test** `tests/carteras.test.js` con: suma y peso de dos fondos; `pct` con coste completo y `null` si a un fondo le falta `plus`; fondo sin `carteraId` o con `carteraId` desconocido → «Sin cartera»; cartera sin filas ausente; orden por valor y «Sin cartera» al final; entrada vacía → `[]`.
- [ ] **Step 2: Run** `node tests/carteras.test.js` → FAIL (módulo inexistente).
- [ ] **Step 3: Implement** `Carteras.agrupa` y añadir el script a las dos listas. **Step 4: Run** node + `python -m unittest discover -s tests` → OK.
- [ ] **Step 5: Commit** `git commit -m "Carteras: totales por cartera como función pura"`.

### Task 5: Posiciones, modo «Cartera» con líneas plegables

**Files:**
- Modify: `app/web/app.js` (`AGRUPAR`, `pintaPosiciones`, estado `pos`)
- Modify: `app/web/tema-carta.css` (estilos de la línea plegable)
- Test: `tests/test_carteras.py` (clase `InterfazPosiciones`, comprobaciones estáticas) + verificación Playwright de Task 8

**Interfaces:**
- Consumes: `Carteras.agrupa` (Task 4), `D.carteras`, `p.carteraId`.
- Produces: opción `{ id: "cartera", et: "Cartera" }` en `AGRUPAR`; en ese modo, una fila `tr.grupo.cartera` por cartera con `tabindex="0"`, `role="button"`, `aria-expanded`, `data-cartera`, y las filas de sus fondos debajo (ocultas si está plegada). Estado de plegado en `localStorage` clave `patrimonio.carterasAbiertas` (lista JSON de ids abiertos; por defecto vacía = todas plegadas). Búsqueda activa (`pos.q` no vacío) ⇒ las carteras con coincidencias se muestran desplegadas con solo las filas coincidentes (Review Focus 5). La fila de la cartera enseña nombre (`esc`), nº de fondos, peso, valor, plusvalía y rentabilidad; TIR «—». Sin `D.carteras` o vacío, la opción «Cartera» no aparece.

- [ ] **Step 1: Write the failing tests** estáticos: `AGRUPAR` contiene `id: "cartera"`; el HTML de la fila usa `esc(` para el nombre; no hay `style=` (lo cubre `test_csp`); la clave `patrimonio.carterasAbiertas` existe.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** reutilizando `fila()`/`cmp` existentes; Enter/Espacio y clic alternan; recordar con `recuerda.guarda`. **Step 4: Run** `python -m unittest discover -s tests` → OK.
- [ ] **Step 5: Commit** `git commit -m "Carteras: modo Cartera en Posiciones con líneas plegables"`.

### Task 6: Editor, vista «Carteras» y desplegable en el producto

**Files:**
- Modify: `app/web/editor.js` (lista `vistas`, `vistaCarteras`, formulario, acciones `ACC`, ficha del producto)
- Test: `tests/test_carteras.py` (clase `InterfazEditor`, estáticos)

**Interfaces:**
- Consumes: `POST /api/carteras`, `DELETE /api/carteras/<id>` (Task 1) a través de `guarda("carteras", datos)` / `borra("carteras", id)` del editor.
- Produces: vista `["carteras", "Carteras"]` entre «Pignoraciones» y «Alertas»; tabla (nombre, entidad, nº de fondos, LTV) con acciones `nuevaCartera`, `editarCartera`, `borrarCartera`; formulario con nombre, entidad, LTV opcional y casillas de fondos de inversión (excluye `SOLO_SALDO`); en la ficha del producto, `<select name="carteraId">` con «Sin cartera» + carteras. Toda cadena de usuario por `esc()`.

- [ ] **Step 1: Write the failing tests** estáticos: la vista y las tres acciones existen; `name="carteraId"` en el formulario de producto; el nombre de cartera pasa por `esc(`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** siguiendo el patrón de `vistaPignoraciones`/`formPig` (modal, `api`, recarga con `location.reload()` como la vista Alertas). **Step 4: Run** `python -m unittest discover -s tests` → OK.
- [ ] **Step 5: Commit** `git commit -m "Carteras: vista de edición y desplegable en el producto"`.

### Task 7: Formulario y tarjeta del préstamo con carteras

**Files:**
- Modify: `app/web/editor.js` (formulario de pignoración, líneas ~236-262), `app/web/app.js` (`tarjetaPrestamo`, resumen de garantía)
- Test: `tests/test_carteras.py` (clase `InterfazPrestamo`, estáticos)

**Interfaces:**
- Consumes: `x.carterasDetalle`, `x.ltvSugerido`, `x.activos` (efectivos) de `D.pignoraciones` (Task 2).
- Produces: bloque «Carteras en garantía» (casillas `name="cartera"`) sobre las de fondos sueltos; el envío incluye `carteraIds`; el campo LTV muestra `ltvSugerido` como `placeholder`/ayuda cuando existe; la tarjeta del préstamo añade la línea «Garantía: {cartera(s)} + N fondo(s) suelto(s)» y el detalle sigue listando los fondos efectivos.

- [ ] **Step 1: Write the failing tests** estáticos (`carteraIds` en el envío; `carterasDetalle` usado con `esc`). **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** `python -m unittest discover -s tests` → OK.
- [ ] **Step 5: Commit** `git commit -m "Carteras: carteras como garantía en el formulario y la tarjeta del préstamo"`.

### Task 8: Verificación en la app real, documentación y revisión

**Files:**
- Modify: `docs/GLOSARIO.md` (término «Cartera»), `docs/auto/informe.md`, `docs/auto/tablero.md` (tarjeta «Carteras de fondos»), `README.md` si menciona las pignoraciones
- Create: `docs/auto/carteras_vivo.js` (script Playwright de la verificación)

- [ ] **Step 1:** Arrancar la app con una carpeta temporal (demo + 3 fondos asignados a «Cartera Ejemplo» con LTV 50 + un préstamo con esa cartera) en el puerto 8791 (`PATRIMONIO_NO_ABRIR=1 PATRIMONIO_REFRESCO_HORAS=0`).
- [ ] **Step 2:** Con Playwright, a 1280 y 390 px en claro y oscuro: crear/editar/borrar una cartera desde Datos → Carteras; asignar fondos desde la ficha del producto; Posiciones en modo «Cartera» (plegada por defecto, desplegar con clic y con Enter, recargar y comprobar que recuerda); búsqueda con una cartera plegada; pignorar la cartera y ver el margen con el LTV sugerido; vender un fondo de la cartera pignorada y comprobar el bloqueo. Expected: 0 desbordes horizontales, 0 errores de consola, 0 `securitypolicyviolation`, 0 `[data-st]` sin aplicar.
- [ ] **Step 3:** Comparar capturas (PIL) de las pestañas que no cambian entre `5ca8d91` (worktree) y la rama actual. Expected: idénticas salvo lo nuevo.
- [ ] **Step 4:** Exportar `/api/exportar-web` y `?ocultar=1`, abrir con `file://`: sin errores, sin importes nuevos.
- [ ] **Step 5:** Actualizar glosario, informe y tablero; ejecutar la suite completa; commit `git commit -m "Carteras: verificación, glosario e informe"`; `git push origin auto/mejora-continua`.
- [ ] **Step 6:** Lanzar `seguridad-privacidad` y `verificador` sobre `git diff 5ca8d91..HEAD`; resolver sus reservas y volver a verificar; actualizar la descripción del PR #5.
