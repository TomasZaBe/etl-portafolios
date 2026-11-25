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

Actualmente no hay pruebas propias de la aplicación. Se incorporarán
junto con los modelos, la importación de datos y los cálculos.

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

Actualmente no hay pruebas propias de la aplicación. El workflow
ejecutará las pruebas que se incorporen durante el desarrollo.
