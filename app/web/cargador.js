/* Carga los scripts con un sello temporal para que, al recargar despues de
   actualizar, el navegador no sirva los datos viejos de su cache.
   async=false conserva el orden de ejecucion. */
(function () {
  // Con file:// no se puede anadir "?v=": algunos navegadores no encuentran
  // el archivo. Ahi basta con la revalidacion por fecha de modificacion.
  var sello = location.protocol === "file:" ? "" : "?v=" + Date.now();
  ["datos.js", "canal.js", "graficos.js", "proyeccion.js", "metricas.js", "alertas.js", "carteras.js", "asignacion.js", "montecarlo.js", "app.js", "editor.js"].forEach(function (archivo) {
    var s = document.createElement("script");
    s.src = archivo + sello;
    s.async = false;
    document.body.appendChild(s);
  });
})();
