from datetime import date
from decimal import Decimal
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.test import TestCase

from core.exceptions import ApplicationError
from portafolios.etl import ejecutar_etl
from portafolios.models import Activo, Portafolio, Posicion, Precio
from portafolios.services import (
    ErrorCalculoCantidades,
    cantidades_iniciales_calcular,
    portafolio_cantidades_iniciales_calcular,
)
from portafolios.tests.test_etl import ARCHIVO_REAL

FECHA_INICIO = date(2022, 2, 15)
FECHA_SIGUIENTE = date(2022, 2, 16)


class CantidadesTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.activo_a = Activo.objects.create(nombre="A")
        cls.activo_b = Activo.objects.create(nombre="B")
        cls.portafolio = Portafolio.objects.create(
            nombre="portafolio 1", fecha_inicio=FECHA_INICIO
        )
        Posicion.objects.create(
            portafolio=cls.portafolio, activo=cls.activo_a, weight_inicial="0.6"
        )
        Posicion.objects.create(
            portafolio=cls.portafolio, activo=cls.activo_b, weight_inicial="0.4"
        )
        Precio.objects.bulk_create(
            [
                Precio(activo=cls.activo_a, fecha=FECHA_INICIO, valor=10),
                Precio(activo=cls.activo_b, fecha=FECHA_INICIO, valor=3),
                # Los precios de otras fechas no deben usarse.
                Precio(activo=cls.activo_a, fecha=FECHA_SIGUIENTE, valor=20),
                Precio(activo=cls.activo_b, fecha=FECHA_SIGUIENTE, valor=6),
            ]
        )

    def cantidad(self, activo, portafolio=None):
        return Posicion.objects.get(
            portafolio=portafolio or self.portafolio, activo=activo
        ).cantidad


class PortafolioCantidadesInicialesTests(CantidadesTestCase):
    def test_calcula_cantidad_con_el_precio_de_la_fecha_de_inicio(self):
        portafolio_cantidades_iniciales_calcular(
            portafolio=self.portafolio, valor_inicial=Decimal("1000")
        )

        # 0.6 * 1000 / 10
        self.assertEqual(self.cantidad(self.activo_a), Decimal("60"))

    def test_redondea_a_10_decimales(self):
        portafolio_cantidades_iniciales_calcular(
            portafolio=self.portafolio, valor_inicial=Decimal("1000")
        )

        # 0.4 * 1000 / 3
        self.assertEqual(self.cantidad(self.activo_b), Decimal("133.3333333333"))

    def test_guarda_el_valor_inicial_en_el_portafolio(self):
        portafolio_cantidades_iniciales_calcular(
            portafolio=self.portafolio, valor_inicial=Decimal("1000")
        )

        self.portafolio.refresh_from_db()
        self.assertEqual(self.portafolio.valor_inicial, Decimal("1000"))

    def test_usa_mil_millones_por_defecto(self):
        portafolio_cantidades_iniciales_calcular(portafolio=self.portafolio)

        self.assertEqual(self.cantidad(self.activo_a), Decimal("60000000"))

    def test_devuelve_posiciones_con_precio_inicial(self):
        posiciones = portafolio_cantidades_iniciales_calcular(
            portafolio=self.portafolio, valor_inicial=Decimal("1000")
        )

        self.assertEqual(
            [(p.activo.nombre, p.precio_inicial) for p in posiciones],
            [("A", Decimal("10")), ("B", Decimal("3"))],
        )

    def test_recalcular_reemplaza_las_cantidades(self):
        portafolio_cantidades_iniciales_calcular(
            portafolio=self.portafolio, valor_inicial=Decimal("1000")
        )
        portafolio_cantidades_iniciales_calcular(
            portafolio=self.portafolio, valor_inicial=Decimal("2000")
        )

        self.assertEqual(self.cantidad(self.activo_a), Decimal("120"))

    def test_weight_cero_da_cantidad_cero(self):
        Posicion.objects.filter(activo=self.activo_a).update(weight_inicial=0)

        portafolio_cantidades_iniciales_calcular(
            portafolio=self.portafolio, valor_inicial=Decimal("1000")
        )

        self.assertEqual(self.cantidad(self.activo_a), Decimal("0"))

    def test_rechaza_valor_inicial_no_positivo(self):
        with self.assertRaisesMessage(ErrorCalculoCantidades, "mayor que 0"):
            portafolio_cantidades_iniciales_calcular(
                portafolio=self.portafolio, valor_inicial=Decimal("0")
            )

    def test_rechaza_valor_inicial_no_finito(self):
        for valor in ("NaN", "Infinity"):
            with self.subTest(valor=valor):
                with self.assertRaisesMessage(ErrorCalculoCantidades, "mayor que 0"):
                    portafolio_cantidades_iniciales_calcular(
                        portafolio=self.portafolio, valor_inicial=Decimal(valor)
                    )

    def test_rechaza_valor_inicial_con_mas_de_2_decimales(self):
        with self.assertRaises(ValidationError):
            portafolio_cantidades_iniciales_calcular(
                portafolio=self.portafolio, valor_inicial=Decimal("1000.555")
            )

        self.assertIsNone(self.cantidad(self.activo_a))

    def test_rechaza_valor_inicial_con_demasiados_digitos(self):
        with self.assertRaises(ValidationError):
            portafolio_cantidades_iniciales_calcular(
                portafolio=self.portafolio, valor_inicial=Decimal("1E25")
            )

    def test_rechaza_cantidad_que_excede_la_precision_y_no_guarda_nada(self):
        # Con un precio inicial muy bajo la cantidad supera los 18 dígitos
        # enteros que admite el campo.
        Precio.objects.filter(activo=self.activo_b, fecha=FECHA_INICIO).update(
            valor=Decimal("0.000001")
        )

        with self.assertRaisesMessage(ErrorCalculoCantidades, "excede la precisión"):
            portafolio_cantidades_iniciales_calcular(
                portafolio=self.portafolio, valor_inicial=Decimal("1E17")
            )

        self.assertIsNone(self.cantidad(self.activo_a))

    def test_es_un_application_error(self):
        self.assertTrue(issubclass(ErrorCalculoCantidades, ApplicationError))

    def test_requiere_fecha_de_inicio(self):
        portafolio = Portafolio.objects.create(nombre="sin fecha")

        with self.assertRaisesMessage(ErrorCalculoCantidades, "no tiene fecha"):
            portafolio_cantidades_iniciales_calcular(portafolio=portafolio)

    def test_requiere_posiciones(self):
        portafolio = Portafolio.objects.create(
            nombre="vacío", fecha_inicio=FECHA_INICIO
        )

        with self.assertRaisesMessage(ErrorCalculoCantidades, "no tiene activos"):
            portafolio_cantidades_iniciales_calcular(portafolio=portafolio)

    def test_requiere_precio_en_la_fecha_de_inicio_y_no_guarda_nada(self):
        Precio.objects.filter(activo=self.activo_b, fecha=FECHA_INICIO).delete()

        with self.assertRaisesMessage(ErrorCalculoCantidades, "para: B"):
            portafolio_cantidades_iniciales_calcular(portafolio=self.portafolio)

        self.assertIsNone(self.cantidad(self.activo_a))
        self.portafolio.refresh_from_db()
        self.assertIsNone(self.portafolio.valor_inicial)


