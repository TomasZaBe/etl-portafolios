import tempfile
from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.core.management import CommandError, call_command
from django.test import TestCase

from core.exceptions import ApplicationError
from portafolios.etl import ErrorValidacionETL, ejecutar_etl
from portafolios.models import Activo, Portafolio, Posicion, Precio

ARCHIVO_REAL = settings.BASE_DIR / "data" / "datos.xlsx"
FECHA_INICIO = datetime(2022, 2, 15)
FECHA_SIGUIENTE = datetime(2022, 2, 16)


def weights_base():
    # El orden de los activos es distinto al de las columnas de precios,
    # igual que en el archivo real.
    return pd.DataFrame(
        {
            "Fecha": [FECHA_INICIO, FECHA_INICIO],
            "activos": ["B", "A"],
            "portafolio 1": [0.4, 0.6],
            "portafolio 2": [0.5, 0.5],
        }
    )


def precios_base():
    return pd.DataFrame(
        {
            "Dates": [FECHA_INICIO, FECHA_SIGUIENTE],
            "A": [10.0, 11.0],
            "B": [20.0, 22.0],
        }
    )


class EtlTestCase(TestCase):
    def setUp(self):
        directorio = tempfile.TemporaryDirectory()
        self.addCleanup(directorio.cleanup)
        self.directorio = Path(directorio.name)

    def escribir_excel(self, hojas=None, nombre="datos.xlsx"):
        if hojas is None:
            hojas = {"weights": weights_base(), "Precios": precios_base()}
        ruta = self.directorio / nombre
        with pd.ExcelWriter(ruta) as escritor:
            for hoja, df in hojas.items():
                df.to_excel(escritor, sheet_name=hoja, index=False)
        return ruta

    def assertErrorETL(self, ruta, fragmento):
        with self.assertRaises(ErrorValidacionETL) as contexto:
            ejecutar_etl(ruta)
        self.assertTrue(
            any(fragmento in error for error in contexto.exception.errores),
            f"'{fragmento}' no aparece en {contexto.exception.errores}",
        )
        self.assertFalse(Activo.objects.exists())
        self.assertFalse(Precio.objects.exists())


class ArchivoRealTests(TestCase):
    """Carga el archivo entregado en el enunciado."""

    @classmethod
    def setUpTestData(cls):
        cls.resumen = ejecutar_etl(ARCHIVO_REAL)

    def test_resumen_de_la_carga(self):
        self.assertEqual(self.resumen.activos, 17)
        self.assertEqual(self.resumen.portafolios, 2)
        self.assertEqual(self.resumen.posiciones, 34)
        self.assertEqual(self.resumen.precios, 17 * 367)

    def test_registra_la_fecha_de_inicio_sin_valor_inicial(self):
        for portafolio in Portafolio.objects.all():
            self.assertEqual(portafolio.fecha_inicio, date(2022, 2, 15))
            self.assertIsNone(portafolio.valor_inicial)

    def test_weights_iniciales_suman_1_por_portafolio(self):
        for portafolio in Portafolio.objects.all():
            suma = sum(p.weight_inicial for p in portafolio.posiciones.all())
            self.assertEqual(suma, Decimal("1"))

    def test_limpia_el_ruido_de_punto_flotante(self):
        posicion = Posicion.objects.get(
            portafolio__nombre="portafolio 1", activo__nombre="Otros RV"
        )
        self.assertEqual(posicion.weight_inicial, Decimal("0.018"))

    def test_asocia_precios_por_nombre_de_activo(self):
        precio = Precio.objects.get(activo__nombre="Japón", fecha=date(2022, 2, 15))
        self.assertEqual(precio.valor, Decimal("390.26256"))

    def test_rango_de_fechas_de_precios(self):
        fechas = Precio.objects.values_list("fecha", flat=True)
        self.assertEqual(min(fechas), date(2022, 2, 15))
        self.assertEqual(max(fechas), date(2023, 2, 16))


