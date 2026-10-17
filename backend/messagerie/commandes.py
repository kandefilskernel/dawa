"""
Mise à jour du stock par SMS / WhatsApp, une commande par ligne :

    DISPO doliprane 4500     → disponible (prix facultatif, en FC)
    RUPTURE amoxicilline     → en rupture
    PRIX coartem 12000       → change le prix
    OK                       → « tout mon stock est à jour »
    AIDE                     → rappel des commandes
"""

import unicodedata

from django.utils import timezone

from catalogue.search import rechercher_medicaments
from pharmacies.models import Pharmacie
from stock.models import Stock

AIDE = (
    "Uzima - commandes :\n"
    "DISPO nom [prix]\nRUPTURE nom\nPRIX nom prix\nOK = stock à jour\n"
    "Ex : DISPO doliprane 4500"
)
MAX_LIGNES = 10


def _sans_accents(texte):
    return "".join(c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn")


def _chiffres(numero):
    return "".join(c for c in numero if c.isdigit())


def pharmacie_par_numero(numero):
    """Retrouve la pharmacie par son téléphone ou WhatsApp (9 derniers chiffres, indicatif ignoré)."""
    fin = _chiffres(numero)[-9:]
    if len(fin) < 9:
        return None
    for p in Pharmacie.objects.filter(est_validee=True).only("id", "telephone", "whatsapp", "nom"):
        if fin in (_chiffres(p.telephone)[-9:], _chiffres(p.whatsapp)[-9:]):
            return p
    return None


def _prix(mot):
    brut = mot.replace(".", "").replace(" ", "").upper().removesuffix("FC")
    return int(brut) if brut.isdigit() and 0 < int(brut) < 10_000_000 else None


def _traiter_ligne(pharmacie, ligne):
    mots = ligne.split()
    verbe = _sans_accents(mots[0]).upper()
    reste = mots[1:]

    if verbe in ("AIDE", "HELP", "?"):
        return AIDE
    if verbe in ("OK", "AJOUR"):
        nb = pharmacie.stocks.filter(disponible=True).update(mis_a_jour_le=timezone.now())
        return f"Merci ! {nb} produit(s) confirmé(s) disponibles."
    if verbe not in ("DISPO", "DISPONIBLE", "RUPTURE", "PRIX"):
        return f"? Commande inconnue « {mots[0]} ». Envoyez AIDE."

    prix = _prix(reste[-1]) if reste else None
    if prix is not None:
        reste = reste[:-1]
    nom = " ".join(reste).strip()
    if len(nom) < 2:
        return f"? Précisez le médicament. Ex : {verbe} doliprane"
    medicament = rechercher_medicaments(nom).first()
    if medicament is None:
        return f"? « {nom} » introuvable dans le catalogue."
    # « DISPO amoxicilline 500 » : 500 est le dosage, pas un prix.
    if verbe != "PRIX" and prix is not None and str(prix) in medicament.dosage.replace(" ", ""):
        medicament = rechercher_medicaments(f"{nom} {prix}").first() or medicament
        prix = None

    if verbe == "PRIX":
        if prix is None:
            return f"? Indiquez le prix. Ex : PRIX {nom} 4500"
        Stock.objects.update_or_create(
            pharmacie=pharmacie, medicament=medicament, defaults={"prix": prix, "source": Stock.Source.SMS}
        )
        return f"OK {medicament.nom_commercial} {medicament.dosage} : {prix} FC."

    disponible = verbe != "RUPTURE"
    valeurs = {"disponible": disponible, "source": Stock.Source.SMS}
    if prix is not None:
        valeurs["prix"] = prix
    Stock.objects.update_or_create(pharmacie=pharmacie, medicament=medicament, defaults=valeurs)
    etat = "disponible" if disponible else "en rupture"
    return f"OK {medicament.nom_commercial} {medicament.dosage} : {etat}" + (f", {prix} FC." if prix else ".")


def traiter_message(pharmacie, texte):
    """Applique chaque ligne du message et renvoie la réponse à envoyer (courte, pour un SMS)."""
    lignes = [l.strip() for l in texte.strip().splitlines() if l.strip()][:MAX_LIGNES]
    if not lignes:
        return AIDE
    return "\n".join(_traiter_ligne(pharmacie, l) for l in lignes)
