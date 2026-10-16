import json
import uuid
from unittest import mock

from django.contrib.gis.geos import Point
from django.test import TestCase, override_settings

from catalogue.models import Medicament
from config.jetons import entete_authorization
from conseil.models import Question
from pharmacies.models import Pharmacie
from reservations.models import Reservation
from stock.models import AlerteStock, Stock

from . import fcm
from .envoi import notifier_reponse
from .models import AppareilPush

COMPTE = json.dumps({"project_id": "dawa-test", "client_email": "x@dawa-test.iam", "private_key": "-"})


def pharmacie(nom):
    return Pharmacie.objects.create(nom=nom, adresse="x", telephone="0", est_validee=True,
                                    position=Point(27.479, -11.664, srid=4326))


class EnregistrementTests(TestCase):
    def setUp(self):
        self.client_id = uuid.uuid4()
        self.auth = entete_authorization(self.client_id)

    def poster(self, **donnees):
        return self.client.post("/api/appareil/notifications/", {"jeton": "fcm-1", **donnees},
                                content_type="application/json", HTTP_AUTHORIZATION=self.auth)

    def test_enregistrer_puis_changer_de_langue(self):
        self.assertEqual(self.poster().status_code, 201)
        self.assertEqual(self.poster(langue="sw").status_code, 200)
        appareil = AppareilPush.objects.get()
        self.assertEqual((appareil.client_id, appareil.langue), (self.client_id, "sw"))

    def test_jeton_obligatoire_et_langue_controlee(self):
        r = self.client.post("/api/appareil/notifications/", {"jeton": "fcm-1"}, content_type="application/json")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(self.poster(langue="de").status_code, 400)

    def test_desinscrire(self):
        self.poster()
        r = self.client.delete("/api/appareil/notifications/", {"jeton": "fcm-1"},
                               content_type="application/json", HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(r.status_code, 204)
        self.assertFalse(AppareilPush.objects.exists())


@override_settings(FIREBASE_COMPTE_SERVICE=COMPTE)
class EnvoiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.med = Medicament.objects.create(dci="Amoxicilline", nom_commercial="Amoxicilline", dosage="500 mg")
        cls.pharmacie = pharmacie("Pharmacie du Centre")

    def setUp(self):
        self.client_id = uuid.uuid4()
        AppareilPush.objects.create(client_id=self.client_id, jeton="fcm-fr", langue="fr")
        envoi = mock.patch("notifications.envoi.fcm.envoyer")
        self.envoyer = envoi.start()
        self.addCleanup(envoi.stop)

    def reservation(self, **extra):
        return Reservation.objects.create(client_id=self.client_id, nom="Client", telephone="+243990000001",
                                          pharmacie=self.pharmacie, medicament=self.med, **extra)

    def test_reservation_acceptee_puis_prete(self):
        r = self.reservation()
        with self.captureOnCommitCallbacks(execute=True):
            r.changer_statut(Reservation.Statut.ACCEPTEE)
        jeton, titre, corps, donnees = self.envoyer.call_args.args
        self.assertEqual((jeton, titre), ("fcm-fr", "Réservation acceptée"))
        self.assertEqual(corps, "Pharmacie du Centre prépare votre Amoxicilline 500 mg.")
        self.assertEqual(donnees, {"type": "reservation", "id": r.pk})

        with self.captureOnCommitCallbacks(execute=True):
            r.changer_statut(Reservation.Statut.PRETE)
        self.assertEqual(self.envoyer.call_args.args[1], "Votre médicament est prêt")

    def test_dans_la_langue_du_telephone(self):
        AppareilPush.objects.filter(jeton="fcm-fr").update(langue="sw")
        with self.captureOnCommitCallbacks(execute=True):
            self.reservation().changer_statut(Reservation.Statut.REFUSEE)
        self.assertEqual(self.envoyer.call_args.args[1], "Oda imekataliwa")

    def test_jeton_perime_oublie(self):
        self.envoyer.side_effect = fcm.JetonPerime
        with self.captureOnCommitCallbacks(execute=True):
            self.reservation().changer_statut(Reservation.Statut.ACCEPTEE)
        self.assertFalse(AppareilPush.objects.exists())

    def test_erreur_inattendue_sans_bloquer_le_pharmacien(self):
        self.envoyer.side_effect = RuntimeError("panne")
        r = self.reservation()
        with self.assertLogs("notifications.envoi", "ERROR"), self.captureOnCommitCallbacks(execute=True):
            r.changer_statut(Reservation.Statut.ACCEPTEE)
        r.refresh_from_db()
        self.assertEqual(r.statut, Reservation.Statut.ACCEPTEE)

    def test_alerte_annonce_le_medicament_en_stock(self):
        equivalent = Medicament.objects.create(dci="Amoxicilline", nom_commercial="Clamoxyl", dosage="500 mg")
        AlerteStock.objects.create(client_id=self.client_id, medicament=self.med,
                                   position=Point(27.479, -11.664, srid=4326), rayon_km=5)
        with self.captureOnCommitCallbacks(execute=True):
            Stock.objects.create(pharmacie=self.pharmacie, medicament=equivalent)
        _, titre, corps, donnees = self.envoyer.call_args.args
        self.assertEqual(titre, "Clamoxyl 500 mg est disponible")
        self.assertEqual(corps, "Disponible maintenant à Pharmacie du Centre.")
        self.assertEqual(donnees["type"], "alerte")

    def test_reponse_a_une_question(self):
        question = Question.objects.create(client_id=self.client_id, texte="Avant ou après le repas ?")
        with self.captureOnCommitCallbacks(execute=True):
            notifier_reponse(question)
        self.assertEqual(self.envoyer.call_args.args[1], "Un pharmacien vous a répondu")

    def test_autre_appareil_non_prevenu(self):
        r = Reservation.objects.create(client_id=uuid.uuid4(), nom="Autre", telephone="+243990000002",
                                       pharmacie=self.pharmacie, medicament=self.med)
        with self.captureOnCommitCallbacks(execute=True):
            r.changer_statut(Reservation.Statut.ACCEPTEE)
        self.envoyer.assert_not_called()

    @override_settings(FIREBASE_COMPTE_SERVICE="")
    def test_sans_firebase_rien_n_est_envoye(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.reservation().changer_statut(Reservation.Statut.ACCEPTEE)
        self.envoyer.assert_not_called()


@override_settings(FIREBASE_COMPTE_SERVICE=COMPTE)
class FcmTests(TestCase):
    def setUp(self):
        acces = mock.patch("notifications.fcm._jeton_acces", return_value="acces")
        acces.start()
        self.addCleanup(acces.stop)

    def erreur(self, code, detail):
        import io
        import urllib.error

        return urllib.error.HTTPError("url", code, "x", {}, io.BytesIO(detail.encode()))

    def test_message_envoye_au_bon_projet(self):
        with mock.patch("notifications.fcm._poster") as poster:
            fcm.envoyer("fcm-1", "Titre", "Corps", {"id": 3})
        url, corps, entetes = poster.call_args.args
        self.assertEqual(url, "https://fcm.googleapis.com/v1/projects/dawa-test/messages:send")
        message = json.loads(corps)["message"]
        self.assertEqual(message["token"], "fcm-1")
        self.assertEqual(message["data"], {"id": "3"})  # FCM n'accepte que des chaînes
        self.assertEqual(entetes["Authorization"], "Bearer acces")

    def test_telephone_desinstalle(self):
        with mock.patch("notifications.fcm._poster", side_effect=self.erreur(404, '{"status": "NOT_FOUND"}')):
            with self.assertRaises(fcm.JetonPerime):
                fcm.envoyer("fcm-1", "T", "C")

    def test_autre_erreur_journalisee(self):
        with mock.patch("notifications.fcm._poster", side_effect=self.erreur(500, "panne")),                 self.assertLogs("notifications.fcm", "WARNING"):
            fcm.envoyer("fcm-1", "T", "C")
