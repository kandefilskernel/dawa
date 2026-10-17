from django.urls import path

from . import livreur

app_name = "livreur"

urlpatterns = [
    path("<uuid:jeton>/", livreur.page, name="page"),
    path("<uuid:jeton>/position/", livreur.position, name="position"),
    path("<uuid:jeton>/course/<int:pk>/livree/", livreur.livree, name="livree"),
]
