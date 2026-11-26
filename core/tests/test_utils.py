from django.test import TestCase

from core.utils import get_object
from portafolios.models import Activo


class GetObjectTests(TestCase):
    def test_devuelve_el_objeto(self):
        activo = Activo.objects.create(nombre="EEUU")

        self.assertEqual(get_object(Activo, nombre="EEUU"), activo)

    def test_acepta_un_queryset(self):
        activo = Activo.objects.create(nombre="EEUU")

        self.assertEqual(get_object(Activo.objects.all(), pk=activo.pk), activo)

    def test_devuelve_none_si_no_existe(self):
        self.assertIsNone(get_object(Activo, nombre="no existe"))
