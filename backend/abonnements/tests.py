from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.test import TestCase
from django.utils import timezone

from catalogue.models import Medicament
from pharmacies.models import Pharmacie
from portail.models import Pharmacien
from stock.models import Stock

from .models import Abonnement


def pharmacie(nom, lat):
    return Pharmacie.objects.create(nom=nom, adresse="x", telephone="0", est_validee=True,
                                    position=Point(27.479, lat, srid=4326))


class AbonnementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.proche = pharmacie("Proche", -11.665)
        cls.moyenne = pharmacie("Moyenne", -11.680)
        cls.loin = pharmacie("Loin sponsor", -11.695)
        cls.med = Medicament.objects.create(dci="Paracétamol", nom_commercial="Doliprane", dosage="500 mg")
        for p in (cls.proche, cls.moyenne, cls.loin):
            Stock.objects.create(pharmacie=p, medicament=cls.med, prix=4000)
        utilisateur = get_user_model().objects.create_user("pharma", password="mdp-test-123")
        Pharmacien.objects.create(utilisateur=utilisateur, pharmacie=cls.loin)

    def rechercher(self):
        return self.client.get("/api/recherche/", {"medicament": self.med.id, "lat": -11.664, "lng": 27.479}).json()

    def test_demande_paiement_puis_activation(self):
        self.client.login(username="pharma", password="mdp-test-123")
        self.client.post("/portail/abonnement/", {"formule": "visibilite", "mois": "3"})
        abonnement = Abonnement.objects.get()
        self.assertEqual((abonnement.statut, abonnement.montant), ("en_attente", 225_000))
        self.assertEqual(self.rechercher()["resultats"][0]["pharmacie"]["nom"], "Proche")  # pas encore actif

        abonnement.activer("MP123")
        self.assertEqual(abonnement.fin - abonnement.debut, timedelta(days=90))
        resultats = self.rechercher()["resultats"]
        self.assertEqual([r["pharmacie"]["nom"] for r in resultats], ["Loin sponsor", "Proche", "Moyenne"])
        self.assertEqual([r["sponsorise"] for r in resultats], [True, False, False])

    def test_renouvellement_s_enchaine(self):
        premier = Abonnement.objects.create(pharmacie=self.loin, formule="essentiel", montant=1, reference="A1")
        premier.activer()
        second = Abonnement.objects.create(pharmacie=self.loin, formule="essentiel", montant=1, reference="A2")
        second.activer()
        self.assertEqual(second.debut, premier.fin)

    def test_abonnement_expire_n_est_plus_sponsorise(self):
        Abonnement.objects.create(
            pharmacie=self.loin, formule="visibilite", montant=1, reference="A3", statut="actif",
            debut=timezone.localdate() - timedelta(days=40), fin=timezone.localdate() - timedelta(days=10),
        )
        self.assertFalse(any(r["sponsorise"] for r in self.rechercher()["resultats"]))