class CargaTests(EtlTestCase):
    def test_asocia_weights_y_precios_por_nombre(self):
        ejecutar_etl(self.escribir_excel())

        posicion = Posicion.objects.get(
            portafolio__nombre="portafolio 1", activo__nombre="A"
        )
        self.assertEqual(posicion.weight_inicial, Decimal("0.6"))
        precio = Precio.objects.get(activo__nombre="A", fecha=FECHA_INICIO.date())
        self.assertEqual(precio.valor, Decimal("10"))

    def test_es_idempotente(self):
        ruta = self.escribir_excel()
        ejecutar_etl(ruta)
        ejecutar_etl(ruta)

        self.assertEqual(Activo.objects.count(), 2)
        self.assertEqual(Portafolio.objects.count(), 2)
        self.assertEqual(Posicion.objects.count(), 4)
        self.assertEqual(Precio.objects.count(), 4)

    def test_recarga_actualiza_precios_y_weights(self):
        ejecutar_etl(self.escribir_excel())
        precios = precios_base()
        precios.loc[0, "A"] = 12.5
        weights = weights_base()
        weights["portafolio 1"] = [0.3, 0.7]
        ejecutar_etl(self.escribir_excel({"weights": weights, "Precios": precios}))

        precio = Precio.objects.get(activo__nombre="A", fecha=FECHA_INICIO.date())
        self.assertEqual(precio.valor, Decimal("12.5"))
        posicion = Posicion.objects.get(
            portafolio__nombre="portafolio 1", activo__nombre="A"
        )
        self.assertEqual(posicion.weight_inicial, Decimal("0.7"))

    def test_recarga_limpia_cantidades_y_valor_inicial(self):
        ruta = self.escribir_excel()
        ejecutar_etl(ruta)
        Portafolio.objects.update(valor_inicial=1000)
        Posicion.objects.update(cantidad=5)

        ejecutar_etl(ruta)

        self.assertFalse(Portafolio.objects.filter(valor_inicial__isnull=False))
        self.assertFalse(Posicion.objects.filter(cantidad__isnull=False))

    def test_recarga_elimina_posiciones_de_activos_retirados(self):
        ejecutar_etl(self.escribir_excel())
        weights = pd.DataFrame(
            {
                "Fecha": [FECHA_INICIO],
                "activos": ["A"],
                "portafolio 1": [1.0],
                "portafolio 2": [1.0],
            }
        )
        precios = precios_base().drop(columns="B")
        ejecutar_etl(self.escribir_excel({"weights": weights, "Precios": precios}))

        self.assertEqual(
            set(Posicion.objects.values_list("activo__nombre", flat=True)), {"A"}
        )

    def test_ignora_filas_vacias_al_final(self):
        weights = pd.concat(
            [
                weights_base(),
                pd.DataFrame([[None] * 4] * 3, columns=weights_base().columns),
            ]
        )
        ejecutar_etl(
            self.escribir_excel({"weights": weights, "Precios": precios_base()})
        )

        self.assertEqual(Posicion.objects.count(), 4)

    def test_acepta_nombres_de_hoja_sin_distinguir_mayusculas(self):
        ruta = self.escribir_excel(
            {"Weights": weights_base(), "precios": precios_base()}
        )
        ejecutar_etl(ruta)

        self.assertEqual(Precio.objects.count(), 4)

    def test_quita_espacios_en_nombres_de_activos(self):
        weights = weights_base()
        weights["activos"] = [" B ", "A "]
        ejecutar_etl(
            self.escribir_excel({"weights": weights, "Precios": precios_base()})
        )

        self.assertEqual(
            set(Activo.objects.values_list("nombre", flat=True)), {"A", "B"}
        )


