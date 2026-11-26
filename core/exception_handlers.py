"""Manejador de excepciones de la API.

Implementa el enfoque propuesto por el Django-Styleguide: todas las respuestas
de error tienen la forma ``{"message": str, "extra": dict}``.

- Los errores de validación (de serializers o de ``full_clean``) se devuelven
  con ``message = "Error de validación"`` y el detalle por campo en
  ``extra["fields"]``.
- ``ApplicationError`` se devuelve con su mensaje, sus datos extra y su código.
- Cualquier otro error de DRF usa su detalle como mensaje.
- El resto de las excepciones no se silencia: terminan en un error 500.
"""

from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error
from rest_framework.views import exception_handler

from core.exceptions import ApplicationError

MENSAJE_VALIDACION = "Error de validación"


def manejador_de_excepciones(exc, ctx):
    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(as_serializer_error(exc))

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()

    if isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    response = exception_handler(exc, ctx)

    if response is None:
        if isinstance(exc, ApplicationError):
            return Response(
                {"message": exc.message, "extra": exc.extra},
                status=exc.status_code,
            )
        return response

    if isinstance(exc, exceptions.ValidationError):
        response.data = {
            "message": MENSAJE_VALIDACION,
            "extra": {"fields": response.data},
        }
    else:
        response.data = {"message": response.data["detail"], "extra": {}}

    return response
