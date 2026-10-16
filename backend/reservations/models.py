from datetime import timedelta

from django.conf import settings
from django.contrib.gis.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone

from catalogue.models import Medicament
from pharmacies.models import Pharmacie

DUREE_RESERVATION = timedelta(hours=2)
DUREE_LIVRAISON_MAX = timedelta(hours=6)
MAX_RESERVATIONS_ACTIVES = 3


def frais_livraison(distance_km):
    """Forfait + prix au km, arrondi aux 500 FC supérieurs."""
    brut = settings.LIVRAISON_FORFAIT_FC + settings.LIVRAISON_PRIX_KM_FC * distance_km
    return int(-(-brut // 500) * 500)


class Livreur(models.Model):
    """Livreur moto travaillant avec une pharmacie."""

    pharmacie = models.ForeignKey(Pharmacie, on_delete=models.CASCADE, related_name="livreurs")
    nom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return f"{self.nom} ({self.telephone})"


class Reservation(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente de la pharmacie"
        ACCEPTEE = "acceptee", "Acceptée"
        PRETE = "prete", "Prête"
        EN_LIVRAISON = "en_livraison", "En cours de livraison"
        LIVREE = "livree", "Livrée"
        RETIREE = "retiree", "Retirée"
        REFUSEE = "refusee", "Refusée"
        ANNULEE = "annulee", "Annulée"
        EXPIREE = "expiree", "Expirée"

    class Mode(models.TextChoices):
        RETRAIT = "retrait", "Retrait à la pharmacie"
        LIVRAISON = "livraison", "Livraison à moto"

    ACTIFS = (Statut.EN_ATTENTE, Statut.ACCEPTEE, Statut.PRETE, Statut.EN_LIVRAISON)

    # Transitions que la pharmacie peut effectuer, selon le mode.
    TRANSITIONS = {
        Statut.EN_ATTENTE.value: (Statut.ACCEPTEE, Statut.REFUSEE),
        Statut.ACCEPTEE.value: (Statut.PRETE, Statut.REFUSEE),
    }
    TRANSITIONS_RETRAIT = {Statut.PRETE.value: (Statut.RETIREE,)}
    TRANSITIONS_LIVRAISON = {
        Statut.PRETE.value: (Statut.EN_LIVRAISON,),
        Statut.EN_LIVRAISON.value: (Statut.LIVREE,),
    }

    client_id = models.UUIDField(db_index=True)
    nom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20)
    pharmacie = models.ForeignKey(Pharmacie, on_delete=models.CASCADE, related_name="reservations")
    medicament = models.ForeignKey(Medicament, on_delete=models.PROTECT, related_name="reservations")
    quantite = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    statut = models.CharField(max_length=12, choices=Statut.choices, default=Statut.EN_ATTENTE)
    message_pharmacie = models.CharField(max_length=255, blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    expire_le = models.DateTimeField()

    # Livraison
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.RETRAIT)
    adresse_livraison = models.CharField(max_length=255, blank=True)
    position_livraison = models.PointField(geography=True, srid=4326, null=True, blank=True)
    frais_livraison = models.PositiveIntegerField("frais de livraison (FC)", null=True, blank=True)
    livreur = models.ForeignKey(Livreur, null=True, blank=True, on_delete=models.SET_NULL, related_name="courses")

    class Meta:
        ordering = ["-cree_le"]
        verbose_name = "réservation"

    def __str__(self):
        return f"{self.medicament} × {self.quantite} — {self.pharmacie} ({self.get_statut_display()})"

    def save(self, *args, **kwargs):
        if self.expire_le is None:
            self.expire_le = timezone.now() + DUREE_RESERVATION
        super().save(*args, **kwargs)

    @property
    def est_livraison(self):
        return self.mode == self.Mode.LIVRAISON

    @property
    def statut_effectif(self):
        """Une réservation active dont le délai est passé est considérée comme expirée."""
        if self.statut in self.ACTIFS and timezone.now() >= self.expire_le:
            return self.Statut.EXPIREE
        return self.statut

    @property
    def est_active(self):
        return self.statut_effectif in self.ACTIFS

    @property
    def transitions_possibles(self):
        statut = str(self.statut_effectif)
        propres = self.TRANSITIONS_LIVRAISON if self.est_livraison else self.TRANSITIONS_RETRAIT
        return self.TRANSITIONS.get(statut) or propres.get(statut, ())

    def changer_statut(self, nouveau, message="", livreur=None):
        """Fait avancer la réservation. Lève ValueError si la transition est interdite."""
        if nouveau not in self.transitions_possibles:
            raise ValueError(
                f"Impossible de passer de « {Reservation.Statut(self.statut_effectif).label} » "
                f"à « {Reservation.Statut(nouveau).label} »."
            )
        if nouveau == self.Statut.EN_LIVRAISON:
            if livreur is None or livreur.pharmacie_id != self.pharmacie_id or not livreur.actif:
                raise ValueError("Choisissez le livreur qui part avec la commande.")
            self.livreur = livreur
            self.expire_le = timezone.now() + DUREE_LIVRAISON_MAX
        self.statut = nouveau
        if message:
            self.message_pharmacie = message[:255]
        if nouveau == self.Statut.PRETE:
            # Le client a de nouveau 2 heures (retrait), ou la course doit partir dans ce délai.
            self.expire_le = timezone.now() + DUREE_RESERVATION
        self.save(update_fields=["statut", "message_pharmacie", "expire_le", "livreur"])
        from notifications.envoi import notifier_reservation

        notifier_reservation(self)
