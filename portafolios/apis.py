"""Endpoints REST de los portafolios.

Siguen la estructura del Django-Styleguide: cada API valida la entrada con un
serializer propio, delega la consulta a un selector y da forma a la respuesta
con un serializer de salida. Los errores de negocio (``ApplicationError``) los
traduce el manejador de excepciones de ``core``.
"""

from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import get_object
from portafolios.models import Portafolio
from portafolios.selectors import portafolio_evolucion, portafolio_list


class PortafolioListApi(APIView):
    class OutputSerializer(serializers.ModelSerializer):
        class Meta:
            model = Portafolio
            fields = ["id", "nombre", "fecha_inicio", "valor_inicial"]

    def get(self, request):
        data = self.OutputSerializer(portafolio_list(), many=True).data
        return Response(data)


class PortafolioEvolucionApi(APIView):
    """Weights w_i,t y valor total V_t de un portafolio entre dos fechas.

    Parámetros opcionales: ``fecha_inicio`` y ``fecha_fin`` (AAAA-MM-DD). Sin
    ellos se devuelve todo el rango disponible.
    """

    class FilterSerializer(serializers.Serializer):
        fecha_inicio = serializers.DateField(required=False)
        fecha_fin = serializers.DateField(required=False)

        def validate(self, attrs):
            fecha_inicio = attrs.get("fecha_inicio")
            fecha_fin = attrs.get("fecha_fin")
            if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
                raise serializers.ValidationError(
                    {"fecha_fin": "Debe ser igual o posterior a fecha_inicio."}
                )
            return attrs

    class OutputSerializer(serializers.Serializer):
        class ValorEnFechaSerializer(serializers.Serializer):
            class ActivoEnFechaSerializer(serializers.Serializer):
                activo = serializers.CharField()
                monto = serializers.FloatField()
                weight = serializers.FloatField()

            fecha = serializers.DateField()
            valor_total = serializers.FloatField()
            activos = ActivoEnFechaSerializer(many=True)

        portafolio = serializers.SerializerMethodField()
        fecha_inicio = serializers.DateField(allow_null=True)
        fecha_fin = serializers.DateField(allow_null=True)
        valores = ValorEnFechaSerializer(many=True)

        def get_portafolio(self, data):
            portafolio = data["portafolio"]
            return {"id": portafolio.id, "nombre": portafolio.nombre}

    def get(self, request, portafolio_id):
        filtros = self.FilterSerializer(data=request.query_params)
        filtros.is_valid(raise_exception=True)
        portafolio = get_object(Portafolio, pk=portafolio_id)
        if portafolio is None:
            raise NotFound(f"No existe el portafolio {portafolio_id}.")

        valores = portafolio_evolucion(portafolio=portafolio, **filtros.validated_data)

        data = self.OutputSerializer(
            {
                "portafolio": portafolio,
                "fecha_inicio": valores[0].fecha if valores else None,
                "fecha_fin": valores[-1].fecha if valores else None,
                "valores": valores,
            }
        ).data
        return Response(data)
