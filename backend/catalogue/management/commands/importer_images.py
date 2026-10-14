import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from catalogue.images import nom_fichier, preparer_photo
from catalogue.models import Medicament

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class Command(BaseCommand):
    help = (
        "Importe en masse les photos d'un dossier. Chaque fichier est associé à un médicament par son nom : "
        "« doliprane-500-mg.jpg » (nom + dosage), « doliprane.jpg » (nom seul, si unique), "
        "le code-barres « 3400935955838.jpg », ou l'identifiant « 12.jpg ». "
        "Un fichier credits.json facultatif ({\"doliprane-500-mg\": \"Auteur, CC BY 4.0, source\"}) "
        "renseigne le crédit de chaque photo, obligatoire pour une photo sous licence libre."
    )

    def add_arguments(self, parser):
        parser.add_argument("dossier", nargs="?", default="images_a_importer")
        parser.add_argument("--lister", action="store_true", help="Affiche le nom de fichier attendu pour chaque médicament.")
        parser.add_argument("--simulation", action="store_true", help="Montre ce qui serait importé, sans rien modifier.")

    def handle(self, *args, dossier, lister=False, simulation=False, **options):
        medicaments = list(Medicament.objects.all())

        if lister:
            for m in medicaments:
                etat = "illustration" if m.image_est_illustration or not m.image else "photo ✓"
                self.stdout.write(f"{nom_fichier(m)}.jpg    [{etat}]    {m}")
            return

        chemin = Path(dossier)
        if not chemin.is_dir():
            raise CommandError(f"Dossier introuvable : {chemin.resolve()}")

        index = self._index(medicaments)
        fichier_credits = chemin / "credits.json"
        credits = json.loads(fichier_credits.read_text(encoding="utf-8")) if fichier_credits.exists() else {}
        importes, inconnus = 0, []
        for fichier in sorted(chemin.iterdir()):
            if fichier.suffix.lower() not in EXTENSIONS:
                continue
            medicament = index.get(slugify(fichier.stem))
            if medicament is None:
                inconnus.append(fichier.name)
                continue
            credit = credits.get(fichier.stem, "")
            if simulation:
                self.stdout.write(f"{fichier.name} → {medicament}" + (f"  ({credit})" if credit else ""))
            else:
                with fichier.open("rb") as f:
                    photo = preparer_photo(f, nom_fichier(medicament))
                if medicament.image:
                    medicament.image.delete(save=False)
                medicament.image.save(photo.name, photo, save=False)
                medicament.image_est_illustration = False
                medicament.image_credit = credit
                medicament.save(update_fields=["image", "image_est_illustration", "image_credit"])
            importes += 1

        verbe = "seraient importées" if simulation else "importée(s)"
        self.stdout.write(self.style.SUCCESS(f"{importes} photo(s) {verbe}."))
        if inconnus:
            self.stdout.write(self.style.WARNING(
                f"{len(inconnus)} fichier(s) sans médicament correspondant : {', '.join(inconnus)}\n"
                "Lancez avec --lister pour voir les noms attendus."
            ))

    def _index(self, medicaments):
        """Clés reconnues → médicament. Un nom commercial seul n'est retenu que s'il est unique."""
        index = {}
        par_nom = {}
        for m in medicaments:
            index[nom_fichier(m)] = m
            index[str(m.pk)] = m
            if m.code_barres:
                index[slugify(m.code_barres)] = m
            par_nom.setdefault(slugify(m.nom_commercial), []).append(m)
        for cle, liste in par_nom.items():
            if len(liste) == 1:
                index.setdefault(cle, liste[0])
        return index
