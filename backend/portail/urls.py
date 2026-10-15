from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "portail"

urlpatterns = [
    path("", views.tableau_de_bord, name="tableau"),
    path("connexion/", auth_views.LoginView.as_view(template_name="portail/connexion.html"), name="connexion"),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="deconnexion"),
    path("reservations/", views.reservations, name="reservations"),
    path("reservations/<int:pk>/statut/", views.changer_statut_reservation, name="statut_reservation"),
    path("stock/", views.stock, name="stock"),
    path("stock/confirmer/", views.confirmer_stock, name="confirmer_stock"),
    path("stock/<int:medicament_id>/", views.modifier_stock, name="modifier_stock"),
    path("stock/<int:medicament_id>/photo/", views.envoyer_photo, name="envoyer_photo"),
    path("profil/", views.profil, name="profil"),
    path("profil/livreurs/", views.livreurs, name="livreurs"),
    path("abonnement/", views.abonnement, name="abonnement"),
    path("profil/tester-sms/", views.tester_sms, name="tester_sms"),
    path("commandes/", views.commandes, name="commandes"),
    path("commandes/<int:pk>/", views.commande, name="commande"),
    path("commandes/nouvelle/<int:grossiste_id>/", views.nouvelle_commande, name="nouvelle_commande"),
    path("questions/", views.questions, name="questions"),
    path("questions/<int:pk>/repondre/", views.repondre_question, name="repondre_question"),
    path("questions/<int:pk>/suggestion/", views.suggerer_reponse_question, name="suggerer_reponse"),
]
