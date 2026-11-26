# ETL y API de portafolios con Django

Solución a la [pregunta técnica de Python](https://abaquscl.notion.site/Pregunta-t-cnica-Python-d00b3f926b0845edaec7f198919c83d4):
un proyecto Django que carga los datos de `datos.xlsx`, calcula las cantidades
iniciales de dos portafolios y expone la evolución de su valor total
V<sub>t</sub> y de sus weights w<sub>i,t</sub> mediante una API REST y una
vista con gráficos.

## Contenido

- [Resumen de la solución](#resumen-de-la-solución)
- [Inicio rápido](#inicio-rápido)
- [Resultados](#resultados)
- [API](#api)
- [Configuración](#configuración)
- [Admin](#admin)
- [Comandos](#comandos)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Decisiones de diseño](#decisiones-de-diseño)
- [Desarrollo](#desarrollo)

## Resumen de la solución

| Punto del enunciado | Solución | Dónde |
|---|---|---|
| 1. Modelar activos, portafolios, precios, cantidades, weights y montos | Modelos `Activo`, `Portafolio`, `Precio` y `Posicion`. Los montos, V<sub>t</sub> y w<sub>i,t</sub> se calculan, no se guardan. | `portafolios/models.py` |
| 2. ETL que carga `datos.xlsx` | Comando `cargar_datos`: extrae, valida y carga en una transacción. | `portafolios/etl.py` |
| 3. Cantidades iniciales C<sub>i,0</sub> con V<sub>0</sub> = 1.000.000.000 | Comando `calcular_cantidades`. | `portafolios/services.py` |
| 4. API REST con `fecha_inicio` y `fecha_fin` que entrega w<sub>i,t</sub> y V<sub>t</sub> usando el ORM | `GET /api/portafolios/{id}/evolucion/`. Una única consulta del ORM calcula x<sub>i,t</sub>, V<sub>t</sub> y w<sub>i,t</sub>. | `portafolios/selectors.py`, `portafolios/apis.py` |
| 5. Vista que usa la API: áreas apiladas para w<sub>i,t</sub> y líneas para V<sub>t</sub> | Página principal con Chart.js y filtro de fechas. | `portafolios/templates/`, `portafolios/static/` |
| Bonus: Django-Styleguide | Lógica de escritura en servicios, consultas en selectores, APIs con serializers de filtros y de salida, errores con `ApplicationError` y un manejador central, y configuración con variables de entorno. | `services.py`, `selectors.py`, `apis.py`, `core/`, `config/env.py` |

El proyecto incluye 126 pruebas automatizadas y un workflow de integración
continua que las ejecuta en cada pull request.

## Inicio rápido

Requisitos: Git y Python 3.12 o superior (requerido por Django 6.1). Los
comandos están escritos para Windows.

**1. Clonar el repositorio**

```powershell
git clone https://github.com/TomasZaBe/etl-portafolios.git
cd etl-portafolios
```

**2. Crear y activar el entorno virtual**

```powershell
python -m venv .venv
```

En PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

En CMD:

```bat
.venv\Scripts\activate.bat
```

Con el entorno activado, el prompt muestra `(.venv)` al inicio. Todos los
comandos `python` de este README asumen que el entorno está activado. Si
PowerShell bloquea el script de activación, se puede habilitar solo para la
sesión actual con
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`.

**3. Instalar las dependencias y crear la base de datos**

```powershell
python -m pip install -r requirements.txt
python manage.py migrate
```

El proyecto usa SQLite. La base de datos `db.sqlite3` se crea localmente y no
se incluye en el repositorio.

No hace falta configurar nada más para ejecutarlo en local: las variables de
entorno tienen valores por defecto para desarrollo (ver
[Configuración](#configuración)).

**4. Cargar los datos y calcular las cantidades iniciales**

```powershell
python manage.py cargar_datos
python manage.py calcular_cantidades
```

`cargar_datos` lee `data/datos.xlsx`, el archivo del enunciado, que se incluye
en el repositorio. `calcular_cantidades` muestra en la terminal la tabla de
cantidades iniciales.

**5. Iniciar el servidor**

```powershell
python manage.py runserver
```

- http://127.0.0.1:8000/: vista con los gráficos de evolución.
- http://127.0.0.1:8000/api/portafolios/: API REST. Al abrirla en el navegador,
  Django REST Framework muestra una interfaz navegable.

Para detener el servidor, pulsar Ctrl + C en la terminal.

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

### Valor total al final del período

| Portafolio | V<sub>t</sub> al 15/02/2022 | V<sub>t</sub> al 16/02/2023 | Variación |
|---|---:|---:|---:|
| Portafolio 1 | 1.000.000.000,00 | 929.055.490,74 | −7,09 % |
| Portafolio 2 | 1.000.000.000,00 | 923.548.704,77 | −7,65 % |

La evolución completa de V<sub>t</sub> y de los w<sub>i,t</sub> se puede
consultar en la vista de gráficos o en la API.

## API

Todos los endpoints responden JSON y solo aceptan `GET`.

### Listar portafolios

`GET /api/portafolios/`

```json
[
  {"id": 1, "nombre": "portafolio 1", "fecha_inicio": "2022-02-15", "valor_inicial": "1000000000.00"},
  {"id": 2, "nombre": "portafolio 2", "fecha_inicio": "2022-02-15", "valor_inicial": "1000000000.00"}
]
```

### Evolución de un portafolio

`GET /api/portafolios/{id}/evolucion/?fecha_inicio=AAAA-MM-DD&fecha_fin=AAAA-MM-DD`

Devuelve, para cada fecha del rango (ambos extremos incluidos), el valor total
V<sub>t</sub> y, por activo, el monto x<sub>i,t</sub> y el weight
w<sub>i,t</sub>.

| Parámetro | Obligatorio | Descripción |
|---|---|---|
| `fecha_inicio` | No | Primera fecha del rango. Por defecto, la fecha de inicio del portafolio. |
| `fecha_fin` | No | Última fecha del rango. Por defecto, la última fecha con precios. |

Ejemplo: `GET /api/portafolios/1/evolucion/?fecha_inicio=2023-02-16&fecha_fin=2023-02-16`

```json
{
  "portafolio": {"id": 1, "nombre": "portafolio 1"},
  "fecha_inicio": "2023-02-16",
  "fecha_fin": "2023-02-16",
  "valores": [
    {
      "fecha": "2023-02-16",
      "valor_total": 929055490.74,
      "activos": [
        {"activo": "ABS", "monto": 14669009.88, "weight": 0.0157891644},
        {"activo": "Asia Desarrollada", "monto": 14805550.75, "weight": 0.0159361318},
        {"activo": "EEUU", "monto": 264168711.91, "weight": 0.2843411557}
      ]
    }
  ]
}
```

El ejemplo muestra solo 3 de los 17 activos.

### Errores

Todos los errores tienen la forma `{"message": str, "extra": object}`. En los
errores de validación, `extra.fields` trae el detalle por campo:

```json
{
  "message": "Error de validación",
  "extra": {"fields": {"fecha_fin": ["Debe ser igual o posterior a fecha_inicio."]}}
}
```

| Código | Caso |
|---|---|
| `400` | Una fecha no tiene el formato `AAAA-MM-DD`, o `fecha_fin` es anterior a `fecha_inicio`. |
| `404` | No existe el portafolio. |
| `409` | El portafolio no tiene sus cantidades iniciales calculadas. |

## Configuración

La configuración se lee desde variables de entorno con `django-environ`. Se
pueden definir en el sistema o en un archivo `.env` en la raíz del proyecto;
`.env.example` sirve de plantilla. El archivo `.env` no se versiona.

| Variable | Por defecto | Descripción |
|---|---|---|
| `DJANGO_SECRET_KEY` | Una clave de desarrollo | Clave secreta de Django. Obligatoria fuera del entorno local. |
| `DJANGO_DEBUG` | `True` | Modo de depuración. Debe ser `False` en producción. |
| `DJANGO_ALLOWED_HOSTS` | Vacío | Hosts permitidos, separados por comas. |

Los valores por defecto solo sirven para desarrollo local, para que el
proyecto se pueda ejecutar recién clonado.

## Admin

El admin de Django (`/admin/`) es de solo lectura: permite revisar los datos
cargados, pero no agregarlos, modificarlos ni eliminarlos. Los datos se
modifican únicamente con `cargar_datos` y `calcular_cantidades`. Para entrar se
necesita un usuario creado con `python manage.py createsuperuser`.

## Comandos

### `cargar_datos`

```powershell
python manage.py cargar_datos
python manage.py cargar_datos --archivo ruta\al\archivo.xlsx
```

Carga activos, portafolios, weights iniciales y precios. Por defecto lee
`data/datos.xlsx`. Si el archivo no es válido, lista todos los errores
encontrados y no modifica la base de datos.

La carga es idempotente: ejecutarla varias veces deja la base de datos en el
mismo estado. Al recargar se vacían las cantidades calculadas, por lo que hay
que volver a ejecutar `calcular_cantidades`.

### `calcular_cantidades`

```powershell
python manage.py calcular_cantidades
python manage.py calcular_cantidades --valor-inicial 500000000
```

Calcula C<sub>i,0</sub> = w<sub>i,0</sub> · V<sub>0</sub> / P<sub>i,0</sub>
para cada activo de cada portafolio y muestra el resultado. Por defecto usa
V<sub>0</sub> = 1.000.000.000.

## Estructura del proyecto

```text
etl-portafolios/
├── config/
│   ├── settings.py             Configuración de Django
│   └── env.py                  Lectura de variables de entorno
├── core/                       Código común a todo el proyecto
│   ├── models.py               BaseModel
│   ├── exceptions.py           ApplicationError
│   ├── exception_handlers.py   Formato de los errores de la API
│   └── utils.py                get_object
├── data/datos.xlsx             Archivo de entrada del enunciado
├── .env.example                Plantilla de variables de entorno
└── portafolios/
    ├── models.py               Activo, Portafolio, Precio y Posicion
    ├── etl.py                  ETL de datos.xlsx
    ├── services.py             Cálculo de las cantidades iniciales
    ├── selectors.py            Consultas: evolución de V_t, x_i,t y w_i,t
    ├── apis.py                 Endpoints REST
    ├── admin.py                Admin de solo lectura
    ├── views.py                Vista de gráficos
    ├── urls.py                 Rutas de la vista y de la API
    ├── management/commands/    cargar_datos y calcular_cantidades
    ├── templates/portafolios/  HTML de la vista
    ├── static/portafolios/     JavaScript y CSS de los gráficos
    ├── migrations/
    └── tests/                  Pruebas por módulo
```

## Decisiones de diseño

### Modelo de datos

El dominio se modela con cuatro modelos:

| Modelo | Representa | Origen |
|---|---|---|
| `Activo` | Cada uno de los 17 activos invertibles | Hojas `weights` y `Precios` |
| `Portafolio` | Portafolio, su valor inicial V<sub>0</sub> y su fecha de inicio t = 0 | Hoja `weights` y cálculo inicial |
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

El ETL tiene tres etapas separadas:

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

La carga inserta o actualiza los registros, por lo que es idempotente. Al
recargar se vacían las cantidades y el valor inicial de los portafolios, porque
sus weights o precios iniciales pueden haber cambiado.

La fecha de los weights se guarda como fecha de inicio del portafolio. Por eso
un portafolio puede tener fecha de inicio sin valor inicial, pero no al revés.

### Cálculo de las cantidades iniciales

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

### API

La API usa Django REST Framework y sigue la estructura del Django-Styleguide:
`selectors.py` contiene las consultas y `apis.py` contiene endpoints delgados,
que validan la entrada con un serializer de filtros y dan forma a la respuesta
con un serializer de salida.

**Los cálculos se hacen en la base de datos con una única consulta del ORM:**

```python
Precio.objects.filter(activo__posiciones__portafolio=portafolio, fecha__gte=..., fecha__lte=...)
    .annotate(monto=Cast("valor", FloatField()) * Cast("activo__posiciones__cantidad", FloatField()))
    .annotate(valor_total=Window(Sum("monto"), partition_by=F("fecha")))
    .annotate(weight=F("monto") / F("valor_total"))
```

- El filtro une cada precio con la posición del activo en el portafolio, de
  donde se obtiene c<sub>i,0</sub>.
- x<sub>i,t</sub> = p<sub>i,t</sub> · c<sub>i,0</sub> se calcula fila a fila.
- V<sub>t</sub> se obtiene con una función de ventana
  (`SUM(...) OVER (PARTITION BY fecha)`), que suma los montos de cada fecha sin
  colapsar las filas. Así, w<sub>i,t</sub> = x<sub>i,t</sub> / V<sub>t</sub>
  se calcula en la misma consulta.

El selector hace en total dos consultas: una para verificar que las cantidades
estén calculadas y otra para los cálculos. Hay una prueba que lo verifica.

Otras decisiones:

- **La API entrega números de punto flotante.** Los montos y V<sub>t</sub> se
  redondean a 2 decimales y los weights a 10. Los datos de entrada se siguen
  guardando como `Decimal`; la conversión ocurre solo al calcular.
- **Las fechas son opcionales.** Sin `fecha_inicio` ni `fecha_fin` se devuelve
  todo el rango disponible, lo que simplifica la vista de gráficos.
- **Solo se consideran fechas desde la fecha de inicio del portafolio**, porque
  antes de t = 0 las cantidades no están definidas.
- **Si el portafolio no tiene las cantidades calculadas**, la API responde
  `409 Conflict` en lugar de devolver valores vacíos o incorrectos.
- **El portafolio se obtiene en la API con `get_object`**, la utilidad que
  propone el Django-Styleguide, que devuelve `None` en vez de lanzar `Http404`.

### Manejo de errores

Se sigue la propuesta del Django-Styleguide:

- **Los errores de negocio heredan de `ApplicationError`** (`core/exceptions.py`),
  que tiene `message` y `extra`. Lo hacen los errores del ETL, del cálculo de
  cantidades y de la consulta de evolución.
- **Un manejador central** (`core/exception_handlers.py`) da a todas las
  respuestas de error la forma `{"message", "extra"}`. También convierte la
  `ValidationError` de Django (por ejemplo, la de `full_clean()`) en un 400, en
  lugar de dejar que termine en un error 500.
- **Las APIs no capturan excepciones de negocio**: las traduce el manejador.
- **Extensión propia:** `ApplicationError` tiene un `status_code` (400 por
  defecto). Así el error de cantidades sin calcular responde 409.
- **Los errores inesperados no se silencian** y terminan en un error 500.

Los comandos también traducen estos errores a mensajes claros. Por ejemplo,
`calcular_cantidades --valor-inicial 1000.555` informa que el valor admite
como máximo 2 decimales, en vez de terminar con una traza de error.

### Admin de solo lectura

Los datos se modifican solo con los servicios. Si el admin permitiera
editarlos, se podrían dejar weights que no suman 1 o cantidades que no
corresponden al valor inicial guardado.

### Orden por defecto de los modelos

`Precio` y `Posicion` se ordenan por defecto por sus propias columnas
(`fecha`, `activo_id`, `portafolio_id`). Ordenar por el nombre del activo o del
portafolio agregaría dos JOINs a cada consulta sobre esos modelos. Hay una
prueba que lo verifica, y el admin define su propio orden por nombre.

### Diferencias con el Django-Styleguide

Algunas recomendaciones de la guía no se aplicaron, porque no aportan en un
proyecto de este tamaño:

- **Un solo archivo de settings** en vez de `config/django/base.py`,
  `local.py`, `production.py` y `test.py`. Lo que la guía busca, que nada
  dependa del entorno salvo las variables, se cumple con `config/env.py`.
- **Pruebas en archivos por módulo** (`tests/test_services.py`) en vez de
  subcarpetas (`tests/services/test_<servicio>.py`), porque hay un solo
  servicio y un solo selector principales.
- **Sin factories de `factory_boy`.** La guía acepta `objects.create()` cuando
  el proyecto no las tiene.
- **Serializers anidados como clases** en vez de `inline_serializer`.
- **El ETL usa nombres de etapas** (`extraer`, `transformar`, `cargar`) en
  lugar de `<entidad>_<acción>`, porque describen mejor un proceso ETL.

### Vista de gráficos

- **La vista consume la API desde el navegador**, como pide el enunciado. La
  vista de Django solo entrega el HTML y no consulta la base de datos; el
  JavaScript pide los portafolios y la evolución de cada uno a la API.
- **Las URLs de la API se generan con `{% url %}`** y se pasan al JavaScript
  como atributos `data-*`, para no repetir rutas fijas en el código del
  navegador.
- **Gráficos con Chart.js 4.4.1** cargado desde un CDN, sin paso de
  compilación:
  - Un gráfico de líneas compara el V<sub>t</sub> de ambos portafolios en el
    mismo eje, con un resumen de la variación en el rango.
  - Un gráfico de áreas apiladas por portafolio muestra los w<sub>i,t</sub>,
    que suman 100 % en cada fecha.
- **Cada activo tiene un color fijo** en ambos gráficos de weights, tomado de
  la paleta de máximo contraste de Kelly, para que los 17 activos se distingan.
- **Los errores de la API se muestran en la página**, por ejemplo un rango de
  fechas inválido o cantidades sin calcular.

## Desarrollo

### Verificaciones

Con el entorno virtual activado:

```powershell
python -m ruff check .
python -m ruff format --check .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Para aplicar el formato automáticamente: `python -m ruff format .`

### Pruebas

Las 126 pruebas están organizadas por módulo en `core/tests/` y
`portafolios/tests/`:

| Archivo | Cubre |
|---|---|
| `core/tests/test_exception_handlers.py` | Formato de cada tipo de error de la API. |
| `core/tests/test_utils.py` | `get_object`. |
| `test_models.py` | Restricciones de unicidad, rangos de valores, precisión decimal y orden por defecto sin JOINs. |
| `test_etl.py` | Carga del archivo real, idempotencia, recarga y cada validación del ETL. |
| `test_services.py` | Cálculo de las cantidades iniciales, validación del valor inicial y errores del comando. |
| `test_selectors.py` | Cálculo de x<sub>i,t</sub>, V<sub>t</sub> y w<sub>i,t</sub>, filtros de fecha y número de consultas. |
| `test_apis.py` | Respuestas de la API y sus errores 400, 404, 405 y 409. |
| `test_admin.py` | Admin de solo lectura. |
| `test_views.py` | Vista de gráficos y archivos estáticos. |

El JavaScript de los gráficos se verificó manualmente en el navegador, con el
rango completo, un rango filtrado, un rango inválido, un rango sin datos y el
ancho de un teléfono.

### Integración continua

El workflow de GitHub Actions (`.github/workflows/ci.yml`) se ejecuta en cada
pull request hacia `main` y en cada cambio publicado en `main`. Usa Python 3.15
y las dependencias fijadas en `requirements.txt`, y verifica:

- Compatibilidad de las dependencias instaladas.
- Revisión de código y formato con Ruff.
- Configuración de Django.
- Ausencia de cambios en los modelos sin su migración.
- Ejecución de todas las pruebas.

Los cambios se integraron mediante pull requests, uno por cada punto del
enunciado.
