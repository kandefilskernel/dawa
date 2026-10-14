from rest_framework import mixins, serializers, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from catalogue.images import preparer_photo
from catalogue.models import Medicament
from catalogue.serializers import MedicamentSerializer
from config.client import client_id
from pharmacies.models import Pharmacie

from .models import Lot, Signalement, normaliser_lot

MESSAGES = {
    "conforme": "Ce lot est enregistré comme conforme.",
    "expire": "Ce lot est connu, mais sa date d'expiration est dépassée : ne l'utilisez pas.",
    "rappele": "Ce lot a fait l'objet d'un rappel : ne l'utilisez pas et rapportez-le à votre pharmacie.",
    "contrefait": "Ce lot est signalé comme contrefait : ne l'utilisez pas et signalez-nous où vous l'avez acheté.",
    "inconnu": (
        "Ce numéro de lot n'est pas dans notre base. Cela ne veut pas dire que le produit est faux : "
        "notre base est encore incomplète. Vérifiez l'emballage et demandez conseil à votre pharmacien."
    ),
}


class VerificationView(APIView):
    """GET /api/verification/?lot=AB123[&medicament=12] — vérifie un numéro de lot."""

    def get(self, request):
        numero = normaliser_lot(request.query_params.get("lot", ""))
        if len(numero) < 3:
            raise ValidationError({"lot": "Saisissez le numéro de lot imprimé sur la boîte (au moins 3 caractères)."})
        lots = Lot.objects.filter(numero_normalise=numero).select_related("medicament")
        if request.query_params.get("medicament"):
            lots = lots.filter(medicament_id=request.query_params["medicament"])
        # Si plusieurs produits partagent ce numéro, le statut le plus grave l'emporte.
        gravite = {Lot.Statut.CONTREFAIT: 0, Lot.Statut.RAPPELE: 1, Lot.Statut.CONFORME: 2}
        lot = min(lots, key=lambda l: gravite[l.statut], default=None)

        if lot is None:
            resultat = "inconnu"
        elif lot.statut == Lot.Statut.CONFORME and lot.est_expire:
            resultat = "expire"
        else:
            resultat = lot.statut

        return Response({
            "resultat": resultat,
            "message": MESSAGES[resultat],
            "lot": None if lot is None else {
                "numero": lot.numero,
                "fabricant": lot.fabricant,
                "date_expiration": lot.date_expiration,
                "note": lot.note,
                "medicament": MedicamentSerializer(lot.medicament, context={"request": request}).data,
            },
        })


class SignalementSerializer(serializers.ModelSerializer):
    medicament_id = serializers.PrimaryKeyRelatedField(
        queryset=Medicament.objects.all(), source="medicament", required=False, allow_null=True
    )
    pharmacie_id = serializers.PrimaryKeyRelatedField(
        queryset=Pharmacie.objects.all(), source="pharmacie", required=False, allow_null=True
    )

    class Meta:
        model = Signalement
        fields = ["id", "medicament_id", "numero_lot", "pharmacie_id", "lieu_achat", "description",
                  "photo", "telephone", "cree_le", "traite", "suite_donnee"]
        read_only_fields = ["cree_le", "traite", "suite_donnee"]
        extra_kwargs = {"photo": {"required": False}}

    def validate_description(self, valeur):
        if len(valeur.strip()) < 10:
            raise serializers.ValidationError("Décrivez le problème en quelques mots (10 caractères minimum).")
        return valeur.strip()

    def create(self, validated_data):
        photo = validated_data.pop("photo", None)
        signalement = Signalement(client_id=self.context["client_id"], **validated_data)
        if photo:
            signalement.photo = preparer_photo(photo, f"signalement-{signalement.client_id.hex[:8]}")
        signalement.save()
        return signalement


class SignalementViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """Signalements de produits suspects de l'appareil (X-Client-Id)."""

    serializer_class = SignalementSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = None

    def get_queryset(self):
        return Signalement.objects.filter(client_id=client_id(self.request))

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == "create":
            context["client_id"] = client_id(self.request)
        return context
