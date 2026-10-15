from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from catalogue.views import MedicamentViewSet
from config.views import JetonAppareilView
from conseil.views import QuestionViewSet
from pharmacies.views import PharmacieViewSet
from messagerie.views import MessageEntrantView
from reservations.views import DevisLivraisonView, ReservationViewSet
from sante.views import EtablissementViewSet
from stock.views import AlerteViewSet, RechercheView
from verification.views import SignalementViewSet, VerificationView

router = DefaultRouter()
router.register("medicaments", MedicamentViewSet, basename="medicament")
router.register("pharmacies", PharmacieViewSet, basename="pharmacie")
router.register("reservations", ReservationViewSet, basename="reservation")
router.register("alertes", AlerteViewSet, basename="alerte")
router.register("etablissements", EtablissementViewSet, basename="etablissement")
router.register("signalements", SignalementViewSet, basename="signalement")
router.register("questions", QuestionViewSet, basename="question")

admin.site.site_header = "Dawa — administration"
admin.site.site_title = "Dawa"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("portail/", include("portail.urls")),
    path("dawa/", include("gestion.urls")),
    path("etablissement/", include("sante.urls")),
    path("api/appareil/jeton/", JetonAppareilView.as_view(), name="jeton_appareil"),
    path("api/recherche/", RechercheView.as_view(), name="recherche"),
    path("api/verification/", VerificationView.as_view(), name="verification"),
    path("api/livraison/devis/", DevisLivraisonView.as_view(), name="devis_livraison"),
    path("api/messagerie/entrant/", MessageEntrantView.as_view(), name="messagerie_entrant"),
    path("api/", include(router.urls)),
]

if settings.DEBUG:
    # En production, les images sont servies par le serveur web (nginx) ou un stockage objet.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
