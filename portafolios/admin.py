from django.contrib import admin

from portafolios.models import Activo, Portafolio, Posicion, Precio


@admin.register(Activo)
class ActivoAdmin(admin.ModelAdmin):
    list_display = ["nombre"]
    search_fields = ["nombre"]


class PosicionInline(admin.TabularInline):
    model = Posicion
    extra = 0
    autocomplete_fields = ["activo"]


@admin.register(Portafolio)
class PortafolioAdmin(admin.ModelAdmin):
    list_display = ["nombre", "valor_inicial", "fecha_inicio"]
    search_fields = ["nombre"]
    inlines = [PosicionInline]


@admin.register(Precio)
class PrecioAdmin(admin.ModelAdmin):
    list_display = ["activo", "fecha", "valor"]
    list_filter = ["activo"]
    date_hierarchy = "fecha"
    list_select_related = ["activo"]


@admin.register(Posicion)
class PosicionAdmin(admin.ModelAdmin):
    list_display = ["portafolio", "activo", "weight_inicial", "cantidad"]
    list_filter = ["portafolio", "activo"]
    list_select_related = ["portafolio", "activo"]
