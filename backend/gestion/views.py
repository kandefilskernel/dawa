"""
Espace Uzima : l'équipe valide les inscriptions, gère la visibilité des pharmacies,
active les abonnements payés et traite les signalements. Réservé aux comptes « équipe » (is_staff).
Les règles sont dans gestion/services.py (partagées avec l'API du site Next.js).
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from abonnements.models import Abonnement
from kyc.dossier import Dossier
from kyc.models import Piece
from pharmacies.models import Pharmacie
from sante.models import Etablissement
from verification.models import Signalement

from . import services
from .services import GENRES, ActionImpossible


def equipe_requise(vue):
    @login_required
    @wraps(vue)
    def enveloppe(request, *args, **kwargs):
        if not request.user.is_staff:
            return render(request, "gestion/acces_refuse.html", status=403)
        request.nb_demandes = services.nb_demandes()
        return vue(request, *args, **kwargs)

    return enveloppe


def _motif(request):
    return request.POST.get("motif", "").strip()


def _executer(request, action, *args):
    """Applique une règle ; son message de succès (ou de refus) s'affiche sur la page suivante."""
    try:
        resultat = action(*args)
    except ActionImpossible as e:
        messages.error(request, str(e))
        return None
    return resultat


_position_a_verifier = services.position_a_verifier


@equipe_requise
def tableau(request):
    return render(request, "gestion/tableau.html", {
        "onglet": "tableau",
        "pharmacies_visibles": Pharmacie.objects.visibles().count(),
        "abonnements_a_activer": Abonnement.objects.filter(statut=Abonnement.Statut.EN_ATTENTE).count(),
        "abonnements_actifs": Abonnement.objects.actifs().count(),
        "signalements_a_traiter": Signalement.objects.filter(traite=False).count(),
    })


def _demande(genre, compte):
    """Vue unifiée d'une inscription à vérifier (pharmacie ou établissement de santé)."""
    structure = getattr(compte, GENRES[genre][1])
    return {
        "genre": genre, "compte": compte, "structure": structure,
        "type": "Pharmacie" if genre == "pharmacie" else structure.get_type_display(),
        "dossier": Dossier(structure.pieces.all()),
        "position_a_verifier": _position_a_verifier(structure),
        "admin_url": reverse(f"admin:{structure._meta.app_label}_{structure._meta.model_name}_change",
                             args=[structure.pk]),
    }


@equipe_requise
def demandes(request):
    return render(request, "gestion/demandes.html", {
        "onglet": "demandes",
        "demandes": [_demande(genre, compte) for genre, compte in services.demandes_en_attente()],
        "refusees": services.demandes_refusees(),
    })


@equipe_requise
@require_POST
def decider_demande(request, genre, pk):
    message = _executer(request, services.decider_demande, genre, pk, request.POST.get("decision"),
                        _motif(request), request.user)
    if message:
        messages.success(request, message)
    return redirect("gestion:demandes")


@equipe_requise
@require_POST
def verifier_piece(request, pk):
    """Accepter ou rejeter une pièce justificative (le motif du rejet est montré à la structure)."""
    piece = get_object_or_404(Piece, pk=pk)
    _executer(request, services.verifier_piece, piece, request.POST.get("decision"), _motif(request), request.user)
    return redirect(f"{reverse('gestion:demandes')}#structure-{piece.pharmacie_id or piece.etablissement_id}")


@equipe_requise
def pharmacies(request):
    q = request.GET.get("q", "").strip()
    liste = Pharmacie.objects.prefetch_related("pharmaciens__utilisateur", "pieces").order_by("nom")
    if q:
        liste = liste.filter(Q(nom__icontains=q) | Q(quartier__icontains=q) | Q(telephone__icontains=q)
                             | Q(numero_agrement__icontains=q))
    filtre = request.GET.get("filtre", "")
    if filtre == "visibles":
        liste = liste.filter(est_validee=True)
    elif filtre == "masquees":
        liste = liste.filter(est_validee=False)
    sponsorisees = Abonnement.objects.ids_pharmacies_sponsorisees()
    liste = list(liste[:100])
    for p in liste:
        p.kyc_verifie = Dossier(p.pieces.all()).verifie
    return render(request, "gestion/pharmacies.html", {
        "onglet": "pharmacies", "pharmacies": liste, "q": q, "filtre": filtre, "sponsorisees": sponsorisees,
    })


