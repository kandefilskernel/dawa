from django.contrib import admin, messages

from .models import Livreur, Reservation


def _changer_statut(statut, libelle):
    @admin.action(description=libelle)
    def action(modeladmin, request, queryset):
        nb, refus = 0, 0
        for reservation in queryset:
            try:
                reservation.changer_statut(statut)
                nb += 1
            except ValueError:
                refus += 1
        modeladmin.message_user(request, f"{nb} réservation(s) mise(s) à jour.", messages.SUCCESS)
        if refus:
            modeladmin.message_user(
                request, f"{refus} ignorée(s) : transition impossible depuis leur statut.", messages.WARNING
            )

    action.__name__ = f"marquer_{statut}"
    return action


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ["medicament", "quantite", "pharmacie", "nom", "telephone", "mode", "statut_affiche", "expire_le"]
    list_filter = ["statut", "mode", "pharmacie"]
    search_fields = ["nom", "telephone", "medicament__nom_commercial", "pharmacie__nom"]
    readonly_fields = ["client_id", "cree_le"]
    actions = [
        _changer_statut(Reservation.Statut.ACCEPTEE, "Accepter"),
        _changer_statut(Reservation.Statut.PRETE, "Marquer prête à retirer"),
        _changer_statut(Reservation.Statut.RETIREE, "Marquer retirée"),
        _changer_statut(Reservation.Statut.REFUSEE, "Refuser"),
    ]

    @admin.display(description="statut")
    def statut_affiche(self, obj):
        return Reservation.Statut(obj.statut_effectif).label


@admin.register(Livreur)
class LivreurAdmin(admin.ModelAdmin):
    list_display = ["nom", "telephone", "pharmacie", "actif"]
    list_filter = ["actif", "pharmacie"]
    search_fields = ["nom", "telephone"]
