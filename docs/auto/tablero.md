# Tablero

Estados: `pendiente` · `en curso` · `en revisión` · `hecho` · `bloqueado` · `decisión del usuario`.
Prioridad: A (ahora) · B (después) · C (cuando sobre tiempo). Mantiene el orquestador.

## Producto y calidad (lo ya hecho y planeado, a revisar)

| ID | Tarjeta | Prio | Estado | Dueño | Criterio de aceptación |
|---|---|---|---|---|---|
| Q1 | Revisar todas las alertas y avisos: cuándo salen, texto, descartar, duplicados | A | pendiente | verificador + disenador-ui | Cada alerta tiene regla documentada y test o comprobación; ningún aviso repetido entre Resumen, pie y «Este mes» |
| Q2 | Mes a mes: separar la deuda de los componentes y no contar amortización como «mercado» (C6) | A | pendiente | ingeniero-calculo | `resumen_mensual` no atribuye al mercado la bajada de deuda; test |
| Q3 | «Aportado»: distinguir capital propio de dinero prestado (C5) en KPI y comparador | A | pendiente | ingeniero-calculo | Dos cifras con definición visible; test con préstamo invertido |
| Q4 | Revisar coherencia de textos: glosario (posición/producto, activos/neto, plusvalía) | B | pendiente | redactor | Un solo término por concepto en UI y README |
| Q5 | Mensajes de importación (MyInvestor, plantilla, IA): claridad y errores | B | pendiente | redactor + verificador | Cada error dice qué hacer |
| Q6 | Bitcoin en vivo desde el servidor (`/api/vivo`), no desde el navegador | B | pendiente | ingeniero-calculo | El navegador no llama a terceros; test |
| Q7 | CSP estricta sin scripts en línea | B | pendiente | disenador-ui + seguridad-privacidad | `Content-Security-Policy` activa, 0 violaciones en consola |
| Q8 | Dividendos e ingresos: pantalla y cálculo (yield on cost) | C | pendiente | ingeniero-calculo + disenador-ui | Ingresos por mes/año con tests |
| Q9 | Alertas configurables (umbral de concentración, LTV, desviación de asignación) | C | pendiente | disenador-ui | Umbrales guardados en la cartera con migración v3 |
| Q10 | Rendimiento de `datos.js` (tamaño) y repintados | C | pendiente | ingeniero-calculo | Medido antes/después |

## Interfaz: dirección «Carta de navegación» (ver `docs/DIRECCION_VISUAL.md`)

| ID | Tarjeta | Prio | Estado | Dueño | Criterio de aceptación |
|---|---|---|---|---|---|
| V1 | Fase 1: tokens y tipografía (claro/oscuro) en `tema-carta.css` | A | pendiente | disenador-ui | Contraste AA; sin cambios de HTML; tests verdes |
| V2 | Fase 2: componentes (hoja, rúbrica, KPI, alertas al margen, tablas, badges) | A | pendiente | disenador-ui | Capturas 390/1280 en ambos temas sin desbordes |
| V3 | Fase 3: gráficos (paleta 2 tonos, cuadrícula, etiquetas directas, tabla alternativa) | B | pendiente | disenador-ui | `aria-label` en todos los SVG |
| V4 | Fase 4: composición del Resumen y estados vacíos con rosa de los vientos | B | pendiente | disenador-ui | Las 3 preguntas se responden sin scroll a 1280×800 |
| V5 | Fase 5: auditoría de contraste y capturas de referencia | B | pendiente | verificador | Informe de contraste sin fallos |

## Proceso

| ID | Tarjeta | Prio | Estado | Dueño | Criterio de aceptación |
|---|---|---|---|---|---|
| P1 | CI en GitHub (tests + build Docker) | A | en revisión | orquestador | Flujo verde en `auto/mejora-continua` |
| P2 | Ejecución desatendida programada a las 04:21 | A | en revisión | orquestador | Tarea creada y listada |
