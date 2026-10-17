from datetime import datetime
from unittest import mock
from zoneinfo import ZoneInfo

from django.contrib.gis.geos import Point
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from catalogue.models import Medicament
from stock.models import Stock

from . import trajets
from .horaires import etat, plages
from .models import Garde, Pharmacie

LUBUMBASHI = ZoneInfo("Africa/Lubumbashi")


def le(jour, heure, minute=0):
    """Octobre 2026 : le 12 est un lundi."""
    return datetime(2026, 10, jour, heure, minute, tzinfo=LUBUMBASHI)


class HorairesTests(SimpleTestCase):
    def test_lecture(self):
        self.assertEqual(plages("Lun–Sam 8h–20h")[5], [(480, 1200)])
        self.assertNotIn(6, plages("Lun–Sam 8h–20h"))
        p = plages("Lun-Ven 8h30 - 18h, Sam 9h–13h")
        self.assertEqual((p[0], p[5]), ([(510, 1080)], [(540, 780)]))
        self.assertEqual(len(plages("24h/24")), 7)
        self.assertEqual(plages("Tous les jours 7h–22h")[6], [(420, 1320)])
        self.assertIsNone(plages(""))
        self.assertIsNone(plages("appelez-nous"))

    def test_etat(self):
        h = "Lun–Sam 8h–20h"
        self.assertEqual(etat(h, le(12, 10)), (True, 0))
        self.assertEqual(etat(h, le(12, 7, 30)), (False, 30))
        self.assertEqual(etat(h, le(12, 21)), (False, 11 * 60))       # rouvre demain à 8h
        self.assertEqual(etat(h, le(17, 21)), (False, 35 * 60))       # samedi soir → lundi 8h
        self.assertEqual(etat("", le(12, 3)), (None, None))


class TrajetsTests(SimpleTestCase):
    def test_estimation_sans_serveur(self):
        t = trajets.trajets((-11.664, 27.479), [(-11.664, 27.479 + 0.0184)])[0]  # ~2 km
        self.assertEqual({m: v.source for m, v in t.items()}, dict.fromkeys(trajets.MODES, "estimation"))
        self.assertAlmostEqual(t["moto"].distance_km, 2.0 * 1.35, delta=0.05)
        self.assertEqual(t["moto"].minutes, 7)    # 2,7 km à 22 km/h
        self.assertEqual(t["pied"].minutes, 33)   # 2,5 km à 4,5 km/h
        self.assertLess(t["moto"].minutes, t["voiture"].minutes)

    @override_settings(ROUTAGE_URL="http://osrm.test")
    def test_distances_par_la_route(self):
        def reponse(url):
            pied = "routed-foot" in url
            return {"code": "Ok", "distances": [[0, 3000 if pied else 4400]]}

        with mock.patch.object(trajets, "_get_json", side_effect=reponse) as appel:
            t = trajets.trajets((-11.6641, 27.479), [(-11.67, 27.49)])[0]
            trajets.trajets((-11.6641, 27.479), [(-11.67, 27.49)])  # mis en cache
        self.assertEqual(appel.call_count, 2)  # un appel par profil, pas de nouvel appel ensuite
        self.assertEqual((t["pied"].distance_km, t["pied"].minutes, t["pied"].source), (3.0, 40, "route"))
        self.assertEqual((t["moto"].minutes, t["voiture"].minutes), (12, 16))

    def setUp(self):
        cache.clear()

    @override_settings(ROUTAGE_URL="http://osrm.test")
    def test_serveur_injoignable(self):
        with mock.patch.object(trajets, "_get_json", side_effect=TimeoutError) as appel:
            t = trajets.trajets((-11.6642, 27.479), [(-11.67, 27.49)])[0]
            trajets.trajets((-11.6642, 27.479), [(-11.68, 27.49)])
        self.assertEqual(t["moto"].source, "estimation")
        self.assertEqual(appel.call_count, 2)  # en panne : pas de nouvel essai pendant quelques minutes

    @override_settings(ROUTAGE_URL="http://osrm.test")
    def test_un_seul_profil_repond(self):
        def reponse(url):
            if "routed-foot" in url:
                raise TimeoutError
            return {"code": "Ok", "distances": [[0, 4500]]}

        with mock.patch.object(trajets, "_get_json", side_effect=reponse):
            t = trajets.trajets((-11.6643, 27.479), [(-11.67, 27.49)])[0]
        self.assertEqual((t["pied"].distance_km, t["pied"].minutes, t["pied"].source), (4.5, 60, "route"))


class PlusRapideTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.amox = Medicament.objects.create(dci="Amoxicilline", nom_commercial="Amoxil", dosage="500 mg")

        def pharmacie(nom, lng, horaires="Lun–Dim 0h–24h"):
            p = Pharmacie.objects.create(nom=nom, adresse="x", telephone="0", est_validee=True,
                                         horaires=horaires, position=Point(lng, -11.664, srid=4326))
            Stock.objects.create(pharmacie=p, medicament=cls.amox, prix=5000)
            return p

        cls.fermee = pharmacie("Fermée tout près", 27.480, "Lun–Ven 8h–9h")
        cls.ouverte = pharmacie("Ouverte un peu loin", 27.500)
        cls.garde = pharmacie("De garde, fermée normalement", 27.510, "Lun–Ven 8h–9h")
        Garde.objects.create(pharmacie=cls.garde, debut=timezone.now(), fin=timezone.now() + timezone.timedelta(hours=8))

    def rechercher(self, mode="moto"):
        with mock.patch("pharmacies.horaires.maintenant", return_value=le(17, 22)):  # samedi soir
            return self.client.get("/api/recherche/", {"medicament": self.amox.pk, "lat": -11.664, "lng": 27.479,
                                                       "rayon": 10, "mode": mode}).json()

    def test_classement_par_delai(self):
        d = self.rechercher()
        self.assertEqual(d["mode"], "moto")
        noms = [r["pharmacie"]["nom"] for r in d["resultats"]]
        self.assertEqual(noms, ["Ouverte un peu loin", "De garde, fermée normalement", "Fermée tout près"])
        fermee = d["resultats"][2]["acces"]
        self.assertFalse(fermee["ouverte"])
        self.assertEqual(fermee["ouvre_dans_min"], 34 * 60)  # lundi 8h
        self.assertTrue(d["resultats"][1]["acces"]["ouverte"])
        ouverte = d["resultats"][0]["acces"]
        self.assertEqual(ouverte["delai_min"]["moto"], ouverte["trajets"]["moto"]["minutes"])
        self.assertEqual(set(ouverte["trajets"]), {"pied", "moto", "voiture"})

    def test_stock_non_confirme_classe_apres(self):
        Stock.objects.filter(pharmacie=self.ouverte).update(mis_a_jour_le=timezone.now() - timezone.timedelta(days=5))
        noms = [r["pharmacie"]["nom"] for r in self.rechercher()["resultats"]]
        self.assertEqual(noms[0], "De garde, fermée normalement")

    def test_mode_inconnu(self):
        self.assertEqual(self.rechercher(mode="avion")["mode"], "moto")


class ItineraireTests(TestCase):
    def setUp(self):
        cache.clear()

    params = {"lat": -11.664, "lng": 27.479, "vers_lat": -11.672, "vers_lng": 27.492, "mode": "pied"}

    def test_sans_serveur_ligne_droite(self):
        d = self.client.get("/api/itineraire/", self.params).json()
        self.assertEqual(d["source"], "estimation")
        self.assertEqual(d["points"], [[-11.664, 27.479], [-11.672, 27.492]])
        self.assertEqual(d["mode"], "pied")
        self.assertGreater(d["minutes"], 15)

    @override_settings(ROUTAGE_URL="http://osrm.test")
    def test_trace_par_la_route(self):
        route = {"code": "Ok", "routes": [{"distance": 3810.0, "geometry": {
            "coordinates": [[27.479, -11.664], [27.485, -11.668], [27.492, -11.672]]}}]}
        with mock.patch.object(trajets, "_get_json", return_value=route) as appel:
            d = self.client.get("/api/itineraire/", {**self.params, "mode": "moto"}).json()
        self.assertIn("/routed-car/route/v1/", appel.call_args[0][0])
        self.assertEqual(d["points"][1], [-11.668, 27.485])
        self.assertEqual((d["distance_km"], d["minutes"], d["source"]), (3.81, 10, "route"))

    def test_parametres_obligatoires(self):
        self.assertEqual(self.client.get("/api/itineraire/", {"lat": 1, "lng": 2}).status_code, 400)
