import io
import shutil
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image

from .images import nom_fichier
from .models import Medicament

MEDIA_TEST = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_TEST)
class ImagesTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEST, ignore_errors=True)

    def setUp(self):
        self.doliprane = Medicament.objects.create(
            dci="Paracétamol", nom_commercial="Doliprane", dosage="500 mg", forme="comprime"
        )
        self.sirop = Medicament.objects.create(
            dci="Amoxicilline", nom_commercial="Amoxicilline suspension", dosage="250 mg/5 ml",
            forme="suspension", ordonnance_requise=True,
        )

    def ouvrir(self, medicament):
        medicament.refresh_from_db()
        medicament.image.open("rb")
        try:
            return Image.open(io.BytesIO(medicament.image.read()))
        finally:
            medicament.image.close()

    def test_generation_pour_toutes_les_formes(self):
        for forme, _ in Medicament.Forme.choices:
            Medicament.objects.create(dci="Test", nom_commercial=f"Produit {forme}", dosage="10 mg", forme=forme)
        call_command("generer_images", stdout=io.StringIO())
        for m in Medicament.objects.all():
            self.assertTrue(m.image_est_illustration)
            image = self.ouvrir(m)
            self.assertEqual((image.format, image.size), ("WEBP", (640, 640)))

    def test_import_remplace_illustration_et_n_est_pas_ecrase(self):
        call_command("generer_images", stdout=io.StringIO())
        dossier = Path(tempfile.mkdtemp())
        try:
            # Photo PNG volumineuse avec transparence, nommée selon le médicament.
            Image.new("RGBA", (2000, 1500), (255, 0, 0, 128)).save(dossier / f"{nom_fichier(self.doliprane)}.png")
            Image.new("RGB", (50, 50)).save(dossier / "inconnu.jpg")
            sortie = io.StringIO()
            call_command("importer_images", str(dossier), stdout=sortie)
            self.assertIn("1 photo(s) importée(s)", sortie.getvalue())
            self.assertIn("inconnu.jpg", sortie.getvalue())
        finally:
            shutil.rmtree(dossier)

        self.doliprane.refresh_from_db()
        self.assertFalse(self.doliprane.image_est_illustration)
        image = self.ouvrir(self.doliprane)
        self.assertEqual(image.format, "WEBP")
        self.assertLessEqual(max(image.size), 800)

        # Régénérer les illustrations ne touche pas aux vraies photos.
        call_command("generer_images", "--regenerer", stdout=io.StringIO())
        self.doliprane.refresh_from_db()
        self.assertFalse(self.doliprane.image_est_illustration)

    def test_api_expose_url_absolue(self):
        call_command("generer_images", stdout=io.StringIO())
        r = self.client.get("/api/medicaments/", {"q": "doliprane"})
        med = r.json()["results"][0]
        self.assertTrue(med["image"].startswith("http://testserver/media/medicaments/doliprane-500-mg"))
        self.assertTrue(med["image_est_illustration"])
