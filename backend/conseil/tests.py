import uuid

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.test import TestCase

from config.jetons import entete_authorization
from pharmacies.models import Pharmacie
from portail.models import Pharmacien

from .models import Question


def pharmacien(nom):
    pharmacie = Pharmacie.objects.create(nom=nom, adresse="x", telephone="0", est_validee=True,
                                         position=Point(27.48, -11.66, srid=4326))
    utilisateur = get_user_model().objects.create_user(nom, password="mdp-test-123")
    Pharmacien.objects.create(utilisateur=utilisateur, pharmacie=pharmacie)
    return pharmacie


class QuestionTests(TestCase):
    def setUp(self):
        self.client_id = str(uuid.uuid4())

    def poser(self, texte="Puis-je prendre du paracétamol avec de l'ibuprofène ?"):
        return self.client.post("/api/questions/", {"texte": texte}, content_type="application/json",
                                HTTP_AUTHORIZATION=entete_authorization(self.client_id))

    def mes_questions(self):
        return self.client.get("/api/questions/", HTTP_AUTHORIZATION=entete_authorization(self.client_id)).json()

    def test_poser_et_recevoir_reponse(self):
        self.assertEqual(self.poser().status_code, 201)
        pharmacie = pharmacien("pharma1")
        self.client.login(username="pharma1", password="mdp-test-123")
        page = self.client.get("/portail/questions/")
        self.assertContains(page, "paracétamol avec")
        question = Question.objects.get()
        self.client.post(f"/portail/questions/{question.pk}/repondre/", {"reponse": "Oui, en respectant les doses."})
        reponse = self.mes_questions()[0]
        self.assertEqual(reponse["statut"], "repondue")
        self.assertEqual(reponse["repondu_par"], pharmacie.nom)

    def test_premier_pharmacien_l_emporte(self):
        self.poser()
        question = Question.objects.get()
        pharmacien("pharma1")
        pharmacien("pharma2")
        self.client.login(username="pharma1", password="mdp-test-123")
        self.client.post(f"/portail/questions/{question.pk}/repondre/", {"reponse": "Première réponse", "orienter": "1"})
        self.client.login(username="pharma2", password="mdp-test-123")
        self.client.post(f"/portail/questions/{question.pk}/repondre/", {"reponse": "Deuxième réponse"})
        question.refresh_from_db()
        self.assertEqual((question.reponse, question.statut), ("Première réponse", "orientee"))

    def test_limites(self):
        self.assertEqual(self.poser("Court").status_code, 400)
        for _ in range(3):
            self.poser()
        self.assertEqual(self.poser().status_code, 400)  # 3 questions en attente maximum
