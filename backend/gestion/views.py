"""
Espace Uzima : l'équipe valide les inscriptions, gère la visibilité des pharmacies,
active les abonnements payés et traite les signalements. Réservé aux comptes « équipe » (is_staff).
"""
import logging
from functools import wraps
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views.decorators.http import require_POST

from abonnements.models import Abonnement
from kyc.dossier import Dossier
from kyc.models import Piece
from pharmacies.models import Pharmacie
from portail.forms import CENTRE_LUBUMBASHI
from portail.models import Pharmacien
from sante.models import Etablissement, ResponsableEtablissement
from verification.models import Signalement

journal_securite = logging.getLogger("dawa.securite")


def equipe_requise(vue):
    @login_required
    @wraps(vue)
    def enveloppe(request, *args, **kwargs):
        if not request.user.is_staff:
            return render(request, "gestion/acces_refuse.html", status=403)
        request.nb_demandes = sum(m.objects.filter(statut=m.Statut.EN_ATTENTE).count() for m, _, _ in GENRES.values())
        return vue(request, *args, **kwargs)

    return enveloppe


def _motif(request):
    return request.POST.get("motif", "").strip()


def _position_a_verifier(structure):
    """Vrai si la structure n'a pas donné sa position (placée au centre-ville par défaut)."""
    return (round(structure.position.x, 3), round(structure.position.y, 3)) == CENTRE_LUBUMBASHI


@equipe_requise
def tableau(request):
    return render(request, "gestion/tableau.html", {
        "onglet": "tableau",
        "pharmacies_visibles": Pharmacie.objects.visibles().count(),
        "abonnements_a_activer": Abonnement.objects.filter(statut=Abonnement.Statut.EN_ATTENTE).count(),
        "abonnements_actifs": Abonnement.objects.actifs().count(),
        "signalements_a_traiter": Signalement.objects.filter(traite=False).count(),
    })


# Types de comptes à valider : (modèle de compte, nom du lien vers la structure, libellé).
GENRES = {
    "pharmacie": (Pharmacien, "pharmacie", "pharmacie"),
    "etablissement": (ResponsableEtablissement, "etablissement", "établissement"),
}


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
    attente = [
        _demande(genre, compte)
        for genre, (modele, lien, _) in GENRES.items()
        for compte in modele.objects.filter(statut=modele.Statut.EN_ATTENTE)
        .select_related(lien, "utilisateur").prefetch_related(f"{lien}__pieces")
    ]
    attente.sort(key=lambda d: d["compte"].cree_le)
    refusees = sorted(
        [c for modele, lien, _ in GENRES.values()
         for c in modele.objects.filter(statut=modele.Statut.REFUSE).select_related(lien).order_by("-traite_le")[:10]],
        key=lambda c: c.traite_le, reverse=True,
    )[:10]
    return render(request, "gestion/demandes.html", {"onglet": "demandes", "demandes": attente, "refusees": refusees})


@equipe_requise
@require_POST
def decider_demande(request, genre, pk):
    if genre not in GENRES:
        raise Http404
    modele, lien, _ = GENRES[genre]
    compte = get_object_or_404(modele.objects.select_related(lien), pk=pk, statut=modele.Statut.EN_ATTENTE)
    structure = getattr(compte, lien)
    if request.POST.get("decision") == "valider":
        if not Dossier(structure.pieces.all()).verifie:
            messages.error(request, f"Impossible de valider {structure} : toutes les pièces obligatoires "
                                    "doivent d'abord être acceptées.")
        else:
            compte.valider(request.user)
            messages.success(request, f"{structure} est validé(e) et visible dans l'app.")
    elif _motif(request):
        compte.refuser(request.user, _motif(request))
        messages.success(request, f"Demande de {structure} refusée.")
    else:
        messages.error(request, "Indiquez le motif du refus : il est montré au demandeur.")
    return redirect("gestion:demandes")


@equipe_requise
@require_POST
def verifier_piece(request, pk):
    """Accepter ou rejeter une pièce justificative (le motif du rejet est montré à la structure)."""
    piece = get_object_or_404(Piece, pk=pk)
    if request.POST.get("decision") == "accepter":
        piece.verifier(request.user, acceptee=True)
    elif _motif(request):
        piece.verifier(request.user, acceptee=False, motif=_motif(request))
    else:
        messages.error(request, "Indiquez pourquoi la pièce est rejetée (ex. illisible, expirée).")
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


