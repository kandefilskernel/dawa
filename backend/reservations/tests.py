import uuid
from datetime import timedelta

from django.contrib.gis.geos import Point
from django.test import TestCase
from django.utils import timezone

from config.jetons import entete_authorization
from catalogue.models import Medicament
from pharmacies.models import Pharmacie
from stock.models import AlerteStock, Stock

from .models import Reservation


def pharmacie(nom, lat=-11.664, lng=27.479):
    return Pharmacie.objects.create(
        nom=nom, adresse="x", telephone="0", est_validee=True, position=Point(lng, lat, srid=4326)
    )


class ReservationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.med = Medicament.objects.create(dci="Amoxicilline", nom_commercial="Amoxicilline", dosage="500 mg")
        cls.p1 = pharmacie("P1")
        cls.p2 = pharmacie("P2")
        Stock.objects.create(pharmacie=cls.p1, medicament=cls.med, prix=5000)
        Stock.objects.create(pharmacie=cls.p2, medicament=cls.med, disponible=False)

    def setUp(self):
        self.client_id = str(uuid.uuid4())

    def post(self, pharmacie, **extra):
        data = {"pharmacie_id": pharmacie.id, "medicament_id": self.med.id, "quantite": 2,
                "nom": "Client test", "telephone": "+243 990 000 001", **extra}
        return self.client.post("/api/reservations/", data, content_type="application/json",
                                HTTP_AUTHORIZATION=entete_authorization(self.client_id))

    def get(self, client_id=None):
        return self.client.get("/api/reservations/", HTTP_AUTHORIZATION=entete_authorization(client_id or self.client_id))

    def annuler(self, rid):
        return self.client.post(f"/api/reservations/{rid}/annuler/", HTTP_AUTHORIZATION=entete_authorization(self.client_id))

    def test_reserver_puis_lister(self):
        r = self.post(self.p1)
        self.assertEqual(r.status_code, 201, r.content)
        corps = r.json()
        self.assertEqual(corps["statut"], "en_attente")
        self.assertEqual(corps["prix_unitaire"], 5000)
        self.assertEqual(corps["telephone"], "+243990000001")
        self.assertEqual(len(self.get().json()), 1)
        # Un autre appareil ne voit pas cette réservation.
        self.assertEqual(self.get(client_id=str(uuid.uuid4())).json(), [])

    def test_refuse_si_rupture(self):
        self.assertEqual(self.post(self.p2).status_code, 400)

    def test_refuse_doublon_et_sans_client(self):
        self.post(self.p1)
        self.assertEqual(self.post(self.p1).status_code, 400)
        r = self.client.post("/api/reservations/", {}, content_type="application/json")
        self.assertEqual(r.status_code, 401)  # sans jeton : l'app redemande un jeton

    def test_expiration(self):
        rid = self.post(self.p1).json()["id"]
        Reservation.objects.filter(pk=rid).update(expire_le=timezone.now() - timedelta(minutes=1))
        self.assertEqual(self.get().json()[0]["statut"], "expiree")
        self.assertEqual(self.annuler(rid).status_code, 400)

    def test_annuler(self):
        rid = self.post(self.p1).json()["id"]
        self.assertEqual(self.annuler(rid).json()["statut"], "annulee")


class AlerteTests(TestCase):
    def setUp(self):
        self.client_id = str(uuid.uuid4())
        self.doliprane = Medicament.objects.create(dci="Paracétamol", nom_commercial="Doliprane", dosage="500 mg")
        self.panadol = Medicament.objects.create(dci="Paracétamol", nom_commercial="Panadol", dosage="500 mg")
        self.proche = pharmacie("Proche", -11.665, 27.480)
        self.loin = pharmacie("Loin", -11.400, 27.300)

    def creer_alerte(self):
        return self.client.post(
            "/api/alertes/",
            {"medicament_id": self.doliprane.id, "lat": -11.664, "lng": 27.479, "rayon_km": 5},
            content_type="application/json", HTTP_AUTHORIZATION=entete_authorization(self.client_id),
        )

    def alertes(self):
        return self.client.get("/api/alertes/", HTTP_AUTHORIZATION=entete_authorization(self.client_id)).json()

    def test_declenchee_par_equivalent_proche(self):
        self.assertEqual(self.creer_alerte().status_code, 201)
        Stock.objects.create(pharmacie=self.loin, medicament=self.doliprane)  # hors rayon
        self.assertIsNone(self.alertes()[0]["declenchee_le"])
        Stock.objects.create(pharmacie=self.proche, medicament=self.panadol)  # équivalent proche
        alerte = self.alertes()[0]
        self.assertIsNotNone(alerte["declenchee_le"])
        self.assertEqual(alerte["pharmacie"]["nom"], "Proche")

    def test_pas_de_doublon_et_suppression(self):
        self.creer_alerte()
        self.creer_alerte()
        self.assertEqual(AlerteStock.objects.count(), 1)
        alerte_id = self.alertes()[0]["id"]
        r = self.client.delete(f"/api/alertes/{alerte_id}/", HTTP_AUTHORIZATION=entete_authorization(self.client_id))
        self.assertEqual(r.status_code, 204)


class LivraisonTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from .models import Livreur

        cls.med = Medicament.objects.create(dci="Amoxicilline", nom_commercial="Amoxicilline", dosage="500 mg")
        cls.pharmacie = pharmacie("Livre", -11.664, 27.479)
        cls.sans_livreur = pharmacie("Ne livre pas", -11.664, 27.479)
        for p in (cls.pharmacie, cls.sans_livreur):
            Stock.objects.create(pharmacie=p, medicament=cls.med, prix=5000)
        cls.livreur = Livreur.objects.create(pharmacie=cls.pharmacie, nom="Moto 1", telephone="+243990000009")

    def setUp(self):
        self.client_id = str(uuid.uuid4())

    def reserver(self, pharmacie, **extra):
        data = {"pharmacie_id": pharmacie.id, "medicament_id": self.med.id, "nom": "Client",
                "telephone": "+243990000001", "mode": "livraison",
                "adresse_livraison": "Av. Kasaï 12, près de l'église", "lat_livraison": -11.690, "lng_livraison": 27.470,
                **extra}
        return self.client.post("/api/reservations/", data, content_type="application/json",
                                HTTP_AUTHORIZATION=entete_authorization(self.client_id))

    def test_frais_calcules_et_devis(self):
        r = self.reserver(self.pharmacie)
        self.assertEqual(r.status_code, 201, r.content)
        # ~3 km : 2000 + 500 × 3,05 = 3525 → arrondi à 4000 FC
        self.assertEqual(r.json()["frais_livraison"], 4000)
        devis = self.client.get("/api/livraison/devis/", {"pharmacie": self.pharmacie.id, "lat": -11.690, "lng": 27.470}).json()
        self.assertEqual((devis["frais"], devis["possible"]), (4000, True))

    def test_refus(self):
        self.assertEqual(self.reserver(self.sans_livreur).status_code, 400)  # pas de livreur
        self.assertEqual(self.reserver(self.pharmacie, lat_livraison=-11.0).status_code, 400)  # trop loin
        self.assertEqual(self.reserver(self.pharmacie, adresse_livraison="").status_code, 400)

    def test_cycle_livraison(self):
        from .models import Livreur

        res = Reservation.objects.get(pk=self.reserver(self.pharmacie).json()["id"])
        res.changer_statut("acceptee")
        res.changer_statut("prete")
        self.assertEqual(res.transitions_possibles, (Reservation.Statut.EN_LIVRAISON,))
        autre = Livreur.objects.create(pharmacie=self.sans_livreur, nom="Autre", telephone="0")
        with self.assertRaises(ValueError):
            res.changer_statut("en_livraison", livreur=autre)  # livreur d'une autre pharmacie
        res.changer_statut("en_livraison", livreur=self.livreur)
        res.changer_statut("livree")
        donnees = self.client.get("/api/reservations/", HTTP_AUTHORIZATION=entete_authorization(self.client_id)).json()[0]
        self.assertEqual((donnees["statut"], donnees["livreur"]["nom"]), ("livree", "Moto 1"))


