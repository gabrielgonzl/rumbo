# Informe de ejecuciones automáticas

> Lo mantiene el orquestador. Sin datos personales. Lo más reciente, arriba.

## Preparación (13/10/2026)

- Se define la dirección visual (`docs/DIRECCION_VISUAL.md`), el protocolo (`docs/auto/PROTOCOLO.md`),
  el tablero y los agentes (`.claude/agents/`).
- CI de GitHub añadido (`.github/workflows/ci.yml`): tests de Python y de Node, y construcción de la imagen.
- Estado de partida: 83 tests de Python y 4 archivos de pruebas de Node pasan en la rama `fase3`.

### Decisiones pendientes del usuario

- Fusionar los PR #2 y #3 en `main` (no lo hace la automatización).
- Indicar el LTV máximo del contrato para medir el margen real del préstamo.
- Si quiere que las ejecuciones desatendidas sigan encadenándose más de 6 veces.
