from django.db import models

from pharmacies.models import Pharmacie


class MessageEntrant(models.Model):
    """Journal des SMS / WhatsApp reçus (audit et support)."""

    canal = models.CharField(max_length=12, default="sms")
    expediteur = models.CharField(max_length=30)
    texte = models.TextField(max_length=1600)
    pharmacie = models.ForeignKey(Pharmacie, null=True, blank=True, on_delete=models.SET_NULL)
    reponse = models.TextField(blank=True)
    recu_le = models.DateTimeField(auto_now_add=True)
    simulation = models.BooleanField(default=False, help_text="Envoyé depuis le simulateur du portail")

    class Meta:
        ordering = ["-recu_le"]
        verbose_name = "message reçu"
        verbose_name_plural = "messages reçus"

    def __str__(self):
        return f"{self.expediteur} : {self.texte[:40]}"
