from django.db.models import Model, QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404


def get_object(model_or_queryset: type[Model] | QuerySet, **kwargs) -> Model | None:
    """Devuelve el objeto que cumple los filtros o ``None`` si no existe.

    Es la utilidad que propone el Django-Styleguide para obtener objetos en las
    APIs sin lanzar ``Http404``.
    """
    try:
        return get_object_or_404(model_or_queryset, **kwargs)
    except Http404:
        return None
