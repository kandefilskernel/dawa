from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView
from django.contrib.gis.measure import D
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from PIL import Image, UnidentifiedImageError

from abonnements.models import Abonnement
from catalogue.images import nom_fichier, preparer_photo
from catalogue.models import Medicament
from catalogue.search import rechercher_medicaments
from config.securite import compter, limite_atteinte
from conseil.assistant import AssistantIndisponible, assistant_actif, suggerer_reponse
from conseil.models import Question
from notifications.envoi import notifier_reponse
from grossistes.models import Commande, Grossiste, LigneCommande, Offre
from kyc.dossier import Dossier, PieceForm
from messagerie.commandes import traiter_message
from messagerie.models import MessageEntrant
from reservations.models import Livreur, Reservation
from stock.models import Recherche, Stock

from .forms import InscriptionForm, ProfilForm

RAYON_DEMANDE_KM = 5
MAX_INSCRIPTIONS_PAR_HEURE = 5
JOURS_DEMANDE = 30


def pharmacien_requis(vue):
    """Connexion obligatoire + compte rattaché à une pharmacie. Expose `request.pharmacie`."""

    @login_required
    @wraps(vue)
    def enveloppe(request, *args, **kwargs):
        pharmacien = getattr(request.user, "pharmacien", None)
        if pharmacien is None:
            if request.user.is_staff:
                return redirect("gestion:tableau")  # équipe Dawa : vers l'espace de gestion
            if hasattr(request.user, "responsable_etablissement"):
                return redirect("etablissement:espace")
            return render(request, "portail/acces_refuse.html", status=403)
        if not pharmacien.actif:
            # Inscription en attente, refusée ou compte suspendu : seule la page de statut est accessible.
            return render(request, "portail/compte_statut.html", _contexte_dossier(pharmacien), status=403)
        request.dossier_incomplet = bool(Dossier(pharmacien.pharmacie.pieces.all()).manquantes)
        request.pharmacie = pharmacien.pharmacie
        request.nb_a_traiter = _reservations_actives(request.pharmacie).filter(
            statut=Reservation.Statut.EN_ATTENTE
        ).count()
        request.nb_questions = Question.objects.filter(statut=Question.Statut.EN_ATTENTE).count()
        return vue(request, *args, **kwargs)

    return enveloppe


def _contexte_dossier(pharmacien, form=None):
    return {"pharmacien": pharmacien, "dossier": Dossier(pharmacien.pharmacie.pieces.all()),
            "action": reverse("portail:dossier"), "form_piece": form}


@login_required
def dossier(request):
    """Pièces justificatives (KYC) : accessible quel que soit le statut du compte, pour compléter le dossier."""
    pharmacien = getattr(request.user, "pharmacien", None)
    if pharmacien is None:
        return render(request, "portail/acces_refuse.html", status=403)
    formulaire = None
    if request.method == "POST":
        formulaire = PieceForm(request.POST, request.FILES)
        if formulaire.is_valid():
            formulaire.enregistrer(pharmacie=pharmacien.pharmacie)
            messages.success(request, "Document envoyé. L'équipe Dawa va le vérifier.")
            return redirect("portail:dossier")
        messages.error(request, " ".join(e for erreurs in formulaire.errors.values() for e in erreurs))
    if not pharmacien.actif:
        return render(request, "portail/compte_statut.html", _contexte_dossier(pharmacien, formulaire), status=403)
    request.pharmacie = pharmacien.pharmacie
    return render(request, "portail/dossier.html", {**_contexte_dossier(pharmacien, formulaire), "onglet": "profil"})


