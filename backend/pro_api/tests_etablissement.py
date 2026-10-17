from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point

from kyc.models import Piece
from sante.models import Etablissement, ResponsableEtablissement

from .tests import MDP, ApiWebTestCase, creer_pharmacien
from .tests_pharmacie import image_jpeg

API = "/api/web/etablissement/"


class EspaceEtablissementTests(ApiWebTestCase):
    def setUp(self):
        super().setUp()
        self.etablissement = Etablissement.objects.create(
            nom="Clinique Espoir", type="clinique", adresse="Av. X", telephone="+243990000300",
            est_valide=True, position=Point(27.47, -11.66, srid=4326))
        utilisateur = get_user_model().objects.create_user("clinique", password=MDP)
        self.responsable = ResponsableEtablissement.objects.create(
            utilisateur=utilisateur, etablissement=self.etablissement, fonction="Médecin directeur")
        self.connecter("clinique")

    def test_espace_et_modification_de_la_fiche(self):
        espace = self.api.get(API).json()
        self.assertEqual((espace["statut"], espace["type"], espace["fonction"]), ("actif", "Clinique", "Médecin directeur"))
        self.assertEqual(espace["fiche"]["telephone"], "+243990000300")
        reponse = self.poster(API, {"services": "pédiatrie, maternité", "urgences_24h": True})
        self.assertEqual(reponse.status_code, 200, reponse.content)
        self.assertEqual(reponse.json()["message"], "Fiche mise à jour.")
        self.etablissement.refresh_from_db()
        self.assertEqual((self.etablissement.services, self.etablissement.urgences_24h), ("pédiatrie, maternité", True))
        self.poster(API, {"urgences_24h": False})
        self.etablissement.refresh_from_db()
        self.assertFalse(self.etablissement.urgences_24h)
        self.assertEqual(self.poster(API, {"adresse": ""}).status_code, 400)

    def test_compte_en_attente_sans_fiche_mais_avec_dossier(self):
        self.responsable.statut = ResponsableEtablissement.Statut.EN_ATTENTE
        self.responsable.save()
        self.assertIsNone(self.api.get(API).json()["fiche"])
        self.assertEqual(self.poster(API, {"services": "x"}).status_code, 403)
        envoi = self.api.post(f"{API}dossier/", {"type": Piece.Type.IDENTITE, "fichier": image_jpeg("id.jpg")},
                              format="multipart", HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(envoi.status_code, 201, envoi.content)
        self.assertEqual(Piece.objects.get().etablissement, self.etablissement)

    def test_reserve_aux_responsables(self):
        self.poster("/api/web/compte/deconnexion/")
        creer_pharmacien("pharma")
        self.connecter("pharma")
        self.assertEqual(self.api.get(API).status_code, 403)


class InscriptionEtablissementTests(ApiWebTestCase):
    def test_inscription(self):
        reponse = self.poster("/api/web/compte/inscription/etablissement/", {
            "nom": "Centre de santé Uzima", "type": "centre_sante", "numero_agrement": "DPS/42",
            "telephone": "+243990000400", "adresse": "Av. Y", "fonction": "Administrateur", "urgences_24h": True,
            "email": "cs@example.com", "username": "cs-uzima",
            "password1": "Mot-de-passe-2026", "password2": "Mot-de-passe-2026"})
        self.assertEqual(reponse.status_code, 201, reponse.content)
        self.assertEqual((reponse.json()["role"], reponse.json()["statut"]), ("etablissement", "en_attente"))
        etablissement = Etablissement.objects.get(numero_agrement="DPS/42")
        self.assertTrue(etablissement.urgences_24h)
        self.assertFalse(etablissement.est_valide)
        doublon = self.poster("/api/web/compte/deconnexion/") and self.poster(
            "/api/web/compte/inscription/etablissement/", {"numero_agrement": "dps/42"})
        self.assertIn("numero_agrement", doublon.json()["erreurs"])
