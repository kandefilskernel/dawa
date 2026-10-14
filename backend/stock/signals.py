from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from catalogue.search import equivalents

from .models import AlerteStock, Stock

# Rayon maximal d'une alerte (cf. AlerteSerializer) : pré-filtre via l'index spatial.
RAYON_ALERTE_MAX_KM = 50


@receiver(post_save, sender=Stock)
def declencher_alertes(sender, instance, **kwargs):
    """Quand un médicament devient disponible, on prévient les alertes en attente à portée."""
    if not instance.disponible or not instance.pharmacie.est_validee:
        return
    alertes = (
        AlerteStock.objects.filter(
            declenchee_le__isnull=True,
            medicament__in=equivalents(instance.medicament),
            position__dwithin=(instance.pharmacie.position, D(km=RAYON_ALERTE_MAX_KM)),
        )
        .annotate(distance=Distance("position", instance.pharmacie.position))
    )
    a_declencher = [a.pk for a in alertes if a.distance.km <= a.rayon_km]
    if a_declencher:
        AlerteStock.objects.filter(pk__in=a_declencher).update(
            declenchee_le=timezone.now(), pharmacie=instance.pharmacie
        )
