import uuid

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point

from abonnements.models import Abonnement
from kyc.dossier import OBLIGATOIRES
from kyc.models import Piece
from pharmacies.models import Pharmacie
from portail.models import Pharmacien
from sante.models import Etablissement, ResponsableEtablissement
from verification.models import Signalement

from .tests import MDP, ApiWebTestCase, creer_pharmacien

API = "/api/web/equipe/"


class EquipeTestCase(ApiWebTestCase):
    def setUp(self):
        super().setUp()
        self.equipe = get_user_model().objects.create_user("equipe", password=MDP, is_staff=True)
        self.compte = creer_pharmacien("nouvelle", statut=Pharmacien.Statut.EN_ATTENTE)
        self.pharmacie = self.compte.pharmacie
        Pharmacie.objects.filter(pk=self.pharmacie.pk).update(est_validee=False)
        self.connecter("equipe")

    def pieces(self, structure=None, accepter=False):
        pieces = [Piece.objects.create(pharmacie=structure or self.pharmacie, type=t, fichier=f"pieces/{t}.pdf")
                  for t in OBLIGATOIRES]
        if accepter:
            for p in pieces:
                p.verifier(self.equipe, acceptee=True)
        return pieces

    def get(self, chemin, **params):
        reponse = self.api.get(f"{API}{chemin}", params)
        self.assertEqual(reponse.status_code, 200, reponse.content)
        return reponse.json()


class AccesEquipeTests(EquipeTestCase):
    def test_reserve_a_l_equipe(self):
        self.poster("/api/web/compte/deconnexion/")
        self.assertEqual(self.api.get(f"{API}tableau/").status_code, 403)
        creer_pharmacien("pharma")
        self.connecter("pharma")
        self.assertEqual(self.api.get(f"{API}demandes/").status_code, 403)
        reponse = self.poster(f"{API}demandes/pharmacie/{self.compte.pk}/", {"decision": "valider"})
        self.assertEqual(reponse.status_code, 403)


class DemandesTests(EquipeTestCase):
    def test_tableau(self):
        tableau = self.get("tableau/")
        self.assertEqual((tableau["identifiant"], tableau["nb_demandes"]), ("equipe", 1))

    def test_pieces_puis_validation(self):
        pieces = self.pieces()
        demande = self.get("demandes/")["demandes"][0]
        self.assertEqual((demande["genre"], demande["structure"]["nom"]), ("pharmacie", "Pharmacie nouvelle"))
        self.assertEqual(demande["dossier"]["lignes"][0]["piece"]["document"], f"/dawa/pieces/{pieces[0].pk}/")

        # Validation refusée tant que les pièces ne sont pas acceptées.
        refus = self.poster(f"{API}demandes/pharmacie/{self.compte.pk}/", {"decision": "valider"})
        self.assertEqual(refus.status_code, 400)
        self.assertIn("pièces obligatoires", refus.json()["message"])

        rejet = self.poster(f"{API}pieces/{pieces[0].pk}/", {"decision": "rejeter"})
        self.assertEqual(rejet.status_code, 400)
        rejet = self.poster(f"{API}pieces/{pieces[0].pk}/", {"decision": "rejeter", "motif": "Illisible"}).json()
        self.assertEqual(rejet["dossier"]["lignes"][0]["piece"]["statut"], "rejetee")
        for p in pieces:
            self.poster(f"{API}pieces/{p.pk}/", {"decision": "accepter"})

        validation = self.poster(f"{API}demandes/pharmacie/{self.compte.pk}/", {"decision": "valider"})
        self.assertEqual(validation.status_code, 200, validation.content)
        self.assertEqual(validation.json()["nb_demandes"], 0)
        self.compte.refresh_from_db()
        self.assertEqual((self.compte.statut, self.compte.traite_par), ("actif", self.equipe))
        self.assertTrue(Pharmacie.objects.get(pk=self.pharmacie.pk).est_validee)

    def test_refus_avec_motif_et_etablissement(self):
        etablissement = Etablissement.objects.create(nom="Hôpital Test", type="hopital", adresse="x",
                                                     position=Point(27.479, -11.664, srid=4326))
        utilisateur = get_user_model().objects.create_user("hopital", password=MDP)
        responsable = ResponsableEtablissement.objects.create(utilisateur=utilisateur, etablissement=etablissement,
                                                              statut=ResponsableEtablissement.Statut.EN_ATTENTE)
        demandes = self.get("demandes/")["demandes"]
        hopital = next(d for d in demandes if d["genre"] == "etablissement")
        self.assertEqual(hopital["structure"]["type"], "Hôpital")
        self.assertTrue(hopital["structure"]["position_a_verifier"])
        url = f"{API}demandes/etablissement/{responsable.pk}/"
        self.assertEqual(self.poster(url, {"decision": "refuser"}).status_code, 400)
        self.assertEqual(self.poster(url, {"decision": "refuser", "motif": "Autorisation introuvable"}).status_code, 200)
        responsable.refresh_from_db()
        self.assertEqual((responsable.statut, responsable.motif), ("refuse", "Autorisation introuvable"))
        self.assertEqual(self.get("demandes/")["refusees"][0]["motif"], "Autorisation introuvable")
        self.assertEqual(self.poster(f"{API}demandes/inconnu/1/", {"decision": "valider"}).status_code, 404)


