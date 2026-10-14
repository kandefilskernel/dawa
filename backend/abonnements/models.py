from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from pharmacies.models import Pharmacie

DUREE_MOIS = timedelta(days=30)


class AbonnementQuerySet(models.QuerySet):
    def actifs(self, jour=None):
        jour = jour or timezone.localdate()
        return self.filter(statut=Abonnement.Statut.ACTIF, debut__lte=jour, fin__gt=jour)

    def ids_pharmacies_sponsorisees(self):
        return set(self.actifs().filter(formule=Abonnement.Formule.VISIBILITE).values_list("pharmacie_id", flat=True))


class Abonnement(models.Model):
    class Formule(models.TextChoices):
        ESSENTIEL = "essentiel", "Essentiel — stock, réservations, statistiques"
        VISIBILITE = "visibilite", "Visibilité — Essentiel + mise en avant dans les recherches"

    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente du paiement"
        ACTIF = "actif", "Actif"
        ANNULE = "annule", "Annulé"

    pharmacie = models.ForeignKey(Pharmacie, on_delete=models.CASCADE, related_name="abonnements")
    formule = models.CharField(max_length=12, choices=Formule.choices)
    mois = models.PositiveSmallIntegerField(default=1)
    montant = models.PositiveIntegerField("montant (FC)")
    statut = models.CharField(max_length=12, choices=Statut.choices, default=Statut.EN_ATTENTE)
    reference = models.CharField(max_length=20, unique=True, help_text="À indiquer dans le paiement mobile money")
    reference_paiement = models.CharField(
        max_length=60, blank=True, help_text="Référence de la transaction reçue (M-Pesa, Orange Money, Airtel Money)"
    )
    debut = models.DateField(null=True, blank=True)
    fin = models.DateField(null=True, blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    objects = AbonnementQuerySet.as_manager()

    class Meta:
        ordering = ["-cree_le"]

    def __str__(self):
        return f"{self.pharmacie} — {self.get_formule_display().split(' —')[0]} ({self.get_statut_display()})"

    @staticmethod
    def prix(formule, mois=1):
        return settings.ABONNEMENT_PRIX_FC[formule] * mois

    def activer(self, reference_paiement=""):
        """Paiement reçu : l'abonnement démarre à la fin de l'abonnement actif en cours, sinon aujourd'hui."""
        aujourdhui = timezone.localdate()
        en_cours = (
            Abonnement.objects.actifs().filter(pharmacie=self.pharmacie).exclude(pk=self.pk).order_by("-fin").first()
        )
        self.debut = max(aujourdhui, en_cours.fin) if en_cours else aujourdhui
        self.fin = self.debut + DUREE_MOIS * self.mois
        self.statut = self.Statut.ACTIF
        if reference_paiement:
            self.reference_paiement = reference_paiement
        self.save()