def _visibilite(request, genre, pk, retour):
    resultat = _executer(request, services.changer_visibilite, genre, pk, request.POST.get("action"),
                         _motif(request), request.user)
    if resultat:
        messages.success(request, resultat[1])
    return redirect(retour)


@equipe_requise
@require_POST
def visibilite_pharmacie(request, pk):
    """Suspendre (retirer de l'app et bloquer le portail) ou réactiver une pharmacie."""
    return _visibilite(request, "pharmacie", pk, "gestion:pharmacies")


@equipe_requise
def etablissements(request):
    q = request.GET.get("q", "").strip()
    liste = Etablissement.objects.prefetch_related("responsables__utilisateur", "pieces").order_by("nom")
    if q:
        liste = liste.filter(Q(nom__icontains=q) | Q(quartier__icontains=q) | Q(numero_agrement__icontains=q))
    liste = list(liste[:100])
    for e in liste:
        e.kyc_verifie = Dossier(e.pieces.all()).verifie
    return render(request, "gestion/etablissements.html", {"onglet": "etablissements", "etablissements": liste, "q": q})


@equipe_requise
@require_POST
def visibilite_etablissement(request, pk):
    """Suspendre (retirer de l'annuaire santé) ou réactiver un établissement."""
    return _visibilite(request, "etablissement", pk, "gestion:etablissements")


@equipe_requise
@require_POST
def lien_mot_de_passe(request, pk):
    """Lien « nouveau mot de passe » à envoyer par WhatsApp ou SMS (voir services.lien_mot_de_passe)."""
    infos = services.lien_mot_de_passe(pk, request.user, lambda uid, jeton: request.build_absolute_uri(
        reverse("portail:mot_de_passe_nouveau", kwargs={"uidb64": uid, "token": jeton})))
    return render(request, "gestion/lien_mot_de_passe.html", {
        **infos, "onglet": "pharmacies" if hasattr(infos["compte"], "pharmacie") else "etablissements",
    })


@equipe_requise
def abonnements(request):
    return render(request, "gestion/abonnements.html", {
        "onglet": "abonnements",
        "en_attente": Abonnement.objects.filter(statut=Abonnement.Statut.EN_ATTENTE)
        .select_related("pharmacie").order_by("cree_le"),
        "actifs": Abonnement.objects.actifs().select_related("pharmacie").order_by("fin")[:30],
    })


@equipe_requise
@require_POST
def activer_abonnement(request, pk):
    abonnement = _executer(request, services.activer_abonnement, pk, request.POST.get("reference_paiement", ""))
    if abonnement:
        messages.success(request, f"Abonnement de {abonnement.pharmacie} activé jusqu'au {abonnement.fin:%d/%m/%Y}.")
    return redirect("gestion:abonnements")


@equipe_requise
def signalements(request):
    return render(request, "gestion/signalements.html", {
        "onglet": "signalements",
        "a_traiter": Signalement.objects.filter(traite=False).select_related("medicament", "pharmacie")
        .order_by("cree_le"),
        "traites": Signalement.objects.filter(traite=True).select_related("medicament").order_by("-cree_le")[:10],
    })


@equipe_requise
@require_POST
def traiter_signalement(request, pk):
    if _executer(request, services.traiter_signalement, pk, request.POST.get("suite_donnee", "")):
        messages.success(request, "Signalement traité.")
    return redirect("gestion:signalements")
