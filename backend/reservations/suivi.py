"""
Suivi d'une livraison : où est le livreur et quand arrive-t-il ?

L'heure d'arrivée est recalculée à chaque position, avec la vitesse réellement mesurée sur les
dernières minutes (distance parcourue ÷ temps). Arrêté (feu, embouteillage) ou trop peu de points :
on prend la vitesse habituelle d'une moto à Lubumbashi.
"""
from datetime import timedelta

from django.utils import timezone

from pharmacies.trajets import VITESSES_KMH, distance_route_km, distance_vol_oiseau_km

FENETRE_VITESSE = timedelta(minutes=5)
DUREE_MIN_MESURE = timedelta(seconds=30)
VITESSE_MIN_KMH = 5.0
VITESSE_MAX_KMH = 60.0
POSITION_ANCIENNE = timedelta(minutes=2)
POINTS_TRACE = 60


def _latlng(point):
    return point.y, point.x


def vitesse_mesuree_kmh(positions):
    """Vitesse moyenne sur les dernières minutes, ou None si on ne peut pas la mesurer."""
    if len(positions) < 2:
        return None
    recentes = [p for p in positions if p.recue_le >= positions[-1].recue_le - FENETRE_VITESSE]
    if len(recentes) < 2:
        return None
    duree = recentes[-1].recue_le - recentes[0].recue_le
    if duree < DUREE_MIN_MESURE:
        return None
    distance = sum(
        distance_vol_oiseau_km(*_latlng(a.position), *_latlng(b.position)) for a, b in zip(recentes, recentes[1:])
    )
    vitesse = distance / (duree.total_seconds() / 3600)
    if vitesse < VITESSE_MIN_KMH:
        return None
    return min(vitesse, VITESSE_MAX_KMH)


def suivi(reservation):
    positions = list(reservation.positions.order_by("-recue_le")[:POINTS_TRACE])[::-1]
    destination = reservation.position_livraison
    pharmacie = reservation.pharmacie.position
    donnees = {
        "statut": reservation.statut_effectif,
        "livreur": {"nom": reservation.livreur.nom, "telephone": reservation.livreur.telephone}
        if reservation.livreur else None,
        "pharmacie": {"lat": pharmacie.y, "lng": pharmacie.x, "nom": reservation.pharmacie.nom},
        "destination": {"lat": destination.y, "lng": destination.x} if destination else None,
        "position": None,
        "trace": [list(_latlng(p.position)) for p in positions],
    }
    if not positions or destination is None or reservation.statut_effectif != reservation.Statut.EN_LIVRAISON:
        return donnees

    derniere = positions[-1]
    mesuree = vitesse_mesuree_kmh(positions)
    vitesse = mesuree or VITESSES_KMH["moto"]
    distance, source = distance_route_km(_latlng(derniere.position), _latlng(destination), "moto")
    minutes = distance / vitesse * 60
    # La moto a continué de rouler depuis la dernière position reçue.
    arrivee = max(derniere.recue_le + timedelta(minutes=minutes), timezone.now())
    donnees.update({
        "position": {"lat": derniere.position.y, "lng": derniere.position.x, "recue_le": derniere.recue_le,
                     "ancienne": timezone.now() - derniere.recue_le > POSITION_ANCIENNE},
        "distance_restante_km": round(distance, 2),
        "distance_source": source,
        "vitesse_kmh": round(vitesse, 1),
        "vitesse_mesuree": mesuree is not None,
        "minutes_restantes": max(1, round((arrivee - timezone.now()).total_seconds() / 60)),
        "arrivee_estimee": arrivee,
    })
    return donnees
