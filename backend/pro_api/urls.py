from django.urls import path

from . import compte

app_name = "pro_api"

urlpatterns = [
    path("compte/moi/", compte.MoiView.as_view(), name="moi"),
    path("compte/connexion/", compte.ConnexionView.as_view(), name="connexion"),
    path("compte/deconnexion/", compte.DeconnexionView.as_view(), name="deconnexion"),
    path("compte/mot-de-passe-oublie/", compte.MotDePasseOublieView.as_view(), name="mot_de_passe_oublie"),
    path("compte/mot-de-passe-nouveau/", compte.NouveauMotDePasseView.as_view(), name="mot_de_passe_nouveau"),
]