class ValidacionTests(EtlTestCase):
    def test_archivo_que_no_es_excel(self):
        ruta = self.directorio / "datos.xlsx"
        ruta.write_text("no es un excel")
        self.assertErrorETL(ruta, "No se pudo leer el archivo")

    def test_falta_una_hoja(self):
        ruta = self.escribir_excel({"weights": weights_base()})
        self.assertErrorETL(ruta, "Falta la hoja 'Precios'")

    def test_weights_que_no_suman_1(self):
        weights = weights_base()
        weights["portafolio 1"] = [0.4, 0.5]
        ruta = self.escribir_excel({"weights": weights, "Precios": precios_base()})
        self.assertErrorETL(ruta, "deben sumar 1")

    def test_weight_fuera_de_rango(self):
        weights = weights_base()
        weights["portafolio 1"] = [-0.2, 1.2]
        ruta = self.escribir_excel({"weights": weights, "Precios": precios_base()})
        self.assertErrorETL(ruta, "fuera del rango [0, 1]")

    def test_weight_vacio(self):
        weights = weights_base()
        weights.loc[0, "portafolio 1"] = None
        ruta = self.escribir_excel({"weights": weights, "Precios": precios_base()})
        self.assertErrorETL(ruta, "weights vacíos o no numéricos")

    def test_activo_repetido_en_weights(self):
        weights = weights_base()
        weights["activos"] = ["A", "A"]
        ruta = self.escribir_excel({"weights": weights, "Precios": precios_base()})
        self.assertErrorETL(ruta, "repite activos: A")

    def test_varias_fechas_de_inicio(self):
        weights = weights_base()
        weights["Fecha"] = [FECHA_INICIO, FECHA_SIGUIENTE]
        ruta = self.escribir_excel({"weights": weights, "Precios": precios_base()})
        self.assertErrorETL(ruta, "única fecha de inicio")

    def test_activo_sin_precios(self):
        ruta = self.escribir_excel(
            {"weights": weights_base(), "Precios": precios_base().drop(columns="B")}
        )
        self.assertErrorETL(ruta, "sin columna en 'Precios': B")

    def test_activo_con_precios_sin_weight(self):
        precios = precios_base()
        precios["C"] = [1.0, 1.0]
        ruta = self.escribir_excel({"weights": weights_base(), "Precios": precios})
        self.assertErrorETL(ruta, "sin weight en 'weights': C")

    def test_precio_vacio(self):
        precios = precios_base()
        precios.loc[1, "A"] = None
        ruta = self.escribir_excel({"weights": weights_base(), "Precios": precios})
        self.assertErrorETL(ruta, "'A' tiene 1 precios vacíos")

    def test_precio_no_positivo(self):
        precios = precios_base()
        precios.loc[1, "B"] = 0
        ruta = self.escribir_excel({"weights": weights_base(), "Precios": precios})
        self.assertErrorETL(ruta, "'B' tiene 1 precios menores o iguales a 0")

    def test_fecha_de_precio_repetida(self):
        precios = precios_base()
        precios["Dates"] = [FECHA_INICIO, FECHA_INICIO]
        ruta = self.escribir_excel({"weights": weights_base(), "Precios": precios})
        self.assertErrorETL(ruta, "repite fechas: 2022-02-15")

    def test_sin_precios_en_la_fecha_de_inicio(self):
        precios = precios_base()
        precios["Dates"] = [FECHA_SIGUIENTE, datetime(2022, 2, 17)]
        ruta = self.escribir_excel({"weights": weights_base(), "Precios": precios})
        self.assertErrorETL(ruta, "No hay precios para la fecha de inicio")

    def test_es_un_application_error_con_los_errores_en_extra(self):
        ruta = self.escribir_excel({"weights": weights_base()})

        with self.assertRaises(ApplicationError) as contexto:
            ejecutar_etl(ruta)
        self.assertEqual(contexto.exception.message, "El archivo no es válido.")
        self.assertEqual(
            contexto.exception.extra,
            {"errores": ["Falta la hoja 'Precios' en el archivo."]},
        )

    def test_informa_todos_los_errores_de_una_hoja(self):
        weights = weights_base()
        weights["portafolio 1"] = [0.4, 0.5]
        weights["portafolio 2"] = [0.9, 0.5]
        ruta = self.escribir_excel({"weights": weights, "Precios": precios_base()})

        with self.assertRaises(ErrorValidacionETL) as contexto:
            ejecutar_etl(ruta)
        self.assertEqual(len(contexto.exception.errores), 2)


class ComandoCargarDatosTests(EtlTestCase):
    def test_carga_y_muestra_resumen(self):
        salida = StringIO()
        call_command("cargar_datos", archivo=self.escribir_excel(), stdout=salida)

        self.assertIn(
            "2 activos, 2 portafolios, 4 posiciones y 4 precios", salida.getvalue()
        )

    def test_archivo_inexistente(self):
        with self.assertRaisesMessage(CommandError, "No existe el archivo"):
            call_command("cargar_datos", archivo=self.directorio / "no_existe.xlsx")

    def test_archivo_invalido_muestra_los_errores(self):
        ruta = self.escribir_excel({"weights": weights_base()})
        with self.assertRaisesMessage(CommandError, "- Falta la hoja 'Precios'"):
            call_command("cargar_datos", archivo=ruta)
