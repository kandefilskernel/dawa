"""
Notifications au patient : réservation qui avance, médicament redevenu disponible,
réponse d'un pharmacien. Envoyées après validation en base, dans un fil séparé
pour ne pas ralentir la page du pharmacien.
"""
import logging
import threading

from django.conf import settings
from django.db import transaction

from . import fcm
from .models import AppareilPush

logger = logging.getLogger(__name__)

# Le swahili est à faire relire, comme celui de l'app.
MESSAGES = {
    "reservation_acceptee": {
        "fr": ("Réservation acceptée", "{pharmacie} prépare votre {medicament}."),
        "sw": ("Oda imekubaliwa", "{pharmacie} inaandaa {medicament} yako."),
        "en": ("Reservation accepted", "{pharmacie} is preparing your {medicament}."),
    },
    "reservation_prete": {
        "fr": ("Votre médicament est prêt", "{medicament} vous attend à {pharmacie} pendant 2 heures."),
        "sw": ("Dawa yako iko tayari", "{medicament} inakusubiri {pharmacie} kwa saa 2."),
        "en": ("Your medicine is ready", "{medicament} is waiting for you at {pharmacie} for 2 hours."),
    },
    "reservation_prete_livraison": {
        "fr": ("Commande prête", "{pharmacie} a préparé {medicament} : le livreur part bientôt."),
        "sw": ("Oda iko tayari", "{pharmacie} imeandaa {medicament}: mpelekaji ataondoka hivi karibuni."),
        "en": ("Order ready", "{pharmacie} has prepared {medicament}: the courier leaves soon."),
    },
    "reservation_en_livraison": {
        "fr": ("Livreur en route", "{medicament} arrive de {pharmacie}."),
        "sw": ("Mpelekaji yuko njiani", "{medicament} inakuja kutoka {pharmacie}."),
        "en": ("Courier on the way", "{medicament} is coming from {pharmacie}."),
    },
    "reservation_refusee": {
        "fr": ("Réservation refusée", "{pharmacie} ne peut pas vous servir {medicament}. Cherchez une autre pharmacie dans Uzima."),
        "sw": ("Oda imekataliwa", "{pharmacie} haiwezi kukupa {medicament}. Tafuta duka lingine la dawa kwenye Uzima."),
        "en": ("Reservation declined", "{pharmacie} can't supply {medicament}. Find another pharmacy in Uzima."),
    },
    "alerte": {
        "fr": ("{medicament} est disponible", "Disponible maintenant à {pharmacie}."),
        "sw": ("{medicament} inapatikana", "Inapatikana sasa {pharmacie}."),
        "en": ("{medicament} is available", "Now available at {pharmacie}."),
    },
    "question": {
        "fr": ("Un pharmacien vous a répondu", "Ouvrez Uzima pour lire la réponse."),
        "sw": ("Mfamasia amekujibu", "Fungua Uzima usome jibu."),
        "en": ("A pharmacist has replied", "Open Uzima to read the answer."),
    },
}


def nom_medicament(medicament):
    return " ".join(s for s in (medicament.nom_commercial, medicament.dosage) if s)


def _envoyer_a(client_id, cle, valeurs, donnees):
    for appareil in AppareilPush.objects.filter(client_id=client_id):
        titre, corps = MESSAGES[cle].get(appareil.langue, MESSAGES[cle]["fr"])
        try:
            fcm.envoyer(appareil.jeton, titre.format(**valeurs), corps.format(**valeurs), donnees)
        except fcm.JetonPerime:
            appareil.delete()
        except Exception:  # Une notification ratée ne doit jamais casser l'action du pharmacien.
            logger.exception("Notification « %s » non envoyée", cle)


def notifier(client_id, cle, valeurs, donnees):
    """Prévient tous les téléphones de cet appareil, une fois la transaction validée."""
    if not fcm.actif():
        return

    def lancer():
        if settings.NOTIFICATIONS_SYNCHRONES:
            _envoyer_a(client_id, cle, valeurs, donnees)
        else:
            threading.Thread(target=_envoyer_a, args=(client_id, cle, valeurs, donnees), daemon=True).start()

    transaction.on_commit(lancer)


def notifier_reservation(reservation):
    from reservations.models import Reservation

    Statut = Reservation.Statut
    cle = {
        Statut.ACCEPTEE: "reservation_acceptee",
        Statut.PRETE: "reservation_prete_livraison" if reservation.est_livraison else "reservation_prete",
        Statut.EN_LIVRAISON: "reservation_en_livraison",
        Statut.REFUSEE: "reservation_refusee",
    }.get(reservation.statut)
    if cle:
        notifier(reservation.client_id, cle,
                 {"medicament": nom_medicament(reservation.medicament), "pharmacie": reservation.pharmacie.nom},
                 {"type": "reservation", "id": reservation.pk})


def notifier_alerte(alerte, stock):
    """`stock` peut porter un équivalent du médicament demandé : on annonce celui qui est en rayon."""
    notifier(alerte.client_id, "alerte",
             {"medicament": nom_medicament(stock.medicament), "pharmacie": stock.pharmacie.nom},
             {"type": "alerte", "id": alerte.pk})


def notifier_reponse(question):
    notifier(question.client_id, "question", {}, {"type": "question", "id": question.pk})
