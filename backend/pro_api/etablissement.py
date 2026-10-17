"""API de l'espace des établissements de santé (/api/web/etablissement/) : mêmes règles que sante/espace.py."""
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from sante.forms import FicheEtablissementForm

from . import donnees
from .base import VueWeb, erreur_formulaire


class VueEtablissement(VueWeb):
    """Réservée au responsable d'un établissement, quel que soit le statut du compte."""

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not request.user.is_authenticated:
            raise NotAuthenticated("Connectez-vous pour accéder à votre espace.")
        self.responsable = getattr(request.user, "responsable_etablissement", None)
        if self.responsable is None:
            raise PermissionDenied("Ce compte n'est pas rattaché à un établissement de santé.")
        self.etablissement = self.responsable.etablissement


def fiche_json(e):
    return {c: getattr(e, c) for c in FicheEtablissementForm.Meta.fields}


class EspaceView(VueEtablissement):
    """GET : statut, fiche et justificatifs. POST : fiche affichée aux patients (compte validé uniquement)."""

    def _reponse(self, **extra):
        e, r = self.etablissement, self.responsable
        return Response({
            "statut": r.statut, "motif": r.motif, "fonction": r.fonction,
            "nom": e.nom, "type": e.get_type_display(),
            "fiche": fiche_json(e) if r.actif else None,
            "dossier": donnees.dossier(e.pieces.all()),
            **extra,
        })

    def get(self, request):
        return self._reponse()

    def post(self, request):
        if not self.responsable.actif:
            raise PermissionDenied("La fiche se modifie une fois l'établissement validé par l'équipe Uzima.")
        e = self.etablissement
        valeurs = {c: request.data.get(c, getattr(e, c)) for c in FicheEtablissementForm.Meta.fields}
        # Case à cocher : absente du formulaire = décochée, comme une page web classique.
        if not valeurs["urgences_24h"] or valeurs["urgences_24h"] in ("0", "false", "False"):
            valeurs.pop("urgences_24h")
        formulaire = FicheEtablissementForm(valeurs, instance=e)
        if not formulaire.is_valid():
            raise erreur_formulaire(formulaire)
        formulaire.save()
        return self._reponse(message="Fiche mise à jour.")


class DossierView(VueEtablissement):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        donnees.enregistrer_piece(request, etablissement=self.etablissement)
        return Response({"message": "Document envoyé. L'équipe Uzima va le vérifier.",
                         "dossier": donnees.dossier(self.etablissement.pieces.all())}, status=status.HTTP_201_CREATED)
