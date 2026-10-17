"""API du portail pharmacie (/api/web/pharmacie/) : mêmes règles que les pages Django de portail/."""
from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from abonnements.models import Abonnement
from catalogue.models import Medicament
from catalogue.search import rechercher_medicaments
from conseil.assistant import AssistantIndisponible, assistant_actif, suggerer_reponse
from conseil.models import Question
from grossistes.models import Commande, Grossiste
from kyc.dossier import Dossier
from portail import services
from portail.forms import ProfilForm
from portail.services import ActionImpossible
from reservations.models import Livreur, Reservation

from . import donnees
from .base import VueWeb, erreur, erreur_formulaire

FILTRES_STOCK = ("tous", "dispo", "rupture", "a_confirmer", "absent")
ONGLETS_RESERVATIONS = ("a_traiter", "en_cours", "historique")
STOCK_PAR_PAGE = 40


class VuePharmacie(VueWeb):
    """Réservée au pharmacien d'un compte actif. Expose `self.pharmacien` et `self.pharmacie`."""

    compte_actif_requis = True

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not request.user.is_authenticated:
            raise NotAuthenticated("Connectez-vous pour accéder au portail.")
        self.pharmacien = getattr(request.user, "pharmacien", None)
        if self.pharmacien is None:
            raise PermissionDenied("Ce compte n'est pas rattaché à une pharmacie.")
        if self.compte_actif_requis and not self.pharmacien.actif:
            raise PermissionDenied("Compte pas encore validé ou suspendu.")
        self.pharmacie = self.pharmacien.pharmacie


def _action(fonction, *args):
    """Exécute une règle du portail ; son refus devient une erreur 400 lisible."""
    try:
        return fonction(*args)
    except ActionImpossible as e:
        raise erreur(str(e))


# --- Mise en forme ---

def livreur_json(l):
    return {"id": l.pk, "nom": l.nom, "telephone": l.telephone, "lien": donnees.adresse_site(l.lien_page)}


def reservation_json(r):
    effectif = r.statut_effectif
    return {
        "id": r.pk,
        "statut": effectif,
        "statut_libelle": Reservation.Statut(effectif).label if effectif != r.statut else r.get_statut_display(),
        "expiree": effectif == Reservation.Statut.EXPIREE,
        "est_active": r.est_active,
        "transitions": [str(t) for t in r.transitions_possibles],
        "cree_le": r.cree_le,
        "expire_le": r.expire_le,
        "nom": r.nom,
        "telephone": r.telephone,
        "quantite": r.quantite,
        "message_pharmacie": r.message_pharmacie,
        "medicament": donnees.medicament(r.medicament),
        "est_livraison": r.est_livraison,
        "adresse_livraison": r.adresse_livraison,
        "position_livraison": ({"lat": r.position_livraison.y, "lng": r.position_livraison.x}
                               if r.position_livraison else None),
        "frais_livraison": r.frais_livraison,
        "livreur": livreur_json(r.livreur) if r.livreur else None,
    }


def stock_json(s):
    if s is None:
        return None
    return {"disponible": s.disponible, "prix": s.prix, "mis_a_jour_le": s.mis_a_jour_le}


def fiche_json(p):
    return {"nom": p.nom, "numero_agrement": p.numero_agrement, "telephone": p.telephone, "whatsapp": p.whatsapp,
            "horaires": p.horaires, "adresse": p.adresse, "quartier": p.quartier}


def abonnement_json(a):
    if a is None:
        return None
    return {"id": a.pk, "formule": a.formule, "formule_libelle": a.get_formule_display().split(" — ")[0],
            "mois": a.mois, "montant": a.montant, "reference": a.reference, "statut": a.statut,
            "statut_libelle": a.get_statut_display(), "debut": a.debut, "fin": a.fin}


def commande_json(c, detail=False):
    lignes = list(c.lignes.all())
    infos = {
        "id": c.pk, "grossiste": {"id": c.grossiste_id, "nom": c.grossiste.nom}, "cree_le": c.cree_le,
        "statut": c.statut, "statut_libelle": c.get_statut_display(), "note": c.note,
        "nb_produits": len(lignes), "total": sum(l.sous_total for l in lignes),
    }
    if detail:
        infos["lignes"] = [{"quantite": l.quantite, "medicament": donnees.medicament(l.medicament),
                            "conditionnement": l.conditionnement, "prix_unitaire": l.prix_unitaire,
                            "sous_total": l.sous_total} for l in lignes]
        infos["whatsapp"] = c.message_whatsapp() if c.statut == Commande.Statut.ENVOYEE else None
        infos["actions"] = (["recue", "annuler"] if c.statut == Commande.Statut.ENVOYEE
                            else ["recue"] if c.statut == Commande.Statut.CONFIRMEE else [])
    return infos


