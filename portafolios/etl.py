"""ETL que lee ``datos.xlsx`` y lo carga en la base de datos.

El proceso tiene tres etapas:

1. ``extraer``: lee las hojas ``weights`` y ``Precios`` del archivo.
2. ``transformar``: limpia y valida los datos sin tocar la base de datos.
3. ``cargar``: guarda los datos validados en una única transacción.

``ejecutar_etl`` encadena las tres etapas. La carga es idempotente: ejecutarla
varias veces con el mismo archivo deja la base de datos en el mismo estado.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
from django.db import transaction

from core.exceptions import ApplicationError
from portafolios.models import Activo, Portafolio, Posicion, Precio

HOJA_WEIGHTS = "weights"
HOJA_PRECIOS = "Precios"

# Los weights del archivo traen ruido de punto flotante (0.018000000000000002).
# Se redondean a la precisión de los campos del modelo.
DECIMALES_WEIGHT = 6
DECIMALES_PRECIO = 6
TOLERANCIA_SUMA_WEIGHTS = Decimal("0.000001")
MAX_EJEMPLOS_EN_ERROR = 5


class ErrorValidacionETL(ApplicationError):
    """El archivo no tiene el formato o los valores esperados.

    Reúne todos los errores encontrados en ``errores`` (y en ``extra``).
    """

    def __init__(self, errores: list[str]):
        self.errores = list(errores)
        super().__init__("El archivo no es válido.", extra={"errores": self.errores})


@dataclass(frozen=True)
class DatosPortafolios:
    """Datos validados y listos para cargar."""

    fecha_inicio: date
    activos: tuple[str, ...]
    # portafolio -> activo -> w_i,0
    weights: dict[str, dict[str, Decimal]]
    # (activo, fecha, p_i,t)
    precios: tuple[tuple[str, date, Decimal], ...]


@dataclass(frozen=True)
class ResumenCarga:
    activos: int
    portafolios: int
    posiciones: int
    precios: int


def ejecutar_etl(ruta: Path | str) -> ResumenCarga:
    df_weights, df_precios = extraer(ruta)
    datos = transformar(df_weights=df_weights, df_precios=df_precios)
    return cargar(datos)


# --- Extracción -------------------------------------------------------------


def extraer(ruta: Path | str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Lee las hojas de weights y precios.

    Los nombres de hoja se comparan sin distinguir mayúsculas, porque el
    enunciado habla de "Weights" y el archivo usa "weights".
    """
    try:
        with pd.ExcelFile(ruta) as libro:
            hojas = {nombre.strip().lower(): nombre for nombre in libro.sheet_names}
            faltantes = [
                hoja
                for hoja in (HOJA_WEIGHTS, HOJA_PRECIOS)
                if hoja.lower() not in hojas
            ]
            if faltantes:
                raise ErrorValidacionETL(
                    [f"Falta la hoja '{hoja}' en el archivo." for hoja in faltantes]
                )
            df_weights = pd.read_excel(libro, sheet_name=hojas[HOJA_WEIGHTS.lower()])
            df_precios = pd.read_excel(libro, sheet_name=hojas[HOJA_PRECIOS.lower()])
    except ErrorValidacionETL:
        raise
    except (OSError, ValueError) as error:
        raise ErrorValidacionETL([f"No se pudo leer el archivo: {error}"]) from error
    return df_weights, df_precios


# --- Transformación y validación --------------------------------------------


def transformar(
    *, df_weights: pd.DataFrame, df_precios: pd.DataFrame
) -> DatosPortafolios:
    """Limpia y valida ambas hojas y verifica que sean coherentes entre sí."""
    fecha_inicio, weights = _transformar_weights(df_weights)
    precios = _transformar_precios(df_precios)

    activos_weights = set(next(iter(weights.values())))
    activos_precios = set(precios.columns)
    fechas_precios = set(precios.index)

    errores = []
    if sin_precio := activos_weights - activos_precios:
        errores.append(
            f"Activos de '{HOJA_WEIGHTS}' sin columna en '{HOJA_PRECIOS}': "
            f"{_ejemplos(sorted(sin_precio))}."
        )
    if sin_weight := activos_precios - activos_weights:
        errores.append(
            f"Activos de '{HOJA_PRECIOS}' sin weight en '{HOJA_WEIGHTS}': "
            f"{_ejemplos(sorted(sin_weight))}."
        )
    if fecha_inicio not in fechas_precios:
        errores.append(
            f"No hay precios para la fecha de inicio {fecha_inicio:%Y-%m-%d}, "
            "necesarios para calcular las cantidades iniciales."
        )
    if errores:
        raise ErrorValidacionETL(errores)

    # Los activos se asocian por nombre: el orden de las filas en 'weights'
    # no coincide con el orden de las columnas en 'Precios'.
    filas_precios = tuple(
        (activo, fecha, precios.at[fecha, activo])
        for fecha in sorted(fechas_precios)
        for activo in sorted(activos_precios)
    )
    return DatosPortafolios(
        fecha_inicio=fecha_inicio,
        activos=tuple(sorted(activos_weights)),
        weights=weights,
        precios=filas_precios,
    )