@equipe_requise
@require_POST
def visibilite_pharmacie(request, pk):
    """Suspendre (retirer de l'app et bloquer le portail) ou réactiver une pharmacie."""
    pharmacie = get_object_or_404(Pharmacie, pk=pk)
    comptes = list(pharmacie.pharmaciens.exclude(statut=Pharmacien.Statut.REFUSE))
    if request.POST.get("action") == "reactiver":
        for compte in comptes:
            compte.valider(request.user)
        Pharmacie.objects.filter(pk=pharmacie.pk).update(est_validee=True)
        messages.success(request, f"{pharmacie} est de nouveau visible.")
    elif _motif(request):
        for compte in comptes:
            compte.suspendre(request.user, _motif(request))
        Pharmacie.objects.filter(pk=pharmacie.pk).update(est_validee=False)
        messages.success(request, f"{pharmacie} est suspendue et retirée de l'app.")
    else:
        messages.error(request, "Indiquez le motif de la suspension : il est montré à la pharmacie.")
    return redirect("gestion:pharmacies")


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
    etablissement = get_object_or_404(Etablissement, pk=pk)
    comptes = list(etablissement.responsables.exclude(statut=ResponsableEtablissement.Statut.REFUSE))
    if request.POST.get("action") == "reactiver":
        for compte in comptes:
            compte.valider(request.user)
        Etablissement.objects.filter(pk=pk).update(est_valide=True)
        messages.success(request, f"{etablissement} est de nouveau visible.")
    elif _motif(request):
        for compte in comptes:
            compte.suspendre(request.user, _motif(request))
        Etablissement.objects.filter(pk=pk).update(est_valide=False)
        messages.success(request, f"{etablissement} est suspendu et retiré de l'app.")
    else:
        messages.error(request, "Indiquez le motif de la suspension.")
    return redirect("gestion:etablissements")


@equipe_requise
@require_POST
def lien_mot_de_passe(request, pk):
    """
    Lien « nouveau mot de passe » créé par l'équipe, à envoyer par WhatsApp ou SMS à une structure
    qui n'a pas (ou plus) accès à son e-mail. Jamais pour un compte de l'équipe.
    """
    utilisateur = get_object_or_404(get_user_model(), pk=pk, is_staff=False, is_superuser=False, is_active=True)
    compte = (getattr(utilisateur, "pharmacien", None) or getattr(utilisateur, "responsable_etablissement", None))
    if compte is None:
        raise Http404
    structure = getattr(compte, "pharmacie", None) or compte.etablissement
    lien = request.build_absolute_uri(reverse("portail:mot_de_passe_nouveau", kwargs={
        "uidb64": urlsafe_base64_encode(force_bytes(utilisateur.pk)),
        "token": default_token_generator.make_token(utilisateur),
    }))
    journal_securite.warning("Lien de mot de passe créé par %s pour %s", request.user, utilisateur)
    numero = "".join(c for c in (getattr(structure, "whatsapp", "") or structure.telephone) if c.isdigit())
    texte = (f"Uzima : pour choisir un nouveau mot de passe du compte « {utilisateur.get_username()} », "
             f"ouvrez ce lien (valable 24 h) : {lien}")
    return render(request, "gestion/lien_mot_de_passe.html", {
        "onglet": "pharmacies" if hasattr(compte, "pharmacie") else "etablissements",
        "utilisateur": utilisateur, "structure": structure, "lien": lien, "texte": texte,
        "whatsapp": f"https://wa.me/{numero}?text={quote(texte)}" if numero else "",
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
    abonnement = get_object_or_404(Abonnement, pk=pk, statut=Abonnement.Statut.EN_ATTENTE)
    reference = request.POST.get("reference_paiement", "").strip()
    if not reference:
        messages.error(request, "Indiquez la référence de la transaction mobile money reçue.")
    else:
        abonnement.activer(reference[:60])
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
    signalement = get_object_or_404(Signalement, pk=pk, traite=False)
    suite = request.POST.get("suite_donnee", "").strip()
    if not suite:
        messages.error(request, "Indiquez la suite donnée (ex. transmis à l'inspection, lot conforme…).")
    else:
        Signalement.objects.filter(pk=pk).update(traite=True, suite_donnee=suite[:255])
        messages.success(request, "Signalement traité.")
    return redirect("gestion:signalements")
