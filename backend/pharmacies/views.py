from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from catalogue.search import rechercher_medicaments
from stock.serializers import StockPharmacieSerializer

from .geo import position_depuis_requete, rayon_depuis_requete
from .models import Pharmacie
from .serializers import PharmacieSerializer, contexte_pharmacies
from .trajets import itineraire, mode_depuis


class PharmacieViewSet(viewsets.ReadOnlyModelViewSet):
    """Pharmacies validées. Avec `?lat=&lng=` : triées par distance dans `?rayon=` km."""

    serializer_class = PharmacieSerializer

    def get_queryset(self):
        qs = Pharmacie.objects.visibles()
        position = position_depuis_requete(self.request)
        if position is not None:
            qs = (
                qs.filter(position__dwithin=(position, D(km=rayon_depuis_requete(self.request))))
                .annotate(distance=Distance("position", position))
                .order_by("distance")
            )
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update(contexte_pharmacies())
        return context

    @action(detail=False)
    def garde(self, request):
        """Pharmacies de garde en ce moment (sans limite de rayon)."""
        qs = Pharmacie.objects.visibles().de_garde()
        position = position_depuis_requete(request)
        if position is not None:
            qs = qs.annotate(distance=Distance("position", position)).order_by("distance")
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True)
    def stock(self, request, pk=None):
        """Produits disponibles dans cette pharmacie. `?q=` pour filtrer."""
        pharmacie = self.get_object()
        stocks = pharmacie.stocks.filter(disponible=True).select_related("medicament")
        q = request.query_params.get("q", "").strip()
        if len(q) >= 2:
            stocks = stocks.filter(medicament__in=rechercher_medicaments(q))
        stocks = stocks.order_by("medicament__nom_commercial")
        return Response(StockPharmacieSerializer(stocks, many=True, context={"request": request}).data)


class ItineraireView(APIView):
    """
    GET /api/itineraire/?lat=..&lng=..&vers_lat=..&vers_lng=..&mode=moto

    Tracé du trajet par la route (liste de points [lat, lng]), distance et durée.
    Sans serveur de routage : ligne droite et durée estimée (`source` = "estimation").
    """

    def get(self, request):
        depart = position_depuis_requete(request)
        try:
            arrivee = (float(request.query_params["vers_lat"]), float(request.query_params["vers_lng"]))
        except (KeyError, ValueError):
            arrivee = None
        if depart is None or arrivee is None or not (-90 <= arrivee[0] <= 90 and -180 <= arrivee[1] <= 180):
            raise ValidationError({"position": "lat, lng, vers_lat et vers_lng sont obligatoires."})
        mode = mode_depuis(request.query_params.get("mode"))
        return Response({"mode": mode, **itineraire((depart.y, depart.x), arrivee, mode)})
