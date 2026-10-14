"""
Jetons d'appareil signés en RSA (JWT RS256).

Le serveur signe avec sa clé privée ; personne d'autre ne peut fabriquer ni modifier un jeton.
Le jeton porte l'identifiant anonyme de l'appareil (`sub`), qui relie un téléphone
à ses réservations, alertes, questions et signalements.
"""
import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

ALGORITHME = "RS256"
EMETTEUR = "dawa"
AUDIENCE = "dawa-app"
TAILLE_CLE = 3072


class JetonInvalide(Exception):
    pass


def generer_cle_privee():
    return rsa.generate_private_key(public_exponent=65537, key_size=TAILLE_CLE)


def cle_en_pem(cle):
    return cle.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


@lru_cache(maxsize=1)
def _cles():
    """(clé privée, clé publique, identifiant de clé). Chargée une fois par processus."""
    pem = settings.JWT_CLE_PRIVEE
    if not pem and settings.JWT_CLE_PRIVEE_FICHIER.exists():
        pem = settings.JWT_CLE_PRIVEE_FICHIER.read_text()
    if pem:
        cle = serialization.load_pem_private_key(pem.encode(), password=None)
    elif settings.DEBUG or settings.TESTS:
        # Développement sans clé : clé temporaire, les jetons sont perdus au redémarrage.
        logger.warning("Aucune clé RSA configurée : clé temporaire (lancez `manage.py generer_cle_rsa`).")
        cle = generer_cle_privee()
    else:
        raise ImproperlyConfigured("JWT_CLE_PRIVEE ou JWT_CLE_PRIVEE_FICHIER est obligatoire en production.")

    if cle.key_size < 2048:
        raise ImproperlyConfigured("La clé RSA doit faire au moins 2048 bits.")
    publique = cle.public_key()
    der = publique.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return cle, publique, hashlib.sha256(der).hexdigest()[:16]


def emettre_jeton(client_id=None):
    """Jeton signé pour l'appareil `client_id` (nouvel identifiant si absent)."""
    cle, _, kid = _cles()
    maintenant = datetime.now(timezone.utc)
    charge = {
        "sub": str(client_id or uuid.uuid4()),
        "iss": EMETTEUR,
        "aud": AUDIENCE,
        "iat": maintenant,
        "exp": maintenant + timedelta(days=settings.JWT_DUREE_JOURS),
    }
    return jwt.encode(charge, cle, algorithm=ALGORITHME, headers={"kid": kid})


def lire_jeton(jeton):
    """Vérifie la signature RSA, l'émetteur, l'audience et l'expiration. Renvoie l'UUID de l'appareil."""
    _, publique, _ = _cles()
    try:
        charge = jwt.decode(
            jeton, publique,
            algorithms=[ALGORITHME],  # liste fermée : refuse « none » et HS256 forgé avec la clé publique
            issuer=EMETTEUR, audience=AUDIENCE,
            options={"require": ["sub", "iat", "exp", "iss", "aud"]},
        )
        return uuid.UUID(charge["sub"])
    except jwt.ExpiredSignatureError:
        raise JetonInvalide("Jeton expiré.")
    except (jwt.InvalidTokenError, ValueError):
        raise JetonInvalide("Jeton invalide.")


def entete_authorization(client_id):
    """Valeur de l'en-tête Authorization pour un appareil (utile aux tests)."""
    return f"Bearer {emettre_jeton(client_id)}"