# --- Vues ---

class ResumeView(VuePharmacie):
    """Pastilles de la navigation et bandeau « dossier incomplet », affichés sur toutes les pages."""

    def get(self, request):
        return Response({
            "pharmacie": {"id": self.pharmacie.pk, "nom": self.pharmacie.nom},
            "nb_a_traiter": services.reservations_actives(self.pharmacie)
            .filter(statut=Reservation.Statut.EN_ATTENTE).count(),
            "nb_questions": Question.objects.filter(statut=Question.Statut.EN_ATTENTE).count(),
            "dossier_incomplet": bool(Dossier(self.pharmacie.pieces.all()).manquantes),
        })


class TableauView(VuePharmacie):
    def get(self, request):
        p = self.pharmacie
        actives = services.reservations_actives(p)
        stocks = p.stocks.all()
        demande = list(services.demande_proche(p))
        return Response({
            "nb_en_attente": actives.filter(statut=Reservation.Statut.EN_ATTENTE).count(),
            "nb_en_cours": actives.exclude(statut=Reservation.Statut.EN_ATTENTE).count(),
            "nb_disponibles": stocks.filter(disponible=True).count(),
            "nb_ruptures": stocks.filter(disponible=False).count(),
            "nb_a_confirmer": stocks.filter(disponible=True, mis_a_jour_le__lt=services.limite_fraicheur()).count(),
            "demande": [{
                "medicament_id": d["medicament_id"], "nom": d["medicament__nom_commercial"],
                "dosage": d["medicament__dosage"],
                "image": f"{settings.MEDIA_URL}{d['medicament__image']}" if d["medicament__image"] else None,
                "nb": d["nb"],
            } for d in demande],
            "rayon_km": services.RAYON_DEMANDE_KM,
            "jours": services.JOURS_DEMANDE,
            "dernieres": [reservation_json(r) for r in actives.select_related("medicament", "livreur")[:5]],
            "livreurs": [livreur_json(l) for l in p.livreurs.filter(actif=True)],
        })


class ReservationsView(VuePharmacie):
    def get(self, request):
        p = self.pharmacie
        onglet = request.query_params.get("onglet", "a_traiter")
        if onglet not in ONGLETS_RESERVATIONS:
            onglet = "a_traiter"
        actives = services.reservations_actives(p)
        if onglet == "a_traiter":
            liste = actives.filter(statut=Reservation.Statut.EN_ATTENTE).order_by("cree_le")
        elif onglet == "en_cours":
            liste = actives.exclude(statut=Reservation.Statut.EN_ATTENTE).order_by("expire_le")
        else:
            liste = p.reservations.exclude(pk__in=actives.values("pk")).order_by("-cree_le")
        return Response({
            "onglet": onglet,
            "nb_a_traiter": actives.filter(statut=Reservation.Statut.EN_ATTENTE).count(),
            "reservations": [reservation_json(r) for r in liste.select_related("medicament", "livreur")[:50]],
            "livreurs": [livreur_json(l) for l in p.livreurs.filter(actif=True)],
        })


class StatutReservationView(VuePharmacie):
    """Accepter, refuser (avec motif), marquer prête, partir en livraison (avec un livreur), retirée, livrée."""

    def post(self, request, pk):
        reservation = get_object_or_404(Reservation.objects.select_related("medicament"), pk=pk,
                                        pharmacie=self.pharmacie)
        livreur = None
        if request.data.get("livreur"):
            livreur = Livreur.objects.filter(pk=request.data["livreur"], pharmacie=self.pharmacie).first()
        try:
            reservation.changer_statut(str(request.data.get("statut", "")),
                                       str(request.data.get("message", "")).strip(), livreur=livreur)
        except ValueError as e:
            raise erreur(str(e))
        return Response(reservation_json(reservation))


class StockView(VuePharmacie):
    def get(self, request):
        p = self.pharmacie
        filtre = request.query_params.get("filtre", "tous")
        if filtre not in FILTRES_STOCK:
            filtre = "tous"
        q = request.query_params.get("q", "").strip()
        medicaments = rechercher_medicaments(q) if len(q) >= 2 else Medicament.objects.order_by("nom_commercial")
        limite = services.limite_fraicheur()
        if filtre == "dispo":
            medicaments = medicaments.filter(stocks__pharmacie=p, stocks__disponible=True)
        elif filtre == "rupture":
            medicaments = medicaments.filter(stocks__pharmacie=p, stocks__disponible=False)
        elif filtre == "a_confirmer":
            medicaments = medicaments.filter(stocks__pharmacie=p, stocks__disponible=True,
                                             stocks__mis_a_jour_le__lt=limite)
        elif filtre == "absent":
            medicaments = medicaments.exclude(stocks__pharmacie=p)

        page = Paginator(medicaments, STOCK_PAR_PAGE).get_page(request.query_params.get("page"))
        stocks = {s.medicament_id: s for s in p.stocks.filter(medicament_id__in=[m.id for m in page])}
        return Response({
            "filtre": filtre, "q": q, "page": page.number, "pages": page.paginator.num_pages,
            "nb_a_confirmer": p.stocks.filter(disponible=True, mis_a_jour_le__lt=limite).count(),
            "lignes": [{
                "medicament": donnees.medicament(m),
                "stock": stock_json(stocks.get(m.id)),
                "a_confirmer": m.id in stocks and stocks[m.id].disponible and stocks[m.id].mis_a_jour_le < limite,
            } for m in page],
        })


