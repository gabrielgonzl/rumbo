# Informe de ejecuciones automáticas

> Lo mantiene el orquestador. Sin datos personales. Lo más reciente, arriba.

## Ronda 4 (sesión en la nube)

**Revisión de las cifras por cartera, del texto «ni traspasar» y de la robustez:** seguridad-privacidad **VETÓ** una vez más (el propio
informe escribía el término que se buscaba y una cifra real de una cartera; corregido en `f7c8c92`) y el verificador APRUEBA CON
RESERVAS (TIR y rentabilidad por cartera contra un cálculo independiente en Python, 0 desbordes, 0 errores, exportación sin importes
correcta, venta fechada antes de la pignoración permitida y posterior rechazada con el texto nuevo). Resuelto con test antes de código:
- `motor.xirr` devolvía una TIR falsa (≈ +450 %) si todos los flujos caían el mismo día; ahora `None`.
- `carteras.resumen` salta carteras sin id o que no son dict, no lanza con aportado/valor/flujos mal formados y no da −100 % si a un
  fondo le falta el valor.
- Un fondo vendido del todo ya no hace perder la TIR de su cartera (cuenta como aportado 0; sus compras y cobros siguen en los flujos).
- `sanea_copia` ya no lanza con un `slot` infinito o enorme (mismo tipo de fallo que el `ltvMax`).
- La línea de cartera en Posiciones ya no suma la plusvalía de solo una parte de los fondos: todos o ninguno, como la rentabilidad.
- **Cerrada (F2, rebalanceo en Fiscalidad):** el usuario confirma que Fiscalidad ya refleja todo lo suyo, así que no se toca la lógica fiscal. (Antes estaba pendiente porque) no se toca la lógica fiscal sin saber cómo representan los datos del usuario el
  rebalanceo (los lotes importados ya traen su fecha fiscal, así que puede no haber ventas falsas). Se necesita que el usuario mire
  Fiscalidad y diga si aparece alguna venta que sea un rebalanceo o un traspaso.

**Rentabilidad real por cartera (F3):** `app/carteras.py` (función pura) publica en `datos.carteras` el número de fondos, el valor, el
aportado, la plusvalía, la rentabilidad y la **TIR combinada** (la de todos los flujos de los fondos juntos más el valor de hoy,
no la media de las TIR). Regla de honestidad: el valor siempre se suma; el resto solo se da si todos los fondos tienen aportado
(y flujos, para la TIR): si a uno le falta, es `null`. En la web sin importes se escalan `valor`, `aportado` y `plusvalia` y
los porcentajes quedan. La línea de la cartera en Posiciones enseña esa TIR solo cuando están a la vista todos sus fondos (con
un filtro activo pone «—»). Comprobado en la app real: la cifra de la línea coincide con la del servidor.
Un test mío salió intermitente (la exportación escala con un factor aleatorio redondeado a céntimos): tolerancia ajustada y
suite ejecutada 5 veces seguidas en verde.

**Pignoración: «no se puede vender ni traspasar» (petición del usuario):** un activo pignorado tampoco se puede traspasar hasta
liquidar la pignoración. En Rumbo un traspaso se anota como venta + compra, así que ya quedaba bloqueado por el lado de la venta
(también si el activo está en una cartera pignorada); lo que faltaba era decirlo. Ahora el rechazo, el candado 🔒, la insignia «En
garantía», la tarjeta del préstamo, el texto de Pignoraciones, el README y el glosario dicen «vender ni traspasar», y el rechazo
explica cómo se anota un traspaso. Tests en `TextosDeBloqueo`; comprobado en la app real.

**Carteras de fondos (nueva función pedida por el usuario; spec y plan en `docs/superpowers/`):** agrupar los fondos que una
entidad gestiona juntos y poder pignorarlos como cartera, con un LTV propio. Implementado de forma autónoma por la noche, con TDD
en 8 tareas (ledger local, commits pequeños):
- **Datos (v4):** `carteras` como entidad (nombre ≤ 80 y único, entidad, `ltvMax` opcional en (0, 100]), `carteraId` en los
  productos, migración aditiva e idempotente, API `POST /api/carteras` y `DELETE /api/carteras/<id>` (heredan el control de
  origen). Borrar una cartera suelta sus fondos y la quita de los préstamos; se rechaza si dejaría un préstamo vivo sin garantía.
