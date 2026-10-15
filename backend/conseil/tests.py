import uuid
from types import SimpleNamespace
from unittest import mock

import anthropic
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.test import TestCase, override_settings

from catalogue.models import Medicament
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


def reponse_ia(texte, stop_reason="end_turn"):
    return SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=texte)])


class AssistantIATests(TestCase):
    def setUp(self):
        self.client_id = uuid.uuid4()
        self.medicament = Medicament.objects.create(dci="Amoxicilline", nom_commercial="Amoxil", dosage="500 mg",
                                                    ordonnance_requise=True)
        self.question = Question.objects.create(client_id=self.client_id, medicament=self.medicament,
                                                texte="Je peux le prendre pendant le repas ?")
        pharmacien("pharma1")
        self.client.login(username="pharma1", password="mdp-test-123")
        self.url = f"/portail/questions/{self.question.pk}/suggestion/"

    def suggerer(self, resultat=None, erreur=None):
        api = mock.Mock()
        api.beta.messages.create.return_value = resultat
        api.beta.messages.create.side_effect = erreur
        with mock.patch("conseil.assistant._client", return_value=api):
            return self.client.post(self.url), api.beta.messages.create

    @override_settings(ASSISTANT_IA_CLE="")
    def test_desactive_sans_cle(self):
        self.assertNotContains(self.client.get("/portail/questions/"), "Suggérer une réponse")
        self.assertEqual(self.client.post(self.url).status_code, 503)

    @override_settings(ASSISTANT_IA_CLE="cle-test")
    def test_brouillon(self):
        self.assertContains(self.client.get("/portail/questions/"), "Suggérer une réponse")
        page, appel = self.suggerer(reponse_ia('{"reponse": "Oui, pendant le repas.", "orienter_medecin": false}'))
        self.assertEqual(page.json(), {"reponse": "Oui, pendant le repas.", "orienter": False})
        envoye = appel.call_args.kwargs
        message = envoye["messages"][0]["content"]
        self.assertIn("pendant le repas", message)
        self.assertIn("Amoxil 500 mg", message)
        self.assertIn("sur ordonnance", message)
        self.assertNotIn(str(self.client_id), message)  # aucun identifiant patient envoyé
        self.assertEqual(envoye["fallbacks"], "default")
        # Rien n'est envoyé au patient : la question reste en attente.
        self.question.refresh_from_db()
        self.assertEqual(self.question.statut, Question.Statut.EN_ATTENTE)

    @override_settings(ASSISTANT_IA_CLE="cle-test")
    def test_orientation_medecin(self):
        page, _ = self.suggerer(reponse_ia('{"reponse": "Consultez un médecin.", "orienter_medecin": true}'))
        self.assertTrue(page.json()["orienter"])

    @override_settings(ASSISTANT_IA_CLE="cle-test")
    def test_refus_et_erreurs(self):
        page, _ = self.suggerer(reponse_ia("", stop_reason="refusal"))
        self.assertEqual(page.status_code, 503)
        page, _ = self.suggerer(erreur=anthropic.APIConnectionError(request=mock.Mock()))
        self.assertEqual(page.status_code, 503)
        self.assertIn("injoignable", page.json()["erreur"])
        page, _ = self.suggerer(reponse_ia("pas du json"))
        self.assertEqual(page.status_code, 503)

    @override_settings(ASSISTANT_IA_CLE="cle-test")
    def test_question_deja_repondue(self):
        Question.objects.filter(pk=self.question.pk).update(statut=Question.Statut.REPONDUE)
        page, appel = self.suggerer(reponse_ia("{}"))
        self.assertEqual(page.status_code, 404)
        appel.assert_not_called()

    @override_settings(ASSISTANT_IA_CLE="cle-test")
    def test_reserve_aux_pharmaciens(self):
        self.client.logout()
        self.assertEqual(self.client.post(self.url).status_code, 302)  # vers la connexion


class DelaiAssistantTests(TestCase):
    def test_pire_cas_sous_le_delai_du_serveur(self):
        from conseil import assistant

        pire_cas = assistant.DELAI_SECONDES * (assistant.NOUVELLES_TENTATIVES + 1)
        self.assertLess(pire_cas, 60)  # --timeout de gunicorn dans deploy/demarrer.sh
