import hmac

from django.conf import settings
from rest_framework.exceptions import NotAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .commandes import pharmacie_par_numero, traiter_message
from .models import MessageEntrant


class MessageEntrantView(APIView):
    """
    POST /api/messagerie/entrant/ — webhook du fournisseur SMS / WhatsApp.

    En-tête obligatoire : X-Dawa-Jeton (= MESSAGERIE_JETON). Corps JSON ou formulaire :
    {"de": "+243...", "texte": "DISPO doliprane 4500", "canal": "sms"}
    (les champs « from »/« text » d'Africa's Talking et « From »/« Body » de Twilio sont aussi acceptés).
    Réponse : {"reponse": "..."} — texte à renvoyer à l'expéditeur.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        jeton = settings.MESSAGERIE_JETON
        if not jeton or not hmac.compare_digest(request.headers.get("X-Dawa-Jeton", ""), jeton):
            raise NotAuthenticated("Jeton de messagerie invalide.")

        donnees = request.data
        expediteur = str(donnees.get("de") or donnees.get("from") or donnees.get("From") or "")[:30]
        texte = str(donnees.get("texte") or donnees.get("text") or donnees.get("Body") or "")[:1600]
        canal = "whatsapp" if expediteur.startswith("whatsapp:") else str(donnees.get("canal", "sms"))[:12]

        pharmacie = pharmacie_par_numero(expediteur)
        if pharmacie is None:
            reponse = "Dawa : ce numéro n'est rattaché à aucune pharmacie partenaire."
        else:
            reponse = traiter_message(pharmacie, texte)
        MessageEntrant.objects.create(
            canal=canal, expediteur=expediteur, texte=texte, pharmacie=pharmacie, reponse=reponse
        )
        return Response({"reponse": reponse})