class CantidadesInicialesTodosLosPortafoliosTests(CantidadesTestCase):
    def test_calcula_todos_los_portafolios(self):
        otro = Portafolio.objects.create(
            nombre="portafolio 2", fecha_inicio=FECHA_INICIO
        )
        Posicion.objects.create(portafolio=otro, activo=self.activo_a, weight_inicial=1)

        resultado = cantidades_iniciales_calcular(valor_inicial=Decimal("1000"))

        self.assertEqual(list(resultado), [self.portafolio, otro])
        self.assertEqual(self.cantidad(self.activo_a, otro), Decimal("100"))

    def test_si_un_portafolio_falla_no_guarda_ninguno(self):
        Portafolio.objects.create(nombre="portafolio 2", fecha_inicio=FECHA_INICIO)

        with self.assertRaises(ErrorCalculoCantidades):
            cantidades_iniciales_calcular(valor_inicial=Decimal("1000"))

        self.assertIsNone(self.cantidad(self.activo_a))

    def test_requiere_portafolios(self):
        Portafolio.objects.all().delete()

        with self.assertRaisesMessage(ErrorCalculoCantidades, "No hay portafolios"):
            cantidades_iniciales_calcular()


class CantidadesArchivoRealTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ejecutar_etl(ARCHIVO_REAL)
        cantidades_iniciales_calcular()

    def test_cantidad_de_eeuu(self):
        posicion = Posicion.objects.get(
            portafolio__nombre="portafolio 1", activo__nombre="EEUU"
        )
        # 0.28 * 1.000.000.000 / 9383.57
        self.assertEqual(posicion.cantidad, Decimal("29839.3894860911"))

    def test_cantidades_reconstruyen_el_valor_inicial(self):
        for portafolio in Portafolio.objects.all():
            valor = sum(
                posicion.cantidad
                * Precio.objects.get(
                    activo=posicion.activo, fecha=portafolio.fecha_inicio
                ).valor
                for posicion in portafolio.posiciones.all()
            )
            self.assertAlmostEqual(valor, Decimal("1000000000"), delta=Decimal("1E-5"))

    def test_todas_las_posiciones_tienen_cantidad(self):
        self.assertFalse(Posicion.objects.filter(cantidad__isnull=True).exists())


class ComandoCalcularCantidadesTests(CantidadesTestCase):
    def test_muestra_las_cantidades(self):
        salida = StringIO()
        call_command("calcular_cantidades", valor_inicial="1000", stdout=salida)

        texto = salida.getvalue()
        self.assertIn("portafolio 1 (V_0 = 1,000.00 al 2022-02-15)", texto)
        self.assertIn("60.0000000000", texto)
        self.assertIn("calculadas para 1 portafolios", texto)

    def test_informa_errores(self):
        Portafolio.objects.all().delete()

        with self.assertRaisesMessage(CommandError, "No hay portafolios"):
            call_command("calcular_cantidades")

    def test_valor_inicial_invalido_da_un_mensaje_claro(self):
        for valor in ("1000.555", "1E25"):
            with self.subTest(valor=valor):
                with self.assertRaisesMessage(CommandError, "Valor inicial inválido"):
                    call_command("calcular_cantidades", valor_inicial=valor)

    def test_rechaza_valores_no_numericos_o_no_finitos(self):
        for valor in ("abc", "NaN", "Infinity"):
            with self.subTest(valor=valor):
                with self.assertRaisesMessage(
                    CommandError, f"'{valor}' no es un número válido."
                ):
                    call_command("calcular_cantidades", f"--valor-inicial={valor}")
