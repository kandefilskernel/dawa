from django.contrib.gis.db import models
from django.utils import timezone


class PharmacieQuerySet(models.QuerySet):
    def visibles(self):
        return self.filter(est_validee=True)

    def de_garde(self, moment=None):
        moment = moment or timezone.now()
        return self.filter(gardes__debut__lte=moment, gardes__fin__gt=moment).distinct()

    def avec_livraison(self):
        return self.filter(livreurs__actif=True).distinct()


class Pharmacie(models.Model):
    nom = models.CharField(max_length=150)
    adresse = models.CharField(max_length=255)
    quartier = models.CharField(max_length=100, blank=True)
    commune = models.CharField(max_length=100, blank=True)
    telephone = models.CharField(max_length=20)
    whatsapp = models.CharField(max_length=20, blank=True)
    position = models.PointField(geography=True, srid=4326)
    horaires = models.CharField(max_length=255, blank=True, help_text="Ex. Lun–Sam 8h–20h")
    numero_agrement = models.CharField(max_length=50, blank=True)
    est_validee = models.BooleanField(
        default=False, help_text="Seules les pharmacies validées apparaissent dans l'app."
    )
    cree_le = models.DateTimeField(auto_now_add=True)

    objects = PharmacieQuerySet.as_manager()

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Garde(models.Model):
    pharmacie = models.ForeignKey(Pharmacie, on_delete=models.CASCADE, related_name="gardes")
    debut = models.DateTimeField()
    fin = models.DateTimeField()

    class Meta:
        ordering = ["-debut"]

    def __str__(self):
        return f"{self.pharmacie} — {self.debut:%d/%m %H:%M} → {self.fin:%d/%m %H:%M}"
