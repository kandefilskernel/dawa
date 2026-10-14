from urllib.parse import unquote

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.test import TestCase

from catalogue.models import Medicament
from pharmacies.models import Pharmacie
from portail.models import Pharmacien

from .models import Commande, Grossiste, Offre


class CommandeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pharmacie = Pharmacie.objects.create(nom="Ma pharmacie", adresse="x", telephone="+243990000001",
                                                 est_validee=True, position=Point(27.48, -11.66, srid=4326))
        utilisateur = get_user_model().objects.create_user("pharma", password="mdp-test-123")
        Pharmacien.objects.create(utilisateur=utilisateur, pharmacie=cls.pharmacie)
        cls.grossiste = Grossiste.objects.create(nom="Grossiste Démo", telephone="+243970000000",
                                                 whatsapp="+243 97 000 0000", minimum_commande=50_000)
        cls.med = Medicament.objects.create(dci="Amoxicilline", nom_commercial="Amoxicilline", dosage="500 mg")
        cls.offre = Offre.objects.create(grossiste=cls.grossiste, medicament=cls.med, prix=3000,
                                         conditionnement="boîte de 20")

    def setUp(self):
        self.client.login(username="pharma", password="mdp-test-123")

    def commander(self, quantite):
        return self.client.post(f"/portail/commandes/nouvelle/{self.grossiste.pk}/",
                                {f"qte_{self.offre.pk}": str(quantite), "note": "Avant midi"})

    def test_minimum_de_commande(self):
        self.commander(10)  # 30 000 FC < 50 000
        self.assertFalse(Commande.objects.exists())

    def test_commande_et_lien_whatsapp(self):
        r = self.commander(20)
        commande = Commande.objects.get()
        self.assertRedirects(r, f"/portail/commandes/{commande.pk}/")
        self.assertEqual(commande.total, 60_000)
        lien = commande.message_whatsapp()
        self.assertTrue(lien.startswith("https://wa.me/243970000000?text="))
        self.assertIn("20 × Amoxicilline 500 mg", unquote(lien))

        self.client.post(f"/portail/commandes/{commande.pk}/", {"action": "recue"})
        commande.refresh_from_db()
        self.assertEqual(commande.statut, "livree")
        self.client.post(f"/portail/commandes/{commande.pk}/", {"action": "annuler"})  # trop tard
        commande.refresh_from_db()
        self.assertEqual(commande.statut, "livree")

    def test_pages(self):
        for url in ["/portail/commandes/", f"/portail/commandes/nouvelle/{self.grossiste.pk}/?q=amox"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)
