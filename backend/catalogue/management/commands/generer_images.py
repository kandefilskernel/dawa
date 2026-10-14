from django.core.management.base import BaseCommand

from catalogue.images import generer_illustration
from catalogue.models import Medicament


class Command(BaseCommand):
    help = "Génère une illustration pour chaque médicament sans image (les vraies photos ne sont jamais écrasées)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--regenerer", action="store_true",
            help="Régénère aussi les illustrations existantes (utile après un changement de nom ou de dosage).",
        )

    def handle(self, *args, regenerer=False, **options):
        medicaments = Medicament.objects.all()
        nb = 0
        for medicament in medicaments:
            a_une_photo = medicament.image and not medicament.image_est_illustration
            if a_une_photo or (medicament.image and not regenerer):
                continue
            if medicament.image:
                medicament.image.delete(save=False)
            illustration = generer_illustration(medicament)
            medicament.image.save(illustration.name, illustration, save=False)
            medicament.image_est_illustration = True
            medicament.image_credit = ""
            medicament.save(update_fields=["image", "image_est_illustration", "image_credit"])
            nb += 1
        self.stdout.write(self.style.SUCCESS(f"{nb} illustration(s) générée(s) sur {medicaments.count()} médicaments."))
