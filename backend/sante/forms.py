from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.gis.geos import Point
from django.db import transaction

from portail.forms import CENTRE_LUBUMBASHI

from .models import Etablissement, ResponsableEtablissement


class InscriptionEtablissementForm(UserCreationForm):
    """Inscription d'un hôpital, d'une clinique… : compte + fiche, en attente de validation Dawa."""

    nom = forms.CharField(label="Nom de l'établissement", max_length=150)
    type = forms.ChoiceField(label="Type", choices=Etablissement.Type.choices)
    numero_agrement = forms.CharField(label="Numéro d'autorisation de fonctionnement", max_length=50,
                                      help_text="Délivré par la Division provinciale de la santé. Dawa le vérifie.")
    telephone = forms.CharField(label="Téléphone", max_length=20)
    adresse = forms.CharField(label="Adresse", max_length=255)
    quartier = forms.CharField(label="Quartier", max_length=100, required=False)
    services = forms.CharField(label="Services", max_length=255, required=False,
                               help_text="Ex. pédiatrie, maternité, radiologie, analyses")
    urgences_24h = forms.BooleanField(label="Urgences ouvertes 24h/24", required=False)
    fonction = forms.CharField(label="Votre fonction", max_length=100, help_text="Ex. médecin directeur, administrateur")
    latitude = forms.FloatField(required=False, min_value=-90, max_value=90, widget=forms.HiddenInput)
    longitude = forms.FloatField(required=False, min_value=-180, max_value=180, widget=forms.HiddenInput)
    site_web = forms.CharField(required=False, widget=forms.HiddenInput)  # piège à robots

    field_order = ["nom", "type", "numero_agrement", "telephone", "adresse", "quartier", "services",
                   "urgences_24h", "fonction", "username", "password1", "password2"]

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ["username"]
        labels = {"username": "Identifiant de connexion"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("usable_password", None)
        for nom in ("password1", "password2"):
            self.fields[nom].required = True

    def clean_numero_agrement(self):
        numero = self.cleaned_data["numero_agrement"].strip()
        if Etablissement.objects.filter(numero_agrement__iexact=numero).exists():
            raise forms.ValidationError("Un établissement avec ce numéro est déjà inscrit. Contactez l'équipe Dawa.")
        return numero

    def clean(self):
        donnees = super().clean()
        if donnees.get("site_web"):
            raise forms.ValidationError("Inscription refusée.")
        return donnees

    @transaction.atomic
    def save(self, commit=True):
        utilisateur = super().save()
        d = self.cleaned_data
        lat, lng = d.get("latitude"), d.get("longitude")
        etablissement = Etablissement.objects.create(
            nom=d["nom"].strip(), type=d["type"], numero_agrement=d["numero_agrement"],
            telephone=d["telephone"].strip(), adresse=d["adresse"].strip(), quartier=d["quartier"].strip(),
            services=d["services"].strip(), urgences_24h=d["urgences_24h"], est_valide=False,
            position=Point(lng, lat, srid=4326) if lat is not None and lng is not None
            else Point(*CENTRE_LUBUMBASHI, srid=4326),
        )
        return ResponsableEtablissement.objects.create(
            utilisateur=utilisateur, etablissement=etablissement, fonction=d["fonction"].strip(),
            statut=ResponsableEtablissement.Statut.EN_ATTENTE,
        )


class FicheEtablissementForm(forms.ModelForm):
    class Meta:
        model = Etablissement
        fields = ["telephone", "adresse", "quartier", "services", "urgences_24h"]
        labels = {"telephone": "Téléphone", "adresse": "Adresse", "quartier": "Quartier", "services": "Services",
                  "urgences_24h": "Urgences ouvertes 24h/24"}
