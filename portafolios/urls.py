from django.urls import path

from portafolios.apis import PortafolioEvolucionApi, PortafolioListApi
from portafolios.views import PortafoliosGraficosView

app_name = "portafolios"

urlpatterns = [
    path("", PortafoliosGraficosView.as_view(), name="graficos"),
    path("api/portafolios/", PortafolioListApi.as_view(), name="api-list"),
    path(
        "api/portafolios/<int:portafolio_id>/evolucion/",
        PortafolioEvolucionApi.as_view(),
        name="api-evolucion",
    ),
]
