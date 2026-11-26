from django.urls import reverse
from rest_framework.test import APITestCase

from portafolios.models import Portafolio, Posicion
from portafolios.tests.test_selectors import DIA_0, DIA_1, DIA_2, EvolucionTestCase


class PortafolioListApiTests(EvolucionTestCase, APITestCase):
    def test_lista_los_portafolios(self):
        respuesta = self.client.get(reverse("portafolios:api-list"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.json(),
            [
                {
                    "id": self.portafolio.id,
                    "nombre": "portafolio 1",
                    "fecha_inicio": "2022-02-15",
                    "valor_inicial": "1000.00",
                }
            ],
        )


class PortafolioEvolucionApiTests(EvolucionTestCase, APITestCase):
    def get(self, portafolio_id=None, **params):
        url = reverse(
            "portafolios:api-evolucion",
            kwargs={"portafolio_id": portafolio_id or self.portafolio.id},
        )
        return self.client.get(url, params)

    def test_devuelve_weights_y_valor_total_entre_fechas(self):
        respuesta = self.get(fecha_inicio="2022-02-16", fecha_fin="2022-02-16")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.json(),
            {
                "portafolio": {"id": self.portafolio.id, "nombre": "portafolio 1"},
                "fecha_inicio": "2022-02-16",
                "fecha_fin": "2022-02-16",
                "valores": [
                    {
                        "fecha": "2022-02-16",
                        "valor_total": 1500.0,
                        "activos": [
                            {"activo": "A", "monto": 1000.0, "weight": 0.6666666667},
                            {"activo": "B", "monto": 500.0, "weight": 0.3333333333},
                        ],
                    }
                ],
            },
        )

    def test_fechas_son_opcionales(self):
        respuesta = self.get()

        datos = respuesta.json()
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(datos["fecha_inicio"], DIA_0.isoformat())
        self.assertEqual(datos["fecha_fin"], DIA_2.isoformat())
        self.assertEqual(len(datos["valores"]), 3)

    def test_solo_fecha_inicio(self):
        datos = self.get(fecha_inicio=DIA_1.isoformat()).json()

        self.assertEqual(
            [v["fecha"] for v in datos["valores"]], ["2022-02-16", "2022-02-17"]
        )

    def test_rango_sin_datos(self):
        datos = self.get(fecha_inicio="2030-01-01").json()

        self.assertEqual(datos["valores"], [])
        self.assertIsNone(datos["fecha_inicio"])
        self.assertIsNone(datos["fecha_fin"])

    def test_rechaza_fecha_con_formato_invalido(self):
        respuesta = self.get(fecha_inicio="15/02/2022")

        self.assertEqual(respuesta.status_code, 400)
        datos = respuesta.json()
        self.assertEqual(datos["message"], "Error de validación")
        self.assertIn("fecha_inicio", datos["extra"]["fields"])

    def test_rechaza_fecha_fin_anterior_a_fecha_inicio(self):
        respuesta = self.get(fecha_inicio="2022-02-17", fecha_fin="2022-02-16")

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            respuesta.json(),
            {
                "message": "Error de validación",
                "extra": {
                    "fields": {
                        "fecha_fin": ["Debe ser igual o posterior a fecha_inicio."]
                    }
                },
            },
        )

    def test_portafolio_inexistente(self):
        respuesta = self.get(portafolio_id=999)

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(
            respuesta.json(), {"message": "No existe el portafolio 999.", "extra": {}}
        )

    def test_portafolio_sin_cantidades(self):
        Posicion.objects.update(cantidad=None)

        respuesta = self.get()

        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(
            respuesta.json(),
            {
                "message": "El portafolio 'portafolio 1' no tiene sus cantidades "
                "iniciales calculadas.",
                "extra": {},
            },
        )

    def test_solo_permite_get(self):
        url = reverse(
            "portafolios:api-evolucion", kwargs={"portafolio_id": self.portafolio.id}
        )

        respuesta = self.client.post(url)

        self.assertEqual(respuesta.status_code, 405)
        self.assertEqual(set(respuesta.json()), {"message", "extra"})

    def test_portafolio_recien_creado_sin_datos(self):
        nuevo = Portafolio.objects.create(nombre="nuevo")

        self.assertEqual(self.get(portafolio_id=nuevo.id).status_code, 409)
