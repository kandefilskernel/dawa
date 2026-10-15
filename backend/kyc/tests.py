import io

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from gestion.tests import INSCRIPTION
from portail.models import Pharmacien
from sante.models import Etablissement, ResponsableEtablissement

from .dossier import OBLIGATOIRES
from .models import Piece

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def photo():
    tampon = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(tampon, "JPEG")
    return SimpleUploadedFile("facade.jpg", tampon.getvalue(), content_type="image/jpeg")


def pdf(nom="autorisation.pdf", contenu=PDF):
    return SimpleUploadedFile(nom, contenu, content_type="application/pdf")


class DossierPharmacieTests(TestCase):
    def setUp(self):
        cache.clear()  # compteurs de limites (inscriptions, connexions)
        self.equipe = get_user_model().objects.create_user("equipe", password="mdp-test-123", is_staff=True)
        self.client.post("/portail/inscription/", INSCRIPTION)  # connecte la pharmacie
        self.compte = Pharmacien.objects.get()

    def envoyer(self, type_, fichier):
        return self.client.post("/portail/dossier/", {"formulaire": "piece", "type": type_, "fichier": fichier})

    def envoyer_tout(self):
        for type_ in OBLIGATOIRES:
            self.envoyer(type_, photo() if type_ == Piece.Type.FACADE else pdf())

    def test_le_compte_en_attente_envoie_ses_pieces_hors_du_dossier_public(self):
        page = self.client.get("/portail/")
        self.assertContains(page, "Dernière étape", status_code=403)
        self.envoyer_tout()
        pieces = Piece.objects.filter(pharmacie=self.compte.pharmacie)
        self.assertEqual(pieces.count(), len(OBLIGATOIRES))
        chemin = pieces.first().fichier.path
        self.assertTrue(chemin.startswith(str(settings.KYC_RACINE)))
        self.assertFalse(chemin.startswith(str(settings.MEDIA_ROOT)))
        self.assertNotIn("autorisation", pieces.get(type=Piece.Type.AUTORISATION).fichier.name)  # nom aléatoire
        self.assertContains(self.client.get("/portail/"), "dossier est complet", status_code=403)

    def test_fichiers_refuses(self):
        self.envoyer(Piece.Type.AUTORISATION, pdf("faux.pdf", b"<html>pas un pdf</html>"))
        self.envoyer(Piece.Type.AUTORISATION, pdf("script.exe", PDF))
        self.envoyer(Piece.Type.FACADE, SimpleUploadedFile("facade.jpg", b"pas une image", content_type="image/jpeg"))
        self.assertFalse(Piece.objects.exists())

    def test_seule_l_equipe_ouvre_une_piece(self):
        self.envoyer(Piece.Type.AUTORISATION, pdf())
        piece = Piece.objects.get()
        self.assertEqual(self.client.get(f"/dawa/pieces/{piece.pk}/").status_code, 403)  # la pharmacie elle-même
        self.client.logout()
        self.assertEqual(self.client.get(f"/dawa/pieces/{piece.pk}/").status_code, 302)  # anonyme → connexion
        self.client.login(username="equipe", password="mdp-test-123")
        reponse = self.client.get(f"/dawa/pieces/{piece.pk}/")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse["X-Content-Type-Options"], "nosniff")
        self.assertEqual(b"".join(reponse.streaming_content), PDF)

    def test_validation_bloquee_tant_que_le_dossier_n_est_pas_verifie(self):
        self.envoyer_tout()
        self.client.login(username="equipe", password="mdp-test-123")
        url = f"/dawa/demandes/pharmacie/{self.compte.pk}/"
        self.client.post(url, {"decision": "valider"})
        self.compte.refresh_from_db()
        self.assertEqual(self.compte.statut, Pharmacien.Statut.EN_ATTENTE)

        pieces = list(Piece.objects.all())
        rejetee = pieces[0]
        self.client.post(f"/dawa/pieces/{rejetee.pk}/verifier/", {"decision": "rejeter", "motif": "Illisible"})
        for piece in pieces[1:]:
            self.client.post(f"/dawa/pieces/{piece.pk}/verifier/", {"decision": "accepter"})
        self.client.post(url, {"decision": "valider"})
        self.compte.refresh_from_db()
        self.assertEqual(self.compte.statut, Pharmacien.Statut.EN_ATTENTE)

        # La pharmacie voit le motif et renvoie la pièce ; l'équipe l'accepte puis valide.
        self.client.login(username=INSCRIPTION["username"], password=INSCRIPTION["password1"])
        self.assertContains(self.client.get("/portail/"), "Illisible", status_code=403)
        self.envoyer(rejetee.type, photo() if rejetee.type == Piece.Type.FACADE else pdf())
        self.client.login(username="equipe", password="mdp-test-123")
        nouvelle = Piece.objects.filter(type=rejetee.type).latest("envoyee_le")
        self.client.post(f"/dawa/pieces/{nouvelle.pk}/verifier/", {"decision": "accepter"})
        self.client.post(url, {"decision": "valider"})
        self.compte.refresh_from_db()
        self.assertEqual(self.compte.statut, Pharmacien.Statut.ACTIF)

    def test_rejet_sans_motif_refuse(self):
        self.envoyer(Piece.Type.AUTORISATION, pdf())
        piece = Piece.objects.get()
        self.client.login(username="equipe", password="mdp-test-123")
        self.client.post(f"/dawa/pieces/{piece.pk}/verifier/", {"decision": "rejeter"})
        piece.refresh_from_db()
        self.assertEqual(piece.statut, Piece.Statut.EN_ATTENTE)


