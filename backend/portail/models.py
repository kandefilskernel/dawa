from django.conf import settings
from django.db import models

from kyc.models import CompteValidable
from pharmacies.models import Pharmacie


class Pharmacien(CompteValidable):
    """Compte d'accès au portail, rattaché à une seule pharmacie."""

    utilisateur = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pharmacien"
    )
    pharmacie = models.ForeignKey(Pharmacie, on_delete=models.CASCADE, related_name="pharmaciens")

    class Meta:
        verbose_name = "pharmacien"

    def __str__(self):
        return f"{self.utilisateur.get_username()} — {self.pharmacie}"

    def _rendre_visible(self, visible):
        Pharmacie.objects.filter(pk=self.pharmacie_id).update(est_validee=visible)
