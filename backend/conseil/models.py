from django.db import models

from catalogue.models import Medicament
from pharmacies.models import Pharmacie


class Question(models.Model):
    """
    Question simple d'un patient (notice, prise, interactions), à laquelle répond un pharmacien
    partenaire depuis le portail. Ce n'est ni une consultation ni un diagnostic.
    """

    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente de réponse"
        REPONDUE = "repondue", "Répondue"
        ORIENTEE = "orientee", "Orientée vers un médecin"

    client_id = models.UUIDField(db_index=True)
    texte = models.TextField("question", max_length=1000)
    medicament = models.ForeignKey(Medicament, null=True, blank=True, on_delete=models.SET_NULL)
    statut = models.CharField(max_length=12, choices=Statut.choices, default=Statut.EN_ATTENTE)
    reponse = models.TextField(max_length=2000, blank=True)
    repondu_par = models.ForeignKey(Pharmacie, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="reponses")
    cree_le = models.DateTimeField(auto_now_add=True)
    repondu_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-cree_le"]

    def __str__(self):
        return self.texte[:60]

