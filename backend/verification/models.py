from django.db import models
from django.utils import timezone

from catalogue.models import Medicament
from pharmacies.models import Pharmacie


def normaliser_lot(numero):
    """« lot  ab-123 » → « AB123 » : on ignore espaces, tirets et casse."""
    return "".join(c for c in numero.upper() if c.isalnum())


class Lot(models.Model):
    """
    Lot de fabrication connu. Alimenté par l'équipe Dawa à partir des sources officielles
    (autorité pharmaceutique, alertes de rappel, déclarations des fabricants et grossistes).
    """

    class Statut(models.TextChoices):
        CONFORME = "conforme", "Conforme"
        RAPPELE = "rappele", "Rappelé (ne pas utiliser)"
        CONTREFAIT = "contrefait", "Contrefaçon signalée"

    medicament = models.ForeignKey(Medicament, on_delete=models.CASCADE, related_name="lots")
    numero = models.CharField("numéro de lot", max_length=40)
    numero_normalise = models.CharField(max_length=40, db_index=True, editable=False)
    fabricant = models.CharField(max_length=150, blank=True)
    date_expiration = models.DateField(null=True, blank=True)
    statut = models.CharField(max_length=12, choices=Statut.choices, default=Statut.CONFORME)
    note = models.CharField(max_length=255, blank=True, help_text="Ex. référence de l'alerte de rappel")
    source = models.CharField(max_length=150, blank=True, help_text="D'où vient l'information")
    mis_a_jour_le = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["medicament__nom_commercial", "numero"]
        constraints = [
            models.UniqueConstraint(fields=["medicament", "numero_normalise"], name="lot_unique")
        ]

    def __str__(self):
        return f"{self.medicament} — lot {self.numero}"

    def save(self, *args, **kwargs):
        self.numero_normalise = normaliser_lot(self.numero)
        super().save(*args, **kwargs)

    @property
    def est_expire(self):
        return self.date_expiration is not None and self.date_expiration < timezone.localdate()


class Signalement(models.Model):
    """Produit suspect signalé par un patient (emballage douteux, lot inconnu, effet inhabituel)."""

    client_id = models.UUIDField(db_index=True)
    medicament = models.ForeignKey(Medicament, null=True, blank=True, on_delete=models.SET_NULL)
    numero_lot = models.CharField(max_length=40, blank=True)
    pharmacie = models.ForeignKey(
        Pharmacie, null=True, blank=True, on_delete=models.SET_NULL, help_text="Lieu d'achat"
    )
    lieu_achat = models.CharField(max_length=150, blank=True, help_text="Si ce n'est pas une pharmacie Dawa")
    description = models.TextField(max_length=1000)
    photo = models.ImageField(upload_to="signalements/", blank=True)
    telephone = models.CharField(max_length=20, blank=True, help_text="Pour être recontacté (facultatif)")
    cree_le = models.DateTimeField(auto_now_add=True)
    traite = models.BooleanField(default=False)
    suite_donnee = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["traite", "-cree_le"]

    def __str__(self):
        return f"Signalement du {self.cree_le:%d/%m/%Y} — {self.medicament or self.numero_lot or 'produit'}"
