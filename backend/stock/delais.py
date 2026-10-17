"""
Délai pour obtenir un médicament dans chaque pharmacie : trajet par la route + attente de l'ouverture.

Une pharmacie de garde est considérée ouverte. Un stock non confirmé récemment risque d'être faux
(déplacement pour rien) : il est classé comme s'il était un peu plus loin, sans changer le délai affiché.
"""
from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D

from catalogue.search import equivalents
from pharmacies.horaires import etat
from pharmacies.models import Pharmacie
from pharmacies.serializers import contexte_pharmacies
from pharmacies.trajets import MODES, trajets
from reservations.models import frais_livraison

from .models import Stock

PENALITE_STOCK_NON_CONFIRME_MIN = 15


def acces_pharmacie(pharmacie, trajets_pharmacie, de_garde, moment=None):
    if de_garde:
        ouverte, ouvre_dans = True, 0
    else:
        ouverte, ouvre_dans = etat(pharmacie.horaires, moment)
    attente = ouvre_dans if ouverte is False else 0
    return {
        "ouverte": ouverte,
        "ouvre_dans_min": ouvre_dans if ouverte is False else None,
        "trajets": {mode: t.en_dict() for mode, t in trajets_pharmacie.items()},
        # None : fermée sans ouverture connue dans la semaine.
        "delai_min": {
            mode: (t.minutes + attente) if attente is not None else None
            for mode, t in trajets_pharmacie.items()
        },
    }


def score(resultat, mode):
    delai = resultat.acces["delai_min"][mode]
    if delai is None:
        return float("inf")
    return delai + (0 if resultat.est_confirme else PENALITE_STOCK_NON_CONFIRME_MIN)


def classer_par_delai(resultats, depart, mode, ids_garde, moment=None):
    """Ajoute `acces` à chaque résultat (Stock) et trie du plus rapide au plus lent, puis par prix."""
    assert mode in MODES
    pharmacies = {r.pharmacie_id: r.pharmacie for r in resultats}
    ids = list(pharmacies)
    calcules = trajets(depart, [(pharmacies[i].position.y, pharmacies[i].position.x) for i in ids])
    acces = {
        i: acces_pharmacie(pharmacies[i], t, i in ids_garde, moment) for i, t in zip(ids, calcules)
    }
    for r in resultats:
        r.acces = acces[r.pharmacie_id]
    return sorted(resultats, key=lambda r: (score(r, mode), r.prix if r.prix is not None else 1 << 40))


# Livraison : temps de préparation à la pharmacie, puis trajet à moto jusqu'au patient.
PREPARATION_LIVRAISON_MIN = 15


def options_rapides(medicament, depart, rayon_km=10, nombre=5, moment=None):
    """
    Les pharmacies les plus rapides pour obtenir ce médicament (ou un équivalent) depuis `depart`
    (lat, lng) : Stocks annotés de `acces`, triés pour la moto, avec `livraison` (possible, minutes, frais).
    """
    position = Point(depart[1], depart[0], srid=4326)
    stocks = list(
        Stock.objects.filter(
            medicament__in=equivalents(medicament), disponible=True, pharmacie__in=Pharmacie.objects.visibles(),
            pharmacie__position__dwithin=(position, D(km=rayon_km)),
        ).select_related("pharmacie", "medicament")
        .annotate(distance=Distance("pharmacie__position", position)).order_by("distance")[:50]
    )
    contexte = contexte_pharmacies()
    classes = classer_par_delai(stocks, depart, "moto", contexte["ids_garde"], moment)
    choisis, vus = [], set()
    for s in classes:  # une ligne par pharmacie (le premier produit est le plus rapide / le moins cher)
        if s.pharmacie_id in vus:
            continue
        vus.add(s.pharmacie_id)
        moto = s.acces["trajets"]["moto"]
        possible = s.pharmacie_id in contexte["ids_livraison"] and moto["distance_km"] <= settings.LIVRAISON_DISTANCE_MAX_KM
        delai_moto = s.acces["delai_min"]["moto"]
        s.de_garde = s.pharmacie_id in contexte["ids_garde"]
        s.livraison = {
            "possible": possible,
            "minutes": delai_moto + PREPARATION_LIVRAISON_MIN if possible and delai_moto is not None else None,
            "frais": frais_livraison(moto["distance_km"]) if possible else None,
        }
        choisis.append(s)
        if len(choisis) == nombre:
            break
    return choisis
