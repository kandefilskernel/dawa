"""
Règles de l'espace de l'équipe Uzima, partagées par les pages Django (gestion/views.py) et l'API du site
Next.js (pro_api/equipe.py). Les refus à montrer à l'équipe lèvent ActionImpossible.
"""
import logging
from urllib.parse import quote

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from abonnements.models import Abonnement
from kyc.dossier import Dossier
from pharmacies.models import Pharmacie
from portail.forms import CENTRE_LUBUMBASHI
from portail.models import Pharmacien
from portail.services import ActionImpossible
from sante.models import Etablissement, ResponsableEtablissement
from verification.models import Signalement

__all__ = ["ActionImpossible"]

journal_securite = logging.getLogger("dawa.securite")

# Types de comptes à valider : (modèle de compte, nom du lien vers la structure, libellé).
GENRES = {
    "pharmacie": (Pharmacien, "pharmacie", "pharmacie"),
    "etablissement": (ResponsableEtablissement, "etablissement", "établissement"),
}

# Structures dont l'équipe règle la visibilité : (modèle, champ « visible », related_name des comptes).
STRUCTURES = {
    "pharmacie": (Pharmacie, "est_validee", "pharmaciens"),
    "etablissement": (Etablissement, "est_valide", "responsables"),
}
# Messages : (réactivée, suspendue, motif manquant).
MESSAGES_VISIBILITE = {
    "pharmacie": ("{} est de nouveau visible.", "{} est suspendue et retirée de l'app.",
                  "Indiquez le motif de la suspension : il est montré à la pharmacie."),
    "etablissement": ("{} est de nouveau visible.", "{} est suspendu et retiré de l'app.",
                      "Indiquez le motif de la suspension."),
}


def nb_demandes():
    return sum(m.objects.filter(statut=m.Statut.EN_ATTENTE).count() for m, _, _ in GENRES.values())


def position_a_verifier(structure):
    """Vrai si la structure n'a pas donné sa position (placée au centre-ville par défaut)."""
    return (round(structure.position.x, 3), round(structure.position.y, 3)) == CENTRE_LUBUMBASHI


def demandes_en_attente():
    """(genre, compte) des inscriptions à vérifier, les plus anciennes d'abord."""
    attente = [
        (genre, compte)
        for genre, (modele, lien, _) in GENRES.items()
        for compte in modele.objects.filter(statut=modele.Statut.EN_ATTENTE)
        .select_related(lien, "utilisateur").prefetch_related(f"{lien}__pieces")
    ]
    return sorted(attente, key=lambda d: d[1].cree_le)


def demandes_refusees(nombre=10):
    return sorted(
        [c for modele, lien, _ in GENRES.values()
         for c in modele.objects.filter(statut=modele.Statut.REFUSE).select_related(lien).order_by("-traite_le")[:nombre]],
        key=lambda c: c.traite_le, reverse=True,
    )[:nombre]


def decider_demande(genre, pk, decision, motif, par):
    """Valide (toutes les pièces obligatoires acceptées) ou refuse (motif obligatoire). Renvoie le message."""
    if genre not in GENRES:
        raise Http404
    modele, lien, _ = GENRES[genre]
    compte = get_object_or_404(modele.objects.select_related(lien), pk=pk, statut=modele.Statut.EN_ATTENTE)
    structure = getattr(compte, lien)
    motif = (motif or "").strip()
    if decision == "valider":
        if not Dossier(structure.pieces.all()).verifie:
            raise ActionImpossible(f"Impossible de valider {structure} : toutes les pièces obligatoires "
                                   "doivent d'abord être acceptées.")
        compte.valider(par)
        return f"{structure} est validé(e) et visible dans l'app."
    if not motif:
        raise ActionImpossible("Indiquez le motif du refus : il est montré au demandeur.")
    compte.refuser(par, motif)
    return f"Demande de {structure} refusée."


def verifier_piece(piece, decision, motif, par):
    """Accepter ou rejeter une pièce justificative (le motif du rejet est montré à la structure)."""
    motif = (motif or "").strip()
    if decision == "accepter":
        piece.verifier(par, acceptee=True)
    elif motif:
        piece.verifier(par, acceptee=False, motif=motif)
    else:
        raise ActionImpossible("Indiquez pourquoi la pièce est rejetée (ex. illisible, expirée).")
    return piece


def changer_visibilite(genre, pk, action, motif, par):
    """Suspendre (retirer de l'app et bloquer l'espace, motif obligatoire) ou réactiver une structure."""
    modele, champ, comptes = STRUCTURES[genre]
    structure = get_object_or_404(modele, pk=pk)
    modele_compte = GENRES[genre][0]
    liste = list(getattr(structure, comptes).exclude(statut=modele_compte.Statut.REFUSE))
    motif = (motif or "").strip()
    reactivee, suspendue, sans_motif = MESSAGES_VISIBILITE[genre]
    if action == "reactiver":
        for compte in liste:
            compte.valider(par)
        modele.objects.filter(pk=pk).update(**{champ: True})
        return structure, reactivee.format(structure)
    if not motif:
        raise ActionImpossible(sans_motif)
    for compte in liste:
        compte.suspendre(par, motif)
    modele.objects.filter(pk=pk).update(**{champ: False})
    return structure, suspendue.format(structure)


def lien_mot_de_passe(utilisateur_id, par, construire_lien):
    """
    Lien « nouveau mot de passe » créé par l'équipe, à envoyer par WhatsApp ou SMS à une structure
    qui n'a pas (ou plus) accès à son e-mail. Jamais pour un compte de l'équipe.
    `construire_lien(uid, jeton)` donne l'adresse complète de la page.
    """
    utilisateur = get_object_or_404(get_user_model(), pk=utilisateur_id, is_staff=False, is_superuser=False,
                                    is_active=True)
    compte = getattr(utilisateur, "pharmacien", None) or getattr(utilisateur, "responsable_etablissement", None)
    if compte is None:
        raise Http404
    structure = getattr(compte, "pharmacie", None) or compte.etablissement
    lien = construire_lien(urlsafe_base64_encode(force_bytes(utilisateur.pk)),
                           default_token_generator.make_token(utilisateur))
    journal_securite.warning("Lien de mot de passe créé par %s pour %s", par, utilisateur)
    numero = "".join(c for c in (getattr(structure, "whatsapp", "") or structure.telephone) if c.isdigit())
    texte = (f"Uzima : pour choisir un nouveau mot de passe du compte « {utilisateur.get_username()} », "
             f"ouvrez ce lien (valable 24 h) : {lien}")
    return {
        "utilisateur": utilisateur, "structure": structure, "compte": compte, "lien": lien, "texte": texte,
        "whatsapp": f"https://wa.me/{numero}?text={quote(texte)}" if numero else "",
    }


def activer_abonnement(pk, reference):
    abonnement = get_object_or_404(Abonnement.objects.select_related("pharmacie"), pk=pk,
                                   statut=Abonnement.Statut.EN_ATTENTE)
    reference = (reference or "").strip()
    if not reference:
        raise ActionImpossible("Indiquez la référence de la transaction mobile money reçue.")
    abonnement.activer(reference[:60])
    return abonnement


def traiter_signalement(pk, suite):
    get_object_or_404(Signalement, pk=pk, traite=False)
    suite = (suite or "").strip()
    if not suite:
        raise ActionImpossible("Indiquez la suite donnée (ex. transmis à l'inspection, lot conforme…).")
    return Signalement.objects.filter(pk=pk).update(traite=True, suite_donnee=suite[:255])
