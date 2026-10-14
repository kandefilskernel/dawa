import io
import uuid
from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from config.jetons import entete_authorization
from catalogue.models import Medicament

from .models import Lot, Signalement


class VerificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.coartem = Medicament.objects.create(dci="Artéméther", nom_commercial="Coartem")
        Lot.objects.create(medicament=cls.coartem, numero="AB-123", date_expiration=date.today() + timedelta(days=300))
        Lot.objects.create(medicament=cls.coartem, numero="OLD1", date_expiration=date.today() - timedelta(days=1))
        Lot.objects.create(medicament=cls.coartem, numero="RAP9", statut="rappele")
        Lot.objects.create(medicament=cls.coartem, numero="FAUX7", statut="contrefait")

    def verifier(self, lot):
        return self.client.get("/api/verification/", {"lot": lot}).json()

    def test_resultats(self):
        self.assertEqual(self.verifier(" ab 123 ")["resultat"], "conforme")  # espaces, casse, tiret ignorés
        self.assertEqual(self.verifier("OLD1")["resultat"], "expire")
        self.assertEqual(self.verifier("RAP9")["resultat"], "rappele")
        self.assertEqual(self.verifier("faux7")["resultat"], "contrefait")
        inconnu = self.verifier("ZZZ999")
        self.assertEqual(inconnu["resultat"], "inconnu")
        self.assertIn("ne veut pas dire que le produit est faux", inconnu["message"])
        self.assertEqual(self.verifier("AB123")["lot"]["medicament"]["nom_commercial"], "Coartem")

    def test_numero_trop_court(self):
        self.assertEqual(self.client.get("/api/verification/", {"lot": "a"}).status_code, 400)


class SignalementTests(TestCase):
    def setUp(self):
        self.client_id = str(uuid.uuid4())
        self.med = Medicament.objects.create(dci="Artéméther", nom_commercial="Coartem")

    def test_signaler_avec_photo(self):
        tampon = io.BytesIO()
        Image.new("RGB", (1200, 900), "blue").save(tampon, "JPEG")
        r = self.client.post("/api/signalements/", {
            "medicament_id": self.med.id, "numero_lot": "XYZ", "lieu_achat": "Marché Mzee",
            "description": "Boîte mal imprimée, comprimés friables",
            "photo": SimpleUploadedFile("boite.jpg", tampon.getvalue(), content_type="image/jpeg"),
        }, HTTP_AUTHORIZATION=entete_authorization(self.client_id))
        self.assertEqual(r.status_code, 201, r.content)
        signalement = Signalement.objects.get()
        self.assertTrue(signalement.photo.name.endswith(".webp"))
        liste = self.client.get("/api/signalements/", HTTP_AUTHORIZATION=entete_authorization(self.client_id)).json()
        self.assertEqual(len(liste), 1)

    def test_description_obligatoire(self):
        r = self.client.post("/api/signalements/", {"description": "bof"}, HTTP_AUTHORIZATION=entete_authorization(self.client_id))
        self.assertEqual(r.status_code, 400)
