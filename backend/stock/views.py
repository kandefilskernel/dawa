from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db.models import F
from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from abonnements.models import Abonnement
from catalogue.models import Medicament
from catalogue.search import equivalents, rechercher_medicaments
from catalogue.serializers import MedicamentSerializer
from pharmacies.geo import position_depuis_requete, rayon_depuis_requete
from pharmacies.models import Pharmacie
from pharmacies.serializers import contexte_pharmacies

from config.client import client_id

from .models import AlerteStock, Recherche, Stock
from .serializers import AlerteSerializer, ResultatSerializer

MAX_RESULTATS = 50


class RechercheView(APIView):
    """
    GET /api/recherche/?medicament=12&lat=-11.66&lng=27.48&rayon=5   (choisi dans l'autocomplétion)
    GET /api/recherche/?q=amoxicilline&lat=-11.66&lng=27.48           (meilleure correspondance)

    Pharmacies qui ont le médicament ou un équivalent (même DCI, même forme) en stock.
    Triées par distance si une position est fournie, sinon par prix.
    """

    def get(self, request):
        terme, medicament = self._medicament_demande(request)
        medicaments = equivalents(medicament) if medicament else Medicament.objects.none()

        stocks = Stock.objects.filter(
            medicament__in=medicaments,
            disponible=True,
            pharmacie__in=Pharmacie.objects.visibles(),
        ).select_related("pharmacie", "medicament")

        position = position_depuis_requete(request)
        if position is not None:
            stocks = (
                stocks.filter(
                    pharmacie__position__dwithin=(position, D(km=rayon_depuis_requete(request)))
                )
                .annotate(distance=Distance("pharmacie__position", position))
                .order_by("distance", F("prix").asc(nulls_last=True))
            )
        else:
            stocks = stocks.order_by(F("prix").asc(nulls_last=True))

        resultats = list(stocks[:MAX_RESULTATS])
        ids_sponsor = Abonnement.objects.ids_pharmacies_sponsorisees()
        resultats = self._sponsorises_en_tete(resultats, ids_sponsor)
        self._journaliser(terme, medicament, position, len(resultats))

        return Response({
            "terme": terme,
            "medicament": MedicamentSerializer(medicament, context={"request": request}).data if medicament else None,
            "resultats": ResultatSerializer(
                resultats, many=True,
                context={**contexte_pharmacies(), "request": request}
            ).data,
        })

    @staticmethod
    def _sponsorises_en_tete(resultats, ids_sponsor):
        """Jusqu'à 2 pharmacies abonnées « Visibilité » (déjà dans le rayon) remontent en tête."""
        en_tete, vus = [], set()
        for r in resultats:
            if r.pharmacie_id in ids_sponsor and r.pharmacie_id not in vus and len(vus) < settings.MAX_RESULTATS_SPONSORISES:
                en_tete.append(r)
                vus.add(r.pharmacie_id)
        r_sponsor = {id(r) for r in en_tete}
        for r in en_tete:
            r.sponsorise = True
        return en_tete + [r for r in resultats if id(r) not in r_sponsor]

    def _medicament_demande(self, request):
        identifiant = request.query_params.get("medicament")
        if identifiant:
            try:
                medicament = Medicament.objects.get(pk=int(identifiant))
            except (ValueError, Medicament.DoesNotExist):
                raise ValidationError({"medicament": "Médicament inconnu."})
            return medicament.nom_commercial, medicament
        terme = request.query_params.get("q", "").strip()
        if len(terme) < 2:
            raise ValidationError({"q": "Tapez au moins 2 caractères."})
        return terme, rechercher_medicaments(terme).first()

    def _journaliser(self, terme, medicament, position, nb_resultats):
        zone = None
        if position is not None:
            zone = Point(round(position.x, 2), round(position.y, 2), srid=4326)
        Recherche.objects.create(
            terme=terme[:150],
            medicament=medicament,
            zone=zone,
            nb_resultats=nb_resultats,
        )


class AlerteViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    """Alertes de disponibilité de l'appareil identifié par X-Client-Id."""

    serializer_class = AlerteSerializer
    pagination_class = None

    def get_queryset(self):
        return AlerteStock.objects.filter(client_id=client_id(self.request)).select_related(
            "medicament", "pharmacie"
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update(contexte_pharmacies())
        if self.action == "create":
            context["client_id"] = client_id(self.request)
        return context
