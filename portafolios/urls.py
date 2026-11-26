from django.urls import path

from portafolios.apis import PortafolioEvolucionApi, PortafolioListApi

app_name = "portafolios"

urlpatterns = [
    path("api/portafolios/", PortafolioListApi.as_view(), name="api-list"),
    path(
        "api/portafolios/<int:portafolio_id>/evolucion/",
        PortafolioEvolucionApi.as_view(),
        name="api-evolucion",
    ),
]
