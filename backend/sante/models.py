from django.contrib.gis.db import models


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

    class Meta:
        ordering = ["nom"]
        verbose_name = "établissement de santé"
        verbose_name_plural = "établissements de santé"

    def __str__(self):
        return f"{self.nom} ({self.get_type_display()})"
