from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse


class PortafoliosGraficosViewTests(TestCase):
    def setUp(self):
        self.respuesta = self.client.get(reverse("portafolios:graficos"))

    def test_responde_en_la_raiz(self):
        self.assertEqual(reverse("portafolios:graficos"), "/")
        self.assertEqual(self.respuesta.status_code, 200)
        self.assertTemplateUsed(self.respuesta, "portafolios/graficos.html")

    def test_entrega_las_urls_de_la_api_al_javascript(self):
        self.assertContains(
            self.respuesta, f'data-url-portafolios="{reverse("portafolios:api-list")}"'
        )
        self.assertContains(
            self.respuesta, 'data-url-evolucion="/api/portafolios/0/evolucion/"'
        )

    def test_incluye_filtros_de_fecha(self):
        self.assertContains(self.respuesta, 'name="fecha_inicio"')
        self.assertContains(self.respuesta, 'name="fecha_fin"')

    def test_incluye_graficos_y_scripts(self):
        self.assertContains(self.respuesta, 'id="grafico-valor-total"')
        self.assertContains(self.respuesta, "chart.js@4.4.1")
        self.assertContains(self.respuesta, "portafolios/graficos.js")

    def test_archivos_estaticos_existen(self):
        for archivo in ("portafolios/graficos.js", "portafolios/graficos.css"):
            self.assertIsNotNone(finders.find(archivo), archivo)

    def test_no_consulta_la_base_de_datos(self):
        # Los datos se obtienen desde el navegador a través de la API.
        with self.assertNumQueries(0):
            self.client.get(reverse("portafolios:graficos"))