class MotDePasseOublie(PasswordResetView):
    """« Mot de passe oublié » limité par adresse IP (pas d'envoi massif d'e-mails)."""

    template_name = "portail/mot_de_passe/oublie.html"
    email_template_name = "portail/mot_de_passe/email.txt"
    subject_template_name = "portail/mot_de_passe/email_sujet.txt"
    success_url = reverse_lazy("portail:mot_de_passe_envoye")

    def form_valid(self, form):
        if limite_atteinte(self.request, "mot_de_passe_oublie", 5):
            # Même réponse qu'un envoi réussi : ne révèle rien sur les comptes existants.
            return redirect(self.success_url)
        compter(self.request, "mot_de_passe_oublie")
        return super().form_valid(form)


def inscription(request):
    """Inscription en ligne d'une pharmacie : compte créé en attente de validation par l'équipe Dawa."""
    if request.user.is_authenticated:
        return redirect("portail:tableau")
    formulaire = InscriptionForm(request.POST or None)
    if request.method == "POST" and limite_atteinte(request, "inscription", MAX_INSCRIPTIONS_PAR_HEURE):
        formulaire.add_error(None, "Trop d'inscriptions depuis cette connexion. Réessayez dans une heure.")
    elif request.method == "POST" and formulaire.is_valid():
        pharmacien = formulaire.save()
        compter(request, "inscription")
        login(request, pharmacien.utilisateur)
        return redirect("portail:tableau")
    return render(request, "portail/inscription.html", {"form": formulaire})


