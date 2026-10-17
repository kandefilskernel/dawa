"""
Vérification d'identité des structures (KYC) : comptes à valider et pièces justificatives.

Les pièces sont stockées HORS du dossier media public (settings.KYC_RACINE) et ne sont
téléchargeables que par l'équipe Uzima, via une vue protégée.
"""
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils import timezone
from django.utils.functional import LazyObject


class _StockagePrive(LazyObject):
    """Stockage hors de MEDIA_ROOT, évalué tard pour suivre les réglages (tests)."""

    def _setup(self):
        self._wrapped = FileSystemStorage(location=settings.KYC_RACINE, base_url=None)


stockage_prive = _StockagePrive()


class CompteValidable(models.Model):
    """Compte d'une structure (pharmacie, établissement) validé manuellement par l'équipe Uzima."""

    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente de validation"
        ACTIF = "actif", "Actif"
        REFUSE = "refuse", "Refusé"
        SUSPENDU = "suspendu", "Suspendu"

    # Comptes créés par l'équipe Uzima : actifs d'emblée. Inscriptions en ligne : en attente.
    statut = models.CharField(max_length=12, choices=Statut.choices, default=Statut.ACTIF)
    motif = models.CharField(max_length=255, blank=True, help_text="Raison du refus ou de la suspension")
    cree_le = models.DateTimeField(default=timezone.now)
    traite_le = models.DateTimeField(null=True, blank=True)
    traite_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="+")

    class Meta:
        abstract = True

    @property
    def actif(self):
        return self.statut == self.Statut.ACTIF

    def _rendre_visible(self, visible):
        """Affiche ou retire la structure dans l'app (défini par chaque type de compte)."""
        raise NotImplementedError

    def _decision(self, statut, par, motif=""):
        self.statut, self.motif, self.traite_par, self.traite_le = statut, motif[:255], par, timezone.now()
        self.save(update_fields=["statut", "motif", "traite_par", "traite_le"])

    def valider(self, par):
        self._decision(self.Statut.ACTIF, par)
        self._rendre_visible(True)

    def refuser(self, par, motif):
        self._decision(self.Statut.REFUSE, par, motif)
        self._rendre_visible(False)

    def suspendre(self, par, motif):
        """Plus d'accès à l'espace et structure retirée de l'app, jusqu'à réactivation."""
        self._decision(self.Statut.SUSPENDU, par, motif)
        self._rendre_visible(False)


class Piece(models.Model):
    """Pièce justificative envoyée par une pharmacie ou un établissement de santé."""

    class Type(models.TextChoices):
        AUTORISATION = "autorisation", "Autorisation d'ouverture / d'exploitation"
        RCCM = "rccm", "RCCM (registre du commerce)"
        ID_NAT = "id_nat", "Identification nationale (Id. Nat.)"
        ORDRE = "ordre", "Carte de l'Ordre du responsable (pharmaciens ou médecins)"
        IDENTITE = "identite", "Pièce d'identité du responsable"
        FACADE = "facade", "Photo de la façade avec l'enseigne"

    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "À vérifier"
        ACCEPTEE = "acceptee", "Acceptée"
        REJETEE = "rejetee", "Rejetée"

    pharmacie = models.ForeignKey("pharmacies.Pharmacie", null=True, blank=True, on_delete=models.CASCADE,
                                  related_name="pieces")
    etablissement = models.ForeignKey("sante.Etablissement", null=True, blank=True, on_delete=models.CASCADE,
                                      related_name="pieces")
    type = models.CharField(max_length=15, choices=Type.choices)
    fichier = models.FileField(storage=stockage_prive, upload_to="pieces/%Y/%m/")
    nom_original = models.CharField(max_length=150, blank=True)
    statut = models.CharField(max_length=12, choices=Statut.choices, default=Statut.EN_ATTENTE)
    motif = models.CharField(max_length=255, blank=True, help_text="Raison du rejet, montrée à la structure")
    envoyee_le = models.DateTimeField(auto_now_add=True)
    verifiee_le = models.DateTimeField(null=True, blank=True)
    verifiee_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="+")

    class Meta:
        ordering = ["type", "-envoyee_le"]
        verbose_name = "pièce justificative"
        verbose_name_plural = "pièces justificatives"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(pharmacie__isnull=False, etablissement__isnull=True)
                | models.Q(pharmacie__isnull=True, etablissement__isnull=False),
                name="piece_une_seule_structure",
            )
        ]

    def __str__(self):
        return f"{self.get_type_display()} — {self.pharmacie or self.etablissement}"

    def verifier(self, par, acceptee, motif=""):
        self.statut = self.Statut.ACCEPTEE if acceptee else self.Statut.REJETEE
        self.motif, self.verifiee_par, self.verifiee_le = ("" if acceptee else motif[:255]), par, timezone.now()
        self.save(update_fields=["statut", "motif", "verifiee_par", "verifiee_le"])


def nom_fichier_piece(nom_original):
    """Nom aléatoire : le nom envoyé par l'utilisateur n'est jamais utilisé sur le disque."""
    return f"{uuid.uuid4().hex}{Path(nom_original).suffix.lower()}"
