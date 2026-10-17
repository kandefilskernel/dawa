from django.urls import path

from . import compte, etablissement, pharmacie as ph

app_name = "pro_api"

urlpatterns = [
    path("compte/moi/", compte.MoiView.as_view(), name="moi"),
    path("compte/connexion/", compte.ConnexionView.as_view(), name="connexion"),
    path("compte/deconnexion/", compte.DeconnexionView.as_view(), name="deconnexion"),
    path("compte/mot-de-passe-oublie/", compte.MotDePasseOublieView.as_view(), name="mot_de_passe_oublie"),
    path("compte/mot-de-passe-nouveau/", compte.NouveauMotDePasseView.as_view(), name="mot_de_passe_nouveau"),
    path("compte/inscription/pharmacie/", compte.InscriptionPharmacieView.as_view(), name="inscription_pharmacie"),
    path("compte/inscription/etablissement/", compte.InscriptionEtablissementView.as_view(),
         name="inscription_etablissement"),

    # Portail pharmacie
    path("pharmacie/resume/", ph.ResumeView.as_view()),
    path("pharmacie/tableau/", ph.TableauView.as_view()),
    path("pharmacie/reservations/", ph.ReservationsView.as_view()),
    path("pharmacie/reservations/<int:pk>/statut/", ph.StatutReservationView.as_view()),
    path("pharmacie/stock/", ph.StockView.as_view()),
    path("pharmacie/stock/confirmer/", ph.ConfirmerStockView.as_view()),
    path("pharmacie/stock/<int:medicament_id>/", ph.ModifierStockView.as_view()),
    path("pharmacie/stock/<int:medicament_id>/photo/", ph.PhotoView.as_view()),
    path("pharmacie/profil/", ph.ProfilView.as_view()),
    path("pharmacie/livreurs/", ph.LivreursView.as_view()),
    path("pharmacie/livreurs/<int:pk>/retirer/", ph.RetirerLivreurView.as_view()),
    path("pharmacie/sms/", ph.SmsView.as_view()),
    path("pharmacie/questions/", ph.QuestionsView.as_view()),
    path("pharmacie/questions/<int:pk>/suggestion/", ph.SuggestionView.as_view()),
    path("pharmacie/questions/<int:pk>/repondre/", ph.RepondreView.as_view()),
    path("pharmacie/abonnement/", ph.AbonnementView.as_view()),
    path("pharmacie/commandes/", ph.CommandesView.as_view()),
    path("pharmacie/commandes/<int:pk>/", ph.CommandeView.as_view()),
    path("pharmacie/grossistes/<int:pk>/", ph.GrossisteView.as_view()),
    path("pharmacie/dossier/", ph.DossierView.as_view()),

    # Espace des établissements de santé
    path("etablissement/", etablissement.EspaceView.as_view()),
    path("etablissement/dossier/", etablissement.DossierView.as_view()),
]
