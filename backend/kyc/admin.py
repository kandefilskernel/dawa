from django.contrib import admin

from .models import Piece


@admin.register(Piece)
class PieceAdmin(admin.ModelAdmin):
    list_display = ["type", "pharmacie", "etablissement", "statut", "envoyee_le", "verifiee_par"]
    list_filter = ["statut", "type"]
    readonly_fields = ["fichier", "nom_original", "envoyee_le", "verifiee_le", "verifiee_par"]