def _transformar_weights(df: pd.DataFrame) -> tuple[date, dict]:
    """Columna A: fecha, columna B: activo, columnas C en adelante: portafolios."""
    df = _limpiar(df)
    if df.shape[1] < 3:
        raise ErrorValidacionETL(
            [
                f"La hoja '{HOJA_WEIGHTS}' debe tener las columnas fecha, activo "
                "y al menos un portafolio."
            ]
        )
    if df.empty:
        raise ErrorValidacionETL([f"La hoja '{HOJA_WEIGHTS}' no tiene datos."])

    columna_fecha, columna_activo, *columnas_portafolios = df.columns
    errores = []

    fechas = pd.to_datetime(df[columna_fecha], errors="coerce")
    if fechas.isna().any():
        errores.append(f"La hoja '{HOJA_WEIGHTS}' tiene fechas vacías o inválidas.")
    elif fechas.nunique() != 1:
        errores.append(
            f"La hoja '{HOJA_WEIGHTS}' debe tener una única fecha de inicio y tiene "
            f"{fechas.nunique()}."
        )

    activos = df[columna_activo].astype("string").str.strip()
    if activos.isna().any() or (activos == "").any():
        errores.append(f"La hoja '{HOJA_WEIGHTS}' tiene activos sin nombre.")
    elif duplicados := sorted(set(activos[activos.duplicated()])):
        errores.append(
            f"La hoja '{HOJA_WEIGHTS}' repite activos: {_ejemplos(duplicados)}."
        )

    nombres_portafolios = [str(columna).strip() for columna in columnas_portafolios]
    if any(nombre.startswith("Unnamed") for nombre in nombres_portafolios):
        errores.append(
            f"La hoja '{HOJA_WEIGHTS}' tiene columnas de portafolio sin nombre."
        )

    weights = {}
    for columna, portafolio in zip(columnas_portafolios, nombres_portafolios):
        valores = pd.to_numeric(df[columna], errors="coerce")
        if valores.isna().any():
            errores.append(
                f"El portafolio '{portafolio}' tiene weights vacíos o no numéricos."
            )
            continue
        weights_portafolio = {
            activo: _a_decimal(valor, DECIMALES_WEIGHT)
            for activo, valor in zip(activos, valores)
        }
        if fuera_de_rango := [
            activo
            for activo, valor in weights_portafolio.items()
            if not Decimal(0) <= valor <= Decimal(1)
        ]:
            errores.append(
                f"El portafolio '{portafolio}' tiene weights fuera del rango "
                f"[0, 1]: {_ejemplos(fuera_de_rango)}."
            )
        suma = sum(weights_portafolio.values())
        if abs(suma - 1) > TOLERANCIA_SUMA_WEIGHTS:
            errores.append(
                f"Los weights del portafolio '{portafolio}' suman {suma} y "
                "deben sumar 1."
            )
        weights[portafolio] = weights_portafolio

    if errores:
        raise ErrorValidacionETL(errores)
    return fechas.iloc[0].date(), weights


