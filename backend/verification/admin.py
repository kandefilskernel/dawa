from django.contrib import admin
from django.utils.html import format_html

from .models import Lot, Signalement


@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display = ["numero", "medicament", "fabricant", "date_expiration", "statut", "source"]
    list_filter = ["statut", "fabricant"]
    search_fields = ["numero", "numero_normalise", "medicament__nom_commercial", "fabricant"]
    autocomplete_fields = ["medicament"]


@admin.register(Signalement)
class SignalementAdmin(admin.ModelAdmin):
    list_display = ["cree_le", "medicament", "numero_lot", "pharmacie", "lieu_achat", "traite"]
    list_filter = ["traite", "cree_le"]
    list_editable = ["traite"]
    search_fields = ["numero_lot", "description", "lieu_achat"]
    readonly_fields = ["client_id", "cree_le", "apercu_photo"]

    @admin.display(description="photo")
    def apercu_photo(self, obj):
        if not obj.photo:
            return "—"
        return format_html('<img src="{}" style="max-width:320px;border-radius:8px">', obj.photo.url)
