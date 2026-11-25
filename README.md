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

## Decisiones de diseño

### Modelo de datos

El dominio se modela con cuatro modelos:

| Modelo | Representa | Origen |
|---|---|---|
| `Activo` | Cada uno de los 17 activos invertibles | Hojas `weights` y `Precios` |
| `Portafolio` | Portafolio, su valor inicial V₀ y su fecha de inicio t = 0 | Hoja `weights` y cálculo inicial |
| `Precio` | Precio p<sub>i,t</sub> de un activo en una fecha | Hoja `Precios` |
| `Posicion` | Activo dentro de un portafolio, con su weight inicial w<sub>i,0</sub> y su cantidad c<sub>i,0</sub> | Hoja `weights` y cálculo inicial |

Cada dato se guarda según aquello de lo que depende:

- **El precio es un modelo propio** porque depende del activo y de la fecha
  (17 activos × 367 fechas). Guardarlo como campo de `Activo` obligaría a usar
  una columna por fecha o un JSON, y ninguna de las dos alternativas permite
  calcular los montos con el ORM.
- **El weight inicial y la cantidad son campos de `Posicion`** porque dependen
  del par portafolio-activo y no de la fecha. El enunciado establece que las
  cantidades se mantienen constantes (c<sub>i,t</sub> = c<sub>i,0</sub>), por lo
  que basta con un registro por activo y portafolio. Guardarlos juntos asegura
  que cada cantidad corresponda siempre a su weight inicial.
- `Posicion` es el modelo intermedio de la relación muchos a muchos entre
  `Portafolio` y `Activo`.

### Valores calculados que no se almacenan

Los montos x<sub>i,t</sub> = p<sub>i,t</sub> · c<sub>i,0</sub>, el valor total
V<sub>t</sub> = Σ x<sub>i,t</sub> y los weights w<sub>i,t</sub> = x<sub>i,t</sub> / V<sub>t</sub>
se derivan de los precios. Por eso se calculan con el ORM al consultar la API y
no se guardan en la base de datos. De esta forma no pueden quedar desalineados
con los precios cargados y no se duplica información.

### Alternativa descartada

Se evaluó modelar `Weight` y `Cantidad` como tablas separadas con fecha
(portafolio, activo, fecha, valor). Esa estructura permitiría registrar
rebalanceos, pero:

- Agrega una generalidad que el enunciado no necesita, porque las cantidades
  no cambian.
- Complica la consulta de la API, que tendría que buscar la cantidad vigente en
  cada fecha.
- No garantiza que cada cantidad tenga su weight correspondiente.

Si en el futuro se necesitaran rebalanceos, la cantidad pasaría a una tabla
con fecha de vigencia.

### Tipos numéricos

Se usa `DecimalField` en lugar de `float` para no acumular errores de
redondeo:

- Precios con 6 decimales (el archivo trae hasta 5).
- Weights con 6 decimales.
- Cantidades con 10 decimales.

## Criterios de finalización

- La importación y los cálculos cuentan con pruebas automatizadas.
- La API valida los parámetros y devuelve los resultados del rango solicitado.
- La vista permite consultar y visualizar los portafolios.
- El README explica cómo instalar, ejecutar y probar el proyecto.
- Los cambios se integran mediante pull requests y pasan las verificaciones
  de integración continua.

## Instalación y ejecución local

### Requisitos previos

- Git.
- Python compatible con la versión de Django indicada en requirements.txt.
- Los siguientes comandos de activación corresponden a Windows CMD.

### Clonar el repositorio

```bat
git clone https://github.com/TomasZaBe/etl-portafolios.git
cd etl-portafolios
```

### Crear y activar el entorno virtual

```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

### Instalar las dependencias

```bat
python -m pip install -r requirements.txt
```

### Preparar la base de datos local

```bat
python manage.py migrate
```

El proyecto utiliza SQLite para el desarrollo local. La base de datos
db.sqlite3 no se incluye en el repositorio.

### Verificar la configuración

```bat
python manage.py check
```

### Iniciar el servidor de desarrollo

```bat
python manage.py runserver
```

Abrir http://127.0.0.1:8000/ en el navegador.

Para detener el servidor, pulsar Ctrl + C en la terminal.

Actualmente se muestra la página de bienvenida de Django.
La API y la vista de portafolios todavía no están implementadas.

## Verificaciones de desarrollo

Con el entorno virtual activo, ejecutar:

### Revisión de código

```bat
python -m ruff check .
```

### Comprobación del formato

```bat
python -m ruff format --check .
```

Para aplicar el formato automáticamente:

```bat
python -m ruff format .
```

### Comprobación de Django

```bat
python manage.py check
```

### Pruebas automatizadas

```bat
python manage.py test
```

Actualmente las pruebas cubren las restricciones de los modelos. Se
ampliarán junto con la importación de datos y los cálculos.

## Integración continua

El workflow de GitHub Actions se ejecuta en pull requests hacia main
y cuando se publican cambios en main.

Utiliza Python 3.15 y las dependencias fijadas en requirements.txt.

Verifica:
- Compatibilidad de las dependencias instaladas.
- Revisión de código y formato mediante Ruff.
- Configuración de Django.
- Ausencia de cambios en modelos sin su correspondiente migración.
- Ejecución de pruebas automatizadas.

El workflow ejecuta todas las pruebas de la aplicación.
