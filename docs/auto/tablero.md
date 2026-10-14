# Tablero

Estados: `pendiente` · `en curso` · `en revisión` · `hecho` · `bloqueado` · `decisión del usuario`.
Prioridad: A (ahora) · B (después) · C (cuando sobre tiempo). Mantiene el orquestador.

## Producto y calidad (lo ya hecho y planeado, a revisar)

| ID | Tarjeta | Prio | Estado | Dueño | Criterio de aceptación |
|---|---|---|---|---|---|
| Q1 | Revisar todas las alertas y avisos: cuándo salen, texto, descartar, duplicados | A | hecho | verificador + disenador-ui | Cada alerta tiene regla documentada y test o comprobación; ningún aviso repetido entre Resumen, pie y «Este mes» |
| Q2 | Mes a mes: separar la deuda de los componentes y no contar amortización como «mercado» (C6) | A | hecho | ingeniero-calculo | `resumen_mensual` no atribuye al mercado la bajada de deuda; test |
| Q3 | «Aportado»: distinguir capital propio de dinero prestado (C5) en KPI y comparador | A | hecho | ingeniero-calculo | Dos cifras con definición visible; test con préstamo invertido |
| Q4 | Revisar coherencia de textos: glosario (posición/producto, activos/neto, plusvalía) | B | hecho | redactor | Un solo término por concepto en UI y README |
| Q5 | Mensajes de importación (MyInvestor, plantilla, IA): claridad y errores | B | hecho | redactor + verificador | Cada error dice qué hacer |
| Q6 | Bitcoin en vivo desde el servidor (`/api/vivo`), no desde el navegador | B | hecho | ingeniero-calculo | El navegador no llama a terceros; test |
| Q7 | CSP estricta sin scripts en línea | B | hecho | disenador-ui + seguridad-privacidad | `Content-Security-Policy` activa, 0 violaciones en consola |
| Q8 | Dividendos e ingresos: pantalla y cálculo (yield on cost) | C | hecho (cálculo + tarjeta «Ingresos por dividendos» en Fiscalidad; no viaja en la web exportada) | ingeniero-calculo + disenador-ui | Ingresos por mes/año con tests |
| Q9 | Alertas configurables (umbral de concentración, LTV, desviación de asignación) | C | hecho | disenador-ui | Umbrales guardados en la cartera con migración v3 |
| Q10 | Rendimiento de `datos.js` (tamaño) y repintados | C | hecho | ingeniero-calculo | Medido antes/después |

## Interfaz: dirección «Carta de navegación» (ver `docs/DIRECCION_VISUAL.md`)

| ID | Tarjeta | Prio | Estado | Dueño | Criterio de aceptación |
|---|---|---|---|---|---|
| V1 | Fase 1: tokens y tipografía (claro/oscuro) en `tema-carta.css` | A | hecho | disenador-ui | Contraste AA; sin cambios de HTML; tests verdes |
| V2 | Fase 2: componentes (hoja, rúbrica, KPI, alertas al margen, tablas, badges) | A | hecho | disenador-ui | Capturas 390/1280 en ambos temas sin desbordes |
| V3 | Fase 3: gráficos (paleta 2 tonos, cuadrícula, etiquetas directas, tabla alternativa) | B | en curso (hecho: `aria-label` en los 10 SVG, con test; falta paleta de 2 tonos y etiquetas directas) | disenador-ui | `aria-label` en todos los SVG |
| V4 | Fase 4: composición del Resumen y estados vacíos con rosa de los vientos | B | pendiente | disenador-ui | Las 3 preguntas se responden sin scroll a 1280×800 |
| V5 | Fase 5: auditoría de contraste y capturas de referencia | B | pendiente | verificador | Informe de contraste sin fallos |

## Proceso

| ID | Tarjeta | Prio | Estado | Dueño | Criterio de aceptación |
|---|---|---|---|---|---|
| P1 | CI en GitHub (tests + build Docker) | A | hecho | orquestador | Flujo verde en `auto/mejora-continua` |
| P2 | Ejecución desatendida programada a las 04:21 | A | en revisión | orquestador | Tarea creada y listada |

## Seguimiento (reservas no bloqueantes de las revisiones)

| ID | Tarjeta | Prio | Estado | Dueño | Criterio de aceptación |
|---|---|---|---|---|---|
| S1 | `alertas.js`: tratar `fechaExtracto` ausente (hoy daría «hace NaN días») | C | hecho | disenador-ui | Test con campo ausente |
| S2 | La cuota se mide contra la fecha de valoración; usar la fecha real de hoy para avisar 7 días antes | B | hecho | disenador-ui | Test con valoración antigua |
| S3 | Alerta de cuota a 390 px: la ✕ queda sola en una línea | C | hecho | disenador-ui | Captura sin hueco |
| S4 | Medidor de LTV sin bandas de zona (sin degradado): recuperar zonas con marcas discretas | B | hecho | disenador-ui | Zonas legibles en ambos temas |
| S5 | Pie repite en parte el aviso legal («no se garantiza la exactitud») | C | hecho | redactor | Una sola mención |

## Nube

| ID | Tarjeta | Prio | Estado | Dueño | Criterio de aceptación |
|---|---|---|---|---|---|
| N1 | Acceso con clave y sesión segura para despliegue en la nube | A | en curso | ingeniero-calculo + seguridad-privacidad | Sin clave no se sirve nada salvo `/login`; tests |
| N2 | Despliegue en GitHub Codespaces (privado) y guía para Fly.io/Render | A | en curso | orquestador | Arranca con un clic; datos fuera de git |
