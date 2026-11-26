from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from portafolios.models import Activo, Portafolio, Posicion, Precio


class AdminSoloLecturaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_superuser(
            username="admin", password="clave-de-prueba"
        )
        cls.activo = Activo.objects.create(nombre="EEUU")
        cls.portafolio = Portafolio.objects.create(nombre="portafolio 1")
        cls.posicion = Posicion.objects.create(
            portafolio=cls.portafolio, activo=cls.activo, weight_inicial=1
        )
        cls.precio = Precio.objects.create(
            activo=cls.activo, fecha="2022-02-15", valor=10
        )

    def setUp(self):
        self.client.force_login(self.usuario)

    def test_permite_ver_los_listados_y_detalles(self):
        for objeto in (self.activo, self.portafolio, self.posicion, self.precio):
            meta = objeto._meta
            with self.subTest(modelo=meta.model_name):
                listado = reverse(
                    f"admin:{meta.app_label}_{meta.model_name}_changelist"
                )
                detalle = reverse(
                    f"admin:{meta.app_label}_{meta.model_name}_change", args=[objeto.pk]
                )
                self.assertEqual(self.client.get(listado).status_code, 200)
                self.assertEqual(self.client.get(detalle).status_code, 200)

    def test_no_permite_agregar(self):
        for modelo in ("activo", "portafolio", "posicion", "precio"):
            with self.subTest(modelo=modelo):
                url = reverse(f"admin:portafolios_{modelo}_add")
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_no_permite_modificar(self):
        url = reverse("admin:portafolios_posicion_change", args=[self.posicion.pk])

        self.client.post(url, {"weight_inicial": "0.5", "cantidad": "99"})

        self.posicion.refresh_from_db()
        self.assertEqual(self.posicion.weight_inicial, 1)
        self.assertIsNone(self.posicion.cantidad)

    def test_no_permite_eliminar(self):
        url = reverse("admin:portafolios_portafolio_delete", args=[self.portafolio.pk])

        self.assertEqual(self.client.post(url, {"post": "yes"}).status_code, 403)
        self.assertTrue(Portafolio.objects.filter(pk=self.portafolio.pk).exists())
