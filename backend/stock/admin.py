from django.contrib import admin

from .models import AlerteStock, Recherche, Stock


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ["medicament", "pharmacie", "disponible", "prix", "mis_a_jour_le", "source"]
    list_filter = ["disponible", "source", "pharmacie"]
    list_editable = ["disponible", "prix"]
    search_fields = ["medicament__nom_commercial", "medicament__dci", "pharmacie__nom"]
    autocomplete_fields = ["medicament", "pharmacie"]


@admin.register(Recherche)
class RechercheAdmin(admin.ModelAdmin):
    list_display = ["terme", "medicament", "nb_resultats", "cree_le"]
    list_filter = ["cree_le"]
    search_fields = ["terme"]
    readonly_fields = [f.name for f in Recherche._meta.fields]


@admin.register(AlerteStock)
class AlerteStockAdmin(admin.ModelAdmin):
    list_display = ["medicament", "rayon_km", "cree_le", "declenchee_le", "pharmacie"]
    list_filter = ["declenchee_le"]
    readonly_fields = ["client_id"]
