import uuid
from datetime import timedelta
from io import BytesIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

from abonnements.models import Abonnement
from catalogue.models import Medicament
from conseil.assistant import AssistantIndisponible
from conseil.models import Question
from grossistes.models import Commande, Grossiste, Offre
from kyc.models import Piece
from pharmacies.models import Garde, Pharmacie
from portail.models import Pharmacien
from reservations.models import Livreur, Reservation
from stock.models import Recherche, Stock

from .tests import MDP, ApiWebTestCase, creer_pharmacien

API = "/api/web/pharmacie/"


def image_jpeg(nom="boite.jpg"):
    tampon = BytesIO()
    Image.new("RGB", (800, 600), (200, 30, 30)).save(tampon, "JPEG")
    return SimpleUploadedFile(nom, tampon.getvalue(), content_type="image/jpeg")


class PharmacieTestCase(ApiWebTestCase):
    def setUp(self):
        super().setUp()
        self.pharmacien = creer_pharmacien("pharma")
        self.pharmacie = self.pharmacien.pharmacie
        self.autre = creer_pharmacien("autre").pharmacie
        self.med = Medicament.objects.create(dci="Amoxicilline", nom_commercial="Amoxicilline", dosage="500 mg")
        self.coartem = Medicament.objects.create(dci="Artéméther", nom_commercial="Coartem")
        Stock.objects.create(pharmacie=self.pharmacie, medicament=self.med, prix=5000)
        self.connecter("pharma")

    def reserver(self, pharmacie=None, **kwargs):
        return Reservation.objects.create(client_id=uuid.uuid4(), nom="Client", telephone="+243990000001",
                                          pharmacie=pharmacie or self.pharmacie, medicament=self.med, **kwargs)

    def get(self, chemin, **params):
        reponse = self.api.get(f"{API}{chemin}", params)
        self.assertEqual(reponse.status_code, 200, reponse.content)
        return reponse.json()


class AccesTests(PharmacieTestCase):
    def test_sans_connexion(self):
        self.poster("/api/web/compte/deconnexion/")
        self.assertEqual(self.api.get(f"{API}tableau/").status_code, 403)

    def test_autres_roles_refuses(self):
        self.poster("/api/web/compte/deconnexion/")
        get_user_model().objects.create_user("equipe", password=MDP, is_staff=True)
        self.connecter("equipe")
        self.assertEqual(self.api.get(f"{API}tableau/").status_code, 403)

    def test_compte_en_attente_seul_le_dossier(self):
        creer_pharmacien("nouveau", statut=Pharmacien.Statut.EN_ATTENTE)
        self.poster("/api/web/compte/deconnexion/")
        self.connecter("nouveau")
        self.assertEqual(self.api.get(f"{API}tableau/").status_code, 403)
        dossier = self.get("dossier/")
        self.assertEqual(dossier["statut"], "en_attente")
        self.assertEqual(len(dossier["dossier"]["manquantes"]), 4)

    def test_ecriture_sans_csrf_refusee(self):
        reponse = self.api.post(f"{API}stock/confirmer/")
        self.assertEqual(reponse.status_code, 403)


