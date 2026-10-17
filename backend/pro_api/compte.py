"""Connexion, déconnexion et mot de passe oublié, communs aux trois espaces."""
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.response import Response

from config.securite import compter, limite_atteinte

from .base import VueWeb, compte_structure, erreur, erreur_formulaire, role

MAX_MOTS_DE_PASSE_OUBLIES = 5


def description_compte(utilisateur):
    """Ce que le site doit savoir sur la personne connectée pour choisir l'espace à afficher."""
    if not utilisateur.is_authenticated:
        return {"connecte": False}
    compte, structure = compte_structure(utilisateur)
    infos = {
        "connecte": True,
        "identifiant": utilisateur.get_username(),
        "role": role(utilisateur),
        "statut": compte.statut if compte else ("actif" if utilisateur.is_staff else None),
        "motif": compte.motif if compte else "",
        "structure": None,
    }
    if structure is not None:
        infos["structure"] = {
            "id": structure.pk,
            "nom": structure.nom,
            "type": structure.get_type_display() if hasattr(structure, "get_type_display") else "Pharmacie",
        }
    return infos


@method_decorator(ensure_csrf_cookie, name="get")
class MoiView(VueWeb):
    """GET : la personne connectée (et dépose le cookie CSRF pour les écritures suivantes)."""

    def get(self, request):
        return Response(description_compte(request.user))


class ConnexionView(VueWeb):
    def post(self, request):
        identifiant = str(request.data.get("identifiant", "")).strip()
        mot_de_passe = str(request.data.get("mot_de_passe", ""))
        if not identifiant or not mot_de_passe:
            raise erreur("Indiquez votre identifiant et votre mot de passe.")
        utilisateur = authenticate(request._request, username=identifiant, password=mot_de_passe)
        if getattr(request._request, "connexion_bloquee", False):  # posé par config.securite
            return Response({"message": "Trop de tentatives : réessayez dans 15 minutes."},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)
        if utilisateur is None:
            raise erreur("Identifiant ou mot de passe incorrect.")
        login(request._request, utilisateur)
        return Response(description_compte(utilisateur))


class DeconnexionView(VueWeb):
    def post(self, request):
        logout(request._request)
        return Response({"connecte": False})


class MotDePasseOublieView(VueWeb):
    """Envoie un lien par e-mail. Réponse identique que le compte existe ou non."""

    def post(self, request):
        formulaire = PasswordResetForm({"email": str(request.data.get("email", "")).strip()})
        if not formulaire.is_valid():
            raise erreur_formulaire(formulaire)
        if not limite_atteinte(request, "mot_de_passe_oublie", MAX_MOTS_DE_PASSE_OUBLIES):
            compter(request, "mot_de_passe_oublie")
            formulaire.save(
                request=request._request,
                subject_template_name="portail/mot_de_passe/email_sujet.txt",
                email_template_name="pro_api/email_mot_de_passe.txt",
                extra_email_context={"adresse_web": settings.UZIMA_WEB_URL},
            )
        return Response({"message": "Si un compte utilise cette adresse, un lien vient d'y être envoyé."})


def _utilisateur_du_lien(uid, jeton):
    try:
        utilisateur = get_user_model().objects.get(pk=force_str(urlsafe_base64_decode(uid)))
    except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
        return None
    return utilisateur if default_token_generator.check_token(utilisateur, jeton) else None


class NouveauMotDePasseView(VueWeb):
    """GET ?uid=&jeton= : le lien est-il encore valable ? POST : enregistre le nouveau mot de passe."""

    def get(self, request):
        utilisateur = _utilisateur_du_lien(request.query_params.get("uid", ""), request.query_params.get("jeton", ""))
        return Response({"valide": utilisateur is not None,
                         "identifiant": utilisateur.get_username() if utilisateur else ""})

    def post(self, request):
        utilisateur = _utilisateur_du_lien(str(request.data.get("uid", "")), str(request.data.get("jeton", "")))
        if utilisateur is None:
            raise erreur("Ce lien n'est plus valable. Demandez-en un nouveau.")
        formulaire = SetPasswordForm(utilisateur, {
            "new_password1": request.data.get("mot_de_passe1", ""),
            "new_password2": request.data.get("mot_de_passe2", ""),
        })
        if not formulaire.is_valid():
            raise erreur_formulaire(formulaire)
        formulaire.save()
        return Response({"message": "Mot de passe enregistré. Vous pouvez vous connecter."})