class ModifierStockView(VuePharmacie):
    def post(self, request, medicament_id):
        medicament = get_object_or_404(Medicament, pk=medicament_id)
        disponible = request.data.get("disponible") in (True, "1", "true", 1)
        stock = _action(services.modifier_stock, self.pharmacie, medicament, disponible, request.data.get("prix", ""))
        return Response(stock_json(stock))


class PhotoView(VuePharmacie):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, medicament_id):
        medicament = get_object_or_404(Medicament, pk=medicament_id)
        _action(services.envoyer_photo, self.pharmacie, medicament, request.FILES.get("photo"))
        return Response({"medicament": donnees.medicament(medicament),
                         "message": f"Merci ! La photo de {medicament} est en ligne pour tous les patients."})


class ConfirmerStockView(VuePharmacie):
    def post(self, request):
        nb = services.confirmer_stock(self.pharmacie)
        return Response({"nb": nb, "message": f"{nb} produit(s) confirmé(s) disponibles. Merci !"})


class ProfilView(VuePharmacie):
    def get(self, request):
        p = self.pharmacie
        maintenant = timezone.now()
        return Response({
            "fiche": fiche_json(p),
            "gardes": [{"debut": g.debut, "fin": g.fin, "en_cours": g.debut <= maintenant < g.fin}
                       for g in p.gardes.filter(fin__gt=maintenant).order_by("debut")[:10]],
            "livreurs": [livreur_json(l) for l in p.livreurs.filter(actif=True)],
            "dossier_incomplet": bool(Dossier(p.pieces.all()).manquantes),
        })

    def post(self, request):
        p = self.pharmacie
        champs = ProfilForm.Meta.fields
        formulaire = ProfilForm({c: request.data.get(c, getattr(p, c)) for c in champs}, instance=p)
        if not formulaire.is_valid():
            raise erreur_formulaire(formulaire)
        formulaire.save()
        return Response({"fiche": fiche_json(p), "message": "Profil enregistré."})


class LivreursView(VuePharmacie):
    def post(self, request):
        livreur = _action(services.ajouter_livreur, self.pharmacie, request.data.get("nom"),
                          request.data.get("telephone"))
        return Response(livreur_json(livreur), status=status.HTTP_201_CREATED)


class RetirerLivreurView(VuePharmacie):
    def post(self, request, pk):
        services.retirer_livreur(self.pharmacie, pk)
        return Response({"message": "Livreur retiré."})


class SmsView(VuePharmacie):
    def post(self, request):
        return Response({"reponse": services.simuler_sms(self.pharmacie, str(request.data.get("texte", "")))})


class QuestionsView(VuePharmacie):
    def get(self, request):
        def question_json(q):
            return {"id": q.pk, "texte": q.texte, "cree_le": q.cree_le, "statut": q.statut,
                    "statut_libelle": q.get_statut_display(), "reponse": q.reponse,
                    "medicament": donnees.medicament(q.medicament) if q.medicament else None}

        return Response({
            "assistant_ia": assistant_actif(),
            "en_attente": [question_json(q) for q in Question.objects.filter(statut=Question.Statut.EN_ATTENTE)
                           .select_related("medicament").order_by("cree_le")[:30]],
            "mes_reponses": [question_json(q) for q in Question.objects.filter(repondu_par=self.pharmacie)
                             .select_related("medicament").order_by("-repondu_le")[:10]],
        })


class SuggestionView(VuePharmacie):
    """Brouillon de réponse proposé par l'assistant IA ; le pharmacien le relit avant d'envoyer."""

    def post(self, request, pk):
        question = get_object_or_404(Question.objects.select_related("medicament"), pk=pk,
                                     statut=Question.Statut.EN_ATTENTE)
        try:
            suggestion = suggerer_reponse(question)
        except AssistantIndisponible as e:
            return Response({"message": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"reponse": suggestion.reponse, "orienter": suggestion.orienter_medecin})


