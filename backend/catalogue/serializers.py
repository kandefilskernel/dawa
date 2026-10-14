from rest_framework import serializers

from .models import Medicament


class MedicamentSerializer(serializers.ModelSerializer):
    forme_libelle = serializers.CharField(source="get_forme_display", read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Medicament
        fields = [
            "id", "dci", "nom_commercial", "dosage", "forme", "forme_libelle",
            "code_barres", "ordonnance_requise", "image", "image_est_illustration",
            "image_credit",
        ]

    def get_image(self, obj):
        if not obj.image:
            return None
        requete = self.context.get("request")
        return requete.build_absolute_uri(obj.image.url) if requete else obj.image.url