class ListesTests(EquipeTestCase):
    def test_pharmacies_filtres_et_suspension(self):
        self.pieces(accepter=True)
        self.poster(f"{API}demandes/pharmacie/{self.compte.pk}/", {"decision": "valider"})
        liste = self.get("pharmacies/", filtre="visibles")["pharmacies"]
        self.assertEqual([(p["nom"], p["kyc_verifie"]) for p in liste], [("Pharmacie nouvelle", True)])
        self.assertEqual(self.get("pharmacies/", q="inexistante")["pharmacies"], [])

        url = f"{API}pharmacies/{self.pharmacie.pk}/visibilite/"
        self.assertEqual(self.poster(url, {"action": "suspendre"}).status_code, 400)
        self.assertEqual(self.poster(url, {"action": "suspendre", "motif": "Impayé"}).json()["message"],
                         "Pharmacie nouvelle est suspendue et retirée de l'app.")
        self.compte.refresh_from_db()
        self.assertEqual(self.compte.statut, "suspendu")
        self.assertEqual(self.get("pharmacies/", filtre="masquees")["pharmacies"][0]["comptes"][0]["statut"], "suspendu")
        self.poster(url, {"action": "reactiver"})
        self.assertTrue(Pharmacie.objects.get(pk=self.pharmacie.pk).est_validee)

    def test_etablissements_visibilite(self):
        etablissement = Etablissement.objects.create(nom="Labo Central", type="laboratoire", adresse="x",
                                                     est_valide=True, position=Point(27.47, -11.66, srid=4326))
        self.assertEqual(self.get("etablissements/", q="labo")["etablissements"][0]["type"], "Laboratoire")
        self.poster(f"{API}etablissements/{etablissement.pk}/visibilite/", {"action": "suspendre", "motif": "Fermé"})
        etablissement.refresh_from_db()
        self.assertFalse(etablissement.est_valide)

    def test_lien_mot_de_passe_vers_le_site(self):
        lien = self.poster(f"{API}comptes/{self.compte.utilisateur_id}/lien-mot-de-passe/").json()
        self.assertIn("/mot-de-passe/", lien["lien"])
        self.assertTrue(lien["whatsapp"].startswith("https://wa.me/"))
        uid, jeton = lien["lien"].rstrip("/").split("/")[-2:]
        valide = self.api.get("/api/web/compte/mot-de-passe-nouveau/", {"uid": uid, "jeton": jeton}).json()
        self.assertEqual(valide, {"valide": True, "identifiant": "nouvelle"})
        # Jamais pour un compte de l'équipe.
        self.assertEqual(self.poster(f"{API}comptes/{self.equipe.pk}/lien-mot-de-passe/").status_code, 404)


class AbonnementsSignalementsTests(EquipeTestCase):
    def test_activer_abonnement(self):
        abonnement = Abonnement.objects.create(pharmacie=self.pharmacie, formule="essentiel", mois=1, montant=30_000,
                                               reference="DAWA-TEST1")
        self.assertEqual(self.get("abonnements/")["en_attente"][0]["reference"], "DAWA-TEST1")
        url = f"{API}abonnements/{abonnement.pk}/activer/"
        self.assertEqual(self.poster(url, {"reference_paiement": ""}).status_code, 400)
        self.assertEqual(self.poster(url, {"reference_paiement": "MP123"}).status_code, 200)
        abonnement.refresh_from_db()
        self.assertEqual((abonnement.statut, abonnement.reference_paiement), ("actif", "MP123"))
        self.assertEqual(self.get("abonnements/")["actifs"][0]["pharmacie"]["nom"], "Pharmacie nouvelle")
        self.assertEqual(self.poster(url, {"reference_paiement": "MP123"}).status_code, 404)

    def test_traiter_signalement(self):
        s = Signalement.objects.create(client_id=uuid.uuid4(), description="Boîte mal imprimée", lieu_achat="Marché")
        self.assertEqual(self.get("signalements/")["a_traiter"][0]["lieu"], "Marché")
        url = f"{API}signalements/{s.pk}/traiter/"
        self.assertEqual(self.poster(url, {"suite_donnee": " "}).status_code, 400)
        self.assertEqual(self.poster(url, {"suite_donnee": "Transmis à l'IPS"}).status_code, 200)
        self.assertEqual(self.get("signalements/")["traites"][0]["suite_donnee"], "Transmis à l'IPS")
