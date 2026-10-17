"""Mise en forme JSON des objets communs aux trois espaces (médicament, dossier KYC…)."""
from django.conf import settings

from kyc.dossier import Dossier, PieceForm

from .base import erreur_formulaire


def image(champ):
    """Adresse relative de l'image (« /media/… »), servie par Django à travers le site."""
    return champ.url if champ else None


def medicament(m):
    return {
        "id": m.pk,
        "nom_commercial": m.nom_commercial,
        "dosage": m.dosage,
        "dci": m.dci,
        "forme": m.get_forme_display(),
        "ordonnance_requise": m.ordonnance_requise,
        "image": image(m.image),
        # Le pharmacien peut photographier la boîte s'il n'y a qu'une illustration (ou rien).
        "photo_possible": not m.image or m.image_est_illustration,
    }


def adresse_site(chemin):
    """Adresse complète d'une page (ex. lien du livreur à envoyer par WhatsApp)."""
    return f"{settings.UZIMA_WEB_URL}{chemin}"


def piece(p):
    if p is None:
        return None
    return {"id": p.pk, "statut": p.statut, "statut_libelle": p.get_statut_display(),
            "envoyee_le": p.envoyee_le, "nom_original": p.nom_original, "motif": p.motif}


def dossier(pieces):
    d = Dossier(pieces)
    return {
        "lignes": [{"type": l.type, "libelle": l.libelle, "aide": l.aide, "obligatoire": l.obligatoire,
                    "piece": piece(l.piece)} for l in d.lignes],
        "manquantes": d.manquantes,
        "verifie": d.verifie,
        "a_verifier": len(d.a_verifier),
    }


def enregistrer_piece(request, **structure):
    """Pièce justificative envoyée en multipart (champs « type » et « fichier »)."""
    formulaire = PieceForm(request.data, request.FILES)
    if not formulaire.is_valid():
        raise erreur_formulaire(formulaire)
    return formulaire.enregistrer(**structure)
