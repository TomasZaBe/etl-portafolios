"""Servicios con la lógica de negocio que modifica los portafolios."""

from decimal import Decimal

from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.utils import timezone

from portafolios.models import Portafolio, Posicion, Precio

VALOR_INICIAL_POR_DEFECTO = Decimal("1000000000")

# Precisión del campo Posicion.cantidad.
PRECISION_CANTIDAD = Decimal("1E-10")


class ErrorCalculoCantidades(Exception):
    """Faltan los datos necesarios para calcular las cantidades iniciales."""


@transaction.atomic
def portafolio_cantidades_iniciales_calcular(
    *, portafolio: Portafolio, valor_inicial: Decimal = VALOR_INICIAL_POR_DEFECTO
) -> list[Posicion]:
    """Calcula y guarda c_i,0 = w_i,0 * V_0 / p_i,0 para cada posición.

    Los precios iniciales p_i,0 se obtienen con el ORM en la misma consulta que
    las posiciones. La división se hace en Python con ``Decimal`` porque SQLite
    opera los decimales como números de punto flotante.

    También guarda V_0 en el portafolio. Las cantidades se mantienen constantes
    en el tiempo (c_i,t = c_i,0), por lo que este cálculo se hace una sola vez
    por carga de datos.
    """
    valor_inicial = Decimal(valor_inicial)
    if valor_inicial <= 0:
        raise ErrorCalculoCantidades("El valor inicial debe ser mayor que 0.")
    if portafolio.fecha_inicio is None:
        raise ErrorCalculoCantidades(
            f"El portafolio '{portafolio}' no tiene fecha de inicio. "
            "Cargue los datos antes de calcular las cantidades."
        )

    precio_inicial = Precio.objects.filter(
        activo=OuterRef("activo"), fecha=portafolio.fecha_inicio
    ).values("valor")[:1]
    posiciones = list(
        Posicion.objects.filter(portafolio=portafolio)
        .select_related("activo")
        .annotate(precio_inicial=Subquery(precio_inicial))
        .order_by("activo__nombre")
    )

    if not posiciones:
        raise ErrorCalculoCantidades(f"El portafolio '{portafolio}' no tiene activos.")
    if sin_precio := [p.activo.nombre for p in posiciones if p.precio_inicial is None]:
        raise ErrorCalculoCantidades(
            f"No hay precio al {portafolio.fecha_inicio:%Y-%m-%d} para: "
            f"{', '.join(sin_precio)}."
        )

    # bulk_update no actualiza los campos auto_now.
    ahora = timezone.now()
    for posicion in posiciones:
        posicion.cantidad = (
            posicion.weight_inicial * valor_inicial / posicion.precio_inicial
        ).quantize(PRECISION_CANTIDAD)
        posicion.updated_at = ahora
    Posicion.objects.bulk_update(posiciones, ["cantidad", "updated_at"])

    portafolio.valor_inicial = valor_inicial
    portafolio.full_clean()
    portafolio.save(update_fields=["valor_inicial", "updated_at"])
    return posiciones


@transaction.atomic
def cantidades_iniciales_calcular(
    *, valor_inicial: Decimal = VALOR_INICIAL_POR_DEFECTO
) -> dict[Portafolio, list[Posicion]]:
    """Calcula las cantidades iniciales de todos los portafolios.

    Si algún portafolio no puede calcularse, no se guarda ninguno.
    """
    portafolios = list(Portafolio.objects.order_by("nombre"))
    if not portafolios:
        raise ErrorCalculoCantidades(
            "No hay portafolios. Cargue los datos antes de calcular las cantidades."
        )
    return {
        portafolio: portafolio_cantidades_iniciales_calcular(
            portafolio=portafolio, valor_inicial=valor_inicial
        )
        for portafolio in portafolios
    }
