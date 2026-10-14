from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .client import client_id
from .jetons import emettre_jeton


class JetonAppareilView(APIView):
    """
    POST /api/appareil/jeton/
    - sans en-tête : premier lancement, nouvel identifiant d'appareil ;
    - avec `Authorization: Bearer <jeton valide>` : renouvellement, même identifiant.
    Un jeton expiré ou falsifié est refusé (401) : l'app redemande alors un nouveau jeton.
    """

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "jeton_appareil"

    def post(self, request):
        renouvellement = "Authorization" in request.headers or "X-Client-Id" in request.headers
        appareil = client_id(request) if renouvellement else None
        return Response({"jeton": emettre_jeton(appareil)}, status=200 if renouvellement else 201)
