"""
Page web du livreur (sur son téléphone), ouverte par son lien personnel /livreur/<jeton>/.

Pas de compte ni de mot de passe : le jeton secret du lien suffit. Pendant une course,
la page envoie la position du téléphone toutes les quelques secondes ; le patient la voit dans l'app.
"""
import json
from datetime import timedelta

from django.contrib.gis.geos import Point
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Livreur, PositionLivreur, Reservation

INTERVALLE_MIN = timedelta(seconds=3)


def _livreur(jeton):
    return get_object_or_404(Livreur.objects.select_related("pharmacie"), jeton=jeton, actif=True)


def page(request, jeton):
    livreur = _livreur(jeton)
    courses = livreur.courses_en_cours().select_related("medicament")
    return render(request, "reservations/livreur.html", {"livreur": livreur, "courses": courses})


def _nombre(valeur, minimum, maximum):
    try:
        valeur = float(valeur)
    except (TypeError, ValueError):
        return None
    return valeur if minimum <= valeur <= maximum else None


# Le jeton secret du lien authentifie le livreur (pas de session ni de cookie) : pas de CSRF à craindre.
@csrf_exempt
@require_POST
def position(request, jeton):
    livreur = _livreur(jeton)
    try:
        donnees = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"erreur": "JSON invalide."}, status=400)
    lat, lng = _nombre(donnees.get("lat"), -90, 90), _nombre(donnees.get("lng"), -180, 180)
    if lat is None or lng is None:
        return JsonResponse({"erreur": "lat et lng sont obligatoires."}, status=400)
    vitesse = _nombre(donnees.get("vitesse"), 0, 100)  # m/s, donnée par le GPS du téléphone
    point = Point(lng, lat, srid=4326)
    maintenant = timezone.now()
    enregistrees = 0
    for course in livreur.courses_en_cours():
        derniere = course.positions.order_by("-recue_le").values_list("recue_le", flat=True).first()
        if derniere and maintenant - derniere < INTERVALLE_MIN:
            continue
        PositionLivreur.objects.create(
            reservation=course, position=point, recue_le=maintenant,
            vitesse_kmh=vitesse * 3.6 if vitesse is not None else None,
            precision_m=_nombre(donnees.get("precision"), 0, 100_000),
        )
        enregistrees += 1
    return JsonResponse({"courses": livreur.courses_en_cours().count(), "enregistrees": enregistrees})


@csrf_exempt
@require_POST
def livree(request, jeton, pk):
    livreur = _livreur(jeton)
    course = get_object_or_404(Reservation, pk=pk, livreur=livreur)
    try:
        course.changer_statut(Reservation.Statut.LIVREE)
    except ValueError:
        pass  # déjà livrée ou expirée : la page se met simplement à jour
    return redirect("livreur:page", jeton=jeton)
