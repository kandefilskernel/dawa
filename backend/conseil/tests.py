import json
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


def bloc_outil(medicament, identifiant="outil_1"):
    return SimpleNamespace(type="tool_use", id=identifiant, name="chercher_medicament", input={"medicament": medicament})


class AssistantChoixTests(TestCase):
    """« J'ai besoin d'Amoxicilline, je suis à pied » → la pharmacie la plus rapide, avec les vraies données."""

    @classmethod
    def setUpTestData(cls):
        from reservations.models import Livreur
        from stock.models import Stock

        cls.amox = Medicament.objects.create(dci="Amoxicilline", nom_commercial="Amoxicilline", dosage="500 mg",
                                             ordonnance_requise=True)

        def pharmacie(nom, lng):
            p = Pharmacie.objects.create(nom=nom, adresse="x", telephone="0", est_validee=True,
                                         horaires="24h/24", position=Point(lng, -11.664, srid=4326))
            Stock.objects.create(pharmacie=p, medicament=cls.amox, prix=5000)
            return p

        cls.proche = pharmacie("Proche", 27.489)        # ~1,1 km
        cls.livre = pharmacie("Avec livreur", 27.505)   # ~2,8 km, livre à moto
        Livreur.objects.create(pharmacie=cls.livre, nom="Jean", telephone="+243990000009")

    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.client_id = str(uuid.uuid4())

    def demander(self, message, **extra):
        return self.client.post("/api/assistant/", {"message": message, "lat": -11.664, "lng": 27.479, **extra},
                                content_type="application/json",
                                HTTP_AUTHORIZATION=entete_authorization(self.client_id))

    @override_settings(ASSISTANT_IA_CLE="")
    def test_regles_sans_ia(self):
        self.assertFalse(self.client.get("/api/assistant/").json()["ia_active"])
        d = self.demander("J'ai besoin d'amoxiciline, je suis à moto").json()
        self.assertEqual((d["source"], d["situation"], d["mode"], d["action"]), ("regles", "trouve", "moto", "reserver"))
        self.assertEqual(d["recommandation"]["pharmacie"]["nom"], "Proche")
        self.assertEqual(d["medicament"]["nom_commercial"], "Amoxicilline")
        self.assertEqual(len(d["autres"]), 1)

    @override_settings(ASSISTANT_IA_CLE="")
    def test_regles_livraison_plus_rapide_qu_a_pied(self):
        from pharmacies.models import Pharmacie as P

        P.objects.filter(pk=self.proche.pk).update(position=Point(27.530, -11.664, srid=4326))  # 5,5 km à pied
        d = self.demander("Amoxicilline svp, je suis à pied, c'est urgent").json()
        self.assertEqual((d["mode"], d["action"]), ("pied", "se_faire_livrer"))
        self.assertEqual(d["recommandation"]["pharmacie"]["nom"], "Avec livreur")
        self.assertTrue(d["recommandation"]["livraison"]["possible"])
        self.assertLess(d["recommandation"]["livraison"]["minutes"], d["recommandation"]["acces"]["delai_min"]["pied"])

    @override_settings(ASSISTANT_IA_CLE="")
    def test_regles_inconnu_et_introuvable(self):
        self.assertEqual(self.demander("Bonjour, ça va ?").json()["situation"], "medicament_inconnu")
        Medicament.objects.create(dci="Artéméther", nom_commercial="Coartem", dosage="20/120 mg")
        d = self.demander("Il me faut du Coartem").json()
        self.assertEqual((d["situation"], d["recommandation"]), ("introuvable", None))

    def ia(self, *reponses):
        api = mock.Mock()
        api.beta.messages.create.side_effect = list(reponses)
        return mock.patch("conseil.choix._client", return_value=api), api.beta.messages.create

    @override_settings(ASSISTANT_IA_CLE="cle-test")
    def test_ia_utilise_les_vraies_donnees(self):
        final = json.dumps({"reponse": "Allez à la pharmacie Proche : 3 min à moto, 5 000 FC.",
                            "pharmacie_id": self.proche.pk, "action": "reserver", "mode": "moto",
                            "orienter_medecin": False})
        patch, appel = self.ia(SimpleNamespace(stop_reason="tool_use", content=[bloc_outil("Amoxicilline")]),
                               reponse_ia(final))
        with patch:
            d = self.demander("J'ai besoin d'Amoxicilline vite").json()
        self.assertEqual((d["source"], d["action"]), ("ia", "reserver"))
        self.assertIn("Proche", d["reponse"])
        self.assertEqual(d["recommandation"]["pharmacie"]["id"], self.proche.pk)
        # Le 2e appel contient le résultat de l'outil : stocks et délais réels de la base.
        envoye = appel.call_args_list[1].kwargs
        resultat = envoye["messages"][-1]["content"][0]
        self.assertEqual(resultat["tool_use_id"], "outil_1")
        donnees = json.loads(resultat["content"])
        self.assertEqual({p["pharmacie"] for p in donnees["pharmacies"]}, {"Proche", "Avec livreur"})
        self.assertTrue(donnees["medicament"]["ordonnance_requise"])
        self.assertNotIn(self.client_id, json.dumps(envoye["messages"], default=str))
        self.assertNotIn("27.479", json.dumps(envoye["messages"], default=str))  # pas la position du patient
        self.assertEqual(envoye["fallbacks"], "default")

    @override_settings(ASSISTANT_IA_CLE="cle-test")
    def test_ia_pharmacie_inventee_ignoree(self):
        final = json.dumps({"reponse": "Pharmacie Imaginaire.", "pharmacie_id": 99999, "action": "reserver",
                            "mode": "moto", "orienter_medecin": True})
        patch, _ = self.ia(SimpleNamespace(stop_reason="tool_use", content=[bloc_outil("amox")]), reponse_ia(final))
        with patch:
            d = self.demander("Amoxicilline, j'ai du mal à respirer").json()
        self.assertEqual((d["recommandation"], d["action"], d["orienter_medecin"]), (None, "aucune", True))

    @override_settings(ASSISTANT_IA_CLE="cle-test")
    def test_ia_en_panne_regles_en_secours(self):
        patch, _ = self.ia(anthropic.APIConnectionError(request=mock.Mock()))
        with patch:
            d = self.demander("amoxicilline").json()
        self.assertEqual((d["source"], d["recommandation"]["pharmacie"]["nom"]), ("regles", "Proche"))
        patch, _ = self.ia(reponse_ia("", stop_reason="refusal"))
        with patch:
            self.assertEqual(self.demander("amoxicilline").json()["source"], "regles")

    @override_settings(ASSISTANT_IA_CLE="")
    def test_validation_et_limite(self):
        self.assertEqual(self.demander("").status_code, 400)
        self.assertEqual(self.client.post("/api/assistant/", {"message": "amoxicilline"},
                                          content_type="application/json",
                                          HTTP_AUTHORIZATION=entete_authorization(self.client_id)).status_code, 400)
        for _ in range(20):
            self.demander("amoxicilline")
        self.assertEqual(self.demander("amoxicilline").status_code, 429)

    def test_pire_cas_sous_le_delai_du_serveur(self):
        from conseil import choix

        self.assertLess(choix.DELAI_SECONDES * choix.TOURS_MAX, 60)
