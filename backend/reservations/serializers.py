from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.utils import timezone
from rest_framework import serializers

from catalogue.models import Medicament
from catalogue.serializers import MedicamentSerializer
from pharmacies.models import Pharmacie
from pharmacies.serializers import PharmacieSerializer
from stock.models import Stock

from .models import MAX_RESERVATIONS_ACTIVES, Reservation, frais_livraison


class ReservationSerializer(serializers.ModelSerializer):
    pharmacie = PharmacieSerializer(read_only=True)
    medicament = MedicamentSerializer(read_only=True)
    pharmacie_id = serializers.PrimaryKeyRelatedField(
        queryset=Pharmacie.objects.visibles(), source="pharmacie", write_only=True
    )
    medicament_id = serializers.PrimaryKeyRelatedField(
        queryset=Medicament.objects.all(), source="medicament", write_only=True
    )
    statut = serializers.CharField(source="statut_effectif", read_only=True)
    statut_libelle = serializers.SerializerMethodField()
    prix_unitaire = serializers.SerializerMethodField()
    lat_livraison = serializers.FloatField(write_only=True, required=False, min_value=-90, max_value=90)
    lng_livraison = serializers.FloatField(write_only=True, required=False, min_value=-180, max_value=180)
    livreur = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = [
            "id", "pharmacie", "medicament", "pharmacie_id", "medicament_id", "quantite",
            "nom", "telephone", "statut", "statut_libelle", "message_pharmacie",
            "prix_unitaire", "cree_le", "expire_le",
            "mode", "adresse_livraison", "lat_livraison", "lng_livraison", "frais_livraison", "livreur",
        ]
        read_only_fields = ["message_pharmacie", "cree_le", "expire_le", "frais_livraison"]

    def get_livreur(self, obj):
        if obj.livreur is None:
            return None
        return {"nom": obj.livreur.nom, "telephone": obj.livreur.telephone}

    def get_statut_libelle(self, obj):
        return Reservation.Statut(obj.statut_effectif).label

    def get_prix_unitaire(self, obj):
        prix = self.context.get("prix")
        if prix is not None:
            return prix.get((obj.pharmacie_id, obj.medicament_id))
        stock = Stock.objects.filter(pharmacie=obj.pharmacie, medicament=obj.medicament).first()
        return stock.prix if stock else None

    def validate_telephone(self, valeur):
        chiffres = "".join(c for c in valeur if c.isdigit() or c == "+")
        if len(chiffres.lstrip("+")) < 9:
            raise serializers.ValidationError("Numéro de téléphone invalide.")
        return chiffres

    def validate(self, data):
        stock = Stock.objects.filter(
            pharmacie=data["pharmacie"], medicament=data["medicament"], disponible=True
        ).first()
        if stock is None:
            raise serializers.ValidationError("Ce médicament n'est plus disponible dans cette pharmacie.")

        client = self.context["client_id"]
        actives = [
            r for r in Reservation.objects.filter(
                client_id=client, statut__in=Reservation.ACTIFS, expire_le__gt=timezone.now()
            )
        ]
        if len(actives) >= MAX_RESERVATIONS_ACTIVES:
            raise serializers.ValidationError(
                f"Vous avez déjà {MAX_RESERVATIONS_ACTIVES} réservations en cours."
            )
        if any(r.pharmacie_id == data["pharmacie"].id and r.medicament_id == data["medicament"].id
               for r in actives):
            raise serializers.ValidationError("Vous avez déjà réservé ce médicament dans cette pharmacie.")
        return self._valider_livraison(data)

    def _valider_livraison(self, data):
        lat, lng = data.pop("lat_livraison", None), data.pop("lng_livraison", None)
        if data.get("mode") != Reservation.Mode.LIVRAISON:
            data.pop("adresse_livraison", None)
            return data
        if not data["pharmacie"].livreurs.filter(actif=True).exists():
            raise serializers.ValidationError("Cette pharmacie ne livre pas encore. Choisissez le retrait.")
        if lat is None or lng is None or len(data.get("adresse_livraison", "").strip()) < 5:
            raise serializers.ValidationError("Indiquez l'adresse de livraison (avenue, numéro, repère).")
        position = Point(lng, lat, srid=4326)
        distance_km = devis_livraison(data["pharmacie"], position)["distance_km"]
        if distance_km > settings.LIVRAISON_DISTANCE_MAX_KM:
            raise serializers.ValidationError(
                f"Adresse trop éloignée ({distance_km:.1f} km) : livraison jusqu'à "
                f"{settings.LIVRAISON_DISTANCE_MAX_KM} km."
            )
        data["position_livraison"] = position
        data["frais_livraison"] = frais_livraison(distance_km)
        return data

    def create(self, validated_data):
        return Reservation.objects.create(client_id=self.context["client_id"], **validated_data)


def devis_livraison(pharmacie, position):
    distance = (
        type(pharmacie).objects.filter(pk=pharmacie.pk)
        .annotate(d=Distance("position", position)).values_list("d", flat=True).first()
    )
    distance_km = round(distance.km, 2)
    return {
        "distance_km": distance_km,
        "frais": frais_livraison(distance_km),
        "possible": distance_km <= settings.LIVRAISON_DISTANCE_MAX_KM
        and pharmacie.livreurs.filter(actif=True).exists(),
    }
