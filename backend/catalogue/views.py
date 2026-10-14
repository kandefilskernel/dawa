from rest_framework import viewsets

from .models import Medicament
from .search import rechercher_medicaments
from .serializers import MedicamentSerializer


class MedicamentViewSet(viewsets.ReadOnlyModelViewSet):
    """Catalogue. `?q=` pour l'autocomplétion, `?code_barres=` pour le scan d'une boîte."""

    serializer_class = MedicamentSerializer

    def get_queryset(self):
        q = self.request.query_params.get("q")
        code = self.request.query_params.get("code_barres")
        if code:
            return Medicament.objects.filter(code_barres=code)
        if q:
            return rechercher_medicaments(q)
        return Medicament.objects.all()
