from django.contrib.gis import admin

from stock.models import Stock

from .models import Garde, Pharmacie


class GardeInline(admin.TabularInline):
    model = Garde
    extra = 0


class StockInline(admin.TabularInline):
    model = Stock
    extra = 0
    autocomplete_fields = ["medicament"]
    readonly_fields = ["mis_a_jour_le"]


@admin.register(Pharmacie)
class PharmacieAdmin(admin.GISModelAdmin):
    list_display = ["nom", "quartier", "commune", "telephone", "est_validee"]
    list_filter = ["est_validee", "commune"]
    list_editable = ["est_validee"]
    search_fields = ["nom", "quartier", "telephone"]
    inlines = [GardeInline, StockInline]
    gis_widget_kwargs = {"attrs": {"default_lat": -11.664, "default_lon": 27.479, "default_zoom": 13}}


@admin.register(Garde)
class GardeAdmin(admin.ModelAdmin):
    list_display = ["pharmacie", "debut", "fin"]
    list_filter = ["debut"]
