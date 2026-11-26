from datetime import date
from decimal import Decimal

from django.test import TestCase

from portafolios.etl import ejecutar_etl
from portafolios.models import Activo, Portafolio, Posicion, Precio
from portafolios.selectors import (
    ErrorPortafolioSinCantidades,
    portafolio_evolucion,
    portafolio_list,
)
from portafolios.services import (
    cantidades_iniciales_calcular,
    portafolio_cantidades_iniciales_calcular,
)
from portafolios.tests.test_etl import ARCHIVO_REAL

DIA_0 = date(2022, 2, 15)
DIA_1 = date(2022, 2, 16)
DIA_2 = date(2022, 2, 17)
ANTES_DEL_INICIO = date(2022, 2, 14)


class EvolucionTestCase(TestCase):
    """Portafolio con V_0 = 1000 y dos activos al 50 %.

    p_A = 10, 20, 5 y p_B = 20, 20, 20 en los días 0, 1 y 2.
    Por lo tanto c_A = 50 y c_B = 25.
    """

    @classmethod
    def setUpTestData(cls):
        cls.activo_a = Activo.objects.create(nombre="A")
        cls.activo_b = Activo.objects.create(nombre="B")
        cls.portafolio = Portafolio.objects.create(
            nombre="portafolio 1", fecha_inicio=DIA_0
        )
        for activo in (cls.activo_a, cls.activo_b):
            Posicion.objects.create(
                portafolio=cls.portafolio, activo=activo, weight_inicial="0.5"
            )
        precios = {
            cls.activo_a: [
                (ANTES_DEL_INICIO, 99),
                (DIA_0, 10),
                (DIA_1, 20),
                (DIA_2, 5),
            ],
            cls.activo_b: [
                (ANTES_DEL_INICIO, 99),
                (DIA_0, 20),
                (DIA_1, 20),
                (DIA_2, 20),
            ],
        }
        Precio.objects.bulk_create(
            Precio(activo=activo, fecha=fecha, valor=valor)
            for activo, serie in precios.items()
            for fecha, valor in serie
        )
        portafolio_cantidades_iniciales_calcular(
            portafolio=cls.portafolio, valor_inicial=Decimal("1000")
        )

    def evolucion(self, **kwargs):
        return portafolio_evolucion(portafolio=self.portafolio, **kwargs)


class PortafolioEvolucionTests(EvolucionTestCase):
    def test_en_la_fecha_de_inicio_reproduce_v0_y_los_weights_iniciales(self):
        inicio = self.evolucion(fecha_fin=DIA_0)[0]

        self.assertEqual(inicio.fecha, DIA_0)
        self.assertEqual(inicio.valor_total, 1000)
        self.assertEqual([a.weight for a in inicio.activos], [0.5, 0.5])

    def test_calcula_montos_valor_total_y_weights_con_cantidades_fijas(self):
        dia_1 = self.evolucion(fecha_inicio=DIA_1, fecha_fin=DIA_1)[0]

        # x_A = 20 * 50 = 1000, x_B = 20 * 25 = 500, V = 1500
        self.assertEqual(dia_1.valor_total, 1500)
        self.assertEqual([a.activo for a in dia_1.activos], ["A", "B"])
        self.assertEqual([a.monto for a in dia_1.activos], [1000, 500])
        self.assertAlmostEqual(dia_1.activos[0].weight, 2 / 3)
        self.assertAlmostEqual(dia_1.activos[1].weight, 1 / 3)

    def test_weights_suman_1_en_cada_fecha(self):
        for valor in self.evolucion():
            self.assertAlmostEqual(sum(a.weight for a in valor.activos), 1)

    def test_filtra_por_rango_de_fechas_inclusivo(self):
        fechas = [v.fecha for v in self.evolucion(fecha_inicio=DIA_1, fecha_fin=DIA_2)]

        self.assertEqual(fechas, [DIA_1, DIA_2])

    def test_sin_fechas_devuelve_todo_el_rango_desde_el_inicio(self):
        fechas = [v.fecha for v in self.evolucion()]

        self.assertEqual(fechas, [DIA_0, DIA_1, DIA_2])

    def test_ignora_precios_anteriores_a_la_fecha_de_inicio(self):
        fechas = [v.fecha for v in self.evolucion(fecha_inicio=ANTES_DEL_INICIO)]

        self.assertEqual(fechas[0], DIA_0)

    def test_rango_sin_precios_devuelve_lista_vacia(self):
        self.assertEqual(self.evolucion(fecha_inicio=date(2030, 1, 1)), [])

    def test_no_mezcla_activos_de_otros_portafolios(self):
        otro = Portafolio.objects.create(nombre="portafolio 2", fecha_inicio=DIA_0)
        Posicion.objects.create(portafolio=otro, activo=self.activo_a, weight_inicial=1)
        portafolio_cantidades_iniciales_calcular(
            portafolio=otro, valor_inicial=Decimal("1000")
        )

        dia_1 = portafolio_evolucion(portafolio=otro, fecha_inicio=DIA_1)[0]
        self.assertEqual([a.activo for a in dia_1.activos], ["A"])
        self.assertEqual(dia_1.valor_total, 2000)
        # El portafolio original no cambia.
        self.assertEqual(self.evolucion(fecha_inicio=DIA_1)[0].valor_total, 1500)

    def test_hace_una_sola_consulta_para_los_calculos(self):
        # 1 consulta para verificar las cantidades + 1 para los cálculos.
        with self.assertNumQueries(2):
            self.evolucion()

    def test_requiere_cantidades_calculadas(self):
        Posicion.objects.filter(activo=self.activo_a).update(cantidad=None)

        with self.assertRaises(ErrorPortafolioSinCantidades):
            self.evolucion()

    def test_requiere_valor_inicial(self):
        Portafolio.objects.filter(pk=self.portafolio.pk).update(valor_inicial=None)
        self.portafolio.refresh_from_db()

        with self.assertRaises(ErrorPortafolioSinCantidades):
            self.evolucion()

    def test_requiere_posiciones(self):
        vacio = Portafolio.objects.create(
            nombre="vacío", fecha_inicio=DIA_0, valor_inicial=1000
        )

        with self.assertRaises(ErrorPortafolioSinCantidades):
            portafolio_evolucion(portafolio=vacio)


class PortafolioListTests(EvolucionTestCase):
    def test_ordena_por_nombre(self):
        Portafolio.objects.create(nombre="a primero")

        self.assertEqual(
            [p.nombre for p in portafolio_list()], ["a primero", "portafolio 1"]
        )


class EvolucionArchivoRealTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ejecutar_etl(ARCHIVO_REAL)
        cantidades_iniciales_calcular()

    def test_rango_completo_por_portafolio(self):
        for portafolio in Portafolio.objects.all():
            valores = portafolio_evolucion(portafolio=portafolio)

            self.assertEqual(len(valores), 367)
            self.assertEqual(valores[0].valor_total, 1_000_000_000)
            for valor in valores:
                self.assertEqual(len(valor.activos), 17)
                self.assertAlmostEqual(sum(a.weight for a in valor.activos), 1)

    def test_weights_iniciales_coinciden_con_el_excel(self):
        portafolio = Portafolio.objects.get(nombre="portafolio 1")
        inicio = portafolio_evolucion(portafolio=portafolio, fecha_fin=DIA_0)[0]
        weights = {a.activo: a.weight for a in inicio.activos}

        self.assertAlmostEqual(weights["EEUU"], 0.28)
        self.assertAlmostEqual(weights["Europa"], 0.087)
