from django.contrib.gis.geos import Point
from rest_framework import serializers

from catalogue.models import Medicament

from catalogue.serializers import MedicamentSerializer
from pharmacies.serializers import PharmacieSerializer

from .models import AlerteStock, Stock


class ResultatSerializer(serializers.ModelSerializer):
    pharmacie = PharmacieSerializer()
    medicament = MedicamentSerializer()
    distance_km = serializers.SerializerMethodField()
    confirme = serializers.BooleanField(source="est_confirme")
    sponsorise = serializers.SerializerMethodField()

    class Meta:
        model = Stock
        fields = ["pharmacie", "medicament", "prix", "mis_a_jour_le", "confirme", "distance_km", "sponsorise"]

    def get_sponsorise(self, obj):
        return getattr(obj, "sponsorise", False)

    def get_distance_km(self, obj):
        distance = getattr(obj, "distance", None)
        return round(distance.km, 2) if distance is not None else None


class StockPharmacieSerializer(serializers.ModelSerializer):
    """Un produit disponible dans la fiche d'une pharmacie."""

    medicament = MedicamentSerializer()
    confirme = serializers.BooleanField(source="est_confirme")

    class Meta:
        model = Stock
        fields = ["medicament", "prix", "mis_a_jour_le", "confirme"]


class AlerteSerializer(serializers.ModelSerializer):
    medicament = MedicamentSerializer(read_only=True)
    medicament_id = serializers.PrimaryKeyRelatedField(
        queryset=Medicament.objects.all(), source="medicament", write_only=True
    )
    pharmacie = PharmacieSerializer(read_only=True)
    lat = serializers.FloatField(write_only=True, min_value=-90, max_value=90)
    lng = serializers.FloatField(write_only=True, min_value=-180, max_value=180)
    rayon_km = serializers.IntegerField(min_value=1, max_value=50, default=10)

    class Meta:
        model = AlerteStock
        fields = [
            "id", "medicament", "medicament_id", "lat", "lng", "rayon_km",
            "cree_le", "declenchee_le", "pharmacie",
        ]
        read_only_fields = ["cree_le", "declenchee_le"]

    def create(self, validated_data):
        lat, lng = validated_data.pop("lat"), validated_data.pop("lng")
        alerte, _ = AlerteStock.objects.update_or_create(
            client_id=self.context["client_id"],
            medicament=validated_data["medicament"],
            declenchee_le__isnull=True,
            defaults={"position": Point(lng, lat, srid=4326), "rayon_km": validated_data["rayon_km"]},
        )
        return alerte
