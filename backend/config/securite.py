"""
Limites contre la force brute et le spam : tentatives de connexion (portail et admin),
inscriptions et demandes de « mot de passe oublié ». Compteurs dans le cache partagé.
"""
import logging

from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.core.cache import cache
from django.core.exceptions import PermissionDenied

journal = logging.getLogger("dawa.securite")

FENETRE_SECONDES = 15 * 60
ECHECS_PAR_IDENTIFIANT = 5    # protège un compte précis
ECHECS_PAR_ADRESSE = 30       # protège contre un essai sur beaucoup de comptes depuis la même adresse


def adresse_ip(request):
    """IP du client. Derrière Caddy, c'est la dernière valeur de X-Forwarded-For (ajoutée par Caddy)."""
    if settings.DERRIERE_PROXY:
        transmise = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if transmise:
            return transmise.split(",")[-1].strip()
    return request.META.get("REMOTE_ADDR", "inconnue")


def _cles(request, identifiant):
    return [f"connexion:id:{(identifiant or '').strip().lower()}", f"connexion:ip:{adresse_ip(request)}"]


def connexion_bloquee(request, identifiant):
    cle_id, cle_ip = _cles(request, identifiant)
    return (cache.get(cle_id, 0) >= ECHECS_PAR_IDENTIFIANT) or (cache.get(cle_ip, 0) >= ECHECS_PAR_ADRESSE)


def _incrementer(cle, duree):
    if cache.add(cle, 1, duree):
        return 1
    try:
        return cache.incr(cle)
    except ValueError:  # expirée entre-temps
        cache.set(cle, 1, duree)
        return 1


class ConnexionLimitee(ModelBackend):
    """ModelBackend avec blocage temporaire après trop d'échecs (portail, espace Dawa et admin)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if request is None:
            return super().authenticate(request, username=username, password=password, **kwargs)
        if connexion_bloquee(request, username):
            request.connexion_bloquee = True
            journal.warning("Connexion bloquée (trop d'échecs) : identifiant=%r ip=%s", username, adresse_ip(request))
            raise PermissionDenied
        utilisateur = super().authenticate(request, username=username, password=password, **kwargs)
        cle_id, cle_ip = _cles(request, username)
        if utilisateur is None:
            _incrementer(cle_id, FENETRE_SECONDES)
            _incrementer(cle_ip, FENETRE_SECONDES)
        else:
            cache.delete(cle_id)
        return utilisateur


def limite_atteinte(request, action, maximum):
    """Vrai si l'action (inscription, mot de passe oublié…) a déjà été faite `maximum` fois depuis cette IP."""
    return cache.get(f"limite:{action}:{adresse_ip(request)}", 0) >= maximum


def compter(request, action, duree_secondes=3600):
    _incrementer(f"limite:{action}:{adresse_ip(request)}", duree_secondes)