- **Pignoración:** la garantía puede mezclar carteras y fondos sueltos y se calcula al leer (`activos_efectivos`), así que un
  fondo añadido después a la cartera pasa a ser garantía y queda bloqueado. LTV efectivo: el del préstamo si lo escribes; si no, el de
  las carteras cuando la garantía son solo carteras con el mismo valor; si no, «sin indicar» (nunca media). La deuda y los
  intereses no cambian.
- **Pantallas:** Posiciones → «Cartera» (línea plegable por cartera, plegada por defecto, recuerda el estado, teclado y
  `aria-expanded`, la búsqueda despliega las que coinciden); Datos → Carteras; desplegable «Cartera» en la ficha del producto;
  bloque «Carteras en garantía» en el préstamo con el LTV sugerido; tarjeta del préstamo con «Cartera Ejemplo + N fondos sueltos».
- **Comprobado en la app real:** crear/editar/borrar carteras, asignar desde la ficha, pignorar la cartera (LTV 50 % sugerido y
  aplicado, zonas 37,5/45 %, 🔒 en los tres fondos, venta de un fondo bloqueada), nombre hostil sin etiquetas; exportación con y sin
  importes abierta con `file://` (sin errores, `•••` con ocultar). 24 de 27 capturas idénticas píxel a píxel con el commit
  anterior; las 3 distintas son la pestaña Datos (botón «Carteras» nuevo). Carga lenta del servidor sin conexión en los
  guardados (reintenta precios): es del entorno, no de la función.
- **Revisión de los agentes sobre las carteras:** seguridad-privacidad **VETÓ** (frases y ejemplos que identificaban el producto y
  la entidad reales del usuario en un repositorio público) y el verificador APRUEBA CON RESERVAS (0 desbordes, 0 errores de consola, 0
  violaciones de CSP, cifras de un préstamo existente idénticas a las del commit anterior, web exportada sin importes con ocultar).
  Resuelto en una pasada: (1) **privacidad:** todos los ejemplos usan «Cartera Ejemplo» / «Entidad Ejemplo» y no hay frases sobre lo que
  tiene el usuario; (2) **hueco funcional:** un fondo ya no puede salir (ni moverse, ni borrarse) de una cartera que respalda un
  préstamo vivo — antes la garantía bajaba y la venta se desbloqueaba sin aviso —, con mensaje que dice qué préstamo hay que cambiar
  antes; (3) copias ajenas: `sanea_copia` normaliza `carteras`, `carteraId` y `carteraIds`, y un `ltvMax` corrupto ya no tumba el
  cálculo; (4) nombres largos de cartera se parten (a 1280 px la tabla vuelve a caber); (5) la búsqueda de Posiciones también
  encuentra por nombre o entidad de la cartera; (6) `ltvMax` escapado por coherencia.
- **Segunda pasada de seguridad-privacidad:** APRUEBA CON RESERVAS y **levanta el veto** para la punta de la rama (la búsqueda del identificador retirado sigue vacía; sin
  datos personales en app/, tests/, docs/, README ni demo/). Reservas bajas resueltas con test: `sanea_copia` ya no lanza con tipos raros
  (`carteraId` lista/dict, `ltvMax` enorme, `pignoraciones: null`), `ltv_sugerido`/`ltv_efectivo` descartan NaN, infinito y enteros enormes, y el
  placeholder de entidad de la pignoración es genérico. Sin cambio: `borrar_cartera` de una cartera que comparte préstamo con otra
  baja la garantía por acción explícita del usuario (anotado como menor).
