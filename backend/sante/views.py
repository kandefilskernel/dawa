from django.contrib.gis.db.models.functions import Distance
from rest_framework import viewsets

from pharmacies.geo import position_depuis_requete

from .models import Etablissement
from .serializers import EtablissementSerializer


class EtablissementViewSet(viewsets.ReadOnlyModelViewSet):
    """Annuaire santé. `?type=hopital`, `?urgences=1`, `?lat=&lng=` pour trier par distance."""

    serializer_class = EtablissementSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Etablissement.objects.filter(est_valide=True)
        params = self.request.query_params
        if params.get("type"):
            qs = qs.filter(type=params["type"])
        if params.get("urgences") == "1":
            qs = qs.filter(urgences_24h=True)
        position = position_depuis_requete(self.request)
        if position is not None:
            qs = qs.annotate(distance=Distance("position", position)).order_by("distance")
        return qs
