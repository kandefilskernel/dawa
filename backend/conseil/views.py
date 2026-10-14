from rest_framework import mixins, serializers, viewsets

from catalogue.models import Medicament
from catalogue.serializers import MedicamentSerializer
from config.client import client_id

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
