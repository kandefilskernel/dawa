from django.contrib import admin

from .models import Commande, Grossiste, LigneCommande, Offre


class OffreInline(admin.TabularInline):
    model = Offre
    extra = 0
    autocomplete_fields = ["medicament"]


@admin.register(Grossiste)
class GrossisteAdmin(admin.ModelAdmin):
    list_display = ["nom", "telephone", "whatsapp", "delai_livraison", "minimum_commande", "actif"]
    list_filter = ["actif"]
    search_fields = ["nom"]
    inlines = [OffreInline]


class LigneInline(admin.TabularInline):
    model = LigneCommande
    extra = 0


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ["pk", "pharmacie", "grossiste", "statut", "total", "cree_le"]
    list_filter = ["statut", "grossiste"]
    list_editable = ["statut"]
    search_fields = ["pharmacie__nom", "grossiste__nom"]
    inlines = [LigneInline]
