from django.urls import path

from kyc.views import telecharger_piece

from . import views

app_name = "gestion"

urlpatterns = [
    path("", views.tableau, name="tableau"),
    path("demandes/", views.demandes, name="demandes"),
    path("demandes/<str:genre>/<int:pk>/", views.decider_demande, name="decider_demande"),
    path("pieces/<int:pk>/", telecharger_piece, name="piece"),
    path("pieces/<int:pk>/verifier/", views.verifier_piece, name="verifier_piece"),
    path("pharmacies/", views.pharmacies, name="pharmacies"),
    path("pharmacies/<int:pk>/visibilite/", views.visibilite_pharmacie, name="visibilite_pharmacie"),
    path("etablissements/", views.etablissements, name="etablissements"),
    path("etablissements/<int:pk>/visibilite/", views.visibilite_etablissement, name="visibilite_etablissement"),
    path("comptes/<int:pk>/lien-mot-de-passe/", views.lien_mot_de_passe, name="lien_mot_de_passe"),
    path("abonnements/", views.abonnements, name="abonnements"),
    path("abonnements/<int:pk>/activer/", views.activer_abonnement, name="activer_abonnement"),
    path("signalements/", views.signalements, name="signalements"),
    path("signalements/<int:pk>/traiter/", views.traiter_signalement, name="traiter_signalement"),
]
