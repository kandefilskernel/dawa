import uuid

from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated

from .jetons import JetonInvalide, lire_jeton

ENTETE_ANCIEN = "X-Client-Id"


def client_id(request):
    """
    Identifiant anonyme de l'appareil, lu dans le jeton signé RSA (`Authorization: Bearer …`)
    obtenu via POST /api/appareil/jeton/. Il relie un téléphone à ses réservations et alertes.
    """
    autorisation = request.headers.get("Authorization", "")
    if autorisation.startswith("Bearer "):
        try:
            return lire_jeton(autorisation.removeprefix("Bearer ").strip())
        except JetonInvalide as erreur:
            raise AuthenticationFailed(str(erreur))

    if settings.ACCEPTER_ANCIEN_CLIENT_ID:
        # Transition : anciennes versions de l'app, identifiant non signé.
        try:
            return uuid.UUID(request.headers.get(ENTETE_ANCIEN, ""))
        except ValueError:
            pass
    raise NotAuthenticated("Jeton d'appareil manquant (POST /api/appareil/jeton/).")
