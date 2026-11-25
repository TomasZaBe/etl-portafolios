# etl-portafolios
ETL y API de portafolios con Django
# ETL y API de portafolios con Django

Proyecto de evaluación técnica para importar datos financieros desde Excel,
modelar portafolios y consultar su evolución mediante una API REST y gráficos.

## Estado del proyecto

En desarrollo. Actualmente se está preparando el repositorio y la documentación
inicial. Las funcionalidades descritas a continuación son el alcance previsto,
no funcionalidades implementadas todavía.

## Objetivo

Calcular y visualizar la evolución del valor total y de los pesos de los activos
de dos portafolios, utilizando los precios históricos y manteniendo constantes
las cantidades iniciales de cada activo.

## Requerimientos funcionales

- Modelar activos, portafolios, precios y posiciones mediante Django.
- Importar las hojas `weights` y `Precios` del archivo `datos.xlsx`.
- Validar los datos antes de cargarlos en la base de datos.
- Calcular las cantidades iniciales para cada portafolio con un valor inicial
  de 1.000.000.000 al 15 de febrero de 2022.
- Calcular los montos por activo, el valor total y los pesos de cada portafolio
  utilizando el ORM de Django.
- Exponer una API REST con filtros `fecha_inicio` y `fecha_fin`.
- Crear una vista que consuma la API y muestre los pesos mediante un gráfico
  de áreas apiladas y el valor total mediante un gráfico de línea.

## Criterios de finalización

- La importación y los cálculos cuentan con pruebas automatizadas.
- La API valida los parámetros y devuelve los resultados del rango solicitado.
- La vista permite consultar y visualizar los portafolios.
- El README explica cómo instalar, ejecutar y probar el proyecto.
- Los cambios se integran mediante pull requests y pasan las verificaciones
  de integración continua.
