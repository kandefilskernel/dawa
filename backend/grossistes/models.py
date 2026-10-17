from urllib.parse import quote

from django.core.validators import MinValueValidator
from django.db import models

from catalogue.models import Medicament
from pharmacies.models import Pharmacie


class Grossiste(models.Model):
    nom = models.CharField(max_length=150)
    telephone = models.CharField(max_length=20)
    whatsapp = models.CharField(max_length=20, blank=True, help_text="Numéro international, ex. +243990000000")
    adresse = models.CharField(max_length=255, blank=True)
    delai_livraison = models.CharField(max_length=60, blank=True, help_text="Ex. 24 h, 48 h")
    minimum_commande = models.PositiveIntegerField("minimum de commande (FC)", default=0)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Offre(models.Model):
    """Prix d'un médicament chez un grossiste."""

    grossiste = models.ForeignKey(Grossiste, on_delete=models.CASCADE, related_name="offres")
    medicament = models.ForeignKey(Medicament, on_delete=models.CASCADE, related_name="offres_grossistes")
    conditionnement = models.CharField(max_length=60, default="boîte", help_text="Ex. boîte de 20, carton de 50")
    prix = models.PositiveIntegerField("prix unitaire (FC)")
    disponible = models.BooleanField(default=True)
    mis_a_jour_le = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["medicament__nom_commercial"]
        constraints = [models.UniqueConstraint(fields=["grossiste", "medicament"], name="offre_unique")]

    def __str__(self):
        return f"{self.medicament} — {self.grossiste} : {self.prix} FC"


class Commande(models.Model):
    class Statut(models.TextChoices):
        ENVOYEE = "envoyee", "Envoyée au grossiste"
        CONFIRMEE = "confirmee", "Confirmée par le grossiste"
        LIVREE = "livree", "Livrée"
        ANNULEE = "annulee", "Annulée"

    pharmacie = models.ForeignKey(Pharmacie, on_delete=models.CASCADE, related_name="commandes")
    grossiste = models.ForeignKey(Grossiste, on_delete=models.PROTECT, related_name="commandes")
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.ENVOYEE)
    note = models.CharField(max_length=255, blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-cree_le"]

    def __str__(self):
        return f"Commande n° {self.pk} — {self.pharmacie} → {self.grossiste}"

    @property
    def total(self):
        return sum(l.sous_total for l in self.lignes.all())

    def message_whatsapp(self):
        lignes = "\n".join(
            f"- {l.quantite} × {l.medicament.nom_commercial} {l.medicament.dosage} ({l.conditionnement})"
            for l in self.lignes.select_related("medicament")
        )
        texte = (
            f"Bonjour, commande Uzima n° {self.pk} de {self.pharmacie.nom} ({self.pharmacie.telephone}) :\n"
            f"{lignes}\nTotal estimé : {self.total} FC."
            + (f"\nNote : {self.note}" if self.note else "")
        )
        numero = "".join(c for c in (self.grossiste.whatsapp or self.grossiste.telephone) if c.isdigit())
        return f"https://wa.me/{numero}?text={quote(texte)}"


class LigneCommande(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name="lignes")
    medicament = models.ForeignKey(Medicament, on_delete=models.PROTECT)
    quantite = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    prix_unitaire = models.PositiveIntegerField("prix unitaire au moment de la commande (FC)")
    conditionnement = models.CharField(max_length=60)

    @property
    def sous_total(self):
        return self.quantite * self.prix_unitaire
