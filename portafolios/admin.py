"""Admin de solo lectura.

Los datos se modifican únicamente con los servicios (comandos ``cargar_datos``
y ``calcular_cantidades``). Editarlos desde el admin permitiría, por ejemplo,
weights que no suman 1 o cantidades que no corresponden al valor inicial.
"""

from django.contrib import admin

from portafolios.models import Activo, Portafolio, Posicion, Precio


class SoloLecturaMixin:
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Activo)
class ActivoAdmin(SoloLecturaMixin, admin.ModelAdmin):
    list_display = ["nombre"]
    search_fields = ["nombre"]


class PosicionInline(SoloLecturaMixin, admin.TabularInline):
    model = Posicion
    fields = ["activo", "weight_inicial", "cantidad"]
    ordering = ["activo__nombre"]


@admin.register(Portafolio)
class PortafolioAdmin(SoloLecturaMixin, admin.ModelAdmin):
    list_display = ["nombre", "valor_inicial", "fecha_inicio"]
    search_fields = ["nombre"]
    inlines = [PosicionInline]


@admin.register(Precio)
class PrecioAdmin(SoloLecturaMixin, admin.ModelAdmin):
    list_display = ["activo", "fecha", "valor"]
    list_filter = ["activo"]
    date_hierarchy = "fecha"
    list_select_related = ["activo"]
    ordering = ["fecha", "activo__nombre"]


@admin.register(Posicion)
class PosicionAdmin(SoloLecturaMixin, admin.ModelAdmin):
    list_display = ["portafolio", "activo", "weight_inicial", "cantidad"]
    list_filter = ["portafolio", "activo"]
    list_select_related = ["portafolio", "activo"]
    ordering = ["portafolio__nombre", "activo__nombre"]
