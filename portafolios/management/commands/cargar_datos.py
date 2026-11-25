from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from portafolios.etl import ErrorValidacionETL, ejecutar_etl

ARCHIVO_POR_DEFECTO = settings.BASE_DIR / "data" / "datos.xlsx"


class Command(BaseCommand):
    help = (
        "Carga activos, portafolios, weights iniciales y precios desde el "
        "archivo Excel de la evaluación."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--archivo",
            type=Path,
            default=ARCHIVO_POR_DEFECTO,
            help=f"Ruta del archivo Excel (por defecto: {ARCHIVO_POR_DEFECTO}).",
        )

    def handle(self, *args, archivo, **options):
        if not archivo.is_file():
            raise CommandError(f"No existe el archivo {archivo}.")

        try:
            resumen = ejecutar_etl(archivo)
        except ErrorValidacionETL as error:
            detalle = "\n".join(f"- {mensaje}" for mensaje in error.errores)
            raise CommandError(f"El archivo no es válido:\n{detalle}") from error

        self.stdout.write(
            self.style.SUCCESS(
                f"Carga completada desde {archivo.name}: "
                f"{resumen.activos} activos, {resumen.portafolios} portafolios, "
                f"{resumen.posiciones} posiciones y {resumen.precios} precios."
            )
        )
