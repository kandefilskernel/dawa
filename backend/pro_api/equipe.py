"""API de l'espace de l'équipe Uzima (/api/web/equipe/) : mêmes règles que les pages Django de gestion/."""
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.response import Response

from abonnements.models import Abonnement
from gestion import services
from gestion.services import GENRES, ActionImpossible
from kyc.dossier import Dossier
from kyc.models import Piece
from pharmacies.models import Pharmacie
from sante.models import Etablissement
from verification.models import Signalement

from . import donnees
from .base import VueWeb, erreur


class VueEquipe(VueWeb):
    """Réservée aux comptes « équipe » (is_staff)."""

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not request.user.is_authenticated:
            raise NotAuthenticated("Connectez-vous pour accéder à l'espace Uzima.")
        if not request.user.is_staff:
            raise PermissionDenied("Espace réservé à l'équipe Uzima.")


def _action(fonction, *args):
    try:
        return fonction(*args)
    except ActionImpossible as e:
        raise erreur(str(e))


# --- Mise en forme ---

def adresse_admin(structure):
    return reverse(f"admin:{structure._meta.app_label}_{structure._meta.model_name}_change", args=[structure.pk])


def dossier_equipe(structure):
    """Dossier KYC avec, pour chaque pièce, l'adresse du document (téléchargement réservé à l'équipe)."""
    d = donnees.dossier(structure.pieces.all())
    for ligne in d["lignes"]:
        if ligne["piece"]:
            ligne["piece"]["document"] = reverse("gestion:piece", args=[ligne["piece"]["id"]])
    return d


def structure_json(s):
    return {
        "id": s.pk, "nom": s.nom, "numero_agrement": s.numero_agrement, "adresse": s.adresse,
        "quartier": s.quartier, "telephone": s.telephone,
        "type": s.get_type_display() if isinstance(s, Etablissement) else "Pharmacie",
        "position": {"lat": s.position.y, "lng": s.position.x},
        "position_a_verifier": services.position_a_verifier(s),
        "admin": adresse_admin(s),
    }


def compte_json(c):
    return {"id": c.pk, "utilisateur_id": c.utilisateur_id, "identifiant": c.utilisateur.get_username(),
            "statut": c.statut, "statut_libelle": c.get_statut_display(), "motif": c.motif,
            "fonction": getattr(c, "fonction", "")}


def abonnement_json(a):
    return {"id": a.pk, "pharmacie": {"id": a.pharmacie_id, "nom": a.pharmacie.nom},
            "formule": a.get_formule_display(), "mois": a.mois, "montant": a.montant, "reference": a.reference,
            "fin": a.fin}


def signalement_json(s):
    return {
        "id": s.pk, "medicament": str(s.medicament) if s.medicament else None, "numero_lot": s.numero_lot,
        "description": s.description, "lieu": str(s.pharmacie) if s.pharmacie else s.lieu_achat,
        "telephone": s.telephone, "photo": donnees.image(s.photo), "cree_le": s.cree_le,
        "suite_donnee": s.suite_donnee,
    }


# --- Vues ---

class TableauView(VueEquipe):
    def get(self, request):
        return Response({
            "identifiant": request.user.get_username(),
            "nb_demandes": services.nb_demandes(),
            "pharmacies_visibles": Pharmacie.objects.visibles().count(),
            "abonnements_a_activer": Abonnement.objects.filter(statut=Abonnement.Statut.EN_ATTENTE).count(),
            "abonnements_actifs": Abonnement.objects.actifs().count(),
            "signalements_a_traiter": Signalement.objects.filter(traite=False).count(),
        })


class DemandesView(VueEquipe):
    def get(self, request):
        def demande_json(genre, compte):
            structure = getattr(compte, GENRES[genre][1])
            return {"genre": genre, "cree_le": compte.cree_le, "compte": compte_json(compte),
                    "structure": structure_json(structure), "dossier": dossier_equipe(structure)}

        return Response({
            "demandes": [demande_json(g, c) for g, c in services.demandes_en_attente()],
            "refusees": [{"nom": str(getattr(c, "pharmacie", None) or c.etablissement), "motif": c.motif,
                          "traite_le": c.traite_le} for c in services.demandes_refusees()],
        })


class DeciderDemandeView(VueEquipe):
    def post(self, request, genre, pk):
        message = _action(services.decider_demande, genre, pk, request.data.get("decision"),
                          request.data.get("motif", ""), request.user)
        return Response({"message": message, "nb_demandes": services.nb_demandes()})


