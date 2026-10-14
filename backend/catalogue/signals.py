from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .images import generer_illustration
from .models import Medicament


@receiver(pre_save, sender=Medicament)
def memoriser_anciennes_valeurs(sender, instance, **kwargs):
    if instance.pk:
        ancien = Medicament.objects.filter(pk=instance.pk).values(*Medicament.CHAMPS_ILLUSTRATION).first()
        instance._valeurs_illustrees = ancien
    else:
        instance._valeurs_illustrees = None


@receiver(post_save, sender=Medicament)
def illustrer_automatiquement(sender, instance, update_fields=None, **kwargs):
    """
    Chaque médicament a toujours une image :
    - pas d'image → illustration générée ;
    - illustration dont le nom, le dosage, la forme… ont changé → illustration redessinée.
    Une vraie photo n'est jamais touchée.
    """
    if update_fields and "image" in update_fields:
        return  # Sauvegarde faite par ce signal ou par un import : rien à faire.

    if instance.image and not instance.image_est_illustration:
        return

    ancien = getattr(instance, "_valeurs_illustrees", None)
    a_jour = instance.image and ancien and all(
        ancien[champ] == getattr(instance, champ) for champ in Medicament.CHAMPS_ILLUSTRATION
    )
    if a_jour:
        return

    if instance.image:
        instance.image.delete(save=False)
    illustration = generer_illustration(instance)
    instance.image.save(illustration.name, illustration, save=False)
    instance.image_est_illustration = True
    instance.image_credit = ""
    instance.save(update_fields=["image", "image_est_illustration", "image_credit"])
