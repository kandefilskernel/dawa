from django.conf import settings
from django.db import models

from pharmacies.models import Pharmacie


class Pharmacien(models.Model):
    """Compte d'accès au portail, rattaché à une seule pharmacie."""

    utilisateur = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pharmacien"
    )
    pharmacie = models.ForeignKey(Pharmacie, on_delete=models.CASCADE, related_name="pharmaciens")

    class Meta:
        verbose_name = "pharmacien"

    def __str__(self):
        return f"{self.utilisateur.get_username()} — {self.pharmacie}"
