from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.test import TestCase

from abonnements.models import Abonnement
from kyc.dossier import OBLIGATOIRES
from kyc.models import Piece
from pharmacies.models import Pharmacie
from portail.models import Pharmacien
from verification.models import Signalement

INSCRIPTION = {
    "nom": "Pharmacie du Marché", "numero_agrement": "IPS/LSHI/2026/042", "telephone": "+243990000001",
    "whatsapp": "", "adresse": "Av. Mama Yemo 12", "quartier": "Centre", "commune": "Lubumbashi",
    "horaires": "Lun–Sam 8h–20h", "latitude": "-11.6601", "longitude": "27.4790",
    "username": "marche", "password1": "Kasapa-2026!", "password2": "Kasapa-2026!",
}


class InscriptionTests(TestCase):
    def inscrire(self, **modifs):
        return self.client.post("/portail/inscription/", {**INSCRIPTION, **modifs})

    def test_inscription_cree_un_compte_en_attente_et_invisible(self):
        r = self.inscrire()
        self.assertRedirects(r, "/portail/", fetch_redirect_response=False)
        compte = Pharmacien.objects.get()
        self.assertEqual(compte.statut, Pharmacien.Statut.EN_ATTENTE)
        self.assertFalse(compte.pharmacie.est_validee)
        self.assertAlmostEqual(compte.pharmacie.position.y, -11.6601)
        # Connecté, mais seule la page de statut est accessible.
        page = self.client.get("/portail/stock/")
        self.assertEqual(page.status_code, 403)
        self.assertContains(page, "en cours de vérification", status_code=403)
        # Invisible dans l'app.
        self.assertNotIn("Pharmacie du Marché", self.client.get("/api/pharmacies/").content.decode())

    def test_refus_doublon_et_robot(self):
        self.inscrire()
        self.client.logout()
        self.assertContains(self.inscrire(username="autre"), "déjà inscrite")
        self.assertEqual(self.inscrire(username="robot", numero_agrement="X1", site_web="http://spam").status_code,
                         200)
        self.assertEqual(Pharmacien.objects.count(), 1)

    def test_sans_position_place_au_centre(self):
        self.inscrire(latitude="", longitude="")
        position = Pharmacien.objects.get().pharmacie.position
        self.assertEqual((round(position.x, 3), round(position.y, 3)), (27.479, -11.664))