class SuiviLivreurTests(TestCase):
    """Le livreur partage sa position depuis sa page ; le patient le voit avancer."""

    @classmethod
    def setUpTestData(cls):
        cls.med = Medicament.objects.create(dci="Amoxicilline", nom_commercial="Amoxil", dosage="500 mg")
        cls.pharmacie = pharmacie("Pharma livraison")
        Stock.objects.create(pharmacie=cls.pharmacie, medicament=cls.med, prix=5000)

    def setUp(self):
        from .models import Livreur

        self.client_id = uuid.uuid4()
        self.livreur = Livreur.objects.create(pharmacie=self.pharmacie, nom="Jean", telephone="+243990000009")
        self.reservation = Reservation.objects.create(
            client_id=self.client_id, nom="Client", telephone="+243990000001", pharmacie=self.pharmacie,
            medicament=self.med, mode=Reservation.Mode.LIVRAISON, adresse_livraison="Av. Test 12",
            position_livraison=Point(27.479, -11.700, srid=4326), statut=Reservation.Statut.PRETE,
        )

    def partir(self):
        self.reservation.changer_statut(Reservation.Statut.EN_LIVRAISON, livreur=self.livreur)

    def envoyer(self, lat, lng=27.479, jeton=None, **extra):
        return self.client.post(f"/livreur/{jeton or self.livreur.jeton}/position/",
                                {"lat": lat, "lng": lng, **extra}, content_type="application/json")

    def suivi(self):
        return self.client.get(f"/api/reservations/{self.reservation.pk}/suivi/",
                               HTTP_AUTHORIZATION=entete_authorization(str(self.client_id)))

    def test_page_du_livreur(self):
        page = self.client.get(f"/livreur/{self.livreur.jeton}/")
        self.assertContains(page, "Aucune course en cours")
        self.partir()
        page = self.client.get(f"/livreur/{self.livreur.jeton}/")
        self.assertContains(page, "Av. Test 12")
        self.assertContains(page, "Partager ma position")
        self.assertEqual(self.client.get(f"/livreur/{uuid.uuid4()}/").status_code, 404)

    def test_position_sans_course_ignoree(self):
        self.assertEqual(self.envoyer(-11.67).json(), {"courses": 0, "enregistrees": 0})
        self.assertEqual(self.envoyer(-11.67, jeton=uuid.uuid4()).status_code, 404)
        self.partir()
        self.assertEqual(self.envoyer(200).status_code, 400)

    def test_arrivee_selon_vitesse_reelle(self):
        from .models import PositionLivreur

        self.partir()
        self.assertEqual(self.envoyer(-11.664, vitesse=8.0, precision=12).json()["enregistrees"], 1)
        self.assertEqual(self.envoyer(-11.6645).json()["enregistrees"], 0)  # moins de 3 s : ignorée
        d = self.suivi().json()
        self.assertEqual(d["statut"], "en_livraison")
        self.assertEqual(d["livreur"]["nom"], "Jean")
        self.assertFalse(d["vitesse_mesuree"])  # une seule position : vitesse habituelle d'une moto
        self.assertEqual(d["vitesse_kmh"], 22.0)

        # 2 minutes plus tard, le livreur a parcouru ~1,1 km vers le sud : ~33 km/h mesurés.
        premiere = PositionLivreur.objects.get()
        PositionLivreur.objects.filter(pk=premiere.pk).update(recue_le=timezone.now() - timedelta(minutes=2))
        self.envoyer(-11.674)
        d = self.suivi().json()
        self.assertTrue(d["vitesse_mesuree"])
        self.assertAlmostEqual(d["vitesse_kmh"], 33.4, delta=1)
        self.assertEqual(d["position"]["lat"], -11.674)
        self.assertEqual(len(d["trace"]), 2)
        # Reste ~2,9 km × 1,35 (détour estimé) ≈ 3,9 km à 33 km/h ≈ 7 min.
        self.assertAlmostEqual(d["distance_restante_km"], 3.9, delta=0.2)
        self.assertEqual(d["minutes_restantes"], 7)

    def test_livree_efface_le_parcours(self):
        self.partir()
        self.envoyer(-11.68)
        r = self.client.post(f"/livreur/{self.livreur.jeton}/course/{self.reservation.pk}/livree/")
        self.assertEqual(r.status_code, 302)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.statut, Reservation.Statut.LIVREE)
        self.assertEqual(self.reservation.positions.count(), 0)
        d = self.suivi().json()
        self.assertEqual((d["statut"], d["position"], d["trace"]), ("livree", None, []))

    def test_suivi_reserve_au_patient_et_aux_livraisons(self):
        autre = self.client.get(f"/api/reservations/{self.reservation.pk}/suivi/",
                                HTTP_AUTHORIZATION=entete_authorization(str(uuid.uuid4())))
        self.assertEqual(autre.status_code, 400)
        Reservation.objects.filter(pk=self.reservation.pk).update(mode=Reservation.Mode.RETRAIT)
        self.assertEqual(self.suivi().status_code, 400)

    def test_lien_du_livreur_dans_le_portail(self):
        from django.contrib.auth import get_user_model

        from portail.models import Pharmacien

        utilisateur = get_user_model().objects.create_user("pharma-liv", password="mdp-test-123")
        Pharmacien.objects.create(utilisateur=utilisateur, pharmacie=self.pharmacie)
        self.client.login(username="pharma-liv", password="mdp-test-123")
        self.assertContains(self.client.get("/portail/profil/"), f"/livreur/{self.livreur.jeton}/")
        self.partir()
        self.assertContains(self.client.get("/portail/reservations/?onglet=en_cours"), "sa page de course")
