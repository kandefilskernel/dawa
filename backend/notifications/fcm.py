"""
Envoi vers Firebase Cloud Messaging (API HTTP v1), sans bibliothèque Google :
le compte de service signe un JWT (RS256) échangé contre un jeton d'accès OAuth2.

Sans compte de service configuré, `actif()` est faux et rien n'est envoyé.
"""
import json
import logging
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import jwt
from django.conf import settings

logger = logging.getLogger(__name__)

URL_JETON = "https://oauth2.googleapis.com/token"
PORTEE = "https://www.googleapis.com/auth/firebase.messaging"
DELAI = 10  # secondes par appel réseau

_verrou = threading.Lock()
_acces = {"jeton": None, "expire": 0.0}


class JetonPerime(Exception):
    """Le téléphone a désinstallé l'app ou le jeton FCM n'est plus valable : on l'oublie."""


def compte_de_service():
    if settings.FIREBASE_COMPTE_SERVICE:
        return json.loads(settings.FIREBASE_COMPTE_SERVICE)
    if settings.FIREBASE_COMPTE_SERVICE_FICHIER.exists():
        return json.loads(settings.FIREBASE_COMPTE_SERVICE_FICHIER.read_text(encoding="utf-8"))
    return None


def actif():
    return compte_de_service() is not None


def _poster(url, corps, entetes):
    requete = urllib.request.Request(url, data=corps, headers=entetes, method="POST")
    with urllib.request.urlopen(requete, timeout=DELAI) as reponse:
        return json.load(reponse)


def _jeton_acces(compte):
    """Jeton OAuth2 valable 1 h, réutilisé jusqu'à 5 min avant son expiration."""
    with _verrou:
        if _acces["jeton"] and time.time() < _acces["expire"] - 300:
            return _acces["jeton"]
        maintenant = int(time.time())
        assertion = jwt.encode(
            {"iss": compte["client_email"], "scope": PORTEE, "aud": URL_JETON,
             "iat": maintenant, "exp": maintenant + 3600},
            compte["private_key"], algorithm="RS256",
        )
        corps = urllib.parse.urlencode({
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion,
        }).encode()
        donnees = _poster(URL_JETON, corps, {"Content-Type": "application/x-www-form-urlencoded"})
        _acces["jeton"] = donnees["access_token"]
        _acces["expire"] = time.time() + donnees.get("expires_in", 3600)
        return _acces["jeton"]


def envoyer(jeton_fcm, titre, corps, donnees=None):
    """Envoie une notification à un téléphone. Lève JetonPerime si le téléphone n'existe plus."""
    compte = compte_de_service()
    if compte is None:
        return
    message = {
        "message": {
            "token": jeton_fcm,
            "notification": {"title": titre, "body": corps},
            "data": {cle: str(valeur) for cle, valeur in (donnees or {}).items()},
            "android": {"priority": "high", "notification": {"channel_id": "dawa_suivi"}},
        }
    }
    url = f"https://fcm.googleapis.com/v1/projects/{compte['project_id']}/messages:send"
    try:
        _poster(url, json.dumps(message).encode(), {
            "Authorization": f"Bearer {_jeton_acces(compte)}",
            "Content-Type": "application/json; charset=utf-8",
        })
    except urllib.error.HTTPError as erreur:
        detail = erreur.read().decode(errors="replace")
        if erreur.code == 404 or "UNREGISTERED" in detail or (erreur.code == 400 and "registration token" in detail):
            raise JetonPerime from erreur
        logger.warning("FCM a refusé la notification (%s) : %s", erreur.code, detail[:300])
    except (urllib.error.URLError, TimeoutError) as erreur:
        logger.warning("FCM injoignable : %s", erreur)
