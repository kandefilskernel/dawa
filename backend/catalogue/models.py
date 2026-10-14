from django.db import models


class Medicament(models.Model):
    class Forme(models.TextChoices):
        COMPRIME = "comprime", "Comprimé"
        GELULE = "gelule", "Gélule"
        SIROP = "sirop", "Sirop"
        INJECTABLE = "injectable", "Injectable"
        POMMADE = "pommade", "Pommade / crème"
        SUSPENSION = "suspension", "Suspension"
        SACHET = "sachet", "Sachet"
        AUTRE = "autre", "Autre"

    dci = models.CharField("DCI (molécule)", max_length=150, db_index=True)
    nom_commercial = models.CharField(max_length=150, db_index=True)
    dosage = models.CharField(max_length=50, blank=True, help_text="Ex. 500 mg, 125 mg/5 ml")
    forme = models.CharField(max_length=20, choices=Forme.choices, default=Forme.COMPRIME)
    code_barres = models.CharField(max_length=32, unique=True, null=True, blank=True)
    ordonnance_requise = models.BooleanField(default=False)
    image = models.ImageField(upload_to="medicaments/", blank=True)
    image_est_illustration = models.BooleanField(
        "image générée", default=False,
        help_text="Coché : illustration automatique. Une vraie photo envoyée la remplace.",
    )
    image_envoyee_par = models.ForeignKey(
        "pharmacies.Pharmacie", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="photos_envoyees", verbose_name="photo envoyée par",
        help_text="Pharmacie qui a envoyé la photo depuis le portail (à vérifier).",
    )

    # Champs dessinés sur l'illustration : si l'un change, elle est redessinée.
    CHAMPS_ILLUSTRATION = ("dci", "nom_commercial", "dosage", "forme", "ordonnance_requise")

    class Meta:
        ordering = ["nom_commercial", "dosage"]
        verbose_name = "médicament"
        constraints = [
            models.UniqueConstraint(
                fields=["nom_commercial", "dosage", "forme"], name="medicament_unique"
            )
        ]

    def __str__(self):
        return f"{self.nom_commercial} {self.dosage} ({self.get_forme_display()})".strip()
