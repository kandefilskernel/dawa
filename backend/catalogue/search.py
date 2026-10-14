from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q
from django.db.models.functions import Greatest

from .models import Medicament

SEUIL_SIMILARITE = 0.3


def rechercher_medicaments(terme):
    """Recherche tolérante aux fautes et aux accents sur le nom commercial et la DCI."""
    terme = terme.strip()
    if not terme:
        return Medicament.objects.none()
    return (
        Medicament.objects.annotate(
            similarite=Greatest(
                TrigramSimilarity("nom_commercial", terme),
                TrigramSimilarity("dci", terme),
            )
        )
        .filter(
            Q(similarite__gte=SEUIL_SIMILARITE)
            | Q(nom_commercial__unaccent__icontains=terme)
            | Q(dci__unaccent__icontains=terme)
        )
        .order_by("-similarite", "nom_commercial")
    )


def equivalents(medicament):
    """Produits interchangeables : même DCI et même forme (ex. Doliprane 500 mg → Panadol 500 mg)."""
    return Medicament.objects.filter(dci__iexact=medicament.dci, forme=medicament.forme)
