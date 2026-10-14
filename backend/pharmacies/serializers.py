from rest_framework import serializers

from .models import Pharmacie


def contexte_pharmacies():
    """Garde et livraison calculées en 2 requêtes pour toute une liste, au lieu d'une par pharmacie."""
    return {
        "ids_garde": set(Pharmacie.objects.de_garde().values_list("id", flat=True)),
        "ids_livraison": set(Pharmacie.objects.avec_livraison().values_list("id", flat=True)),
    }


class PharmacieSerializer(serializers.ModelSerializer):
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()
    de_garde = serializers.SerializerMethodField()
    livraison = serializers.SerializerMethodField()

    class Meta:
        model = Pharmacie
        fields = [
            "id", "nom", "adresse", "quartier", "commune", "telephone", "whatsapp",
            "horaires", "lat", "lng", "distance_km", "de_garde", "livraison",
        ]

    def get_lat(self, obj):
        return obj.position.y

    def get_lng(self, obj):
        return obj.position.x

    def get_distance_km(self, obj):
        distance = getattr(obj, "distance", None)
        return round(distance.km, 2) if distance is not None else None

    def get_livraison(self, obj):
        ids = self.context.get("ids_livraison")
        if ids is not None:
            return obj.id in ids
        return obj.livreurs.filter(actif=True).exists()

    def get_de_garde(self, obj):
        ids_garde = self.context.get("ids_garde")
        return obj.id in ids_garde if ids_garde is not None else None
