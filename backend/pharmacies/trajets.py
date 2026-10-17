"""
Temps de trajet par la route jusqu'aux pharmacies, à pied, en moto et en voiture.

Les distances par la route viennent d'un serveur OSRM (données OpenStreetMap). Le temps est ensuite
calculé avec une vitesse réaliste pour Lubumbashi (embouteillages, routes abîmées) plutôt qu'avec la
vitesse théorique d'OSRM, trop optimiste. Si le serveur ne répond pas vite, on estime :
distance à vol d'oiseau × facteur de détour ÷ vitesse.
"""
import hashlib
import json
import logging
import math
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache

journal = logging.getLogger(__name__)

# Vitesse moyenne réaliste (km/h) et détour moyen des rues par rapport à la ligne droite.
VITESSES_KMH = {"pied": 4.5, "moto": 22.0, "voiture": 16.0}
DETOUR = {"pied": 1.25, "moto": 1.35, "voiture": 1.4}
# Profils OSRM : la moto suit les mêmes routes que la voiture.
PROFILS = {"pied": "routed-foot", "moto": "routed-car", "voiture": "routed-car"}
MODES = tuple(VITESSES_KMH)
MODE_DEFAUT = "moto"
DELAI_OSRM = 4.0
DUREE_CACHE = 6 * 3600
PAUSE_APRES_PANNE = 5 * 60


@dataclass
class Trajet:
    distance_km: float
    minutes: int
    source: str  # "route" (OSRM) ou "estimation"

    def en_dict(self):
        return {"distance_km": round(self.distance_km, 2), "minutes": self.minutes, "source": self.source}


def distance_vol_oiseau_km(lat1, lng1, lat2, lng2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def minutes_pour(distance_km, mode):
    """Au moins 1 minute : « disponible en 0 min » n'a pas de sens."""
    return max(1, round(distance_km / VITESSES_KMH[mode] * 60))


def estimation(depart, arrivee, mode):
    distance = distance_vol_oiseau_km(*depart, *arrivee) * DETOUR[mode]
    return Trajet(distance, minutes_pour(distance, mode), "estimation")


def _get_json(url):
    requete = urllib.request.Request(url, headers={"User-Agent": "Uzima/1.0 (pharmacies Lubumbashi)"})
    with urllib.request.urlopen(requete, timeout=DELAI_OSRM) as reponse:
        return json.load(reponse)


def _coordonnees(points):
    return ";".join(f"{lng:.5f},{lat:.5f}" for lat, lng in points)


def _cle(*morceaux):
    return "trajet:" + hashlib.sha1(repr(morceaux).encode()).hexdigest()


def _en_panne(profil):
    return cache.get(f"trajet:panne:{profil}") is not None


def _signaler_panne(profil, erreur):
    """Après un échec, on n'attend plus ce serveur pendant quelques minutes."""
    journal.info("Routage %s indisponible : %s", profil, erreur)
    cache.set(f"trajet:panne:{profil}", True, PAUSE_APRES_PANNE)


def _distances_route(profil, depart, arrivees):
    """Distances par la route (km) depuis `depart` vers chaque arrivée, None si inconnue."""
    cle = _cle("table", profil, depart, tuple(arrivees))
    en_cache = cache.get(cle)
    if en_cache is not None:
        return en_cache
    if _en_panne(profil):
        return [None] * len(arrivees)
    url = (f"{settings.ROUTAGE_URL}/{profil}/table/v1/driving/{_coordonnees([depart, *arrivees])}"
           f"?sources=0&annotations=distance")
    try:
        donnees = _get_json(url)
    except Exception as e:  # réseau, délai, réponse illisible : on estimera
        _signaler_panne(profil, e)
        return [None] * len(arrivees)
    if donnees.get("code") != "Ok":
        return [None] * len(arrivees)
    ligne = donnees["distances"][0][1:]
    distances = [d / 1000 if d is not None else None for d in ligne]
    cache.set(cle, distances, DUREE_CACHE)
    return distances


def _arrondi(point):
    # ~10 m : la même position donne la même clé de cache.
    return round(point[0], 4), round(point[1], 4)


def trajets(depart, arrivees):
    """
    Pour chaque arrivée (lat, lng), {mode: Trajet} pour les trois modes.
    Les deux profils OSRM (pied, voiture) sont interrogés en parallèle.
    """
    depart = _arrondi(depart)
    arrivees = [_arrondi(a) for a in arrivees]
    if not arrivees:
        return []
    profils = sorted(set(PROFILS.values()))
    routes = {p: [None] * len(arrivees) for p in profils}
    if settings.ROUTAGE_URL:
        with ThreadPoolExecutor(max_workers=len(profils)) as executeur:
            futurs = {p: executeur.submit(_distances_route, p, depart, arrivees) for p in profils}
            routes = {p: f.result() for p, f in futurs.items()}
    resultat = []
    for i, arrivee in enumerate(arrivees):
        par_mode = {}
        for mode in MODES:
            distance = routes[PROFILS[mode]][i]
            if distance is None:
                # Un seul profil a répondu : la distance par la route de l'autre reste plus juste
                # qu'une estimation (à pied, on peut prendre les rues de la voiture, et inversement).
                distance = next((d[i] for d in routes.values() if d[i] is not None), None)
            if distance is None:
                par_mode[mode] = estimation(depart, arrivee, mode)
            else:
                par_mode[mode] = Trajet(distance, minutes_pour(distance, mode), "route")
        resultat.append(par_mode)
    return resultat


def itineraire(depart, arrivee, mode):
    """Tracé du trajet : {"points": [[lat, lng], …], "distance_km", "minutes", "source"}."""
    depart, arrivee = _arrondi(depart), _arrondi(arrivee)
    profil = PROFILS[mode]
    cle = _cle("route", profil, depart, arrivee)
    trace = cache.get(cle)
    if trace is None and settings.ROUTAGE_URL and not _en_panne(profil):
        url = (f"{settings.ROUTAGE_URL}/{profil}/route/v1/driving/{_coordonnees([depart, arrivee])}"
               f"?overview=full&geometries=geojson")
        try:
            donnees = _get_json(url)
            if donnees.get("code") == "Ok" and donnees.get("routes"):
                route = donnees["routes"][0]
                trace = {
                    "points": [[lat, lng] for lng, lat in route["geometry"]["coordinates"]],
                    "distance_km": route["distance"] / 1000,
                }
                cache.set(cle, trace, DUREE_CACHE)
        except Exception as e:
            _signaler_panne(profil, e)
    if trace is None:
        t = estimation(depart, arrivee, mode)
        return {"points": [list(depart), list(arrivee)], **t.en_dict()}
    t = Trajet(trace["distance_km"], minutes_pour(trace["distance_km"], mode), "route")
    return {"points": trace["points"], **t.en_dict()}


def mode_depuis(valeur):
    return valeur if valeur in MODES else MODE_DEFAUT
