from django.contrib import admin, messages

from .models import Abonnement


@admin.action(description="Paiement reçu : activer")
def activer(modeladmin, request, queryset):
    nb = 0
    for abonnement in queryset.filter(statut=Abonnement.Statut.EN_ATTENTE):
        abonnement.activer()
        nb += 1
    modeladmin.message_user(request, f"{nb} abonnement(s) activé(s).", messages.SUCCESS)


@admin.register(Abonnement)
class AbonnementAdmin(admin.ModelAdmin):
    list_display = ["pharmacie", "formule", "mois", "montant", "statut", "reference", "reference_paiement", "debut", "fin"]
    list_filter = ["statut", "formule"]
    search_fields = ["pharmacie__nom", "reference", "reference_paiement"]
    readonly_fields = ["cree_le"]
    actions = [activer]
