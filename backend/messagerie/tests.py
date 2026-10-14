from django.contrib.gis.geos import Point
from django.test import TestCase, override_settings

from catalogue.models import Medicament
from pharmacies.models import Pharmacie
from stock.models import Stock

from .models import MessageEntrant

JETON = "jeton-de-test"


@override_settings(MESSAGERIE_JETON=JETON)
class MessagerieTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pharmacie = Pharmacie.objects.create(nom="Ma pharmacie", adresse="x", telephone="099 000 0001",
                                                 est_validee=True, position=Point(27.48, -11.66, srid=4326))
        cls.doliprane = Medicament.objects.create(dci="Paracétamol", nom_commercial="Doliprane", dosage="500 mg")
        cls.amox = Medicament.objects.create(dci="Amoxicilline", nom_commercial="Amoxicilline", dosage="500 mg")

    def envoyer(self, texte, de="+243990000001", jeton=JETON):
        return self.client.post("/api/messagerie/entrant/", {"de": de, "texte": texte},
                                content_type="application/json", HTTP_X_DAWA_JETON=jeton)

    def stock(self, medicament):
        return Stock.objects.get(pharmacie=self.pharmacie, medicament=medicament)

    def test_jeton_obligatoire(self):
        self.assertIn(self.envoyer("OK", jeton="faux").status_code, (401, 403))

    def test_numero_inconnu(self):
        self.assertIn("aucune pharmacie", self.envoyer("OK", de="+243810000000").json()["reponse"])

    def test_plusieurs_commandes(self):
        r = self.envoyer("dispo dolipran 4500\nRUPTURE amoxicilline\nbonjour")
        lignes = r.json()["reponse"].splitlines()
        self.assertEqual(lignes[0], "OK Doliprane 500 mg : disponible, 4500 FC.")
        self.assertEqual(lignes[1], "OK Amoxicilline 500 mg : en rupture.")
        self.assertIn("Commande inconnue", lignes[2])
        self.assertEqual((self.stock(self.doliprane).prix, self.stock(self.doliprane).source), (4500, "sms"))
        self.assertFalse(self.stock(self.amox).disponible)
        self.assertEqual(MessageEntrant.objects.get().pharmacie, self.pharmacie)

    def test_dosage_n_est_pas_un_prix(self):
        self.envoyer("DISPO amoxicilline 500")
        self.assertIsNone(self.stock(self.amox).prix)

    def test_format_twilio(self):
        r = self.client.post("/api/messagerie/entrant/", {"From": "whatsapp:+243990000001", "Body": "PRIX doliprane 5000"},
                             HTTP_X_DAWA_JETON=JETON)
        self.assertEqual(r.json()["reponse"], "OK Doliprane 500 mg : 5000 FC.")
        self.assertEqual(MessageEntrant.objects.get().canal, "whatsapp")
