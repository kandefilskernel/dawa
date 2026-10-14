from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from config.client import client_id
from pharmacies.geo import position_depuis_requete
from pharmacies.models import Pharmacie
from pharmacies.serializers import contexte_pharmacies
from stock.models import Stock

from .models import Reservation
from .serializers import ReservationSerializer, devis_livraison


class ReservationViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """Réservations de l'appareil identifié par l'en-tête X-Client-Id."""

    serializer_class = ReservationSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            Reservation.objects.filter(client_id=client_id(self.request))
            .select_related("pharmacie", "medicament", "livreur")[:50]
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update(contexte_pharmacies())
        if self.action == "list":
            context["prix"] = self._prix_des_reservations()
        if self.action == "create":
            context["client_id"] = client_id(self.request)
        return context

    def _prix_des_reservations(self):
        """Prix unitaires de toute la liste en une requête (clé : pharmacie, médicament)."""
        paires = [(r.pharmacie_id, r.medicament_id) for r in self.get_queryset()]
        stocks = Stock.objects.filter(
            pharmacie_id__in={p for p, _ in paires}, medicament_id__in={m for _, m in paires}
        ).values_list("pharmacie_id", "medicament_id", "prix")
        return {(p, m): prix for p, m, prix in stocks}

    def get_object(self):
        return Reservation.objects.select_related("pharmacie", "medicament", "livreur").get(
            pk=self.kwargs["pk"], client_id=client_id(self.request)
        )

    @action(detail=True, methods=["post"])
    def annuler(self, request, pk=None):
        try:
            reservation = self.get_object()
        except Reservation.DoesNotExist:
            raise ValidationError("Réservation introuvable.")
        if not reservation.est_active:
            raise ValidationError("Cette réservation n'est plus active.")
        reservation.statut = Reservation.Statut.ANNULEE
        reservation.save(update_fields=["statut"])
        return Response(self.get_serializer(reservation).data)


class DevisLivraisonView(APIView):
    """GET /api/livraison/devis/?pharmacie=3&lat=..&lng=.. — frais avant de réserver."""

    def get(self, request):
        position = position_depuis_requete(request)
        if position is None:
            raise ValidationError({"position": "lat et lng sont obligatoires."})
        try:
            pharmacie = Pharmacie.objects.visibles().get(pk=int(request.query_params.get("pharmacie", "")))
        except (ValueError, Pharmacie.DoesNotExist):
            raise ValidationError({"pharmacie": "Pharmacie inconnue."})
        return Response(devis_livraison(pharmacie, position))