class TableauReservationsTests(PharmacieTestCase):
    def test_resume_et_tableau(self):
        self.reserver()
        Question.objects.create(client_id=uuid.uuid4(), texte="Puis-je prendre ceci ?")
        Recherche.objects.create(terme="coartem", medicament=self.coartem, zone=Point(27.47, -11.66, srid=4326))
        resume = self.get("resume/")
        self.assertEqual((resume["nb_a_traiter"], resume["nb_questions"], resume["dossier_incomplet"]), (1, 1, True))
        tableau = self.get("tableau/")
        self.assertEqual(tableau["nb_en_attente"], 1)
        self.assertEqual(tableau["nb_disponibles"], 1)
        self.assertEqual([d["nom"] for d in tableau["demande"]], ["Coartem"])
        self.assertEqual(tableau["dernieres"][0]["transitions"], ["acceptee", "refusee"])

    def test_onglets_et_isolation(self):
        self.reserver()
        self.reserver(pharmacie=self.autre)
        self.reserver(statut=Reservation.Statut.RETIREE)
        self.assertEqual(len(self.get("reservations/")["reservations"]), 1)
        self.assertEqual(len(self.get("reservations/", onglet="historique")["reservations"]), 1)
        autre = Reservation.objects.get(pharmacie=self.autre)
        self.assertEqual(self.poster(f"{API}reservations/{autre.pk}/statut/", {"statut": "acceptee"}).status_code, 404)

    def test_cycle_livraison_avec_livreur(self):
        livreur = Livreur.objects.create(pharmacie=self.pharmacie, nom="Jean", telephone="+243990000002")
        res = self.reserver(mode=Reservation.Mode.LIVRAISON, adresse_livraison="Av. Kasaï 12")
        url = f"{API}reservations/{res.pk}/statut/"
        self.assertEqual(self.poster(url, {"statut": "acceptee"}).json()["statut"], "acceptee")
        self.assertEqual(self.poster(url, {"statut": "prete"}).json()["transitions"], ["en_livraison"])
        sans_livreur = self.poster(url, {"statut": "en_livraison"})
        self.assertEqual(sans_livreur.status_code, 400)
        self.assertEqual(sans_livreur.json()["message"], "Choisissez le livreur qui part avec la commande.")
        partie = self.poster(url, {"statut": "en_livraison", "livreur": livreur.pk}).json()
        self.assertEqual(partie["livreur"]["nom"], "Jean")
        self.assertIn(f"/livreur/{livreur.jeton}/", partie["livreur"]["lien"])
        self.assertEqual(self.poster(url, {"statut": "livree"}).json()["statut"], "livree")

    def test_refus_avec_motif_et_transition_interdite(self):
        res = self.reserver()
        url = f"{API}reservations/{res.pk}/statut/"
        self.assertEqual(self.poster(url, {"statut": "prete"}).status_code, 400)
        self.poster(url, {"statut": "refusee", "message": "Plus en stock"})
        res.refresh_from_db()
        self.assertEqual((res.statut, res.message_pharmacie), ("refusee", "Plus en stock"))


