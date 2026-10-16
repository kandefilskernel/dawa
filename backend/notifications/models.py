from django.db import models


class AppareilPush(models.Model):
    """
    Téléphone qui accepte les notifications Firebase (FCM). Relié à l'appareil anonyme
    (`client_id` du jeton signé) : ses réservations, alertes et questions.
    """

    class Langue(models.TextChoices):
        FR = "fr", "Français"
        SW = "sw", "Kiswahili"
        EN = "en", "English"

    client_id = models.UUIDField(db_index=True)
    jeton = models.CharField("jeton FCM", max_length=512, unique=True)
    langue = models.CharField(max_length=2, choices=Langue.choices, default=Langue.FR)
    maj_le = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "téléphone (notifications)"
        verbose_name_plural = "téléphones (notifications)"

    def __str__(self):
        return f"{self.client_id} ({self.langue})"
