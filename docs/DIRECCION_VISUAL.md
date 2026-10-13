# Dirección visual · «Carta de navegación»

> Estado: propuesta aprobada para implementar por fases. Sin datos personales.
> Origen: estudio de producto (`docs/ESTUDIO_MEJORAS.md` en local), principios de *calm technology*
> (Calm Tech Institute: «requerir la mínima atención posible», «usar la periferia») y la práctica de
> visualización con tema oscuro (Datawrapper, guía de visualización de la UE: no invertir colores, sino
> adaptar la paleta; no depender solo del rojo/verde).

## Idea

El producto se llama **Rumbo**: es una carta de navegación para tu dinero. El diseño abandona el look
«SaaS oscuro con tarjetas redondeadas y degradados» y adopta el lenguaje de una **carta náutica y un
cuaderno de bitácora**: papel cálido, tinta, filetes finos, cifras en una serif editorial y
anotaciones al margen. Es poco habitual en finanzas, es legible y encaja con el nombre.

Tres reglas de producto mandan sobre las de estilo:

1. **Calma.** Una prioridad cada vez. El Resumen responde a «¿cuánto tengo?, ¿voy bien?, ¿hay algo
   que mirar?» sin gritar. Los avisos los controla el usuario (se descartan, vuelven si algo cambia).
2. **Honestidad.** Cada cifra dice qué es (activos o neto, rentabilidad o valor, estimado o dato).
   Nada de color de marca para ganar o perder: `+`/`−` y, en tablas, ▲▼ además del color.
3. **Local y sin dependencias.** Sin fuentes web ni CDN. Solo pila de sistema.

## Sistema

### Tipografía (pila de sistema, sin descargas)

| Uso | Pila | Notas |
|---|---|---|
| Cifras grandes y títulos de sección | `"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif` | Pesos 500–600. Números con `font-variant-numeric: lining-nums tabular-nums`. |
| Interfaz y tablas | `system-ui,"Segoe UI",sans-serif` | 14 px base. Cifras siempre tabulares. |
| Etiquetas y notas al margen | misma sans en versalitas (`font-variant-caps: all-small-caps`) con `letter-spacing:.08em` | Mínimo 12 px. |

Escala: 12 · 13 · 14 · 16 · 20 · 28 · 44–72 (cifra principal con `clamp`). Sin tamaños sueltos.

### Color (por tema; los contrastes son mínimos de diseño, AA o superior)

| Token | Papel (claro) | Noche (oscuro) | Uso |
|---|---|---|---|
| `--fondo` | `#f3eee1` | `#0d1822` | Lienzo |
| `--superficie` | `#faf7ee` | `#13222f` | Paneles |
| `--tinta` | `#14213d` | `#ece6d6` | Texto principal |
| `--tinta-2` | `#3b4a63` | `#b9c2c9` | Texto secundario (≥ 4,5:1) |
| `--tinta-3` | `#5d6b82` | `#93a1ad` | Notas (≥ 4,5:1) |
| `--filete` | `#cfc6ae` | `#27384a` | Líneas finas de 1 px |
| `--mar` | `#1f6f78` | `#5fb3b8` | Acento principal, enlaces, foco |
| `--latón` | `#8a6a1f` | `#d9b36c` | Acento cálido, objetivos y metas |
| `--señal` | `#b3402a` | `#ef8a6f` | Pérdida y peligro |
| `--sonar` | `#2f6e4f` | `#7bc89c` | Ganancia y correcto |
| `--aviso` | `#8a6200` | `#e3b341` | Atención |

Categorías de gráficos: 8 tintas de carta (mar, latón, señal, sonar, ciruela `#6d4c7d`, arena `#a89968`,
pizarra `#55657a`, coral `#c9715b`) con **dos tonos por tema**; el color identifica la *clase de activo*,
no el producto (el producto se identifica con etiqueta directa en la línea).

### Forma y detalle

- Radio pequeño (4–6 px) y **filetes de 1 px** en lugar de sombras. Sin degradados ni brillos.
- Tarjetas = «hojas»: fondo `--superficie`, filete superior un poco más marcado y una **rúbrica**
  (título en serif + línea fina), como un cuaderno.
- Gráficos: **cuadrícula tipo graticula** (líneas finas muy suaves), trazo de 1,5 px, **etiqueta
  directa al final de cada serie** en vez de leyenda, eventos (aportaciones, cuotas) como marcas al
  margen. Tooltip con filetes, sin sombra.
- Motivo recurrente y discreto: **rosa de los vientos** de 24 px en estados vacíos y en el progreso
  hacia la meta (el «rumbo» se lee como un indicador de ángulo además de la barra).
- Movimiento: ninguno decorativo; solo transiciones de 120 ms al cambiar de vista. Respeta
  `prefers-reduced-motion`.

### Composición del Resumen («página de bitácora»)

```
┌ rúbrica ───────────────────────────────────────────────────────────────┐
│ PATRIMONIO NETO · 12 oct 2026                       ✎ nota al margen    │
│ 29.144,08 €     (serif 64)                          · +6,3 % sobre lo  │
│ ───────────────────────────────────────────────     aportado           │
│ Bruto 34.644 € · Deuda −5.500 € · Neto 29.144 €     · TIR 8,2 %        │
├─────────────────────────────────────┬──────────────────────────────────┤
│ Evolución (activos | neto)          │ Al margen                        │
│  línea fina + etiquetas directas    │  ▸ Una sola cosa que mirar       │
│                                     │  ▸ Este mes                      │
└─────────────────────────────────────┴──────────────────────────────────┘
```

## Fases de implementación (cada una publicable)

1. **Tokens y tipografía** (`tema-carta.css` que sustituye a la capa de colores de `rediseno.css`):
   claro/oscuro, serif en cifras y títulos, filetes. Sin tocar HTML.
2. **Componentes**: tarjeta-hoja, KPI en rúbrica, alertas «al margen», tablas con filetes, badges.
3. **Gráficos**: paleta de dos tonos, cuadrícula, etiquetas directas, accesibilidad (resumen y tabla).
4. **Composición**: Resumen en dos columnas, rosa de los vientos, estados vacíos.
5. **Revisión**: contraste (axe-core o cálculo propio), capturas a 390/768/1280/1920 en ambos temas.

## Criterios de aceptación

- Contraste AA en todo texto; ningún significado solo con color.
- Sin peticiones externas; la web exportada sigue siendo un único `.html`.
- Los 80+ tests pasan; ninguna cifra cambia (solo presentación).
- A 390 px y 1920 px no hay desbordes horizontales.
- Dos temas completos; el tema sigue al sistema si no hay preferencia guardada.

## Qué NO hacer

Degradados morados, brillos «neon», tarjetas con sombra grande, iconografía de moneda decorativa,
gráficos de tarta, animaciones en cifras, esqueletos de carga sobre importes.
