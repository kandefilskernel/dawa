from django.contrib import admin

from .models import MessageEntrant


@admin.register(MessageEntrant)
class MessageEntrantAdmin(admin.ModelAdmin):
    list_display = ["recu_le", "canal", "expediteur", "pharmacie", "texte", "simulation"]
    list_filter = ["canal", "simulation", "pharmacie"]
    search_fields = ["expediteur", "texte"]
    readonly_fields = [f.name for f in MessageEntrant._meta.fields]
