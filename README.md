# etl-portafolios
ETL y API de portafolios con Django
# ETL y API de portafolios con Django

Proyecto de evaluación técnica para importar datos financieros desde Excel,
modelar portafolios y consultar su evolución mediante una API REST y gráficos.

## Estado del proyecto

En desarrollo.

- [x] Modelos de activos, portafolios, precios y posiciones.
- [x] ETL para cargar `datos.xlsx` en la base de datos.
- [x] Cálculo de las cantidades iniciales.
- [ ] API REST con los weights y el valor total entre dos fechas.
- [ ] Vista con los gráficos de evolución.

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

### ETL

El ETL está en `portafolios/etl.py` y se ejecuta con el comando
`cargar_datos`. Tiene tres etapas separadas:

1. **Extraer**: lee las hojas `weights` y `Precios`. Los nombres de hoja se
   comparan sin distinguir mayúsculas, porque el enunciado dice "Weights" y el
   archivo usa "weights".
2. **Transformar y validar**: limpia los datos y reúne todos los errores antes
   de tocar la base de datos.
3. **Cargar**: guarda los datos en una única transacción.

Particularidades del archivo que el ETL resuelve:

- **El orden de los activos difiere entre hojas.** En `weights` el tercer
  activo es UK y en `Precios` es Japón. Los activos se asocian por nombre,
  nunca por posición.
- **La hoja `weights` tiene cientos de filas vacías al final.** Se descartan
  las filas y columnas completamente vacías.
- **Los weights tienen ruido de punto flotante** (`0.018000000000000002`).
  Se convierten a `Decimal` y se redondean a 6 decimales, con lo que cada
  portafolio suma exactamente 1.

Validaciones:

- Existen ambas hojas y tienen la estructura esperada.
- `weights` tiene una única fecha de inicio, activos sin repetir y weights
  numéricos entre 0 y 1 que suman 1 en cada portafolio.
- `Precios` tiene fechas válidas y sin repetir, y precios numéricos mayores
  que 0.
- Ambas hojas tienen los mismos activos.
- Existen precios para la fecha de inicio, necesarios para calcular las
  cantidades iniciales.

La carga es idempotente: inserta o actualiza los registros, por lo que
ejecutarla varias veces deja la base de datos en el mismo estado. Al recargar
se vacían las cantidades y el valor inicial de los portafolios, porque sus
weights o precios iniciales pueden haber cambiado; deben calcularse de nuevo
después de cada carga.

La fecha de los weights se guarda como fecha de inicio del portafolio. Por eso
un portafolio puede tener fecha de inicio sin valor inicial, pero no al revés.

### Cálculo de las cantidades iniciales

El cálculo está en `portafolios/services.py`, siguiendo la convención del
Django-Styleguide de ubicar la lógica de negocio en servicios.

- **Las posiciones y su precio inicial se obtienen con el ORM en una sola
  consulta**, anotando P<sub>i,0</sub> con un `Subquery` sobre `Precio` en la
  fecha de inicio del portafolio.
- **La división se hace en Python con `Decimal`.** SQLite opera los decimales
  como números de punto flotante, por lo que calcular la cantidad en SQL
  perdería precisión. Las cantidades se guardan con 10 decimales.
- **V<sub>0</sub> se guarda en el portafolio** junto con las cantidades, para
  que el resultado quede asociado al valor inicial con que se calculó.
- **El cálculo es un paso separado de la carga**, igual que en el enunciado,
  y recibe V<sub>0</sub> como parámetro en lugar de fijarlo en el código.
- **Si falta algún dato** (fecha de inicio, posiciones o precio inicial de un
  activo), no se guarda ninguna cantidad de ningún portafolio.

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
- Python 3.12 o superior (requerido por Django 6.1). El CI usa Python 3.15.
- Los comandos de este README están escritos para Windows (CMD y PowerShell).

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

En PowerShell, la activación es:

