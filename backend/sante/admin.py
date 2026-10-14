from django.contrib.gis import admin

from .models import Etablissement


@admin.register(Etablissement)
class EtablissementAdmin(admin.GISModelAdmin):
    list_display = ["nom", "type", "quartier", "telephone", "urgences_24h", "est_valide"]
    list_filter = ["type", "urgences_24h", "est_valide"]
    list_editable = ["est_valide"]
    search_fields = ["nom", "quartier", "services"]
    gis_widget_kwargs = {"attrs": {"default_lat": -11.664, "default_lon": 27.479, "default_zoom": 13}}
