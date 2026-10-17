from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from config.client import client_id

from .models import AppareilPush


class EnregistrementSerializer(serializers.Serializer):
    jeton = serializers.CharField(max_length=512)
    langue = serializers.ChoiceField(choices=AppareilPush.Langue.choices, default=AppareilPush.Langue.FR)


class AppareilPushView(APIView):
    """
    POST /api/appareil/notifications/ {"jeton": "<jeton FCM>", "langue": "fr"} — le téléphone accepte
    les notifications (à renvoyer quand Firebase change le jeton ou que la langue change).
    DELETE /api/appareil/notifications/ {"jeton": "…"} — il n'en veut plus.
    """

    def post(self, request):
        appareil = client_id(request)
        donnees = EnregistrementSerializer(data=request.data)
        donnees.is_valid(raise_exception=True)
        # Un jeton FCM appartient à un seul téléphone : s'il change d'appareil Uzima, on le rattache au nouveau.
        _, cree = AppareilPush.objects.update_or_create(
            jeton=donnees.validated_data["jeton"],
            defaults={"client_id": appareil, "langue": donnees.validated_data["langue"]},
        )
        return Response(status=status.HTTP_201_CREATED if cree else status.HTTP_200_OK)

    def delete(self, request):
        AppareilPush.objects.filter(client_id=client_id(request), jeton=request.data.get("jeton", "")).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