def _transformar_precios(df: pd.DataFrame) -> pd.DataFrame:
    """Columna A: fecha, columnas B en adelante: un activo por columna.

    Devuelve un DataFrame indexado por fecha, con un activo por columna y los
    precios como ``Decimal``.
    """
    df = _limpiar(df)
    if df.shape[1] < 2 or df.empty:
        raise ErrorValidacionETL(
            [f"La hoja '{HOJA_PRECIOS}' debe tener fechas y al menos un activo."]
        )

    columna_fecha, *columnas_activos = df.columns
    errores = []

    fechas = pd.to_datetime(df[columna_fecha], errors="coerce")
    if fechas.isna().any():
        errores.append(f"La hoja '{HOJA_PRECIOS}' tiene fechas vacías o inválidas.")
    elif duplicadas := sorted(set(fechas[fechas.duplicated()])):
        errores.append(
            f"La hoja '{HOJA_PRECIOS}' repite fechas: "
            f"{_ejemplos([f'{fecha:%Y-%m-%d}' for fecha in duplicadas])}."
        )

    nombres_activos = [str(columna).strip() for columna in columnas_activos]
    if any(nombre.startswith("Unnamed") for nombre in nombres_activos):
        errores.append(f"La hoja '{HOJA_PRECIOS}' tiene columnas de activo sin nombre.")

    valores = df[columnas_activos].apply(pd.to_numeric, errors="coerce")
    valores.columns = nombres_activos
    for activo in nombres_activos:
        columna = valores[activo]
        if columna.isna().any():
            errores.append(
                f"El activo '{activo}' tiene {int(columna.isna().sum())} precios "
                "vacíos o no numéricos."
            )
        elif (columna <= 0).any():
            errores.append(
                f"El activo '{activo}' tiene {int((columna <= 0).sum())} precios "
                "menores o iguales a 0."
            )

    if errores:
        raise ErrorValidacionETL(errores)

    valores.index = [fecha.date() for fecha in fechas]
    return valores.map(lambda valor: _a_decimal(valor, DECIMALES_PRECIO))


def _limpiar(df: pd.DataFrame) -> pd.DataFrame:
    """Descarta filas y columnas completamente vacías y espacios en los títulos."""
    df = df.dropna(how="all").dropna(axis="columns", how="all")
    df.columns = [str(columna).strip() for columna in df.columns]
    return df


def _a_decimal(valor: float, decimales: int) -> Decimal:
    return round(Decimal(str(valor)), decimales)


def _ejemplos(valores: list[str]) -> str:
    texto = ", ".join(str(valor) for valor in valores[:MAX_EJEMPLOS_EN_ERROR])
    restantes = len(valores) - MAX_EJEMPLOS_EN_ERROR
    return f"{texto} y {restantes} más" if restantes > 0 else texto


# --- Carga ------------------------------------------------------------------


@transaction.atomic
def cargar(datos: DatosPortafolios) -> ResumenCarga:
    """Inserta o actualiza los datos validados.

    Volver a cargar el archivo deja vacías las cantidades y el valor inicial
    de los portafolios, porque sus weights o precios iniciales pueden haber
    cambiado. Deben calcularse de nuevo después de cada carga.
    """
    Activo.objects.bulk_create(
        [Activo(nombre=nombre) for nombre in datos.activos], ignore_conflicts=True
    )
    activos = Activo.objects.in_bulk(datos.activos, field_name="nombre")

    portafolios = {}
    for nombre in datos.weights:
        portafolio, _ = Portafolio.objects.update_or_create(
            nombre=nombre,
            defaults={"fecha_inicio": datos.fecha_inicio, "valor_inicial": None},
        )
        portafolios[nombre] = portafolio

    # Un activo que ya no aparece en el archivo deja de pertenecer al portafolio.
    Posicion.objects.filter(portafolio__in=portafolios.values()).exclude(
        activo__nombre__in=datos.activos
    ).delete()
    Posicion.objects.bulk_create(
        [
            Posicion(
                portafolio=portafolios[portafolio],
                activo=activos[activo],
                weight_inicial=weight,
                cantidad=None,
            )
            for portafolio, weights in datos.weights.items()
            for activo, weight in weights.items()
        ],
        update_conflicts=True,
        unique_fields=["portafolio", "activo"],
        update_fields=["weight_inicial", "cantidad", "updated_at"],
    )

    Precio.objects.bulk_create(
        [
            Precio(activo=activos[activo], fecha=fecha, valor=valor)
            for activo, fecha, valor in datos.precios
        ],
        update_conflicts=True,
        unique_fields=["activo", "fecha"],
        update_fields=["valor", "updated_at"],
        batch_size=1000,
    )

    return ResumenCarga(
        activos=len(activos),
        portafolios=len(portafolios),
        posiciones=sum(len(weights) for weights in datos.weights.values()),
        precios=len(datos.precios),
    )
