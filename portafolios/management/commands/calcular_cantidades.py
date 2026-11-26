from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from core.exceptions import ApplicationError
from portafolios.services import (
    VALOR_INICIAL_POR_DEFECTO,
    cantidades_iniciales_calcular,
)


def valor_decimal(texto: str) -> Decimal:
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        raise ValueError(texto) from None
    if not valor.is_finite():
        raise ValueError(texto)
    return valor


class Command(BaseCommand):
    help = (
        "Calcula las cantidades iniciales c_i,0 = w_i,0 * V_0 / p_i,0 de cada "
        "activo en cada portafolio."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--valor-inicial",
            type=valor_decimal,
            default=VALOR_INICIAL_POR_DEFECTO,
            help=f"Valor inicial V_0 de cada portafolio "
            f"(por defecto: {VALOR_INICIAL_POR_DEFECTO}).",
        )

    def handle(self, *args, valor_inicial, **options):
        try:
            resultado = cantidades_iniciales_calcular(valor_inicial=valor_inicial)
        except ApplicationError as error:
            raise CommandError(error.message) from error
        except ValidationError as error:
            raise CommandError(
                "Valor inicial inválido: " + " ".join(error.messages)
            ) from error

        for portafolio, posiciones in resultado.items():
            self.stdout.write(
                f"\n{portafolio} (V_0 = {portafolio.valor_inicial:,.2f} "
                f"al {portafolio.fecha_inicio:%Y-%m-%d})"
            )
            self.stdout.write(f"{'Activo':<20}{'w_i,0':>10}{'p_i,0':>16}{'c_i,0':>24}")
            for posicion in posiciones:
                self.stdout.write(
                    f"{posicion.activo.nombre:<20}"
                    f"{posicion.weight_inicial:>10.3f}"
                    f"{posicion.precio_inicial:>16,.5f}"
                    f"{posicion.cantidad:>24,.10f}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nCantidades iniciales calculadas para {len(resultado)} portafolios."
            )
        )
