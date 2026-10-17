"""
Règles du portail pharmacie, partagées par les pages Django (portail/views.py) et l'API du site
Next.js (pro_api/pharmacie.py). Les erreurs à montrer au pharmacien lèvent ActionImpossible.
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.gis.measure import D
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

from abonnements.models import Abonnement
from catalogue.images import nom_fichier, preparer_photo
from conseil.models import Question
from grossistes.models import Commande, LigneCommande
from messagerie.commandes import traiter_message
from messagerie.models import MessageEntrant
from notifications.envoi import notifier_reponse
from reservations.models import Livreur, Reservation
from stock.models import Recherche, Stock

RAYON_DEMANDE_KM = 5
JOURS_DEMANDE = 30
TAILLE_MAX_PHOTO = 10 * 1024 * 1024
DUREES_ABONNEMENT = (1, 3, 6, 12)


class ActionImpossible(ValueError):
    """Demande refusée, avec un message clair pour le pharmacien."""


def reservations_actives(pharmacie):
    return pharmacie.reservations.filter(statut__in=Reservation.ACTIFS, expire_le__gt=timezone.now())


def limite_fraicheur():
    return timezone.now() - timedelta(hours=settings.STOCK_FRAICHEUR_HEURES)


def demande_proche(pharmacie, nombre=8):
    """Médicaments recherchés autour de la pharmacie qu'elle n'a pas en stock (les plus demandés d'abord)."""
    disponibles = pharmacie.stocks.filter(disponible=True).values("medicament_id")
    return (
        Recherche.objects.filter(
            cree_le__gte=timezone.now() - timedelta(days=JOURS_DEMANDE),
            medicament__isnull=False,
            zone__dwithin=(pharmacie.position, D(km=RAYON_DEMANDE_KM)),
        )
        .exclude(medicament_id__in=disponibles)
        .values("medicament_id", "medicament__nom_commercial", "medicament__dosage", "medicament__image")
        .annotate(nb=Count("id"))
        .order_by("-nb")[:nombre]
    )


def lire_prix(prix_brut):
    """Prix saisi (« 4 500 » accepté) → entier en FC, ou None si vide."""
    prix_brut = str(prix_brut or "").replace(" ", "").strip()
    if not prix_brut:
        return None
    if prix_brut.isdigit() and 0 < int(prix_brut) < 10_000_000:
        return int(prix_brut)
    raise ActionImpossible("Prix invalide (nombre entier en FC).")


def modifier_stock(pharmacie, medicament, disponible, prix_brut):
    prix = lire_prix(prix_brut)
    stock, _ = Stock.objects.update_or_create(
        pharmacie=pharmacie,
        medicament=medicament,
        defaults={"disponible": disponible, "prix": prix, "source": Stock.Source.PORTAIL},
    )
    return stock


def confirmer_stock(pharmacie):
    """« Mon stock est à jour » : rafraîchit la date de tous les produits disponibles."""
    return pharmacie.stocks.filter(disponible=True).update(mis_a_jour_le=timezone.now())


def envoyer_photo(pharmacie, medicament, fichier):
    """
    Photo de la boîte prise par le pharmacien. Elle remplace une illustration,
    jamais une vraie photo déjà en place.
    """
    if medicament.image and not medicament.image_est_illustration:
        raise ActionImpossible(f"{medicament} a déjà une photo. Contactez l'équipe Uzima pour la changer.")
    if fichier is None:
        raise ActionImpossible("Aucune photo reçue.")
    if fichier.size > TAILLE_MAX_PHOTO:
        raise ActionImpossible("Photo trop lourde (10 Mo maximum).")
    try:
        Image.open(fichier).verify()
        fichier.seek(0)
        photo = preparer_photo(fichier, nom_fichier(medicament))
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ActionImpossible("Ce fichier n'est pas une image valide.")
    if medicament.image:
        medicament.image.delete(save=False)
    medicament.image.save(photo.name, photo, save=False)
    medicament.image_est_illustration = False
    medicament.image_envoyee_par = pharmacie
    medicament.image_credit = ""
    medicament.save(update_fields=["image", "image_est_illustration", "image_envoyee_par", "image_credit"])
    return medicament


def ajouter_livreur(pharmacie, nom, telephone):
    nom, telephone = (nom or "").strip(), (telephone or "").strip()
    if len(nom) < 2 or len("".join(c for c in telephone if c.isdigit())) < 9:
        raise ActionImpossible("Indiquez le nom et un numéro de téléphone valide du livreur.")
    return Livreur.objects.create(pharmacie=pharmacie, nom=nom[:100], telephone=telephone[:20])


def retirer_livreur(pharmacie, livreur_id):
    return Livreur.objects.filter(pk=livreur_id, pharmacie=pharmacie).update(actif=False)


def repondre_question(pharmacie, question_id, reponse, orienter):
    """Vrai si la réponse est enregistrée, faux si un confrère a répondu entre-temps."""
    reponse = (reponse or "").strip()
    if len(reponse) < 5:
        raise ActionImpossible("La réponse est trop courte.")
    # Mise à jour atomique et conditionnelle : si un confrère a répondu entre-temps, on ne l'écrase pas.
    nb = Question.objects.filter(pk=question_id, statut=Question.Statut.EN_ATTENTE).update(
        reponse=reponse[:2000],
        repondu_par=pharmacie,
        repondu_le=timezone.now(),
        statut=Question.Statut.ORIENTEE if orienter else Question.Statut.REPONDUE,
    )
    if nb:
        notifier_reponse(Question.objects.get(pk=question_id))
    return bool(nb)


def formules_abonnement():
    return [
        {"code": code, "libelle": libelle.split(" — ")[0], "detail": libelle.split(" — ")[1],
         "prix": Abonnement.prix(code)}
        for code, libelle in Abonnement.Formule.choices
    ]


def demander_abonnement(pharmacie, formule, mois):
    try:
        mois = int(mois)
    except (TypeError, ValueError):
        mois = 0
    if formule not in Abonnement.Formule.values or mois not in DUREES_ABONNEMENT:
        raise ActionImpossible("Formule ou durée invalide.")
    if pharmacie.abonnements.filter(statut=Abonnement.Statut.EN_ATTENTE).exists():
        raise ActionImpossible("Une demande attend déjà son paiement : réglez-la ou contactez Uzima.")
    return Abonnement.objects.create(
        pharmacie=pharmacie, formule=formule, mois=mois, montant=Abonnement.prix(formule, mois),
        reference=f"DAWA-{pharmacie.pk}-{timezone.now():%y%m%d%H%M}",
    )


def creer_commande(pharmacie, grossiste, quantites, note=""):
    """`quantites` : {id de l'offre: quantité}. Vérifie le minimum de commande du grossiste."""
    quantites = {int(k): min(int(v), 10_000) for k, v in quantites.items() if int(v) > 0}
    choisies = list(grossiste.offres.filter(pk__in=quantites, disponible=True).select_related("medicament"))
    total = sum(o.prix * quantites[o.pk] for o in choisies)
    if not choisies:
        raise ActionImpossible("Indiquez au moins une quantité.")
    if total < grossiste.minimum_commande:
        raise ActionImpossible(f"Minimum de commande chez {grossiste} : {grossiste.minimum_commande} FC "
                               f"(actuel : {total} FC).")
    with transaction.atomic():
        commande = Commande.objects.create(pharmacie=pharmacie, grossiste=grossiste, note=(note or "").strip()[:255])
        LigneCommande.objects.bulk_create([
            LigneCommande(commande=commande, medicament=o.medicament, quantite=quantites[o.pk],
                          prix_unitaire=o.prix, conditionnement=o.conditionnement)
            for o in choisies
        ])
    return commande


def changer_commande(commande, action):
    """« annuler » (pas encore confirmée) ou « recue » (marchandise arrivée)."""
    if action == "annuler" and commande.statut == Commande.Statut.ENVOYEE:
        commande.statut = Commande.Statut.ANNULEE
    elif action == "recue" and commande.statut in (Commande.Statut.ENVOYEE, Commande.Statut.CONFIRMEE):
        commande.statut = Commande.Statut.LIVREE
    else:
        raise ActionImpossible("Action impossible pour cette commande.")
    commande.save(update_fields=["statut"])
    return commande


def simuler_sms(pharmacie, texte):
    """Applique un message comme s'il avait été reçu par SMS (les changements sont réels)."""
    texte = (texte or "")[:1600]
    reponse = traiter_message(pharmacie, texte)
    MessageEntrant.objects.create(
        canal="simulation", expediteur=pharmacie.telephone, texte=texte,
        pharmacie=pharmacie, reponse=reponse, simulation=True,
    )
    return reponse
