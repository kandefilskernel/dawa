import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.test import TestCase
from django.utils import timezone

from catalogue.models import Medicament
from pharmacies.models import Pharmacie
from reservations.models import Reservation
from stock.models import AlerteStock, Recherche, Stock

from .models import Pharmacien


def creer_pharmacie(nom, lat=-11.664, lng=27.479):
    return Pharmacie.objects.create(
        nom=nom, adresse="x", telephone="0", est_validee=True, position=Point(lng, lat, srid=4326)
    )


class PortailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ma_pharmacie = creer_pharmacie("Ma pharmacie")
        cls.autre = creer_pharmacie("Concurrente")
        cls.med = Medicament.objects.create(dci="Amoxicilline", nom_commercial="Amoxicilline", dosage="500 mg")
        cls.coartem = Medicament.objects.create(dci="Artéméther", nom_commercial="Coartem")
        Stock.objects.create(pharmacie=cls.ma_pharmacie, medicament=cls.med, prix=5000)
        Stock.objects.create(pharmacie=cls.autre, medicament=cls.med, prix=4000)

        utilisateur = get_user_model().objects.create_user("pharma", password="mdp-test-123")
        Pharmacien.objects.create(utilisateur=utilisateur, pharmacie=cls.ma_pharmacie)
        get_user_model().objects.create_user("sans-pharmacie", password="mdp-test-123")

    def setUp(self):
        self.client.login(username="pharma", password="mdp-test-123")

    def reserver(self, pharmacie):
        return Reservation.objects.create(
            client_id=uuid.uuid4(), nom="Client", telephone="+243990000001",
            pharmacie=pharmacie, medicament=self.med,
        )

    def test_connexion_obligatoire_et_compte_rattache(self):
        self.client.logout()
        r = self.client.get("/portail/")
        self.assertRedirects(r, "/portail/connexion/?next=/portail/")
        self.client.login(username="sans-pharmacie", password="mdp-test-123")
        self.assertEqual(self.client.get("/portail/").status_code, 403)

    def test_tableau_de_bord_et_demande_locale(self):
        self.reserver(self.ma_pharmacie)
        Recherche.objects.create(terme="coartem", medicament=self.coartem, zone=Point(27.48, -11.66, srid=4326))
        Recherche.objects.create(terme="amox", medicament=self.med, zone=Point(27.48, -11.66, srid=4326))
        r = self.client.get("/portail/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["nb_en_attente"], 1)
        demandes = [d["medicament__nom_commercial"] for d in r.context["demande"]]
        # L'amoxicilline est déjà en stock : seul le Coartem est signalé.
        self.assertEqual(demandes, ["Coartem"])

    def test_cycle_de_vie_reservation(self):
        res = self.reserver(self.ma_pharmacie)
        url = f"/portail/reservations/{res.pk}/statut/"
        self.client.post(url, {"statut": "acceptee"})
        self.client.post(url, {"statut": "prete"})
        res.refresh_from_db()
        self.assertEqual(res.statut, "prete")
        self.assertGreater(res.expire_le, timezone.now() + timedelta(minutes=110))
        # Transition interdite : prête -> acceptée.
        self.client.post(url, {"statut": "acceptee"})
        res.refresh_from_db()
        self.assertEqual(res.statut, "prete")

    def test_refus_avec_message(self):
        res = self.reserver(self.ma_pharmacie)
        self.client.post(f"/portail/reservations/{res.pk}/statut/", {"statut": "refusee", "message": "Plus en stock"})
        res.refresh_from_db()
        self.assertEqual((res.statut, res.message_pharmacie), ("refusee", "Plus en stock"))

    def test_isolation_entre_pharmacies(self):
        res = self.reserver(self.autre)
        r = self.client.post(f"/portail/reservations/{res.pk}/statut/", {"statut": "acceptee"})
        self.assertEqual(r.status_code, 404)
        r = self.client.get("/portail/reservations/")
        self.assertNotContains(r, "Concurrente")

    def test_modifier_stock_en_direct(self):
        r = self.client.post(
            f"/portail/stock/{self.coartem.pk}/", {"disponible": ["0", "1"], "prix": "12 000"},
            HTTP_X_REQUESTED_WITH="fetch",
        )
        self.assertEqual(r.json(), {"ok": True, "disponible": True, "prix": 12000})
        stock = Stock.objects.get(pharmacie=self.ma_pharmacie, medicament=self.coartem)
        self.assertEqual((stock.disponible, stock.prix, stock.source), (True, 12000, "portail"))
        # Seule la pharmacie connectée est modifiée.
        self.assertFalse(Stock.objects.filter(pharmacie=self.autre, medicament=self.coartem).exists())

    def test_prix_invalide(self):
        r = self.client.post(f"/portail/stock/{self.med.pk}/", {"disponible": "1", "prix": "abc"},
                             HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Stock.objects.get(pharmacie=self.ma_pharmacie, medicament=self.med).prix, 5000)

    def test_mise_en_stock_declenche_alertes(self):
        alerte = AlerteStock.objects.create(
            client_id=uuid.uuid4(), medicament=self.coartem, position=Point(27.479, -11.664, srid=4326)
        )
        self.client.post(f"/portail/stock/{self.coartem.pk}/", {"disponible": "1"}, HTTP_X_REQUESTED_WITH="fetch")
        alerte.refresh_from_db()
        self.assertEqual(alerte.pharmacie, self.ma_pharmacie)

    def test_tout_confirmer(self):
        Stock.objects.filter(pharmacie=self.ma_pharmacie).update(mis_a_jour_le=timezone.now() - timedelta(days=5))
        self.client.post("/portail/stock/confirmer/")
        stock = Stock.objects.get(pharmacie=self.ma_pharmacie, medicament=self.med)
        self.assertTrue(stock.est_confirme)

    def test_redirection_externe_refusee(self):
        r = self.client.post("/portail/stock/confirmer/", {"retour": "https://exemple-malveillant.com/"})
        self.assertRedirects(r, "/portail/stock/", fetch_redirect_response=False)

    def test_pages_s_affichent(self):
        for url in ["/portail/", "/portail/reservations/?onglet=en_cours", "/portail/reservations/?onglet=historique",
                    "/portail/stock/?filtre=absent", "/portail/stock/?q=amox", "/portail/profil/"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_profil(self):
        self.client.post("/portail/profil/", {
            "telephone": "+243990001122", "whatsapp": "", "horaires": "Lun–Dim 7h–22h",
            "adresse": "Av. X", "quartier": "Centre",
        })
        self.ma_pharmacie.refresh_from_db()
        self.assertEqual(self.ma_pharmacie.horaires, "Lun–Dim 7h–22h")


class PhotoPortailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pharmacie = creer_pharmacie("Ma pharmacie")
        utilisateur = get_user_model().objects.create_user("pharma", password="mdp-test-123")
        Pharmacien.objects.create(utilisateur=utilisateur, pharmacie=cls.pharmacie)

    def setUp(self):
        self.client.login(username="pharma", password="mdp-test-123")
        self.med = Medicament.objects.create(dci="Paracétamol", nom_commercial="Doliprane", dosage="500 mg")

    def photo(self, nom="boite.jpg"):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from io import BytesIO
        from PIL import Image

        tampon = BytesIO()
        Image.new("RGB", (1600, 1200), (200, 30, 30)).save(tampon, "JPEG")
        return SimpleUploadedFile(nom, tampon.getvalue(), content_type="image/jpeg")

    def test_illustration_creee_automatiquement(self):
        self.assertTrue(self.med.image)
        self.assertTrue(self.med.image_est_illustration)
        ancien = self.med.image.name
        self.med.dosage = "1 g"
        self.med.save()
        self.med.refresh_from_db()
        self.assertNotEqual(self.med.image.name, ancien)  # redessinée avec le nouveau dosage

    def test_envoi_photo_remplace_illustration_une_seule_fois(self):
        r = self.client.post(f"/portail/stock/{self.med.pk}/photo/", {"photo": self.photo()})
        self.assertRedirects(r, "/portail/stock/", fetch_redirect_response=False)
        self.med.refresh_from_db()
        self.assertFalse(self.med.image_est_illustration)
        self.assertEqual(self.med.image_envoyee_par, self.pharmacie)
        self.assertTrue(self.med.image.name.endswith(".webp"))
        nom = self.med.image.name

        # Une deuxième photo n'écrase pas la première.
        self.client.post(f"/portail/stock/{self.med.pk}/photo/", {"photo": self.photo()})
        self.med.refresh_from_db()
        self.assertEqual(self.med.image.name, nom)

    def test_fichier_non_image_refuse(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        faux = SimpleUploadedFile("virus.jpg", b"pas une image", content_type="image/jpeg")
        self.client.post(f"/portail/stock/{self.med.pk}/photo/", {"photo": faux})
        self.med.refresh_from_db()
        self.assertTrue(self.med.image_est_illustration)
