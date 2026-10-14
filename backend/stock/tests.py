from datetime import timedelta

from django.contrib.gis.geos import Point
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from catalogue.models import Medicament
from pharmacies.models import Garde, Pharmacie
from stock.models import Recherche, Stock

CENTRE = (-11.664, 27.479)  # lat, lng


def creer_pharmacie(nom, lat, lng, validee=True):
    return Pharmacie.objects.create(
        nom=nom, adresse="x", telephone="0", est_validee=validee,
        position=Point(lng, lat, srid=4326),
    )


class RechercheTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.doliprane = Medicament.objects.create(dci="Paracétamol", nom_commercial="Doliprane", dosage="500 mg")
        cls.panadol = Medicament.objects.create(dci="Paracétamol", nom_commercial="Panadol", dosage="500 mg")
        cls.amox = Medicament.objects.create(dci="Amoxicilline", nom_commercial="Amoxicilline", dosage="500 mg")

        cls.proche = creer_pharmacie("Proche", -11.665, 27.480)       # ~0,15 km
        cls.moyenne = creer_pharmacie("Moyenne", -11.690, 27.470)     # ~3 km
        cls.loin = creer_pharmacie("Loin", -11.400, 27.300)           # ~35 km
        cls.non_validee = creer_pharmacie("Non validée", -11.664, 27.479, validee=False)

        Stock.objects.create(pharmacie=cls.moyenne, medicament=cls.doliprane, prix=4500)
        Stock.objects.create(pharmacie=cls.proche, medicament=cls.panadol, prix=4000)
        Stock.objects.create(pharmacie=cls.loin, medicament=cls.doliprane, prix=3000)
        Stock.objects.create(pharmacie=cls.non_validee, medicament=cls.doliprane, prix=1000)
        Stock.objects.create(pharmacie=cls.proche, medicament=cls.amox, disponible=False)

    def rechercher(self, **params):
        return self.client.get("/api/recherche/", params)

    def noms(self, response):
        return [r["pharmacie"]["nom"] for r in response.json()["resultats"]]

    def test_nombre_de_requetes_independant_des_resultats(self):
        """Pas de requête par pharmacie (garde, livraison) : le coût ne grandit pas avec la liste."""
        def nb_requetes():
            with CaptureQueriesContext(connection) as ctx:
                self.rechercher(medicament=self.doliprane.pk)
            return len(ctx.captured_queries)

        avant = nb_requetes()
        for i in range(5):
            p = creer_pharmacie(f"Extra {i}", -11.66, 27.48)
            Stock.objects.create(pharmacie=p, medicament=self.doliprane, prix=5000)
        self.assertEqual(nb_requetes(), avant)

    def test_tri_par_distance_et_rayon(self):
        r = self.rechercher(q="doliprane", lat=CENTRE[0], lng=CENTRE[1], rayon=5)
        self.assertEqual(r.status_code, 200)
        # Panadol (même DCI) remonte aussi ; la pharmacie lointaine est hors rayon.
        self.assertEqual(self.noms(r), ["Proche", "Moyenne"])
        self.assertLess(r.json()["resultats"][0]["distance_km"], 1)

    def test_tolere_fautes_et_accents(self):
        r = self.rechercher(q="paracetamol")
        self.assertIn("Proche", self.noms(r))
        r = self.rechercher(q="dolipran")
        self.assertIn("Moyenne", self.noms(r))

    def test_sans_position_tri_par_prix(self):
        r = self.rechercher(q="doliprane")
        prix = [res["prix"] for res in r.json()["resultats"]]
        self.assertEqual(prix, sorted(prix))
        self.assertNotIn("Non validée", self.noms(r))

    def test_equivalents_meme_forme_seulement(self):
        sirop = Medicament.objects.create(
            dci="Paracétamol", nom_commercial="Paracétamol sirop", dosage="120 mg/5 ml", forme="sirop"
        )
        Stock.objects.create(pharmacie=self.proche, medicament=sirop, prix=3000)
        r = self.rechercher(q="doliprane", lat=CENTRE[0], lng=CENTRE[1])
        produits = {res["medicament"]["nom_commercial"] for res in r.json()["resultats"]}
        self.assertEqual(produits, {"Doliprane", "Panadol"})

    def test_recherche_par_medicament_choisi(self):
        r = self.rechercher(medicament=self.panadol.id)
        self.assertEqual(r.json()["medicament"]["nom_commercial"], "Panadol")
        self.assertIn("Moyenne", self.noms(r))  # Doliprane = équivalent
        self.assertEqual(self.rechercher(medicament=99999).status_code, 400)

    def test_rupture_exclue(self):
        r = self.rechercher(q="amoxicilline", lat=CENTRE[0], lng=CENTRE[1])
        self.assertEqual(self.noms(r), [])

    def test_stock_ancien_non_confirme(self):
        Stock.objects.filter(pharmacie=self.proche).update(mis_a_jour_le=timezone.now() - timedelta(days=3))
        r = self.rechercher(q="panadol", lat=CENTRE[0], lng=CENTRE[1])
        self.assertFalse(r.json()["resultats"][0]["confirme"])

    def test_journalise_zone_arrondie(self):
        self.rechercher(q="doliprane", lat=-11.66789, lng=27.47912)
        recherche = Recherche.objects.get()
        self.assertEqual((recherche.zone.y, recherche.zone.x), (-11.67, 27.48))

    def test_parametres_invalides(self):
        self.assertEqual(self.rechercher(q="d").status_code, 400)
        self.assertEqual(self.rechercher(q="doliprane", lat="abc", lng="1").status_code, 400)


class GardeTests(TestCase):
    def test_pharmacies_de_garde(self):
        p1 = creer_pharmacie("De garde", -11.66, 27.48)
        creer_pharmacie("Pas de garde", -11.67, 27.48)
        maintenant = timezone.now()
        Garde.objects.create(pharmacie=p1, debut=maintenant - timedelta(hours=1), fin=maintenant + timedelta(hours=10))
        r = self.client.get("/api/pharmacies/garde/")
        self.assertEqual([p["nom"] for p in r.json()], ["De garde"])
        r = self.client.get("/api/pharmacies/")
        flags = {p["nom"]: p["de_garde"] for p in r.json()["results"]}
        self.assertEqual(flags, {"De garde": True, "Pas de garde": False})