class EspaceDawaTests(TestCase):
    def setUp(self):
        self.equipe = get_user_model().objects.create_user("equipe", password="mdp-test-123", is_staff=True)
        self.client.post("/portail/inscription/", INSCRIPTION)
        self.compte = Pharmacien.objects.get()
        self.client.logout()

    def connecter_equipe(self):
        self.client.login(username="equipe", password="mdp-test-123")

    def dossier_verifie(self):
        for type_ in OBLIGATOIRES:
            piece = Piece.objects.create(pharmacie=self.compte.pharmacie, type=type_, fichier=f"pieces/{type_}.pdf")
            piece.verifier(self.equipe, acceptee=True)

    def test_reserve_a_l_equipe(self):
        self.assertEqual(self.client.get("/dawa/").status_code, 302)  # connexion
        self.client.login(username="marche", password=INSCRIPTION["password1"])
        self.assertEqual(self.client.get("/dawa/demandes/").status_code, 403)
        self.assertEqual(self.client.post(f"/dawa/demandes/pharmacie/{self.compte.pk}/", {"decision": "valider"}).status_code,
                         403)
        self.compte.refresh_from_db()
        self.assertEqual(self.compte.statut, Pharmacien.Statut.EN_ATTENTE)

    def test_equipe_redirigee_depuis_le_portail(self):
        self.connecter_equipe()
        self.assertRedirects(self.client.get("/portail/"), "/dawa/")

    def test_valider_rend_visible_et_ouvre_le_portail(self):
        self.dossier_verifie()
        self.connecter_equipe()
        self.assertContains(self.client.get("/dawa/demandes/"), "Pharmacie du Marché")
        self.client.post(f"/dawa/demandes/pharmacie/{self.compte.pk}/", {"decision": "valider"})
        self.compte.refresh_from_db()
        self.assertEqual((self.compte.statut, self.compte.traite_par), (Pharmacien.Statut.ACTIF, self.equipe))
        self.assertTrue(Pharmacie.objects.get(pk=self.compte.pharmacie_id).est_validee)
        self.client.login(username="marche", password=INSCRIPTION["password1"])
        self.assertEqual(self.client.get("/portail/stock/").status_code, 200)

    def test_refus_exige_un_motif_montre_a_la_pharmacie(self):
        self.connecter_equipe()
        self.client.post(f"/dawa/demandes/pharmacie/{self.compte.pk}/", {"decision": "refuser"})
        self.compte.refresh_from_db()
        self.assertEqual(self.compte.statut, Pharmacien.Statut.EN_ATTENTE)
        self.client.post(f"/dawa/demandes/pharmacie/{self.compte.pk}/", {"decision": "refuser", "motif": "Autorisation introuvable"})
        self.client.login(username="marche", password=INSCRIPTION["password1"])
        self.assertContains(self.client.get("/portail/"), "Autorisation introuvable", status_code=403)

    def test_suspendre_puis_reactiver(self):
        self.dossier_verifie()
        self.connecter_equipe()
        self.client.post(f"/dawa/demandes/pharmacie/{self.compte.pk}/", {"decision": "valider"})
        pharmacie = self.compte.pharmacie
        self.client.post(f"/dawa/pharmacies/{pharmacie.pk}/visibilite/", {"action": "suspendre", "motif": "Impayé"})
        pharmacie.refresh_from_db()
        self.compte.refresh_from_db()
        self.assertFalse(pharmacie.est_validee)
        self.assertEqual(self.compte.statut, Pharmacien.Statut.SUSPENDU)
        self.client.post(f"/dawa/pharmacies/{pharmacie.pk}/visibilite/", {"action": "reactiver"})
        pharmacie.refresh_from_db()
        self.compte.refresh_from_db()
        self.assertTrue(pharmacie.est_validee)
        self.assertEqual(self.compte.statut, Pharmacien.Statut.ACTIF)

    def test_pharmacie_creee_par_l_admin_sans_compte(self):
        pharmacie = Pharmacie.objects.create(nom="Ancienne", adresse="x", telephone="0", est_validee=True,
                                             position=Point(27.48, -11.66, srid=4326))
        self.connecter_equipe()
        self.assertContains(self.client.get("/dawa/pharmacies/?q=Ancienne"), "Ancienne")
        self.client.post(f"/dawa/pharmacies/{pharmacie.pk}/visibilite/", {"action": "suspendre", "motif": "Fermée"})
        pharmacie.refresh_from_db()
        self.assertFalse(pharmacie.est_validee)

    def test_activer_un_abonnement_exige_la_reference(self):
        abonnement = Abonnement.objects.create(pharmacie=self.compte.pharmacie, formule="essentiel", mois=1,
                                               montant=30_000, reference="DAWA-TEST1")
        self.connecter_equipe()
        self.assertContains(self.client.get("/dawa/abonnements/"), "DAWA-TEST1")
        self.client.post(f"/dawa/abonnements/{abonnement.pk}/activer/", {"reference_paiement": ""})
        abonnement.refresh_from_db()
        self.assertEqual(abonnement.statut, Abonnement.Statut.EN_ATTENTE)
        self.client.post(f"/dawa/abonnements/{abonnement.pk}/activer/", {"reference_paiement": "MP123"})
        abonnement.refresh_from_db()
        self.assertEqual((abonnement.statut, abonnement.reference_paiement), (Abonnement.Statut.ACTIF, "MP123"))

    def test_traiter_un_signalement(self):
        signalement = Signalement.objects.create(client_id="00000000-0000-0000-0000-000000000001",
                                                 description="Boîte mal imprimée, lot inconnu")
        self.connecter_equipe()
        self.assertContains(self.client.get("/dawa/signalements/"), "Boîte mal imprimée")
        self.client.post(f"/dawa/signalements/{signalement.pk}/traiter/", {"suite_donnee": "Transmis à l'IPS"})
        signalement.refresh_from_db()
        self.assertTrue(signalement.traite)


class InscriptionMotDePasseTests(TestCase):
    def test_mot_de_passe_obligatoire(self):
        r = self.client.post("/portail/inscription/", {**INSCRIPTION, "password1": "", "password2": ""})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Pharmacien.objects.exists())
