# Informe de ejecuciones automáticas

> Lo mantiene el orquestador. Sin datos personales. Lo más reciente, arriba.

## Ronda 4 (sesión en la nube)

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
  quitarlo exigiría migrarlos a clases (queda como mejora). La web exportada (un solo `.html` abierto como archivo)
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
  dos tonos por tema desde V1 y la cuadrícula existía. **No hecho:** tabla alternativa de datos por gráfico.
- Estado: 142 tests de Python y 5 archivos de Node en verde.

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