```powershell
.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea el script por la política de ejecución, se puede
habilitar solo para la sesión actual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Con el entorno activado, el prompt muestra `(.venv)` al inicio. Todos los
comandos `python` de este README asumen que el entorno está activado.

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

### Cargar los datos

```bat
python manage.py cargar_datos
```

Por defecto lee `data/datos.xlsx`, el archivo entregado en el enunciado, que
se incluye en el repositorio. Para usar otro archivo:

```bat
python manage.py cargar_datos --archivo ruta\al\archivo.xlsx
```

Si el archivo no es válido, el comando lista todos los errores encontrados y no
modifica la base de datos.

### Calcular las cantidades iniciales

```bat
python manage.py calcular_cantidades
```

Calcula C<sub>i,0</sub> = w<sub>i,0</sub> · V<sub>0</sub> / P<sub>i,0</sub>
para cada activo de cada portafolio, con V<sub>0</sub> = 1.000.000.000 por
defecto, y muestra el resultado. Para usar otro valor inicial:

```bat
python manage.py calcular_cantidades --valor-inicial 500000000
```

Debe ejecutarse después de cada `cargar_datos`, porque la carga deja vacías las
cantidades calculadas.

## Resultados

### Cantidades iniciales

Con V<sub>0</sub> = 1.000.000.000 al 15/02/2022 para ambos portafolios. Los
valores se muestran redondeados a 4 decimales; la base de datos guarda 10.

| Activo | P<sub>i,0</sub> | w<sub>i,0</sub> P1 | C<sub>i,0</sub> portafolio 1 | w<sub>i,0</sub> P2 | C<sub>i,0</sub> portafolio 2 |
|---|---:|---:|---:|---:|---:|
| ABS | 368,4400 | 1,5 % | 40.712,1919 | 0,0 % | 0,0000 |
| Asia Desarrollada | 1.212,8100 | 1,6 % | 13.192,5034 | 1,6 % | 13.192,5034 |
| EEUU | 9.383,5700 | 28,0 % | 29.839,3895 | 28,0 % | 29.839,3895 |
| EM Asia | 82,3500 | 4,8 % | 582.877,9599 | 4,8 % | 582.877,9599 |
| EMEA | 290,4490 | 0,5 % | 17.214,7262 | 0,5 % | 17.214,7262 |
| EMHC | 437,0424 | 4,1 % | 93.812,4081 | 0,0 % | 0,0000 |
| Europa | 66,0300 | 8,7 % | 1.317.582,9169 | 6,7 % | 1.014.690,2923 |
| High Yield | 2.355,2500 | 8,6 % | 36.514,1705 | 0,0 % | 0,0000 |
| IG Corporate | 3.314,6600 | 7,6 % | 22.928,4451 | 11,1 % | 33.487,5975 |
| Japón | 390,2626 | 3,8 % | 97.370,3447 | 3,8 % | 97.370,3447 |
| Latam | 26,8400 | 0,5 % | 186.289,1207 | 0,5 % | 186.289,1207 |
| Latam HY | 1.007,5330 | 2,8 % | 27.790,6530 | 0,0 % | 0,0000 |
| MBS+CMBS+AMBS | 2.226,5600 | 9,5 % | 42.666,7146 | 14,6 % | 65.572,0034 |
| MM/Caja | 104,6400 | 5,1 % | 487.385,3211 | 2,8 % | 267.584,0979 |
| Otros RV | 717,8100 | 1,8 % | 25.076,2737 | 1,8 % | 25.076,2737 |
| Tesoro | 2.403,8500 | 8,8 % | 36.607,9414 | 21,5 % | 89.439,8569 |
| UK | 34,4800 | 2,3 % | 667.053,3643 | 2,3 % | 667.053,3643 |

Como comprobación, Σ C<sub>i,0</sub> · P<sub>i,0</sub> reconstruye
V<sub>0</sub> en ambos portafolios con una diferencia menor a 0,000001.

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

Actualmente las pruebas cubren las restricciones de los modelos, el ETL y
el cálculo de las cantidades iniciales, incluidas cargas completas del
archivo real. Se ampliarán junto con la API.

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
