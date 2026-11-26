from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.test import SimpleTestCase
from rest_framework import exceptions, serializers

from core.exception_handlers import manejador_de_excepciones
from core.exceptions import ApplicationError


class ErrorDePrueba(ApplicationError):
    status_code = 409


class ManejadorDeExcepcionesTests(SimpleTestCase):
    def manejar(self, exc):
        return manejador_de_excepciones(exc, {})

    def test_application_error_usa_su_mensaje_extra_y_codigo(self):
        respuesta = self.manejar(ApplicationError("Algo falló", extra={"a": 1}))

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.data, {"message": "Algo falló", "extra": {"a": 1}})

    def test_application_error_respeta_el_codigo_de_la_subclase(self):
        respuesta = self.manejar(ErrorDePrueba("Conflicto"))

        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(respuesta.data, {"message": "Conflicto", "extra": {}})

    def test_validacion_de_serializer_trae_los_campos(self):
        respuesta = self.manejar(
            serializers.ValidationError({"fecha": ["Fecha inválida."]})
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            respuesta.data,
            {
                "message": "Error de validación",
                "extra": {"fields": {"fecha": ["Fecha inválida."]}},
            },
        )

    def test_validacion_de_django_se_convierte_en_400(self):
        respuesta = self.manejar(
            DjangoValidationError({"valor_inicial": ["Demasiados decimales."]})
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            respuesta.data["extra"]["fields"],
            {"valor_inicial": ["Demasiados decimales."]},
        )

    def test_http404_se_convierte_en_404(self):
        respuesta = self.manejar(Http404())

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(set(respuesta.data), {"message", "extra"})

    def test_permission_denied_se_convierte_en_403(self):
        respuesta = self.manejar(PermissionDenied())

        self.assertEqual(respuesta.status_code, 403)

    def test_otros_errores_de_drf_usan_su_detalle(self):
        respuesta = self.manejar(exceptions.NotFound("No existe."))

        self.assertEqual(respuesta.data, {"message": "No existe.", "extra": {}})

    def test_errores_inesperados_no_se_silencian(self):
        self.assertIsNone(self.manejar(RuntimeError("falla")))
