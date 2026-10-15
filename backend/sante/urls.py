from django.urls import path

from . import espace

app_name = "etablissement"

urlpatterns = [
    path("", espace.espace, name="espace"),
    path("inscription/", espace.inscription, name="inscription"),
]
