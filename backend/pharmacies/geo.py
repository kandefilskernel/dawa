from django.contrib.gis.geos import Point
from rest_framework.exceptions import ValidationError

RAYON_DEFAUT_KM = 5
RAYON_MAX_KM = 50


def position_depuis_requete(request):
    """Lit `lat`/`lng` dans la requête. Renvoie un Point ou None si absents."""
    lat = request.query_params.get("lat")
    lng = request.query_params.get("lng")
    if lat is None and lng is None:
        return None
    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError):
        raise ValidationError("lat et lng doivent être des nombres.")
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ValidationError("Coordonnées hors limites.")
    return Point(lng, lat, srid=4326)


def rayon_depuis_requete(request):
    try:
        rayon = float(request.query_params.get("rayon", RAYON_DEFAUT_KM))
    except ValueError:
        raise ValidationError("rayon doit être un nombre (km).")
    return min(max(rayon, 0.1), RAYON_MAX_KM)
