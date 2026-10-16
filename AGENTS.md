# AGENTS.md · Reparto de trabajo entre modelos

Este archivo dice **quién hace qué** cuando se trabaja en este repositorio con
agentes. La idea: el modelo más caro solo piensa donde pensar importa; el
intermedio ejecuta y revisa; el más barato redacta.

| Rol | Modelo | Qué hace | Qué NO hace |
|---|---|---|---|
| **Razonador** | `opus` | Análisis de amenazas, decisiones de diseño, diagnóstico de bugs difíciles, revisión final de seguridad. Devuelve un plan o un veredicto, no código masivo. | Escribir documentación ni tareas mecánicas. |
| **Operario / revisor** | `sonnet` | Implementa los cambios acordados (código, Dockerfile, tests), ejecuta comandos, revisa diffs y verifica antes de dar nada por hecho. | Decidir arquitectura sin plan previo; redactar textos largos. |
| **Redactor** | `haiku` | README, notas de despliegue, mensajes de commit, comentarios y textos de interfaz, siempre a partir de hechos ya verificados. | Tocar lógica, seguridad o configuración. |

## Flujo

1. `opus` razona el problema y deja un plan corto (qué cambiar y por qué).
2. `sonnet` implementa, prueba y revisa el diff contra el plan.
3. `opus` revisa solo los cambios de seguridad (diff, no repo entero).
4. `haiku` redacta la documentación con los hechos ya comprobados.
5. `sonnet` ejecuta la verificación final (ver «Definición de hecho»).

Regla de oro: **si dudas entre dos modelos, usa el más barato que pueda hacerlo
bien**; sube de nivel solo si el resultado falla.

## Skills autorizadas

Las que se proponen para este proyecto (solo se invocan cuando aplican):

- `superpowers:systematic-debugging` · ante cualquier fallo o test que no pasa.
- `superpowers:test-driven-development` · cambios en el servidor y su seguridad.
- `superpowers:verification-before-completion` · antes de decir «hecho».
- `superpowers:requesting-code-review` · antes de integrar un cambio.
- `security-review` · revisión de seguridad del diff pendiente.
- `code-review` · revisión general del diff.
- `simplify` · limpieza tras implementar.
- `engram:engram-memory` · guardar decisiones y hallazgos entre sesiones.

## Reglas del proyecto

- **Los datos del usuario no salen de `mis_datos/`** y nunca se suben a git.
- La app es de un solo usuario: escucha solo en loopback (en Docker, publicada
  únicamente en `127.0.0.1` del anfitrión).
- Toda ruta debe rechazar peticiones de otros orígenes (ver `app/servidor.py`,
  función `controla_origen`). Rutas nuevas heredan esa protección sin tocar nada.
- Nada de credenciales, claves o datos personales en el repo ni en la imagen.
- Los commits y los `push` los autoriza el usuario. Excepción documentada: el trabajo autónomo
  (`docs/auto/PROTOCOLO.md`) puede commitear y empujar **solo** a la rama `auto/mejora-continua`,
  nunca a `main` ni fusionar PR.

## Definición de hecho

- Los tests de seguridad pasan (`python -m unittest discover -s tests`).
- La imagen Docker construye y el contenedor queda `healthy`.
- Una petición con `Sec-Fetch-Site: cross-site` a `/datos.js` devuelve 403.
- La app carga en `http://127.0.0.1:8765/` con el panel visible.

## Trabajo autónomo

Hay un equipo de agentes que mejora el proyecto de forma iterativa y negociada, descrito en
`docs/auto/PROTOCOLO.md`: `orquestador` (opus), `disenador-ui`, `ingeniero-calculo`, `verificador`,
`seguridad-privacidad` y `redactor` (definidos en `.claude/agents/`). El estado vive en
`docs/auto/tablero.md` e `informe.md`; la dirección visual, en `docs/DIRECCION_VISUAL.md`.

- Rama de trabajo: `auto/mejora-continua`. Nunca `main`.
- Sin Docker: se verifica con `python -m app` y carpetas temporales; en GitHub, `ci.yml`.
- Veto: `verificador` y `seguridad-privacidad` pueden vetar; un solo dato personal en el diff es veto.