- **Historial reescrito (orden expresa del usuario):** los 19 commits de las carteras se compactaron en uno para quitar de la
  historia frases que identificaban lo que el usuario tiene contratado. La rama se subió con `--force-with-lease`. Los commits antiguos
  pueden seguir siendo alcanzables por su identificador en GitHub (la línea de tiempo del PR y la red de forks) hasta que GitHub los
  elimine; borrarlos del todo requiere pedírselo a GitHub.
- **Menor cerrado:** al borrar una cartera que está en la garantía de un préstamo vivo, la confirmación lo dice (su garantía bajará y su
  LTV sugerido puede cambiar) en lugar de hacerlo en silencio. Sigue sin dejar borrar la que sea la única garantía de un préstamo.
- **Estado:** 232 tests de Python y 7 archivos de Node en verde.
- **Fuera de esta versión:** el rebalanceo interno sigue viéndose como ventas y compras en Fiscalidad (F2) y aportado/rentabilidad
  reales por cartera (F3). El LTV real lo da el contrato del usuario: el de la cartera es solo una sugerencia.
- **Ambigüedad conocida:** en la interfaz «tu cartera» a secas significa todo el patrimonio; el glosario pide escribir «cartera de
  fondos» para el grupo.

**Revisión de los dos últimos cambios (CSP sin estilos en línea y tablas alternativas):** seguridad-privacidad y
verificador APRUEBAN CON RESERVAS (0 regresiones: 9 pestañas × 1280/390 × claro/oscuro, web exportada con y sin
importes, cero con signo probado con 2 millones de valores, 24 filas máximo en tablas con 1111 fechas, teclado en
`<summary>`). Reservas resueltas en esta tanda:
- **R1 (seguridad):** una copia de seguridad ajena podía meter HTML/`slot` que acabara en una plantilla con `data-st`.
  Ahora `almacen.sanea_copia` (sin `<` ni `>` en ningún texto, `slot` entero 1-12) se aplica en `valida_copia`; los
  tooltips escapan nombres (`escH`); `app.js` escapa `r.producto` y el mensaje de error; el editor usa `slotDe(p)`; y
  `estilos.js` solo aplica una lista de propiedades permitidas (sin `position`, `inset`, `z-index`, `transform`…) y
  descarta `url()`, `@`, `\`, `expression` (`tests/estilos.test.js`). Comprobado en la app real subiendo una copia
  maliciosa: queda saneada. 27 capturas idénticas píxel a píxel con el commit anterior.
- **R2/R3/R4:** el test de «sin `style=`» recorre todos los `*.js`; el exportador ya no depende del salto de línea
  exacto (test con CRLF); el mensaje de error de `app.js` pasa por `esc()`.
- **Defecto previo (verificador):** `barrasApiladas` usaba `fV` sin declararla → `ReferenceError` al pasar el ratón por
  «Aportaciones por mes». Corregido y comprobado con datos reales (tooltip correcto, sin errores).
- **Defecto previo (verificador):** crear una segunda pignoración daba 500 (`siguiente_id` hacía `int(id[1:])` con el
  prefijo `pg`). Corregido (`id[len(prefijo):]`) con tests; en la app real salen `pg1` y `pg2`.
- **Accesibilidad:** el contenedor con scroll de la tabla alternativa es enfocable por teclado (`tabindex`, `role=region`).
- **Sin cambio (decisión de diseño):** el gráfico principal enseña activos (no resta la deuda) y lo dice su nota; la
  tabla alternativa hereda ese total. Las series con valor 0 salen en la tabla y no en el tooltip.
- **No comprobado por el verificador:** gráficos que necesitan precios en línea (comparador, ingresos) renderizados,
  Firefox/Safari, Docker, 1920 px, descarga de copias e importación real.

**Tabla alternativa de datos (cierra V3):** cada gráfico (salvo el minigráfico decorativo) lleva bajo él «Ver los datos
en tabla» (`<details>` cerrado), con los mismos valores y formatos; las series largas se reparten en 24 filas como mucho
(primera y última siempre) y lo dice una nota. Constructores puros con test (`tSerie`, `tReparto`, `tPares`,
`indicesMuestra`); un test estático exige una tabla por SVG. Comprobado en la app real a 1280 y 390 px y en la web
exportada con «ocultar importes» (0 cantidades en euros dentro de las tablas, 0 `undefined`/`NaN`/`null`, sin desbordes).
**Fallo encontrado de paso y corregido:** «TIR de tu capital» salía como «+-0,00 %» (el valor −0 pasaba `>= 0` y luego
se escribía «-0,00»). `fmtPct`, `fmtPctSigno`, `fmtEur` y `fmtEurSigno` ya no enseñan signo a lo que se redondea a cero.

**Endurecimiento de la CSP (después de la revisión):** `style-src 'self'`, sin `'unsafe-inline'`. Los atributos
`style="…"` (≈100 en HTML y plantillas JS) pasan a `data-st="…"`; `app/web/estilos.js` los aplica con `el.style.cssText`
(permitido por la CSP) a los nodos existentes y, con un `MutationObserver`, a los que entren después (89 puntos con
`innerHTML`). La web exportada lleva `estilos.js` dentro. Comprobación: 27 capturas (9 pestañas × 1280 oscuro/claro y
390 claro) idénticas píxel a píxel entre el commit anterior y este; tooltip, vistas del editor y modal con estilo;
0 `securitypolicyviolation`, 0 `data-st` sin aplicar. Test que impide volver a escribir `style=` en la interfaz.

**Revisión del equipo (sobre todo lo de esta ronda):** seguridad-privacidad APRUEBA CON RESERVAS; verificador APRUEBA
CON RESERVAS (5 escenarios × todas las pestañas × 390/1280 × claro/oscuro, y la web exportada con y sin importes:
0 desbordes, 0 errores, 0 violaciones de CSP). Reservas de seguridad resueltas: valor de umbral sin escapar en el
formulario (`editor.js`), `NaN` aceptado por `numero()`/`guarda_alertas` (ahora se rechaza todo no finito), `irEt` sin
`esc()`, y `ingresos` ya no viaja en la web exportada ni con importes. Reserva del verificador sobre los 7
atributos `style` nuevos: resuelta con `estilos.js` (ver arriba). No comprobado por el
verificador: cotejo cifra a cifra con `/datos.js`, solapes de texto, 1920 px, rama con precios actualizados.

- **V3 (parte accesibilidad) hecha:** todo SVG de `graficos.js` lleva `role="img"` y `aria-label` con título y
  resumen (rango de fechas, series, último valor; en reparto, solo porcentajes). Funciones puras con test
  (`tests/graficos.test.js`) y comprobación estática (`tests/test_graficos_accesibles.py`).
- Comprobado en la app real con la cartera de demo: 0 SVG sin etiqueta y 0 errores de consola en las pestañas con gráficos.
- Falta de V3: paleta de 2 tonos y etiquetas directas al final de cada serie.
- **S1 y S2 hechos** (`alertas.js`): la cuota y «hace N días» se miden contra hoy en la app real y contra la fecha
  de la valoración en la web exportada; sin ninguna fecha ya no sale «NaN días» (el texto omite el dato). Tests nuevos.
- **Q8 hecho (pantalla):** tarjeta «Ingresos por dividendos» al principio de la pestaña Fiscalidad: cobrado en 12 meses,
  yield on cost y sobre valor, barras de los últimos 12 meses, tabla por producto y por año. Si `datos.ingresos` es
  null, o en la web exportada / sin importes, no se pinta (el servidor no la envía sin importes). Comprobada en la app
  real con dividendos añadidos a una copia temporal de la demo: 1280 y 390 px sin desbordes ni errores de consola.
- **S3, S4, S5 hechos:** (S3) la ✕ de un aviso sin más botones se queda arriba a la derecha a 390 px; (S4) el medidor
  de LTV recupera las zonas con marcas discretas (atención / riesgo alto, espejo de `nivel_riesgo`, `Alertas.zonasLtv`)
  y una leyenda en texto, sin degradado; (S5) el pie ya no repite «no se garantiza la exactitud» (solo el aviso legal).
  Comprobado en la app real con un préstamo de prueba en una copia temporal de la demo: 390/1280, claro/oscuro, sin
  desbordes ni errores. Un primer intento chocaba con la clase `.zona` ya existente (se renombró a `.zonaLtv`).
- **Q7 hecho:** `Content-Security-Policy` en todas las respuestas del servidor: `default-src 'none'; script-src 'self';
  style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; base-uri 'none';
  form-action 'self'; frame-ancestors 'none'`. El cargador de scripts pasó de `<script>` en línea a `cargador.js`; el
  exportador lo sustituye igual. Comprobado en la app real: 9 pestañas, 0 errores y 0 `securitypolicyviolation`.
  Matiz: `style-src` conserva `'unsafe-inline'` porque la interfaz genera atributos `style`; no ejecutan código, pero
  (ya migrado a `data-st`, ver el comienzo de esta ronda). La web exportada (un solo `.html` abierto como archivo)
  no puede llevar cabeceras y no cambia.
- **Q10 hecho (medido):** cartera sintética de 8 productos × 721 días: `datos.js` = 158 KB (productos 79 KB, resumen mensual
  26 KB); descarga 24 ms; carga hasta pintado 185–396 ms; pestañas 31–46 ms. El tamaño de los datos no es un cuello de
  botella en local, así que no se recorta el formato. Único valor atípico: Planificación, 216 ms por la simulación Monte
  Carlo, que se repetía al volver a la pestaña. Ahora es determinista y se memoiza (`Montecarlo.simulaMemo`): 31 ms al volver.
- **Q4 hecho:** `docs/GLOSARIO.md` (producto, bruto, deuda, neto, activos, aportado/prestado, plusvalía, rentabilidad vs
  rendimiento, garantía, LTV). La interfaz usa «producto» donde decía «posición» (búsqueda, total, peso, columna);
  «Posiciones» queda como nombre de pestaña. Test que impide reintroducirlo. README enlaza al glosario.
- **Q5 hecho:** siete errores de importación y cuatro del servidor ahora dicen qué hacer (rellenar columna, formato de
  número, descargar sin editar, cambiar fuente de precio, pulsar «Previsualizar»). `tests/test_mensajes_importacion.py`.
- **Q9 hecho:** cartera v3 con `alertas.umbrales` (migración que solo añade, idempotente; `app/umbrales.py`):
  concentración por producto (15 %) y por valor dentro de los fondos (5 %), desvío de la asignación (5 pp) y niveles de
  atención/riesgo alto del préstamo (75 % / 90 % del límite). Validación en `almacen.guarda_alertas`; `nivel_riesgo` y
  las zonas del medidor los usan (por defecto, idénticos a antes); nueva alerta «desvío de la asignación» en el Resumen.
  Formulario en Datos → Alertas. Comprobado en la app real: guardar, recargar, alerta y texto «más del 1 %», y error de
  validación visible. Sin préstamo sin límite: los umbrales genéricos 70/85 % no son configurables (decisión de alcance).
  `test_fase3` ahora compara con `VERSION_ACTUAL` (el cambio de versión es el esperado).
- **V3 completada:** etiquetas directas al final de cada serie en las áreas apiladas y en las líneas múltiples
  (comparador, Monte Carlo): nombre corto, marca de color y reparto de alturas para que no se pisen
  (`separaEtiquetas`, `nombreCorto`, con test). Por debajo de 560 px no se pintan y manda la leyenda. La paleta ya tenía
  dos tonos por tema desde V1 y la cuadrícula existía. (La tabla alternativa se hizo después; ver arriba.)
- **V4 hecho (parcial):** en el Resumen, los seis KPI secundarios (aportado, plusvalía, TIR, ritmo, racha, peor caída)
  pasan bajo el gráfico y los filtros de producto bajan debajo de él como leyenda; las tres preguntas (cuánto tengo,
  cómo voy, qué miro) terminan a 576 px a 1280×800 y el gráfico empieza a 658 px (antes, a más de 1000 px). No cabe
  el gráfico entero sin scroll: el criterio «sin scroll» se cumple para las tres preguntas, no para el gráfico.
  Estados vacíos con rosa de los vientos (Este mes, Ingresos, Fiscalidad). Sin desbordes a 390 y 1280, claro y oscuro,
  sin errores de consola; ninguna cifra cambia.
- **V5 hecho:** `tests/test_contraste.py` (118 pares de tokens en ambos temas, todos ≥ mínimo WCAG; peor texto 4,64:1,
  peor gráfico 4,23:1) y comprobación del texto renderizado en las 9 pestañas (`docs/auto/contraste_vivo.js`).
  Un fallo real corregido: filtros apagados con opacidad 0,42 (1,85:1). Informe en `docs/auto/contraste.md`.
  No se regeneraron capturas de referencia a 390/768/1920.
- Estado: 157 tests de Python y 5 archivos de Node en verde.

## Ronda 3 (14/10/2026, parcial: la sesión se reinició)

- **Q6 hecho:** el navegador ya no habla con CoinGecko ni Binance: `/api/vivo` lo consulta el servidor, con
  caché de 30 s; la web exportada no consulta nada.
- **Q8 (cálculo):** `ingresos` (por mes, por año, yield on cost y actual); no viaja en la web «sin importes».
- **V3 (gráficos) se perdió** con el reinicio; vuelve al tablero.
- Estado: 113 tests de Python y 4 archivos de Node en verde.

## Ronda 2 (13/10/2026)

- **Q1 hecho:** la decisión de qué alertas salen y cuándo vive en `app/web/alertas.js` (puro, con tests);
  sin duplicados entre Resumen, «Este mes» y pie; alertas descartables; nada de acciones en la web exportada.
- **Q3 hecho:** KPI «Aportado» y comparador muestran «de tu bolsillo» frente a «prestado».
- **V2 hecho:** componentes de la «Carta de navegación» (hoja, KPI en rúbrica, alertas al margen, tablas con
  filetes, badges, navegación).
- Revisión: seguridad APRUEBA; verificador APRUEBA CON RESERVAS (S1–S5 en el tablero).
- Estado: 94 tests de Python y 4 archivos de Node en verde.

## Ronda 1 (13/10/2026, lanzada a mano por el usuario)

- **Q2 hecho:** el mercado ya no incluye la amortización del préstamo (`amortizacionPrestamo` por mes y por
  producto; solo la deuda, no el efectivo recibido). «Mes a mes» enseña la tarjeta «Deuda amortizada» y la columna.
- **Q3 (parte de cálculo):** `total.dineroPrestado` y `total.capitalPropio`. Falta mostrarlas en KPI/comparador.
- **V1 hecho:** `tema-carta.css` (tokens, serif editorial, filetes, sin degradados; contraste AA calculado).
  Nota: los valores del tema claro se oscurecieron respecto a `DIRECCION_VISUAL.md` para cumplir AA.
- **Seguridad (veto resuelto):** las cifras nuevas (`capitalPropio`, `dineroPrestado`, `amortizacionPrestamo`,
  `deudaPignoraciones`) se escalan en la web «sin importes»; test.
- **Verificador (reserva resuelta):** el efectivo derivado ya no cuenta como amortización; test.
- Estado: 94 tests de Python y 3 de Node en verde.

## Preparación (13/10/2026)

- Se define la dirección visual (`docs/DIRECCION_VISUAL.md`), el protocolo (`docs/auto/PROTOCOLO.md`),
  el tablero y los agentes (`.claude/agents/`).
- CI de GitHub añadido (`.github/workflows/ci.yml`): tests de Python y de Node, y construcción de la imagen.
- Estado de partida: 83 tests de Python y 4 archivos de pruebas de Node pasan en la rama `fase3`.

### Hecho el 13/10/2026

- `main` contiene ya el rediseño y la Fase 3 (PR #2 y #4). La rama `auto/mejora-continua` está al día con `main`.
- Aprobado por el usuario: encadenar hasta 10 ejecuciones (antes 6) y fusionar los PR.

### Decisiones pendientes del usuario

- Indicar el LTV máximo del contrato para medir el margen real del préstamo.
