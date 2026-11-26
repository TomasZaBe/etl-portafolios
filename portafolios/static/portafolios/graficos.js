// Consume la API de portafolios y dibuja:
// - Un gráfico de líneas con el valor total V_t de cada portafolio.
// - Un gráfico de áreas apiladas con los weights w_i,t de cada portafolio.
(function () {
  "use strict";

  const contenedor = document.getElementById("graficos");
  const urlPortafolios = contenedor.dataset.urlPortafolios;
  const urlEvolucion = contenedor.dataset.urlEvolucion;
  const formulario = document.getElementById("filtros");
  const mensaje = document.getElementById("mensaje");
  const resumen = document.getElementById("resumen");
  const contenedorWeights = document.getElementById("graficos-weights");

  // Un color fijo por activo, para que se lea igual en ambos portafolios.
  // Colores de máximo contraste de Kelly, sin blanco ni negro. Se omite el
  // amarillo verdoso (#dcd300), que se confunde con el amarillo (#f3c300).
  const PALETA = [
    "#0067a5", "#f38400", "#008856", "#be0032", "#875692", "#f3c300",
    "#a1caf1", "#882d17", "#8db600", "#e68fac", "#848482", "#604e97",
    "#f99379", "#c2b280", "#b3446c", "#e25822", "#2b3d26",
  ];
  const COLORES_PORTAFOLIO = ["#1f5fbf", "#d9480f", "#2b8a3e", "#862e9c"];

  const numero = new Intl.NumberFormat("es-CL", { maximumFractionDigits: 0 });
  const porcentaje = new Intl.NumberFormat("es-CL", {
    style: "percent",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const millones = new Intl.NumberFormat("es-CL", { maximumFractionDigits: 0 });

  let graficos = [];

  function urlEvolucionDe(portafolioId, filtros) {
    const url = new URL(
      urlEvolucion.replace("/0/", `/${portafolioId}/`),
      window.location.origin
    );
    for (const [clave, valor] of Object.entries(filtros)) {
      if (valor) url.searchParams.set(clave, valor);
    }
    return url;
  }

  async function obtenerJson(url) {
    const respuesta = await fetch(url, { headers: { Accept: "application/json" } });
    const datos = await respuesta.json().catch(() => ({}));
    if (!respuesta.ok) {
      throw new Error(describirError(datos) || `Error ${respuesta.status} al consultar la API.`);
    }
    return datos;
  }

  // Los errores de la API tienen la forma {"message": ..., "extra": {...}}.
  // En los errores de validación, extra.fields trae el detalle por campo.
  function describirError(datos) {
    const campos = (datos.extra && datos.extra.fields) || {};
    const detalle = Object.entries(campos)
      .map(([campo, errores]) => `${campo}: ${[].concat(errores).join(" ")}`)
      .join(" ");
    return [datos.message, detalle].filter(Boolean).join(". ");
  }

  function mostrarMensaje(texto) {
    mensaje.textContent = texto;
    mensaje.hidden = !texto;
  }

  function leerFiltros() {
    const datos = new FormData(formulario);
    return {
      fecha_inicio: datos.get("fecha_inicio"),
      fecha_fin: datos.get("fecha_fin"),
    };
  }

  function colorDeActivo(activos, activo) {
    return PALETA[activos.indexOf(activo) % PALETA.length];
  }

  function destruirGraficos() {
    graficos.forEach((grafico) => grafico.destroy());
    graficos = [];
    contenedorWeights.replaceChildren();
    resumen.replaceChildren();
  }

  function dibujarValorTotal(evoluciones) {
    const fechas = evoluciones[0].valores.map((v) => v.fecha);
    const grafico = new Chart(document.getElementById("grafico-valor-total"), {
      type: "line",
      data: {
        labels: fechas,
        datasets: evoluciones.map((evolucion, indice) => ({
          label: evolucion.portafolio.nombre,
          data: evolucion.valores.map((v) => v.valor_total),
          borderColor: COLORES_PORTAFOLIO[indice % COLORES_PORTAFOLIO.length],
          backgroundColor: COLORES_PORTAFOLIO[indice % COLORES_PORTAFOLIO.length],
          borderWidth: 2,
          pointRadius: 0,
          tension: 0,
        })),
      },
      options: {
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: { ticks: { maxTicksLimit: 12 } },
          y: {
            title: { display: true, text: "Millones de USD" },
            ticks: { callback: (valor) => millones.format(valor / 1e6) },
          },
        },
        plugins: {
          tooltip: {
            callbacks: {
              label: (item) => `${item.dataset.label}: $${numero.format(item.parsed.y)}`,
            },
          },
        },
      },
    });
    graficos.push(grafico);
  }

  function dibujarResumen(evoluciones) {
    for (const evolucion of evoluciones) {
      const primero = evolucion.valores[0];
      const ultimo = evolucion.valores[evolucion.valores.length - 1];
      const variacion = ultimo.valor_total / primero.valor_total - 1;

      const bloque = document.createElement("div");
      const titulo = document.createElement("strong");
      titulo.textContent = evolucion.portafolio.nombre;
      const detalle = document.createElement("span");
      detalle.textContent =
        `$${numero.format(primero.valor_total)} (${primero.fecha}) → ` +
        `$${numero.format(ultimo.valor_total)} (${ultimo.fecha}) `;
      const cambio = document.createElement("span");
      cambio.textContent = `${variacion >= 0 ? "+" : ""}${porcentaje.format(variacion)}`;
      cambio.className = variacion >= 0 ? "positivo" : "negativo";
      bloque.append(titulo, detalle, cambio);
      resumen.append(bloque);
    }
  }

  function dibujarWeights(evolucion, activos) {
    const tarjeta = document.createElement("section");
    tarjeta.className = "tarjeta";
    const titulo = document.createElement("h2");
    titulo.innerHTML = `Weights w<sub>i,t</sub> · ${evolucion.portafolio.nombre}`;
    const lienzo = document.createElement("div");
    lienzo.className = "lienzo lienzo-area";
    const canvas = document.createElement("canvas");
    canvas.setAttribute(
      "aria-label",
      `Gráfico de áreas apiladas de los weights de ${evolucion.portafolio.nombre}`
    );
    lienzo.append(canvas);
    tarjeta.append(titulo, lienzo);
    contenedorWeights.append(tarjeta);

    const datasets = activos.map((activo) => {
      const color = colorDeActivo(activos, activo);
      return {
        label: activo,
        data: evolucion.valores.map((valor) => {
          const encontrado = valor.activos.find((a) => a.activo === activo);
          return encontrado ? encontrado.weight * 100 : 0;
        }),
        borderColor: color,
        backgroundColor: `${color}cc`,
        borderWidth: 1,
        pointRadius: 0,
        tension: 0,
        fill: true,
      };
    });

    const grafico = new Chart(canvas, {
      type: "line",
      data: { labels: evolucion.valores.map((v) => v.fecha), datasets },
      options: {
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: { ticks: { maxTicksLimit: 8 } },
          y: {
            stacked: true,
            min: 0,
            max: 100,
            ticks: { callback: (valor) => `${valor} %` },
          },
        },
        plugins: {
          legend: { position: "bottom", labels: { boxWidth: 12 } },
          tooltip: {
            itemSort: (a, b) => b.parsed.y - a.parsed.y,
            callbacks: {
              label: (item) =>
                `${item.dataset.label}: ${porcentaje.format(item.parsed.y / 100)}`,
            },
          },
        },
      },
    });
    graficos.push(grafico);
  }

  function ajustarFiltros(evoluciones) {
    // Fija el rango disponible en los selectores de fecha.
    const inicio = formulario.elements.fecha_inicio;
    const fin = formulario.elements.fecha_fin;
    const primera = evoluciones[0];
    if (!inicio.value) inicio.value = primera.fecha_inicio;
    if (!fin.value) fin.value = primera.fecha_fin;
  }

  async function actualizar() {
    mostrarMensaje("");
    const filtros = leerFiltros();
    try {
      const portafolios = await obtenerJson(urlPortafolios);
      if (portafolios.length === 0) {
        throw new Error(
          "No hay portafolios. Ejecute los comandos cargar_datos y calcular_cantidades."
        );
      }
      const evoluciones = await Promise.all(
        portafolios.map((p) => obtenerJson(urlEvolucionDe(p.id, filtros)))
      );

      destruirGraficos();
      if (evoluciones.some((e) => e.valores.length === 0)) {
        mostrarMensaje("No hay datos en el rango de fechas seleccionado.");
        return;
      }

      const activos = [
        ...new Set(evoluciones.flatMap((e) => e.valores[0].activos.map((a) => a.activo))),
      ].sort((a, b) => a.localeCompare(b, "es"));

      dibujarValorTotal(evoluciones);
      dibujarResumen(evoluciones);
      evoluciones.forEach((evolucion) => dibujarWeights(evolucion, activos));
      ajustarFiltros(evoluciones);
    } catch (error) {
      destruirGraficos();
      mostrarMensaje(error.message);
    }
  }

  formulario.addEventListener("submit", (evento) => {
    evento.preventDefault();
    actualizar();
  });

  document.getElementById("rango-completo").addEventListener("click", () => {
    formulario.reset();
    actualizar();
  });

  actualizar();
})();