class RepondreView(VuePharmacie):
    def post(self, request, pk):
        orienter = request.data.get("orienter") in (True, "1", "true", 1)
        if not _action(services.repondre_question, self.pharmacie, pk, str(request.data.get("reponse", "")), orienter):
            return Response({"message": "Un confrère a déjà répondu à cette question."},
                            status=status.HTTP_409_CONFLICT)
        return Response({"message": "Réponse envoyée au patient. Merci !"})


class AbonnementView(VuePharmacie):
    def get(self, request):
        p = self.pharmacie
        return Response({
            "actif": abonnement_json(Abonnement.objects.actifs().filter(pharmacie=p).order_by("-fin").first()),
            "en_attente": abonnement_json(p.abonnements.filter(statut=Abonnement.Statut.EN_ATTENTE).first()),
            "historique": [abonnement_json(a) for a in p.abonnements.all()[:12]],
            "formules": services.formules_abonnement(),
            "durees": list(services.DUREES_ABONNEMENT),
            "numero_paiement": settings.DAWA_NUMERO_PAIEMENT,
        })

    def post(self, request):
        demande = _action(services.demander_abonnement, self.pharmacie, request.data.get("formule"),
                          request.data.get("mois"))
        return Response({"abonnement": abonnement_json(demande),
                         "message": f"Demande enregistrée. Payez avec la référence {demande.reference}."},
                        status=status.HTTP_201_CREATED)


class CommandesView(VuePharmacie):
    def get(self, request):
        commandes = self.pharmacie.commandes.select_related("grossiste").prefetch_related("lignes")[:30]
        return Response({
            "commandes": [commande_json(c) for c in commandes],
            "grossistes": [{"id": g.pk, "nom": g.nom, "delai_livraison": g.delai_livraison,
                            "minimum_commande": g.minimum_commande} for g in Grossiste.objects.filter(actif=True)],
        })


class GrossisteView(VuePharmacie):
    """Catalogue d'un grossiste (GET, recherche ?q=) et nouvelle commande (POST)."""

    def get(self, request, pk):
        grossiste = get_object_or_404(Grossiste, pk=pk, actif=True)
        offres = grossiste.offres.filter(disponible=True).select_related("medicament")
        q = request.query_params.get("q", "").strip()
        if len(q) >= 2:
            offres = offres.filter(medicament__in=rechercher_medicaments(q))
        ruptures = set(self.pharmacie.stocks.filter(disponible=False).values_list("medicament_id", flat=True))
        return Response({
            "grossiste": {"id": grossiste.pk, "nom": grossiste.nom, "delai_livraison": grossiste.delai_livraison,
                          "minimum_commande": grossiste.minimum_commande},
            "offres": [{"id": o.pk, "medicament": donnees.medicament(o.medicament), "conditionnement": o.conditionnement,
                        "prix": o.prix, "en_rupture_chez_moi": o.medicament_id in ruptures} for o in offres],
        })

    def post(self, request, pk):
        grossiste = get_object_or_404(Grossiste, pk=pk, actif=True)
        quantites = {}
        brutes = request.data.get("quantites") or {}
        if isinstance(brutes, dict):
            for cle, valeur in brutes.items():
                if str(cle).isdigit() and str(valeur).strip().isdigit() and int(valeur) > 0:
                    quantites[int(cle)] = int(valeur)
        commande = _action(services.creer_commande, self.pharmacie, grossiste, quantites,
                           str(request.data.get("note", "")))
        return Response({**commande_json(commande, detail=True),
                         "message": f"Commande n° {commande.pk} enregistrée. Envoyez-la au grossiste par WhatsApp."},
                        status=status.HTTP_201_CREATED)


class CommandeView(VuePharmacie):
    def _commande(self, pk):
        return get_object_or_404(Commande.objects.select_related("grossiste", "pharmacie"), pk=pk,
                                 pharmacie=self.pharmacie)

    def get(self, request, pk):
        return Response(commande_json(self._commande(pk), detail=True))

    def post(self, request, pk):
        commande = _action(services.changer_commande, self._commande(pk), request.data.get("action"))
        return Response({**commande_json(commande, detail=True),
                         "message": f"Commande n° {pk} : {commande.get_statut_display().lower()}."})


class DossierView(VuePharmacie):
    """Pièces justificatives (KYC) : accessible quel que soit le statut du compte, pour compléter le dossier."""

    compte_actif_requis = False
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        return Response({"statut": self.pharmacien.statut, "motif": self.pharmacien.motif,
                         "nom": self.pharmacie.nom, "dossier": donnees.dossier(self.pharmacie.pieces.all())})

    def post(self, request):
        donnees.enregistrer_piece(request, pharmacie=self.pharmacie)
        return Response({"message": "Document envoyé. L'équipe Uzima va le vérifier.",
                         "dossier": donnees.dossier(self.pharmacie.pieces.all())}, status=status.HTTP_201_CREATED)
