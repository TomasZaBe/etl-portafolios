"""Selectores: consultas de solo lectura sobre los portafolios."""

from dataclasses import dataclass
from datetime import date
from itertools import groupby
from operator import itemgetter

from django.db.models import Count, F, FloatField, Q, QuerySet, Sum, Window
from django.db.models.functions import Cast

from portafolios.models import Portafolio, Precio

DECIMALES_MONTO = 2
DECIMALES_WEIGHT = 10


class ErrorPortafolioSinCantidades(Exception):
    """El portafolio no tiene sus cantidades iniciales calculadas."""


@dataclass(frozen=True)
class ActivoEnFecha:
    activo: str
    monto: float
    weight: float


@dataclass(frozen=True)
class ValorEnFecha:
    fecha: date
    valor_total: float
    activos: list[ActivoEnFecha]


def portafolio_list() -> QuerySet[Portafolio]:
    return Portafolio.objects.order_by("nombre")


def portafolio_evolucion(
    *,
    portafolio: Portafolio,
    fecha_inicio: date | None = None,
    fecha_fin: date | None = None,
) -> list[ValorEnFecha]:
    """Devuelve V_t y, para cada activo, x_i,t y w_i,t entre dos fechas.

    Con c_i,t = c_i,0 constante:

    - x_i,t = p_i,t * c_i,0
    - V_t = sum_i x_i,t
    - w_i,t = x_i,t / V_t

    Los tres valores se calculan en la base de datos con una única consulta
    del ORM: une cada precio con la posición del activo en el portafolio y
    obtiene V_t con una función de ventana que suma los montos de cada fecha.

    Solo se consideran fechas desde la fecha de inicio del portafolio, porque
    antes de esa fecha las cantidades no están definidas. Si no se indican
    fechas, se devuelve todo el rango disponible.
    """
    posiciones = portafolio.posiciones.aggregate(
        total=Count("pk"), sin_cantidad=Count("pk", filter=Q(cantidad__isnull=True))
    )
    if (
        portafolio.valor_inicial is None
        or posiciones["total"] == 0
        or posiciones["sin_cantidad"] > 0
    ):
        raise ErrorPortafolioSinCantidades(
            f"El portafolio '{portafolio}' no tiene sus cantidades iniciales "
            "calculadas."
        )

    filtros = {
        "activo__posiciones__portafolio": portafolio,
        "fecha__gte": max(filter(None, [fecha_inicio, portafolio.fecha_inicio])),
    }
    if fecha_fin is not None:
        filtros["fecha__lte"] = fecha_fin

    # Un único filter() para que el JOIN con Posicion se reutilice en las
    # anotaciones. Se convierte a float porque SQLite opera los decimales como
    # punto flotante y la API entrega números JSON.
    filas = (
        Precio.objects.filter(**filtros)
        .annotate(
            monto=Cast("valor", FloatField())
            * Cast("activo__posiciones__cantidad", FloatField())
        )
        .annotate(valor_total=Window(Sum("monto"), partition_by=F("fecha")))
        .annotate(weight=F("monto") / F("valor_total"))
        .order_by("fecha", "activo__nombre")
        .values("fecha", "activo__nombre", "monto", "valor_total", "weight")
    )

    return [
        ValorEnFecha(
            fecha=fecha,
            valor_total=round(filas_fecha[0]["valor_total"], DECIMALES_MONTO),
            activos=[
                ActivoEnFecha(
                    activo=fila["activo__nombre"],
                    monto=round(fila["monto"], DECIMALES_MONTO),
                    weight=round(fila["weight"], DECIMALES_WEIGHT),
                )
                for fila in filas_fecha
            ],
        )
        for fecha, grupo in groupby(filas, key=itemgetter("fecha"))
        for filas_fecha in [list(grupo)]
    ]