class VerifierPieceView(VueEquipe):
    def post(self, request, pk):
        piece = get_object_or_404(Piece.objects.select_related("pharmacie", "etablissement"), pk=pk)
        _action(services.verifier_piece, piece, request.data.get("decision"), request.data.get("motif", ""),
                request.user)
        structure = piece.pharmacie or piece.etablissement
        return Response({"message": "Pièce acceptée." if piece.statut == Piece.Statut.ACCEPTEE else "Pièce rejetée.",
                         "dossier": dossier_equipe(structure)})


class PharmaciesView(VueEquipe):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        liste = Pharmacie.objects.prefetch_related("pharmaciens__utilisateur", "pieces").order_by("nom")
        if q:
            liste = liste.filter(Q(nom__icontains=q) | Q(quartier__icontains=q) | Q(telephone__icontains=q)
                                 | Q(numero_agrement__icontains=q))
        filtre = request.query_params.get("filtre", "")
        if filtre == "visibles":
            liste = liste.filter(est_validee=True)
        elif filtre == "masquees":
            liste = liste.filter(est_validee=False)
        sponsorisees = Abonnement.objects.ids_pharmacies_sponsorisees()
        return Response({"q": q, "filtre": filtre, "pharmacies": [{
            **structure_json(p), "visible": p.est_validee, "kyc_verifie": Dossier(p.pieces.all()).verifie,
            "sponsorisee": p.pk in sponsorisees, "comptes": [compte_json(c) for c in p.pharmaciens.all()],
        } for p in liste[:100]]})


class EtablissementsView(VueEquipe):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        liste = Etablissement.objects.prefetch_related("responsables__utilisateur", "pieces").order_by("nom")
        if q:
            liste = liste.filter(Q(nom__icontains=q) | Q(quartier__icontains=q) | Q(numero_agrement__icontains=q))
        return Response({"q": q, "etablissements": [{
            **structure_json(e), "visible": e.est_valide, "kyc_verifie": Dossier(e.pieces.all()).verifie,
            "comptes": [compte_json(c) for c in e.responsables.all()],
        } for e in liste[:100]]})


class VisibiliteView(VueEquipe):
    genre = None

    def post(self, request, pk):
        _, message = _action(services.changer_visibilite, self.genre, pk, request.data.get("action"),
                             request.data.get("motif", ""), request.user)
        return Response({"message": message})


class LienMotDePasseView(VueEquipe):
    """Lien « nouveau mot de passe » vers le site, à envoyer par WhatsApp ou SMS au numéro officiel."""

    def post(self, request, pk):
        infos = services.lien_mot_de_passe(pk, request.user,
                                           lambda uid, jeton: donnees.adresse_site(f"/mot-de-passe/{uid}/{jeton}"))
        s = infos["structure"]
        return Response({"identifiant": infos["utilisateur"].get_username(),
                         "structure": {"nom": s.nom, "telephone": s.telephone},
                         "lien": infos["lien"], "texte": infos["texte"], "whatsapp": infos["whatsapp"]})


class AbonnementsView(VueEquipe):
    def get(self, request):
        return Response({
            "en_attente": [abonnement_json(a) for a in Abonnement.objects.filter(statut=Abonnement.Statut.EN_ATTENTE)
                           .select_related("pharmacie").order_by("cree_le")],
            "actifs": [abonnement_json(a) for a in
                       Abonnement.objects.actifs().select_related("pharmacie").order_by("fin")[:30]],
        })


class ActiverAbonnementView(VueEquipe):
    def post(self, request, pk):
        a = _action(services.activer_abonnement, pk, request.data.get("reference_paiement", ""))
        return Response({"message": f"Abonnement de {a.pharmacie} activé jusqu'au {a.fin:%d/%m/%Y}."})


class SignalementsView(VueEquipe):
    def get(self, request):
        return Response({
            "a_traiter": [signalement_json(s) for s in Signalement.objects.filter(traite=False)
                          .select_related("medicament", "pharmacie").order_by("cree_le")],
            "traites": [signalement_json(s) for s in Signalement.objects.filter(traite=True)
                        .select_related("medicament", "pharmacie").order_by("-cree_le")[:10]],
        })


class TraiterSignalementView(VueEquipe):
    def post(self, request, pk):
        _action(services.traiter_signalement, pk, request.data.get("suite_donnee", ""))
        return Response({"message": "Signalement traité."})
