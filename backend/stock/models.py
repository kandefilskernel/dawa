from datetime import timedelta

from django.conf import settings
from django.contrib.gis.db import models
from django.utils import timezone

from catalogue.models import Medicament
from pharmacies.models import Pharmacie


class Stock(models.Model):
    class Source(models.TextChoices):
        APP = "app", "Application"
        ADMIN = "admin", "Administration"
        SMS = "sms", "SMS"
        WHATSAPP = "whatsapp", "WhatsApp"
        PORTAIL = "portail", "Portail pharmacien"

    pharmacie = models.ForeignKey(Pharmacie, on_delete=models.CASCADE, related_name="stocks")
    medicament = models.ForeignKey(Medicament, on_delete=models.CASCADE, related_name="stocks")
    disponible = models.BooleanField(default=True)
    prix = models.PositiveIntegerField("prix (FC)", null=True, blank=True)
    mis_a_jour_le = models.DateTimeField(auto_now=True)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.ADMIN)

    class Meta:
        verbose_name = "stock"
        constraints = [
            models.UniqueConstraint(fields=["pharmacie", "medicament"], name="stock_unique")
        ]

    def __str__(self):
        etat = "dispo" if self.disponible else "rupture"
        return f"{self.medicament} @ {self.pharmacie} ({etat})"

    @property
    def est_confirme(self):
        limite = timezone.now() - timedelta(hours=settings.STOCK_FRAICHEUR_HEURES)
        return self.mis_a_jour_le >= limite


class Recherche(models.Model):
    """Journal des recherches : sert aux statistiques de demande non satisfaite par zone."""

    terme = models.CharField(max_length=150)
    medicament = models.ForeignKey(Medicament, null=True, blank=True, on_delete=models.SET_NULL)
    # Position arrondie (~1 km) : on garde la zone, pas l'adresse exacte de l'utilisateur.
    zone = models.PointField(geography=True, srid=4326, null=True, blank=True)
    nb_resultats = models.PositiveIntegerField(default=0)
    cree_le = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-cree_le"]


class AlerteStock(models.Model):
    """« Prévenez-moi quand ce médicament est disponible près de moi. »"""

    client_id = models.UUIDField(db_index=True)
    medicament = models.ForeignKey(Medicament, on_delete=models.CASCADE, related_name="alertes")
    position = models.PointField(geography=True, srid=4326)
    rayon_km = models.PositiveSmallIntegerField(default=10)
    cree_le = models.DateTimeField(auto_now_add=True)
    declenchee_le = models.DateTimeField(null=True, blank=True)
    pharmacie = models.ForeignKey(
        Pharmacie, null=True, blank=True, on_delete=models.SET_NULL,
        help_text="Pharmacie où le médicament est redevenu disponible.",
    )

    class Meta:
        ordering = ["-cree_le"]
        verbose_name = "alerte de disponibilité"
        verbose_name_plural = "alertes de disponibilité"

    def __str__(self):
        return f"Alerte {self.medicament} ({'déclenchée' if self.declenchee_le else 'en attente'})"
