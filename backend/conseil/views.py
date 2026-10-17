from django.core.cache import cache
from rest_framework import mixins, serializers, viewsets
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from catalogue.models import Medicament
from catalogue.serializers import MedicamentSerializer
from config.client import client_id
from pharmacies.serializers import contexte_pharmacies
from stock.serializers import ResultatSerializer

from .assistant import assistant_actif
from .choix import LONGUEUR_MAX, meilleur_choix
from .models import Question

MAX_QUESTIONS_EN_ATTENTE = 3


class QuestionSerializer(serializers.ModelSerializer):
    medicament = MedicamentSerializer(read_only=True)
    medicament_id = serializers.PrimaryKeyRelatedField(
        queryset=Medicament.objects.all(), source="medicament", write_only=True, required=False, allow_null=True
    )
    statut_libelle = serializers.CharField(source="get_statut_display", read_only=True)
    repondu_par = serializers.CharField(source="repondu_par.nom", read_only=True, default=None)

    class Meta:
        model = Question
        fields = ["id", "texte", "medicament", "medicament_id", "statut", "statut_libelle",
                  "reponse", "repondu_par", "cree_le", "repondu_le"]
        read_only_fields = ["statut", "reponse", "cree_le", "repondu_le"]

    def validate_texte(self, valeur):
        valeur = valeur.strip()
        if len(valeur) < 10:
            raise serializers.ValidationError("Posez votre question en une phrase (10 caractères minimum).")
        return valeur

    def validate(self, data):
        en_attente = Question.objects.filter(
            client_id=self.context["client_id"], statut=Question.Statut.EN_ATTENTE
        ).count()
        if en_attente >= MAX_QUESTIONS_EN_ATTENTE:
            raise serializers.ValidationError(
                "Vous avez déjà des questions en attente. Un pharmacien va vous répondre."
            )
        return data

    def create(self, validated_data):
        return Question.objects.create(client_id=self.context["client_id"], **validated_data)


class QuestionViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """Questions de l'appareil (X-Client-Id) aux pharmaciens partenaires."""

    serializer_class = QuestionSerializer
    pagination_class = None

    def get_queryset(self):
        return Question.objects.filter(client_id=client_id(self.request)).select_related(
            "medicament", "repondu_par"
        )[:30]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == "create":
            context["client_id"] = client_id(self.request)
        return context


class AssistantChoixView(APIView):
    """
    POST /api/assistant/ {"message": "J'ai besoin d'Amoxicilline, je suis à pied", "lat": .., "lng": ..}

    Meilleur choix pour obtenir le médicament vite : pharmacie, délai, réserver / y aller / se faire livrer.
    Rédigé par l'IA si elle est configurée (`source` = "ia"), sinon par une règle simple ("regles").
    """

    MESSAGES_PAR_HEURE = 20

    def get(self, request):
        return Response({"ia_active": assistant_actif()})

    def post(self, request):
        appareil = client_id(request)
        message = str(request.data.get("message", "")).strip()
        if len(message) < 3:
            raise ValidationError({"message": "Écrivez le médicament dont vous avez besoin."})
        try:
            lat, lng = float(request.data["lat"]), float(request.data["lng"])
        except (KeyError, TypeError, ValueError):
            raise ValidationError({"position": "lat et lng sont obligatoires."})
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            raise ValidationError({"position": "Coordonnées hors limites."})
        cle = f"assistant:{appareil}"
        if not cache.add(cle, 1, 3600) and cache.incr(cle) > self.MESSAGES_PAR_HEURE:
            raise Throttled(detail="Trop de messages. Réessayez dans une heure.")

        choix = meilleur_choix(message[:LONGUEUR_MAX], (lat, lng))
        contexte = {**contexte_pharmacies(), "request": request}

        def option(s):
            return {**ResultatSerializer(s, context=contexte).data, "livraison": s.livraison}

        return Response({
            "reponse": choix.reponse,
            "source": choix.source,
            "situation": choix.situation,
            "medicament": MedicamentSerializer(choix.medicament, context=contexte).data if choix.medicament else None,
            "recommandation": option(choix.option) if choix.option is not None else None,
            "action": choix.action,
            "mode": choix.mode,
            "orienter_medecin": choix.orienter_medecin,
            "autres": [option(s) for s in choix.autres],
        })
