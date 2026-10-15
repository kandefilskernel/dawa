from django.conf import settings
from django.contrib.gis.db import models

from kyc.models import CompteValidable


class Etablissement(models.Model):
    """Annuaire santé : hôpitaux, cliniques, centres de santé, laboratoires."""

    class Type(models.TextChoices):
        HOPITAL = "hopital", "Hôpital"
        CLINIQUE = "clinique", "Clinique"
        CENTRE_SANTE = "centre_sante", "Centre de santé"
        LABORATOIRE = "laboratoire", "Laboratoire"
        MATERNITE = "maternite", "Maternité"

    nom = models.CharField(max_length=150)
    type = models.CharField(max_length=15, choices=Type.choices)
    adresse = models.CharField(max_length=255)
    quartier = models.CharField(max_length=100, blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    position = models.PointField(geography=True, srid=4326)
    urgences_24h = models.BooleanField("urgences 24h/24", default=False)
    services = models.CharField(max_length=255, blank=True, help_text="Ex. pédiatrie, radiologie, analyses")
    est_valide = models.BooleanField(default=False)
    numero_agrement = models.CharField("numéro d'autorisation", max_length=50, blank=True)

    class Meta:
        ordering = ["nom"]
        verbose_name = "établissement de santé"
        verbose_name_plural = "établissements de santé"

    def __str__(self):
        return f"{self.nom} ({self.get_type_display()})"


class ResponsableEtablissement(CompteValidable):
    """Compte d'un hôpital, d'une clinique… : gère la fiche de l'établissement et son dossier KYC."""

    utilisateur = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                       related_name="responsable_etablissement")
    etablissement = models.ForeignKey(Etablissement, on_delete=models.CASCADE, related_name="responsables")
    fonction = models.CharField(max_length=100, blank=True, help_text="Ex. médecin directeur, administrateur")

    class Meta:
        verbose_name = "responsable d'établissement"
        verbose_name_plural = "responsables d'établissement"

    def __str__(self):
        return f"{self.utilisateur.get_username()} — {self.etablissement}"

    def _rendre_visible(self, visible):
        Etablissement.objects.filter(pk=self.etablissement_id).update(est_valide=visible)
