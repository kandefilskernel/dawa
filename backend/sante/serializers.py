from rest_framework import serializers

from .models import Etablissement


class EtablissementSerializer(serializers.ModelSerializer):
    type_libelle = serializers.CharField(source="get_type_display", read_only=True)
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = Etablissement
        fields = [
            "id", "nom", "type", "type_libelle", "adresse", "quartier", "telephone",
            "urgences_24h", "services", "lat", "lng", "distance_km",
        ]

    def get_lat(self, obj):
        return obj.position.y

    def get_lng(self, obj):
        return obj.position.x

    def get_distance_km(self, obj):
        distance = getattr(obj, "distance", None)
        return round(distance.km, 2) if distance is not None else None