class StockTests(PharmacieTestCase):
    def test_liste_filtres(self):
        lignes = self.get("stock/")["lignes"]
        self.assertEqual([l["medicament"]["nom_commercial"] for l in lignes], ["Amoxicilline", "Coartem"])
        self.assertEqual(lignes[0]["stock"]["prix"], 5000)
        self.assertIsNone(lignes[1]["stock"])
        self.assertEqual(len(self.get("stock/", filtre="absent")["lignes"]), 1)
        self.assertEqual(self.get("stock/", q="coar")["lignes"][0]["medicament"]["nom_commercial"], "Coartem")

    def test_modifier_et_prix_invalide(self):
        reponse = self.poster(f"{API}stock/{self.coartem.pk}/", {"disponible": True, "prix": "12 000"})
        self.assertEqual((reponse.json()["disponible"], reponse.json()["prix"]), (True, 12000))
        self.assertEqual(Stock.objects.get(pharmacie=self.pharmacie, medicament=self.coartem).source, "portail")
        self.assertFalse(Stock.objects.filter(pharmacie=self.autre, medicament=self.coartem).exists())
        reponse = self.poster(f"{API}stock/{self.med.pk}/", {"disponible": True, "prix": "abc"})
        self.assertEqual(reponse.status_code, 400)
        self.assertEqual(reponse.json()["message"], "Prix invalide (nombre entier en FC).")

    def test_confirmer(self):
        Stock.objects.update(mis_a_jour_le=timezone.now() - timedelta(days=5))
        self.assertEqual(self.get("stock/")["nb_a_confirmer"], 1)
        self.assertEqual(self.poster(f"{API}stock/confirmer/").json()["nb"], 1)
        self.assertEqual(self.get("stock/")["nb_a_confirmer"], 0)

    def test_photo(self):
        reponse = self.api.post(f"{API}stock/{self.coartem.pk}/photo/", {"photo": image_jpeg()},
                                format="multipart", HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(reponse.status_code, 200, reponse.content)
        self.assertFalse(reponse.json()["medicament"]["photo_possible"])
        reponse = self.api.post(f"{API}stock/{self.coartem.pk}/photo/", {"photo": image_jpeg()},
                                format="multipart", HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(reponse.status_code, 400)


class ProfilTests(PharmacieTestCase):
    def test_profil_gardes_et_modification(self):
        Garde.objects.create(pharmacie=self.pharmacie, debut=timezone.now() - timedelta(hours=1),
                             fin=timezone.now() + timedelta(hours=10))
        profil = self.get("profil/")
        self.assertTrue(profil["gardes"][0]["en_cours"])
        reponse = self.poster(f"{API}profil/", {"horaires": "Lun–Dim 7h–22h"})
        self.assertEqual(reponse.json()["fiche"]["horaires"], "Lun–Dim 7h–22h")
        self.pharmacie.refresh_from_db()
        self.assertEqual((self.pharmacie.horaires, self.pharmacie.telephone), ("Lun–Dim 7h–22h", "0"))
        self.assertEqual(self.poster(f"{API}profil/", {"telephone": ""}).status_code, 400)

    def test_livreurs(self):
        self.assertEqual(self.poster(f"{API}livreurs/", {"nom": "J", "telephone": "1"}).status_code, 400)
        livreur = self.poster(f"{API}livreurs/", {"nom": "Jean", "telephone": "+243 990 000 002"}).json()
        self.assertEqual(len(self.get("profil/")["livreurs"]), 1)
        self.poster(f"{API}livreurs/{livreur['id']}/retirer/")
        self.assertEqual(self.get("profil/")["livreurs"], [])

    def test_sms_simule(self):
        reponse = self.poster(f"{API}sms/", {"texte": "RUPTURE amoxicilline"}).json()
        self.assertTrue(reponse["reponse"])
        self.assertFalse(Stock.objects.get(pharmacie=self.pharmacie, medicament=self.med).disponible)


class QuestionsTests(PharmacieTestCase):
    def setUp(self):
        super().setUp()
        self.question = Question.objects.create(client_id=uuid.uuid4(), texte="Puis-je le prendre enceinte ?",
                                                medicament=self.med)

    def test_liste_et_reponse(self):
        self.assertEqual(self.get("questions/")["en_attente"][0]["medicament"]["nom_commercial"], "Amoxicilline")
        self.assertEqual(self.poster(f"{API}questions/{self.question.pk}/repondre/", {"reponse": "non"}).status_code,
                         400)
        reponse = self.poster(f"{API}questions/{self.question.pk}/repondre/",
                              {"reponse": "Demandez l'avis d'un médecin.", "orienter": True})
        self.assertEqual(reponse.status_code, 200)
        self.question.refresh_from_db()
        self.assertEqual((self.question.statut, self.question.repondu_par), ("orientee", self.pharmacie))
        self.assertEqual(self.get("questions/")["mes_reponses"][0]["statut"], "orientee")
        # Déjà répondue : un confrère arrive trop tard.
        deja = self.poster(f"{API}questions/{self.question.pk}/repondre/", {"reponse": "Autre réponse"})
        self.assertEqual(deja.status_code, 409)

    def test_suggestion_ia(self):
        suggestion = mock.Mock(reponse="Brouillon", orienter_medecin=True)
        with mock.patch("pro_api.pharmacie.suggerer_reponse", return_value=suggestion):
            reponse = self.poster(f"{API}questions/{self.question.pk}/suggestion/")
        self.assertEqual(reponse.json(), {"reponse": "Brouillon", "orienter": True})
        with mock.patch("pro_api.pharmacie.suggerer_reponse", side_effect=AssistantIndisponible("Indisponible")):
            reponse = self.poster(f"{API}questions/{self.question.pk}/suggestion/")
        self.assertEqual((reponse.status_code, reponse.json()["message"]), (503, "Indisponible"))


class AbonnementTests(PharmacieTestCase):
    def test_demande_puis_doublon(self):
        donnees = self.get("abonnement/")
        self.assertIsNone(donnees["actif"])
        self.assertEqual([f["code"] for f in donnees["formules"]], list(Abonnement.Formule.values))
        reponse = self.poster(f"{API}abonnement/", {"formule": "visibilite", "mois": 3})
        self.assertEqual(reponse.status_code, 201)
        self.assertEqual(reponse.json()["abonnement"]["montant"], Abonnement.prix("visibilite", 3))
        self.assertEqual(self.get("abonnement/")["en_attente"]["reference"], reponse.json()["abonnement"]["reference"])
        self.assertEqual(self.poster(f"{API}abonnement/", {"formule": "essentiel", "mois": 1}).status_code, 400)
        self.assertEqual(self.poster(f"{API}abonnement/", {"formule": "x", "mois": 2}).status_code, 400)


class CommandesTests(PharmacieTestCase):
    def setUp(self):
        super().setUp()
        self.grossiste = Grossiste.objects.create(nom="Grossiste Katanga", telephone="+243990000009",
                                                  minimum_commande=10_000)
        self.offre = Offre.objects.create(grossiste=self.grossiste, medicament=self.coartem, prix=4000)
        Stock.objects.create(pharmacie=self.pharmacie, medicament=self.coartem, disponible=False)

    def test_catalogue_commande_et_suivi(self):
        self.assertEqual(self.get("commandes/")["grossistes"][0]["nom"], "Grossiste Katanga")
        catalogue = self.get(f"grossistes/{self.grossiste.pk}/")
        self.assertTrue(catalogue["offres"][0]["en_rupture_chez_moi"])

        trop_peu = self.poster(f"{API}grossistes/{self.grossiste.pk}/", {"quantites": {self.offre.pk: 1}})
        self.assertEqual(trop_peu.status_code, 400)
        commande = self.poster(f"{API}grossistes/{self.grossiste.pk}/",
                               {"quantites": {str(self.offre.pk): 3}, "note": "Avant midi"}).json()
        self.assertEqual((commande["total"], commande["actions"]), (12_000, ["recue", "annuler"]))
        self.assertTrue(commande["whatsapp"].startswith("https://wa.me/243990000009?text="))

        detail = self.get(f"commandes/{commande['id']}/")
        self.assertEqual(detail["lignes"][0]["quantite"], 3)
        recue = self.poster(f"{API}commandes/{commande['id']}/", {"action": "recue"}).json()
        self.assertEqual((recue["statut"], recue["actions"]), ("livree", []))
        self.assertEqual(self.poster(f"{API}commandes/{commande['id']}/", {"action": "annuler"}).status_code, 400)

    def test_commande_d_une_autre_pharmacie(self):
        commande = Commande.objects.create(pharmacie=self.autre, grossiste=self.grossiste)
        self.assertEqual(self.api.get(f"{API}commandes/{commande.pk}/").status_code, 404)


class DossierInscriptionTests(ApiWebTestCase):
    def inscrire(self, **champs):
        donnees = {"nom": "Pharmacie Neuve", "numero_agrement": "IPS/123", "telephone": "+243990000010",
                   "adresse": "Av. Mama Yemo", "email": "neuve@example.com", "username": "neuve",
                   "password1": "Mot-de-passe-2026", "password2": "Mot-de-passe-2026", **champs}
        return self.poster("/api/web/compte/inscription/pharmacie/", donnees)

    def test_inscription_puis_envoi_des_pieces(self):
        reponse = self.inscrire(latitude=-11.67, longitude=27.48)
        self.assertEqual(reponse.status_code, 201, reponse.content)
        self.assertEqual((reponse.json()["role"], reponse.json()["statut"]), ("pharmacien", "en_attente"))
        pharmacie = Pharmacie.objects.get(nom="Pharmacie Neuve")
        self.assertFalse(pharmacie.est_validee)
        self.assertAlmostEqual(pharmacie.position.y, -11.67)

        envoi = self.api.post(f"{API}dossier/", {"type": Piece.Type.FACADE, "fichier": image_jpeg("facade.jpg")},
                              format="multipart", HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(envoi.status_code, 201, envoi.content)
        self.assertNotIn(Piece.Type.FACADE, envoi.json()["dossier"]["manquantes"])
        mauvais = self.api.post(f"{API}dossier/", {"type": Piece.Type.ORDRE,
                                                   "fichier": SimpleUploadedFile("x.pdf", b"pas un pdf")},
                                format="multipart", HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(mauvais.status_code, 400)

    def test_erreurs_par_champ_et_robot(self):
        reponse = self.inscrire(password2="different", email="pas-un-email")
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("email", reponse.json()["erreurs"])
        self.assertIn("password2", reponse.json()["erreurs"])
        self.assertEqual(self.inscrire(site_web="http://spam").status_code, 400)
        self.assertFalse(Pharmacie.objects.exists())
