from django.contrib.gis.geos import Point
from django.test import TestCase

from catalogue.models import Medicament
from pharmacies.models import Pharmacie
from stock.models import Stock

from .models import Etablissement


class AnnuaireTests(TestCase):
    def test_filtres_et_tri(self):
        def creer(nom, type_, lat, urgences=False, valide=True):
            Etablissement.objects.create(nom=nom, type=type_, adresse="x", urgences_24h=urgences,
                                         est_valide=valide, position=Point(27.48, lat, srid=4326))

        creer("Hôpital loin", "hopital", -11.70, urgences=True)
        creer("Hôpital proche", "hopital", -11.665, urgences=True)
        creer("Labo", "laboratoire", -11.66)
        creer("Non validé", "hopital", -11.66, valide=False)
        r = self.client.get("/api/etablissements/", {"type": "hopital", "lat": -11.664, "lng": 27.479})
        self.assertEqual([e["nom"] for e in r.json()], ["Hôpital proche", "Hôpital loin"])
        r = self.client.get("/api/etablissements/", {"urgences": "1"})
        self.assertEqual(len(r.json()), 2)


class StockPharmacieTests(TestCase):
    def test_produits_disponibles(self):
        p = Pharmacie.objects.create(nom="P", adresse="x", telephone="0", est_validee=True,
                                     position=Point(27.48, -11.66, srid=4326))
        a = Medicament.objects.create(dci="Amoxicilline", nom_commercial="Amoxicilline")
        b = Medicament.objects.create(dci="Ibuprofène", nom_commercial="Ibuprofène")
        Stock.objects.create(pharmacie=p, medicament=a, prix=5000)
        Stock.objects.create(pharmacie=p, medicament=b, disponible=False)
        r = self.client.get(f"/api/pharmacies/{p.id}/stock/")
        self.assertEqual([s["medicament"]["nom_commercial"] for s in r.json()], ["Amoxicilline"])
        r = self.client.get(f"/api/pharmacies/{p.id}/stock/", {"q": "ibupro"})
        self.assertEqual(r.json(), [])
