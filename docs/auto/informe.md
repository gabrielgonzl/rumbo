# Informe de ejecuciones automáticas

> Lo mantiene el orquestador. Sin datos personales. Lo más reciente, arriba.

## Ronda 4 (sesión en la nube)

- **V3 (parte accesibilidad) hecha:** todo SVG de `graficos.js` lleva `role="img"` y `aria-label` con título y
  resumen (rango de fechas, series, último valor; en reparto, solo porcentajes). Funciones puras con test
  (`tests/graficos.test.js`) y comprobación estática (`tests/test_graficos_accesibles.py`).
- Comprobado en la app real con la cartera de demo: 0 SVG sin etiqueta y 0 errores de consola en las pestañas con gráficos.
- Falta de V3: paleta de 2 tonos y etiquetas directas al final de cada serie.
- Estado: 115 tests de Python y 5 archivos de Node en verde.

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