def _rediriger(request, defaut):
    """Retourne à la page d'origine, uniquement si elle appartient à ce site."""
    retour = request.POST.get("retour", "")
    if url_has_allowed_host_and_scheme(retour, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(retour)
    return redirect(defaut)


def _reservations_actives(pharmacie):
    return pharmacie.reservations.filter(statut__in=Reservation.ACTIFS, expire_le__gt=timezone.now())


def _limite_fraicheur():
    return timezone.now() - timedelta(hours=settings.STOCK_FRAICHEUR_HEURES)


@pharmacien_requis
def tableau_de_bord(request):
    p = request.pharmacie
    actives = _reservations_actives(p)
    stocks = p.stocks.all()

    # Médicaments recherchés autour de la pharmacie qu'elle n'a pas en stock.
    disponibles = stocks.filter(disponible=True).values("medicament_id")
    demande = (
        Recherche.objects.filter(
            cree_le__gte=timezone.now() - timedelta(days=JOURS_DEMANDE),
            medicament__isnull=False,
            zone__dwithin=(p.position, D(km=RAYON_DEMANDE_KM)),
        )
        .exclude(medicament_id__in=disponibles)
        .values("medicament_id", "medicament__nom_commercial", "medicament__dosage", "medicament__image")
        .annotate(nb=Count("id"))
        .order_by("-nb")[:8]
    )

    return render(request, "portail/tableau.html", {
        "onglet": "tableau",
        "nb_en_attente": request.nb_a_traiter,
        "nb_en_cours": actives.exclude(statut=Reservation.Statut.EN_ATTENTE).count(),
        "nb_disponibles": stocks.filter(disponible=True).count(),
        "nb_ruptures": stocks.filter(disponible=False).count(),
        "nb_a_confirmer": stocks.filter(disponible=True, mis_a_jour_le__lt=_limite_fraicheur()).count(),
        "dernieres": actives.select_related("medicament")[:5],
        "demande": demande,
        "rayon_demande": RAYON_DEMANDE_KM,
        "Statut": Reservation.Statut,
        "livreurs": p.livreurs.filter(actif=True),
        "jours_demande": JOURS_DEMANDE,
    })


ONGLETS_RESERVATIONS = {
    "a_traiter": "À traiter",
    "en_cours": "En cours",
    "historique": "Historique",
}


@pharmacien_requis
def reservations(request):
    p = request.pharmacie
    onglet = request.GET.get("onglet", "a_traiter")
    if onglet not in ONGLETS_RESERVATIONS:
        onglet = "a_traiter"

    actives = _reservations_actives(p)
    if onglet == "a_traiter":
        liste = actives.filter(statut=Reservation.Statut.EN_ATTENTE).order_by("cree_le")
    elif onglet == "en_cours":
        liste = actives.exclude(statut=Reservation.Statut.EN_ATTENTE).order_by("expire_le")
    else:
        liste = p.reservations.exclude(pk__in=actives.values("pk")).order_by("-cree_le")

    return render(request, "portail/reservations.html", {
        "onglet": "reservations",
        "sous_onglet": onglet,
        "sous_onglets": ONGLETS_RESERVATIONS,
        "reservations": liste.select_related("medicament", "livreur")[:50],
        "livreurs": p.livreurs.filter(actif=True),
        "Statut": Reservation.Statut,
    })


@pharmacien_requis
@require_POST
def changer_statut_reservation(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk, pharmacie=request.pharmacie)
    livreur = None
    if request.POST.get("livreur"):
        livreur = Livreur.objects.filter(pk=request.POST["livreur"], pharmacie=request.pharmacie).first()
    try:
        reservation.changer_statut(
            request.POST.get("statut", ""), request.POST.get("message", "").strip(), livreur=livreur
        )
        messages.success(request, f"Réservation de {reservation.nom} : {reservation.get_statut_display().lower()}.")
    except ValueError as erreur:
        messages.error(request, str(erreur))
    return _rediriger(request, "portail:reservations")


FILTRES_STOCK = {
    "tous": "Tout le catalogue",
    "dispo": "En stock",
    "rupture": "En rupture",
    "a_confirmer": "À confirmer",
    "absent": "Non référencés",
}


@pharmacien_requis
def stock(request):
    p = request.pharmacie
    filtre = request.GET.get("filtre", "tous")
    q = request.GET.get("q", "").strip()

    medicaments = rechercher_medicaments(q) if len(q) >= 2 else Medicament.objects.order_by("nom_commercial")
    limite = _limite_fraicheur()

    if filtre == "dispo":
        medicaments = medicaments.filter(stocks__pharmacie=p, stocks__disponible=True)
    elif filtre == "rupture":
        medicaments = medicaments.filter(stocks__pharmacie=p, stocks__disponible=False)
    elif filtre == "a_confirmer":
        medicaments = medicaments.filter(
            stocks__pharmacie=p, stocks__disponible=True, stocks__mis_a_jour_le__lt=limite
        )
    elif filtre == "absent":
        medicaments = medicaments.exclude(stocks__pharmacie=p)

    page = Paginator(medicaments, 40).get_page(request.GET.get("page"))
    stocks = {s.medicament_id: s for s in p.stocks.filter(medicament_id__in=[m.id for m in page])}
    lignes = [
        {
            "medicament": m,
            "stock": stocks.get(m.id),
            "a_confirmer": m.id in stocks and stocks[m.id].disponible and stocks[m.id].mis_a_jour_le < limite,
        }
        for m in page
    ]
    return render(request, "portail/stock.html", {
        "onglet": "stock",
        "lignes": lignes,
        "page": page,
        "filtre": filtre,
        "filtres": FILTRES_STOCK,
        "q": q,
        "nb_a_confirmer": p.stocks.filter(disponible=True, mis_a_jour_le__lt=limite).count(),
    })


@pharmacien_requis
@require_POST
def modifier_stock(request, medicament_id):
    medicament = get_object_or_404(Medicament, pk=medicament_id)
    disponible = request.POST.get("disponible") == "1"
    prix_brut = request.POST.get("prix", "").replace(" ", "").strip()
    erreur = None
    prix = None
    if prix_brut:
        if prix_brut.isdigit() and 0 < int(prix_brut) < 10_000_000:
            prix = int(prix_brut)
        else:
            erreur = "Prix invalide (nombre entier en FC)."

    if erreur is None:
        Stock.objects.update_or_create(
            pharmacie=request.pharmacie,
            medicament=medicament,
            defaults={"disponible": disponible, "prix": prix, "source": Stock.Source.PORTAIL},
        )

    if request.headers.get("X-Requested-With") == "fetch":
        if erreur:
            return JsonResponse({"ok": False, "erreur": erreur}, status=400)
        return JsonResponse({"ok": True, "disponible": disponible, "prix": prix})
    if erreur:
        messages.error(request, erreur)
    else:
        messages.success(request, f"{medicament} : mis à jour.")
    return _rediriger(request, "portail:stock")


TAILLE_MAX_PHOTO = 10 * 1024 * 1024


@pharmacien_requis
@require_POST
def envoyer_photo(request, medicament_id):
    """
    Le pharmacien photographie la boîte depuis son téléphone.
    La photo remplace une illustration, jamais une vraie photo déjà en place.
    """
    medicament = get_object_or_404(Medicament, pk=medicament_id)
    fichier = request.FILES.get("photo")
    if medicament.image and not medicament.image_est_illustration:
        messages.error(request, f"{medicament} a déjà une photo. Contactez l'équipe Dawa pour la changer.")
    elif fichier is None:
        messages.error(request, "Aucune photo reçue.")
    elif fichier.size > TAILLE_MAX_PHOTO:
        messages.error(request, "Photo trop lourde (10 Mo maximum).")
    else:
        try:
            Image.open(fichier).verify()
            fichier.seek(0)
            photo = preparer_photo(fichier, nom_fichier(medicament))
        except (UnidentifiedImageError, OSError, SyntaxError):
            messages.error(request, "Ce fichier n'est pas une image valide.")
        else:
            if medicament.image:
                medicament.image.delete(save=False)
            medicament.image.save(photo.name, photo, save=False)
            medicament.image_est_illustration = False
            medicament.image_envoyee_par = request.pharmacie
            medicament.image_credit = ""
            medicament.save(update_fields=["image", "image_est_illustration", "image_envoyee_par", "image_credit"])
            messages.success(request, f"Merci ! La photo de {medicament} est en ligne pour tous les patients.")
    return _rediriger(request, "portail:stock")


@pharmacien_requis
@require_POST
def confirmer_stock(request):
    """« Mon stock est à jour » : rafraîchit la date de tous les produits disponibles."""
    nb = request.pharmacie.stocks.filter(disponible=True).update(mis_a_jour_le=timezone.now())
    messages.success(request, f"{nb} produit(s) confirmé(s) disponibles. Merci !")
    return _rediriger(request, "portail:stock")


@pharmacien_requis
@require_POST
def livreurs(request):
    """Ajouter ou désactiver un livreur de la pharmacie."""
    if request.POST.get("action") == "ajouter":
        nom = request.POST.get("nom", "").strip()
        telephone = request.POST.get("telephone", "").strip()
        if len(nom) < 2 or len("".join(c for c in telephone if c.isdigit())) < 9:
            messages.error(request, "Indiquez le nom et un numéro de téléphone valide du livreur.")
        else:
            Livreur.objects.create(pharmacie=request.pharmacie, nom=nom, telephone=telephone)
            messages.success(request, f"{nom} ajouté : vos clients peuvent maintenant choisir la livraison.")
    elif request.POST.get("action") == "retirer":
        Livreur.objects.filter(pk=request.POST.get("livreur"), pharmacie=request.pharmacie).update(actif=False)
        messages.success(request, "Livreur retiré.")
    return redirect("portail:profil")


@pharmacien_requis
def profil(request):
    p = request.pharmacie
    formulaire = ProfilForm(request.POST or None, instance=p)
    if request.method == "POST" and formulaire.is_valid():
        formulaire.save()
        messages.success(request, "Profil enregistré.")
        return redirect("portail:profil")
    return render(request, "portail/profil.html", {
        "onglet": "profil",
        "form": formulaire,
        "gardes": p.gardes.filter(fin__gt=timezone.now()).order_by("debut")[:10],
        "maintenant": timezone.now(),
        "livreurs": p.livreurs.filter(actif=True),
    })


@pharmacien_requis
def questions(request):
    """Questions des patients, partagées entre toutes les pharmacies partenaires."""
    return render(request, "portail/questions.html", {
        "onglet": "questions",
        "en_attente": Question.objects.filter(statut=Question.Statut.EN_ATTENTE)
        .select_related("medicament").order_by("cree_le")[:30],
        "mes_reponses": Question.objects.filter(repondu_par=request.pharmacie)
        .select_related("medicament").order_by("-repondu_le")[:10],
        "assistant_ia": assistant_actif(),
    })


@pharmacien_requis
@require_POST
def suggerer_reponse_question(request, pk):
    """Brouillon de réponse proposé par l'assistant IA ; le pharmacien le relit avant d'envoyer."""
    question = get_object_or_404(Question.objects.select_related("medicament"), pk=pk,
                                 statut=Question.Statut.EN_ATTENTE)
    try:
        suggestion = suggerer_reponse(question)
    except AssistantIndisponible as e:
        return JsonResponse({"erreur": str(e)}, status=503)
    return JsonResponse({"reponse": suggestion.reponse, "orienter": suggestion.orienter_medecin})


@pharmacien_requis
@require_POST
def repondre_question(request, pk):
    reponse = request.POST.get("reponse", "").strip()
    if len(reponse) < 5:
        messages.error(request, "La réponse est trop courte.")
        return redirect("portail:questions")
    # Mise à jour atomique et conditionnelle : si un confrère a répondu entre-temps, on ne l'écrase pas.
    orienter = request.POST.get("orienter") == "1"
    nb = Question.objects.filter(pk=pk, statut=Question.Statut.EN_ATTENTE).update(
        reponse=reponse[:2000],
        repondu_par=request.pharmacie,
        repondu_le=timezone.now(),
        statut=Question.Statut.ORIENTEE if orienter else Question.Statut.REPONDUE,
    )
    if nb:
        notifier_reponse(Question.objects.get(pk=pk))
        messages.success(request, "Réponse envoyée au patient. Merci !")
    else:
        messages.warning(request, "Un confrère a déjà répondu à cette question.")
    return redirect("portail:questions")


@pharmacien_requis
def abonnement(request):
    p = request.pharmacie
    if request.method == "POST":
        formule = request.POST.get("formule")
        mois = int(request.POST.get("mois", "1")) if request.POST.get("mois", "1").isdigit() else 1
        if formule not in Abonnement.Formule.values or mois not in (1, 3, 6, 12):
            messages.error(request, "Formule ou durée invalide.")
        elif p.abonnements.filter(statut=Abonnement.Statut.EN_ATTENTE).exists():
            messages.warning(request, "Une demande attend déjà son paiement : réglez-la ou contactez Dawa.")
        else:
            reference = f"DAWA-{p.pk}-{timezone.now():%y%m%d%H%M}"
            Abonnement.objects.create(
                pharmacie=p, formule=formule, mois=mois, montant=Abonnement.prix(formule, mois), reference=reference
            )
            messages.success(request, f"Demande enregistrée. Payez avec la référence {reference}.")
        return redirect("portail:abonnement")

    actif = Abonnement.objects.actifs().filter(pharmacie=p).order_by("-fin").first()
    return render(request, "portail/abonnement.html", {
        "onglet": "profil",
        "actif": actif,
        "en_attente": p.abonnements.filter(statut=Abonnement.Statut.EN_ATTENTE).first(),
        "historique": p.abonnements.all()[:12],
        "formules": [
            {"code": code, "libelle": libelle.split(" — ")[0], "detail": libelle.split(" — ")[1],
             "prix": Abonnement.prix(code)}
            for code, libelle in Abonnement.Formule.choices
        ],
        "numero_paiement": settings.DAWA_NUMERO_PAIEMENT,
    })


@pharmacien_requis
def commandes(request):
    return render(request, "portail/commandes.html", {
        "onglet": "stock",
        "commandes": request.pharmacie.commandes.select_related("grossiste").prefetch_related("lignes")[:30],
        "grossistes": Grossiste.objects.filter(actif=True),
    })


@pharmacien_requis
def nouvelle_commande(request, grossiste_id):
    grossiste = get_object_or_404(Grossiste, pk=grossiste_id, actif=True)
    offres = grossiste.offres.filter(disponible=True).select_related("medicament")
    q = request.GET.get("q", "").strip()
    if len(q) >= 2:
        offres = offres.filter(medicament__in=rechercher_medicaments(q))

    if request.method == "POST":
        quantites = {}
        for cle, valeur in request.POST.items():
            if cle.startswith("qte_") and valeur.strip().isdigit() and int(valeur) > 0:
                quantites[int(cle[4:])] = min(int(valeur), 10_000)
        choisies = list(grossiste.offres.filter(pk__in=quantites, disponible=True).select_related("medicament"))
        total = sum(o.prix * quantites[o.pk] for o in choisies)
        if not choisies:
            messages.error(request, "Indiquez au moins une quantité.")
        elif total < grossiste.minimum_commande:
            messages.error(request, f"Minimum de commande chez {grossiste} : {grossiste.minimum_commande} FC (actuel : {total} FC).")
        else:
            with transaction.atomic():
                commande = Commande.objects.create(
                    pharmacie=request.pharmacie, grossiste=grossiste, note=request.POST.get("note", "").strip()[:255]
                )
                LigneCommande.objects.bulk_create([
                    LigneCommande(commande=commande, medicament=o.medicament, quantite=quantites[o.pk],
                                  prix_unitaire=o.prix, conditionnement=o.conditionnement)
                    for o in choisies
                ])
            messages.success(request, f"Commande n° {commande.pk} enregistrée. Envoyez-la au grossiste par WhatsApp.")
            return redirect("portail:commande", pk=commande.pk)

    # Suggestions : produits en rupture chez moi que ce grossiste propose.
    ruptures = set(request.pharmacie.stocks.filter(disponible=False).values_list("medicament_id", flat=True))
    return render(request, "portail/nouvelle_commande.html", {
        "onglet": "stock",
        "grossiste": grossiste,
        "offres": offres,
        "ruptures": ruptures,
        "q": q,
    })


@pharmacien_requis
def commande(request, pk):
    commande = get_object_or_404(Commande.objects.select_related("grossiste"), pk=pk, pharmacie=request.pharmacie)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "annuler" and commande.statut == Commande.Statut.ENVOYEE:
            commande.statut = Commande.Statut.ANNULEE
        elif action == "recue" and commande.statut in (Commande.Statut.ENVOYEE, Commande.Statut.CONFIRMEE):
            commande.statut = Commande.Statut.LIVREE
        else:
            messages.error(request, "Action impossible pour cette commande.")
            return redirect("portail:commande", pk=pk)
        commande.save(update_fields=["statut"])
        messages.success(request, f"Commande n° {pk} : {commande.get_statut_display().lower()}.")
        return redirect("portail:commande", pk=pk)
    return render(request, "portail/commande.html", {
        "onglet": "stock",
        "commande": commande,
        "lignes": commande.lignes.select_related("medicament"),
    })


@pharmacien_requis
@require_POST
def tester_sms(request):
    """Simulateur : applique un message comme s'il avait été reçu par SMS (les changements sont réels)."""
    texte = request.POST.get("texte", "")[:1600]
    reponse = traiter_message(request.pharmacie, texte)
    MessageEntrant.objects.create(
        canal="simulation", expediteur=request.pharmacie.telephone, texte=texte,
        pharmacie=request.pharmacie, reponse=reponse, simulation=True,
    )
    messages.info(request, f"Réponse Dawa : {reponse}")
    return redirect("portail:profil")
