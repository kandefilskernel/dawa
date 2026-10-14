import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from config.jetons import TAILLE_CLE, cle_en_pem, generer_cle_privee


class Command(BaseCommand):
    help = "Crée la clé privée RSA qui signe les jetons d'appareil (JWT RS256)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--remplacer", action="store_true",
            help="Écrase la clé existante : tous les jetons déjà émis deviennent invalides.",
        )

    def handle(self, *args, remplacer=False, **options):
        fichier = settings.JWT_CLE_PRIVEE_FICHIER
        if fichier.exists() and not remplacer:
            raise CommandError(f"{fichier} existe déjà (--remplacer pour l'écraser).")
        fichier.parent.mkdir(parents=True, exist_ok=True)
        fichier.write_bytes(cle_en_pem(generer_cle_privee()))
        os.chmod(fichier, 0o600)
        self.stdout.write(self.style.SUCCESS(f"Clé RSA {TAILLE_CLE} bits écrite dans {fichier}."))
        self.stdout.write("Ne la versionnez jamais et sauvegardez-la : la perdre déconnecte tous les appareils.")