class InscriptionEtablissementTests(TestCase):
    def setUp(self):
        cache.clear()  # compteurs de limites (inscriptions, connexions)

    DONNEES = {
        "nom": "Clinique Espoir", "type": "clinique", "numero_agrement": "DPS/HK/2026/015",
        "telephone": "+243990000123", "adresse": "Av. Kasai 3", "quartier": "Bel-Air", "services": "Maternité",
        "urgences_24h": "on", "fonction": "Médecin directeur", "latitude": "-11.66", "longitude": "27.48",
        "email": "direction@clinique-espoir.cd", "username": "espoir", "password1": "Kasapa-2026!", "password2": "Kasapa-2026!",
    }

    def test_parcours_complet(self):
        equipe = get_user_model().objects.create_user("equipe", password="mdp-test-123", is_staff=True)
        r = self.client.post("/etablissement/inscription/", self.DONNEES)
        self.assertRedirects(r, "/etablissement/", target_status_code=403)
        compte = ResponsableEtablissement.objects.get()
        self.assertFalse(compte.etablissement.est_valide)
        self.assertNotIn("Clinique Espoir", self.client.get("/api/etablissements/").content.decode())
        # La connexion au portail renvoie vers l'espace établissement.
        self.assertRedirects(self.client.get("/portail/"), "/etablissement/", target_status_code=403)

        for type_ in OBLIGATOIRES:
            self.client.post("/etablissement/", {"formulaire": "piece", "type": type_,
                                                 "fichier": photo() if type_ == Piece.Type.FACADE else pdf()})
        self.client.login(username="equipe", password="mdp-test-123")
        self.assertContains(self.client.get("/dawa/demandes/"), "Clinique Espoir")
        for piece in Piece.objects.filter(etablissement=compte.etablissement):
            self.client.post(f"/dawa/pieces/{piece.pk}/verifier/", {"decision": "accepter"})
        self.client.post(f"/dawa/demandes/etablissement/{compte.pk}/", {"decision": "valider"})
        compte.refresh_from_db()
        self.assertEqual((compte.statut, compte.traite_par), (ResponsableEtablissement.Statut.ACTIF, equipe))
        self.assertTrue(Etablissement.objects.get(pk=compte.etablissement_id).est_valide)
        self.assertIn("Clinique Espoir", self.client.get("/api/etablissements/").content.decode())

        # Une fois actif, le responsable met à jour la fiche affichée aux patients.
        self.client.login(username="espoir", password="Kasapa-2026!")
        self.client.post("/etablissement/", {"telephone": "+243990000999", "adresse": "Av. Kasai 3",
                                             "quartier": "Bel-Air", "services": "Maternité, pédiatrie"})
        self.assertEqual(Etablissement.objects.get(pk=compte.etablissement_id).telephone, "+243990000999")

    def test_doublon_refuse(self):
        self.client.post("/etablissement/inscription/", self.DONNEES)
        self.client.logout()
        r = self.client.post("/etablissement/inscription/", {**self.DONNEES, "username": "autre"})
        self.assertContains(r, "déjà inscrit")
