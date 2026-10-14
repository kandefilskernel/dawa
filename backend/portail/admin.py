from django.contrib import admin

from .models import Pharmacien


@admin.register(Pharmacien)
class PharmacienAdmin(admin.ModelAdmin):
    list_display = ["utilisateur", "pharmacie"]
    search_fields = ["utilisateur__username", "pharmacie__nom"]
    autocomplete_fields = ["utilisateur", "pharmacie"]
