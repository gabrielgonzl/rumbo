# Carteras de fondos (diseño)

Estado: pendiente de visto bueno del usuario. Rama de trabajo: `auto/mejora-continua`.

## Por qué

Algunas entidades ofrecen **carteras indexadas gestionadas**: el cliente contrata y aporta a la cartera y un gestor reparte
y reequilibra el dinero entre varios fondos. En Rumbo esos fondos aparecen como productos sueltos (compras por ISIN
importadas) y la app no sabe que forman una cartera. Consecuencias:

- La cartera no se ve como una sola cosa en Posiciones.
- Un préstamo con garantía apunta a fondos sueltos y su LTV máximo se escribe a mano; no hay modo de decir «la garantía es
  esta cartera».

Petición del usuario: que las carteras de fondos sean un concepto propio de la app y que un préstamo pueda tener una
cartera como garantía. Además, **un LTV puede cubrir varios fondos o carteras distintos**: el límite lo fija el contrato del
préstamo sobre el conjunto de la garantía.

Contexto general (fuentes públicas, sin confirmar contra ningún contrato): las carteras indexadas perfiladas suelen reequilibrarse
solas con un umbral de desviación; algunas entidades admiten pignorar carteras enteras y una selección de fondos; no existe un
LTV máximo universal (notas de prensa antiguas hablan de ratios del 50 %). **El LTV real lo da el contrato de cada préstamo.**

## Alcance de esta versión

Entra:
1. Carteras como entidad propia (nombre, entidad, LTV máximo opcional) y fondos asignados a una cartera.
2. Vista de una línea plegable por cartera en Posiciones.
3. Pignoración con carteras enteras y/o fondos sueltos como garantía, con la regla del LTV de abajo.

No entra (fases posteriores):
- Que el rebalanceo interno no cuente como venta en Fiscalidad (hoy lo vería como ventas y compras y calcularía ganancias
  inexistentes; ya figura entre los límites de la pantalla de Fiscalidad).
- Aportado y rentabilidad reales por cartera (en la línea de la cartera se suman las cifras de sus fondos; no se recalcula nada).
- Carteras anidadas o un fondo en varias carteras a la vez.

## Datos (cartera v4)

- `cfg["carteras"] = [{"id": "c1", "nombre": "Cartera Ejemplo", "entidad": "Entidad Ejemplo", "ltvMax": 50}]`. `ltvMax` es opcional
  (% , 0 < x ≤ 100). Los ids salen de `almacen.siguiente_id(lista, "c")`.
- `producto["carteraId"]`: opcional. Ausente o vacío = producto suelto.
- `pignoracion["carteraIds"]`: lista opcional de ids de cartera; convive con `pignoracion["activos"]` (fondos sueltos).
- **Migración v3 → v4** (`almacen.migra`): solo añade `carteras: []`. No toca nada más, es idempotente y se aplica en memoria
  al cargar (se escribe, con copia automática previa, al guardar). `VERSION_ACTUAL = 4`.
- **Validación** (`almacen.guarda_cartera`): nombre obligatorio, ≤ 80 caracteres, sin repetir (sin distinguir mayúsculas);
  entidad ≤ 80; `ltvMax` numérico finito en (0, 100]. Asignar un fondo a una cartera lo saca de la que tuviera.
- **Borrar** una cartera: sus fondos quedan sueltos (`carteraId` eliminado) y se quita de `carteraIds` de los préstamos. Si un
  préstamo se quedara sin ninguna garantía, se rechaza el borrado con un mensaje que dice qué préstamo la usa y qué hacer.
- Un `carteraId` que no existe (copia ajena, borrado a mano) se ignora al leer y se limpia al guardar.
- `almacen.sanea_copia` ya limpia `<`/`>` en todos los textos; el nuevo código no necesita más para las carteras y se añade
  un test con nombres de cartera hostiles.
- API: `POST /api/carteras` (crear/editar) y `DELETE /api/carteras/<id>`, por los mismos registros `GUARDAR`/`BORRAR`
  (heredan el control de origen).
- `motor` publica `carteras` en `datos.js`; cada producto publicado lleva `carteraId`. Sin importes nuevos, así que la web
  exportada lleva nombres, entidad y LTV (un porcentaje, no un importe) y nada más.

## Pignoración y LTV

- **Garantía efectiva** = `activos` (sueltos) ∪ fondos de las carteras de `carteraIds`, sin duplicados. Se calcula al leer
  (`pignoracion.activos_efectivos(cfg, p)`), de modo que un fondo añadido después a la cartera pasa a ser garantía y queda
  bloqueado como el resto.
