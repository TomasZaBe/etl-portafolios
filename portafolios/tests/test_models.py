from datetime import date
from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from portafolios.models import Activo, Portafolio, Posicion, Precio

FECHA_INICIO = date(2022, 2, 15)


class ModelosTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.activo = Activo.objects.create(nombre="EEUU")
        cls.portafolio = Portafolio.objects.create(nombre="portafolio 1")


class ActivoTests(ModelosTestCase):
    def test_nombre_es_unico(self):
        with self.assertRaises(IntegrityError):
            Activo.objects.create(nombre="EEUU")

    def test_str(self):
        self.assertEqual(str(self.activo), "EEUU")


class PortafolioTests(ModelosTestCase):
    def test_nombre_es_unico(self):
        with self.assertRaises(IntegrityError):
            Portafolio.objects.create(nombre="portafolio 1")

    def test_se_crea_sin_valor_ni_fecha_inicial(self):
        self.assertIsNone(self.portafolio.valor_inicial)
        self.assertIsNone(self.portafolio.fecha_inicio)

    def test_acepta_valor_y_fecha_inicial(self):
        portafolio = Portafolio.objects.create(
            nombre="portafolio 2",
            valor_inicial=Decimal("1000000000"),
            fecha_inicio=FECHA_INICIO,
        )
        portafolio.refresh_from_db()
        self.assertEqual(portafolio.valor_inicial, Decimal("1000000000.00"))

    def test_valor_inicial_debe_ser_positivo(self):
        with self.assertRaises(IntegrityError):
            Portafolio.objects.create(
                nombre="portafolio 2", valor_inicial=0, fecha_inicio=FECHA_INICIO
            )

    def test_acepta_fecha_inicio_sin_valor_inicial(self):
        portafolio = Portafolio.objects.create(
            nombre="portafolio 2", fecha_inicio=FECHA_INICIO
        )
        self.assertIsNone(portafolio.valor_inicial)

    def test_valor_inicial_requiere_fecha_inicio(self):
        with self.assertRaises(IntegrityError):
            Portafolio.objects.create(nombre="portafolio 2", valor_inicial=1)


class PrecioTests(ModelosTestCase):
    def test_es_unico_por_activo_y_fecha(self):
        Precio.objects.create(activo=self.activo, fecha=FECHA_INICIO, valor=1)
        with self.assertRaises(IntegrityError):
            Precio.objects.create(activo=self.activo, fecha=FECHA_INICIO, valor=2)

    def test_valor_debe_ser_positivo(self):
        with self.assertRaises(IntegrityError):
            Precio.objects.create(activo=self.activo, fecha=FECHA_INICIO, valor=0)

    def test_conserva_decimales_del_excel(self):
        precio = Precio.objects.create(
            activo=self.activo, fecha=FECHA_INICIO, valor=Decimal("390.26256")
        )
        precio.refresh_from_db()
        self.assertEqual(precio.valor, Decimal("390.26256"))


class PosicionTests(ModelosTestCase):
    def crear_posicion(self, weight_inicial=Decimal("0.28"), cantidad=None):
        return Posicion.objects.create(
            portafolio=self.portafolio,
            activo=self.activo,
            weight_inicial=weight_inicial,
            cantidad=cantidad,
        )

    def test_se_crea_sin_cantidad_hasta_calcularla(self):
        posicion = self.crear_posicion()
        self.assertIsNone(posicion.cantidad)

    def test_es_unica_por_portafolio_y_activo(self):
        self.crear_posicion()
        with self.assertRaises(IntegrityError):
            self.crear_posicion(weight_inicial=Decimal("0.30"))

    def test_acepta_weight_en_los_limites_0_y_1(self):
        otro_activo = Activo.objects.create(nombre="Europa")
        self.crear_posicion(weight_inicial=Decimal("0"))
        Posicion.objects.create(
            portafolio=self.portafolio,
            activo=otro_activo,
            weight_inicial=Decimal("1"),
        )
        self.assertEqual(Posicion.objects.count(), 2)

    def test_rechaza_weight_mayor_a_1(self):
        with self.assertRaises(IntegrityError):
            self.crear_posicion(weight_inicial=Decimal("1.01"))

    def test_rechaza_weight_negativo(self):
        with self.assertRaises(IntegrityError):
            self.crear_posicion(weight_inicial=Decimal("-0.01"))

    def test_rechaza_cantidad_negativa(self):
        with self.assertRaises(IntegrityError):
            self.crear_posicion(cantidad=Decimal("-1"))

    def test_conserva_precision_de_la_cantidad(self):
        posicion = self.crear_posicion(cantidad=Decimal("29839.4243124973"))
        posicion.refresh_from_db()
        self.assertEqual(posicion.cantidad, Decimal("29839.4243124973"))

    def test_relaciona_portafolio_y_activo(self):
        self.crear_posicion()
        self.assertQuerySetEqual(self.portafolio.activos.all(), [self.activo])
        self.assertQuerySetEqual(self.activo.portafolios.all(), [self.portafolio])

    def test_se_elimina_con_su_portafolio(self):
        self.crear_posicion()
        self.portafolio.delete()
        self.assertFalse(Posicion.objects.exists())
