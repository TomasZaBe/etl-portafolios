from django.views.generic import TemplateView


class PortafoliosGraficosView(TemplateView):
    """Página que consume la API y grafica la evolución de los portafolios.

    La vista solo entrega el HTML. Los datos se obtienen desde el navegador
    con la API REST, como pide el enunciado.
    """

    template_name = "portafolios/graficos.html"
