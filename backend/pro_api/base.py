"""
Socle de l'API des espaces professionnels (site Next.js) : session Django + protection CSRF,
rôles (pharmacien, responsable d'établissement, équipe Uzima) et format des erreurs.
"""
from rest_framework import permissions
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView


class SessionAvecCsrf(SessionAuthentication):
    """
    Session Django, avec contrôle CSRF sur toute écriture, même sans être connecté
    (connexion, inscription, mot de passe oublié). Le site envoie le jeton dans l'en-tête X-CSRFToken.
    """

    def authenticate(self, request):
        if request.method not in permissions.SAFE_METHODS:
            self.enforce_csrf(request)
        utilisateur = getattr(request._request, "user", None)
        if not utilisateur or not utilisateur.is_active:
            return None
        return (utilisateur, None)


def role(utilisateur):
    """« pharmacien », « etablissement », « equipe » ou None (même ordre que les anciennes pages)."""
    if not utilisateur or not utilisateur.is_authenticated:
        return None
    if hasattr(utilisateur, "pharmacien"):
        return "pharmacien"
    if hasattr(utilisateur, "responsable_etablissement"):
        return "etablissement"
    if utilisateur.is_staff:
        return "equipe"
    return None


def compte_structure(utilisateur):
    """(compte validable, structure) de l'utilisateur, ou (None, None) pour l'équipe."""
    compte = getattr(utilisateur, "pharmacien", None) or getattr(utilisateur, "responsable_etablissement", None)
    if compte is None:
        return None, None
    return compte, getattr(compte, "pharmacie", None) or compte.etablissement


class VueWeb(APIView):
    """Vue de base : session + CSRF, sans la pagination ni le jeton d'appareil de l'API mobile."""

    authentication_classes = [SessionAvecCsrf]
    permission_classes = [permissions.AllowAny]


def erreur(message, champs=None):
    """Erreur 400 lisible par le site : {"message": "...", "erreurs": {champ: [..]}}."""
    return ValidationError({"message": message, "erreurs": champs or {}})


def erreur_formulaire(formulaire):
    champs = {nom: [str(e) for e in liste] for nom, liste in formulaire.errors.items()}
    return erreur(" ".join(e for liste in champs.values() for e in liste), champs)
