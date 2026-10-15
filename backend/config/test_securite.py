import logging
import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings

from gestion.tests import INSCRIPTION
from portail.models import Pharmacien

MDP = INSCRIPTION["password1"]


class LimiteConnexionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client.post("/portail/inscription/", INSCRIPTION)
        self.client.logout()

    def connexion(self, identifiant="marche", mot_de_passe=MDP, url="/portail/connexion/"):
        return self.client.post(url, {"username": identifiant, "password": mot_de_passe})

    def test_blocage_apres_cinq_echecs_meme_avec_le_bon_mot_de_passe(self):
        for _ in range(5):
            self.assertContains(self.connexion(mot_de_passe="faux"), "incorrect")
        reponse = self.connexion()
        self.assertContains(reponse, "Trop de tentatives")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_reussite_remet_le_compteur_a_zero(self):
        for _ in range(4):
            self.connexion(mot_de_passe="faux")
        self.assertEqual(self.connexion().status_code, 302)
        self.client.logout()
        for _ in range(4):
            self.connexion(mot_de_passe="faux")
        self.assertEqual(self.connexion().status_code, 302)

    def test_l_admin_est_aussi_protege(self):
        for _ in range(5):
            self.connexion(mot_de_passe="faux", url="/admin/login/")
        self.connexion(url="/admin/login/")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_limite_par_adresse_sur_plusieurs_comptes(self):
        for i in range(30):
            self.connexion(identifiant=f"inconnu{i}", mot_de_passe="faux")
        self.assertContains(self.connexion(), "Trop de tentatives")

    def test_limite_des_inscriptions(self):
        for i in range(4):  # la 1re a été faite dans setUp
            self.client.post("/portail/inscription/", {**INSCRIPTION, "username": f"p{i}",
                                                        "numero_agrement": f"AG-{i}", "email": f"p{i}@exemple.cd"})
            self.client.logout()
        reponse = self.client.post("/portail/inscription/", {**INSCRIPTION, "username": "p9", "numero_agrement": "AG-9"})
        self.assertContains(reponse, "Trop d")
        self.assertEqual(Pharmacien.objects.count(), 5)


class MotDePasseOublieTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client.post("/portail/inscription/", INSCRIPTION)
        self.client.logout()

    def demander(self, email=INSCRIPTION["email"]):
        return self.client.post("/portail/mot-de-passe-oublie/", {"email": email})

    def changer_avec_le_lien(self, lien, nouveau="Nouveau-Mdp-2026!"):
        page = self.client.get(lien, follow=True)  # Django redirige vers une URL sans le jeton
        self.assertContains(page, "Nouveau mot de passe")
        self.client.post(page.redirect_chain[-1][0], {"new_password1": nouveau, "new_password2": nouveau})
        return nouveau

    def test_lien_par_email_puis_nouveau_mot_de_passe(self):
        self.assertRedirects(self.demander(), "/portail/mot-de-passe-oublie/envoye/")
        self.assertEqual(len(mail.outbox), 1)
        lien = re.search(r"https?://[^/]+(/portail/mot-de-passe/\S+)", mail.outbox[0].body).group(1)
        nouveau = self.changer_avec_le_lien(lien)
        self.assertTrue(self.client.login(username="marche", password=nouveau))
        # Le lien ne sert qu'une fois.
        self.client.logout()
        self.assertContains(self.client.get(lien, follow=True), "Lien expiré")

    def test_adresse_inconnue_meme_reponse_sans_email(self):
        self.assertRedirects(self.demander("personne@exemple.cd"), "/portail/mot-de-passe-oublie/envoye/")
        self.assertEqual(len(mail.outbox), 0)

    def test_limite_des_demandes(self):
        for _ in range(7):
            self.demander()
        self.assertEqual(len(mail.outbox), 5)

    def test_lien_cree_par_l_equipe(self):
        equipe = get_user_model().objects.create_user("equipe", password="mdp-test-123", is_staff=True)
        pharmacien = get_user_model().objects.get(username="marche")
        url = f"/dawa/comptes/{pharmacien.pk}/lien-mot-de-passe/"
        # Réservé à l'équipe, et jamais pour un compte de l'équipe.
        self.client.login(username="marche", password=MDP)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.login(username="equipe", password="mdp-test-123")
        self.assertEqual(self.client.post(f"/dawa/comptes/{equipe.pk}/lien-mot-de-passe/").status_code, 404)
        page = self.client.post(url)
        self.assertContains(page, "wa.me/243990000001")
        lien = re.search(r'value="https?://[^/]+(/portail/mot-de-passe/[^"]+)"', page.content.decode()).group(1)
        self.client.logout()
        nouveau = self.changer_avec_le_lien(lien)
        self.assertTrue(self.client.login(username="marche", password=nouveau))


@override_settings(ADMINS=[("Equipe", "alertes@exemple.cd")])
class AlerteErreurTests(TestCase):
    def test_une_erreur_500_envoie_un_email_a_l_equipe(self):
        requete = RequestFactory().get("/portail/")
        logging.getLogger("django.request").error("Internal Server Error: /portail/",
                                                  extra={"status_code": 500, "request": requete})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("alertes@exemple.cd", mail.outbox[0].to)
        self.assertTrue(mail.outbox[0].subject.startswith("[Dawa]"))
