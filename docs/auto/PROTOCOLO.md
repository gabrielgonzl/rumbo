# Protocolo de trabajo autónomo (agentes que negocian)

Este documento es lo primero que lee cada ejecución automática. Es la fuente de verdad del proceso.

## Equipo

| Agente (`.claude/agents/`) | Modelo | Rol | Puede |
|---|---|---|---|
| `orquestador` | opus | Lee el tablero, decide qué se hace y en qué orden, arbitra, cierra rondas, escribe el informe | Editar `docs/auto/*`; lanzar a los demás. No toca código de producto |
| `disenador-ui` | sonnet | Implementa la dirección visual (`docs/DIRECCION_VISUAL.md`) y propone mejoras de interfaz | Editar `app/web/*` |
| `ingeniero-calculo` | sonnet | Correctitud de cifras (`motor.py`, `fiscal.py`, `pignoracion.py`, importadores) y sus tests | Editar `app/*.py`, `tests/*` |
| `verificador` | sonnet | Adversario: ejecuta tests, comprueba la app real, busca regresiones y desbordes | Solo lectura + ejecutar; **puede vetar** |
| `seguridad-privacidad` | opus | Revisa cada diff: datos personales, XSS, control de origen, exportación | Solo lectura; **puede vetar** |
| `redactor` | haiku | README, ayuda, informe y mensajes de commit a partir de hechos ya verificados | Editar documentación |

## Reglas que no se negocian

1. **Rama:** todo el trabajo va en `auto/mejora-continua` (creada desde `fase3`). Nunca `main`, nunca
   fusionar PR, nunca `--force`.
2. **Datos del usuario:** no se lee ni se modifica la carpeta de datos real del usuario (`RUMBO_DATOS` en `.env`, o `mis_datos`).
   Las pruebas usan carpetas temporales (`PATRIMONIO_DATOS`) y `demo/cartera.json`.
3. **Privacidad antes de cada commit:** `seguridad-privacidad` revisa el diff. Nada de nombres,
   cuentas, importes reales, rutas personales o correos. Si duda, no se commitea.
4. **Verde o nada:** `python -m unittest discover -s tests` y los `node tests/*.test.js` pasan antes de
   commitear. Un cambio que rompa tests se revierte, no se «arregla» tocando el test.
5. **Sin dependencias nuevas en tiempo de ejecución** ni recursos externos (CDN, fuentes web).
6. **La exportación estática** (`exportar.pagina`) debe seguir funcionando; hay test.
7. **Una cifra no cambia por estilo.** Si un cambio visual altera un número, es un fallo.
8. **Commits pequeños** y con el trailer `Co-Authored-By` que indique el entorno.
9. **Push** solo a `auto/mejora-continua`, y solo si las reglas 3 y 4 se cumplen.

## Ronda (el bucle)

```
1. SALUD   orquestador ejecuta tests y lee docs/auto/tablero.md + informe.md
2. ELEGIR  como mucho 3 tarjetas; prioridad = impacto × (1/esfuerzo); respeta dependencias
3. PROPONER  cada especialista asignado escribe docs/auto/propuestas/NNN-titulo.md
             (contexto · cambio · riesgos · criterios de aceptación medibles)
4. OBJETAR   verificador y seguridad-privacidad añaden «## Objeciones» (máx. 2 rondas de réplica)
5. DECIDIR   orquestador: aceptar / ajustar / rechazar. Empate o riesgo alto → opción conservadora y
             la tarjeta pasa a «decisión del usuario»
6. HACER     el especialista implementa en la rama, con tests
7. VERIFICAR verificador: tests + app real (ver «Verificación») + diff. Seguridad: diff
8. CERRAR    commit (+ push si procede), actualizar tablero e informe, volver al paso 1
```

## Verificación sin Docker

Docker puede no estar disponible. Para comprobar la app real:

```bash
PATRIMONIO_DATOS=<carpeta temporal con demo> PATRIMONIO_NO_ABRIR=1 PATRIMONIO_PUERTO=8791 \
  PATRIMONIO_REFRESCO_HORAS=0 python -m app
```

Luego, con el navegador integrado (herramientas `mcp__Claude_Browser__*`) o `curl`: abrir
`http://127.0.0.1:8791/`, recorrer las pestañas, comprobar que no hay desbordes horizontales
(`document.documentElement.scrollWidth <= innerWidth`) ni errores de consola. Parar el servidor al
terminar. En GitHub, el flujo `.github/workflows/ci.yml` ejecuta los tests y construye la imagen.

## Cuándo parar

- Tablero sin tarjetas «pendiente» de prioridad alta o media.
- Dos rondas seguidas sin mejora verificable.
- Tests rotos que no se pueden arreglar con seguridad → revertir y documentar.
- Recursos de la sesión casi agotados → cerrar la ronda en curso, escribir `informe.md` y parar.

## Encadenar ejecuciones

Al terminar, si el tablero tiene trabajo pendiente y `docs/auto/estado.json` indica menos de 6
ejecuciones seguidas, el orquestador programa la siguiente (tarea única unas 5 h 10 min después)
con `mcp__scheduled-tasks__create_scheduled_task` y el mismo prompt. Incrementa `ejecuciones`.
Si no puede programarla, lo deja escrito en el informe.

## Informe

`docs/auto/informe.md`: por ejecución, qué se hizo, evidencia (tests, comprobaciones), qué queda y
**decisiones que necesitan al usuario**. Sin datos personales.
