import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.hazmat.primitives import serialization
from django.test import TestCase, override_settings

from .jetons import AUDIENCE, EMETTEUR, _cles, emettre_jeton, generer_cle_privee, lire_jeton


def charge(client_id, **modifs):
    maintenant = datetime.now(timezone.utc)
    return {
        "sub": str(client_id), "iss": EMETTEUR, "aud": AUDIENCE,
        "iat": maintenant, "exp": maintenant + timedelta(days=1), **modifs,
    }


class JetonAppareilTests(TestCase):
    def reservations(self, **entetes):
        return self.client.get("/api/reservations/", headers=entetes)

    def test_premier_lancement_puis_appel_authentifie(self):
        r = self.client.post("/api/appareil/jeton/")
        self.assertEqual(r.status_code, 201)
        jeton = r.json()["jeton"]
        self.assertEqual(jwt.get_unverified_header(jeton)["alg"], "RS256")
        self.assertEqual(self.reservations(Authorization=f"Bearer {jeton}").status_code, 200)

    def test_renouvellement_garde_le_meme_appareil(self):
        appareil = uuid.uuid4()
        r = self.client.post("/api/appareil/jeton/", headers={"Authorization": f"Bearer {emettre_jeton(appareil)}"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(lire_jeton(r.json()["jeton"]), appareil)

    def test_sans_jeton_refuse(self):
        self.assertEqual(self.reservations().status_code, 401)

    def test_ancien_identifiant_non_signe_refuse_par_defaut(self):
        self.assertEqual(self.reservations(**{"X-Client-Id": str(uuid.uuid4())}).status_code, 401)

    @override_settings(ACCEPTER_ANCIEN_CLIENT_ID=True)
    def test_ancien_identifiant_accepte_pendant_la_transition(self):
        self.assertEqual(self.reservations(**{"X-Client-Id": str(uuid.uuid4())}).status_code, 200)

    def test_jeton_signe_par_une_autre_cle_refuse(self):
        faux = jwt.encode(charge(uuid.uuid4()), generer_cle_privee(), algorithm="RS256")
        self.assertEqual(self.reservations(Authorization=f"Bearer {faux}").status_code, 401)

    def test_jeton_modifie_refuse(self):
        entete, _, signature = emettre_jeton(uuid.uuid4()).split(".")
        autre = jwt.utils.base64url_encode(b'{"sub":"%s"}' % str(uuid.uuid4()).encode()).decode()
        self.assertEqual(self.reservations(Authorization=f"Bearer {entete}.{autre}.{signature}").status_code, 401)

    def test_algorithme_none_et_hs256_refuses(self):
        sans_signature = jwt.encode(charge(uuid.uuid4()), None, algorithm="none")
        # Attaque classique : signer en HMAC avec la clé publique, en espérant qu'elle serve de secret.
        _, publique, _ = _cles()
        pem = publique.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        b64 = lambda octets: jwt.utils.base64url_encode(octets).decode()
        corps = json.dumps({"sub": str(uuid.uuid4()), "iss": EMETTEUR, "aud": AUDIENCE, "iat": 0, "exp": 4102444800})
        entete = json.dumps({"alg": "HS256", "typ": "JWT"})
        signe = f"{b64(entete.encode())}.{b64(corps.encode())}"
        hs256 = f"{signe}.{b64(hmac.new(pem, signe.encode(), hashlib.sha256).digest())}"
        for jeton in (sans_signature, hs256):
            self.assertEqual(self.reservations(Authorization=f"Bearer {jeton}").status_code, 401)

    def test_jeton_expire_refuse(self):
        cle, _, _ = _cles()
        expire = jwt.encode(
            charge(uuid.uuid4(), exp=datetime.now(timezone.utc) - timedelta(seconds=1)), cle, algorithm="RS256"
        )
        r = self.reservations(Authorization=f"Bearer {expire}")
        self.assertEqual(r.status_code, 401)
        self.assertIn("expiré", r.json()["detail"])

    def test_mauvaise_audience_refusee(self):
        cle, _, _ = _cles()
        autre_usage = jwt.encode(charge(uuid.uuid4(), aud="autre"), cle, algorithm="RS256")
        self.assertEqual(self.reservations(Authorization=f"Bearer {autre_usage}").status_code, 401)
