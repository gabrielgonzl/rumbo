# Auditoría de contraste (V5)

Generada con `python tests/test_contraste.py` sobre `app/web/tema-carta.css` (WCAG 2.1: texto ≥ 4,5:1; gráficos y bordes de campo ≥ 3:1).

**118 de 118 pares cumplen.**

## Tema claro

| Grupo | Mínimo ratio | Peor par |
|---|---|---|
| texto | 4.75 (mín. 4.5) | `tinta3` sobre `sup3` |
| gráfico | 4.23 (mín. 3.0) | `s12` sobre `plano` |
| borde de campo | 3.71 (mín. 3.0) | `campo` sobre `plano` |
| texto sobre acento | 6.60 (mín. 4.5) | `sobre-acento` sobre `mar` |

## Tema oscuro

| Grupo | Mínimo ratio | Peor par |
|---|---|---|
| texto | 4.64 (mín. 4.5) | `tinta3` sobre `sup3` |
| gráfico | 5.58 (mín. 3.0) | `s8` sobre `sup` |
| borde de campo | 3.90 (mín. 3.0) | `campo` sobre `sup` |
| texto sobre acento | 7.37 (mín. 4.5) | `sobre-acento` sobre `mar` |

## Comprobación en la app real (texto renderizado)

Script: `docs/auto/contraste_vivo.js` (Playwright; recorre las 9 pestañas en ambos temas con la cartera de demo, mezcla
color, opacidad y fondos reales y compara con 4,5:1, o 3:1 en texto grande).

- **Hallazgo corregido:** los filtros apagados (`aria-pressed="false"`) bajaban la opacidad a 0,42 → «Solo largo plazo»
  llegaba a 1,85:1 (claro) y 2,19:1 (oscuro). Ahora usan tinta apagada (`--tinta3` / `--tinta2`), tachado y marca hueca,
  sin opacidad (`tema-carta.css`). El significado ya no depende solo del color.
- **Excepción:** el botón «›» de Mes a mes cuando está `disabled` (2,72:1 claro / 3,69:1 oscuro): los componentes
  inactivos están exentos en WCAG 1.4.3.
- Resultado tras el arreglo: 0 fallos en texto activo, 9 pestañas × 2 temas.
- No cubre: texto sobre imágenes (no hay), estados `:hover`/`:focus` ni las capturas de referencia a 390/768/1920 px.