- Usan la garantía efectiva: valor de la garantía, `activosDetalle`, `marcas()` (insignia 🔒), `bloquea_venta()`, y por tanto el
  margen, el estrés y las zonas del medidor. La deuda, el cuadro de amortización y los intereses no cambian.
- **Regla del LTV máximo efectivo** (`pignoracion.ltv_efectivo(cfg, p)`):
  1. Si el préstamo tiene `ltvMax` escrito, manda ese.
  2. Si no, y la garantía son **solo carteras** y todas tienen `ltvMax` con el mismo valor, se usa ese.
  3. En cualquier otro caso: sin indicar (como hoy, con el aviso «límite sin indicar»).
- El formulario del préstamo muestra el valor sugerido por la regla 2 como texto de ayuda en el campo.
- Validación (`guarda_pignoracion`): hace falta al menos un fondo suelto **o** una cartera, y que la garantía efectiva no
  quede vacía; `carteraIds` inexistentes se rechazan con mensaje.

## Pantallas

1. **Datos → Carteras** (vista nueva en el editor): tabla (nombre, entidad, nº de fondos, LTV) y formulario con nombre,
   entidad, LTV opcional y casillas de fondos. Acciones por `data-acc` como el resto del editor.
2. **Ficha del producto** (Datos → Productos): desplegable «Cartera».
3. **Posiciones**: modo de agrupación «Cartera». Cada cartera es una línea plegable (nombre · n fondos · peso · valor ·
   plusvalía · rentabilidad), plegada por defecto, con el estado recordado en `localStorage`; teclado Enter/Espacio y
   `aria-expanded`. Los productos sin cartera van bajo «Sin cartera». Los totales de la línea se calculan con la lógica de
   los demás agrupamientos; la rentabilidad de la línea es plusvalía total / coste total solo cuando hay coste de todos
   los fondos (si no, «—»). La TIR de la línea es «—».
4. **Formulario del préstamo**: bloque «Carteras en garantía» sobre las casillas de fondos sueltos. La tarjeta del préstamo
   resume la garantía («Cartera Ejemplo + 2 fondos») y el detalle sigue listando los fondos.
5. **Web exportada**: sin pantalla de edición; Posiciones agrupa por cartera con los mismos datos que ya viajan.

Todo lo que viene del usuario (nombres de cartera/entidad) se escapa con `esc()` y los estilos usan `data-st` con la lista
de propiedades de `estilos.js`.

## Errores y casos límite

- Cartera sin fondos: se permite (aparece con 0 fondos y valor 0); no puede ser garantía de un préstamo (garantía vacía).
- Cartera con LTV pero préstamo con LTV propio distinto: manda el del préstamo; no se avisa (es una decisión explícita).
- Garantía mixta (cartera + fondos sueltos) sin LTV en el préstamo: sin indicar.
- Un fondo vendido por completo sigue perteneciendo a su cartera, con valor 0.
- Productos derivados (deuda, efectivo) no se asignan a carteras; el desplegable solo ofrece productos de inversión.

## Pruebas y verificación

- Python: migración v3→v4 (idempotente, no toca nada más), validación de cartera (nombre vacío/repetido/largo, LTV 0/101/NaN),
  mover y borrar con efecto en productos y préstamos, `activos_efectivos`, `ltv_efectivo` (las tres ramas), bloqueo de
  venta de un fondo de una cartera pignorada, API con origen cruzado (403), `sanea_copia` con nombres hostiles, exportación
  sin importes nuevos. `test_fase3` sigue comparando con `VERSION_ACTUAL`.
- Node: totales de una línea de cartera (suma, peso, plusvalía, rentabilidad con y sin coste completo) como función pura.
- App real (Playwright, cartera temporal): crear cartera, asignar fondos, plegar/desplegar, pignorar la cartera, ver el
  margen con el LTV sugerido, borrar la cartera; 390 y 1280 px, claro y oscuro; sin desbordes, errores de consola ni
  violaciones de CSP; comparación de capturas con el commit anterior en las pestañas que no cambian.
- Revisión de `seguridad-privacidad` y `verificador` antes de dar nada por hecho.

## Riesgos

- Es una migración de esquema: se mitiga con migración solo aditiva y copia automática antes de escribir.
- `pignoracion.estado()` no recibe `cfg`: la garantía efectiva y el LTV se resuelven en `resumen()`, `marcas()` y
  `bloquea_venta()`, que sí lo reciben; hay que revisar todos los llamantes para no dejar ninguno con los `activos` en crudo.
- El LTV sugerido por cartera es solo una ayuda: el dato bueno es el del contrato del préstamo.
