import re

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from pharmacies.models import Pharmacie
from portail.models import Pharmacien
from sante.models import Etablissement, ResponsableEtablissement

MDP = "mdp-test-123"


def creer_pharmacien(identifiant, statut=Pharmacien.Statut.ACTIF, email=""):
    pharmacie = Pharmacie.objects.create(nom=f"Pharmacie {identifiant}", adresse="x", telephone="0",
                                         est_validee=True, position=Point(27.47, -11.66, srid=4326))
    utilisateur = get_user_model().objects.create_user(identifiant, email=email, password=MDP)
    return Pharmacien.objects.create(utilisateur=utilisateur, pharmacie=pharmacie, statut=statut)


class ApiWebTestCase(TestCase):
    """Client qui se comporte comme le site Next.js : cookie CSRF obtenu via /moi/, puis en-tête X-CSRFToken."""

    def setUp(self):
        cache.clear()
        self.api = APIClient(enforce_csrf_checks=True)

    def csrf(self):
        self.api.get("/api/web/compte/moi/")
        return self.api.cookies["csrftoken"].value

    def poster(self, url, donnees=None, **kwargs):
        return self.api.post(url, donnees or {}, format="json", HTTP_X_CSRFTOKEN=self.csrf(), **kwargs)

    def connecter(self, identifiant):
        reponse = self.poster("/api/web/compte/connexion/", {"identifiant": identifiant, "mot_de_passe": MDP})
        self.assertEqual(reponse.status_code, 200, reponse.content)
        return reponse


class CompteTests(ApiWebTestCase):
    def test_moi_sans_connexion_et_cookie_csrf(self):
        reponse = self.api.get("/api/web/compte/moi/")
        self.assertEqual(reponse.json(), {"connecte": False})
        self.assertIn("csrftoken", reponse.cookies)

    def test_connexion_sans_jeton_csrf_refusee(self):
        creer_pharmacien("pharma")
        reponse = self.api.post("/api/web/compte/connexion/", {"identifiant": "pharma", "mot_de_passe": MDP},
                                format="json")
        self.assertEqual(reponse.status_code, 403)

    def test_connexion_pharmacien(self):
        creer_pharmacien("pharma")
        infos = self.connecter("pharma").json()
        self.assertEqual(infos["role"], "pharmacien")
        self.assertEqual(infos["statut"], "actif")
        self.assertEqual(infos["structure"]["nom"], "Pharmacie pharma")
        self.assertEqual(self.api.get("/api/web/compte/moi/").json()["identifiant"], "pharma")

    def test_connexion_pharmacien_en_attente(self):
        creer_pharmacien("nouveau", statut=Pharmacien.Statut.EN_ATTENTE)
        self.assertEqual(self.connecter("nouveau").json()["statut"], "en_attente")

    def test_roles_etablissement_et_equipe(self):
        etablissement = Etablissement.objects.create(nom="Hôpital", type="hopital", adresse="x",
                                                     position=Point(27.47, -11.66, srid=4326))
        utilisateur = get_user_model().objects.create_user("hopital", password=MDP)
        ResponsableEtablissement.objects.create(utilisateur=utilisateur, etablissement=etablissement)
        get_user_model().objects.create_user("equipe", password=MDP, is_staff=True)
        self.assertEqual(self.connecter("hopital").json()["structure"]["type"], "Hôpital")
        self.poster("/api/web/compte/deconnexion/")
        infos = self.connecter("equipe").json()
        self.assertEqual((infos["role"], infos["statut"], infos["structure"]), ("equipe", "actif", None))

    def test_mauvais_mot_de_passe_puis_blocage(self):
        creer_pharmacien("pharma")
        for _ in range(5):
            reponse = self.poster("/api/web/compte/connexion/", {"identifiant": "pharma", "mot_de_passe": "faux"})
            self.assertEqual(reponse.status_code, 400)
            self.assertEqual(reponse.json()["message"], "Identifiant ou mot de passe incorrect.")
        reponse = self.poster("/api/web/compte/connexion/", {"identifiant": "pharma", "mot_de_passe": MDP})
        self.assertEqual(reponse.status_code, 429)

    def test_deconnexion(self):
        creer_pharmacien("pharma")
        self.connecter("pharma")
        self.assertEqual(self.poster("/api/web/compte/deconnexion/").status_code, 200)
        self.assertFalse(self.api.get("/api/web/compte/moi/").json()["connecte"])


@override_settings(UZIMA_WEB_URL="https://uzima.example")
class MotDePasseTests(ApiWebTestCase):
    def test_lien_par_email_puis_nouveau_mot_de_passe(self):
        creer_pharmacien("pharma", email="pharma@example.com")
        reponse = self.poster("/api/web/compte/mot-de-passe-oublie/", {"email": "pharma@example.com"})
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        uid, jeton = re.search(r"https://uzima\.example/mot-de-passe/([^/]+)/(\S+)", mail.outbox[0].body).groups()

        lien = self.api.get("/api/web/compte/mot-de-passe-nouveau/", {"uid": uid, "jeton": jeton}).json()
        self.assertEqual(lien, {"valide": True, "identifiant": "pharma"})

        reponse = self.poster("/api/web/compte/mot-de-passe-nouveau/", {
            "uid": uid, "jeton": jeton, "mot_de_passe1": "Nouveau-mdp-2026", "mot_de_passe2": "autre"})
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("new_password2", reponse.json()["erreurs"])

        reponse = self.poster("/api/web/compte/mot-de-passe-nouveau/", {
            "uid": uid, "jeton": jeton, "mot_de_passe1": "Nouveau-mdp-2026", "mot_de_passe2": "Nouveau-mdp-2026"})
        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(get_user_model().objects.get(username="pharma").check_password("Nouveau-mdp-2026"))
        # Le lien ne sert qu'une fois.
        self.assertFalse(self.api.get("/api/web/compte/mot-de-passe-nouveau/",
                                      {"uid": uid, "jeton": jeton}).json()["valide"])

    def test_email_inconnu_meme_reponse(self):
        reponse = self.poster("/api/web/compte/mot-de-passe-oublie/", {"email": "personne@example.com"})
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_limite_par_adresse(self):
        creer_pharmacien("pharma", email="pharma@example.com")
        for _ in range(7):
            self.poster("/api/web/compte/mot-de-passe-oublie/", {"email": "pharma@example.com"})
        self.assertEqual(len(mail.outbox), 5)

    def test_lien_invalide(self):
        reponse = self.poster("/api/web/compte/mot-de-passe-nouveau/", {
            "uid": "xx", "jeton": "yy", "mot_de_passe1": "Nouveau-mdp-2026", "mot_de_passe2": "Nouveau-mdp-2026"})
        self.assertEqual(reponse.status_code, 400)
