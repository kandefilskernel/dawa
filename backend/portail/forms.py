from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.gis.geos import Point
from django.db import transaction

from pharmacies.models import Pharmacie

from .models import Pharmacien

# (longitude, latitude) du centre-ville de Lubumbashi.
CENTRE_LUBUMBASHI = (27.479, -11.664)


class ProfilForm(forms.ModelForm):
    class Meta:
        model = Pharmacie
        fields = ["telephone", "whatsapp", "horaires", "adresse", "quartier"]
        labels = {
            "telephone": "Téléphone",
            "whatsapp": "WhatsApp",
            "horaires": "Horaires d'ouverture",
            "adresse": "Adresse",
            "quartier": "Quartier",
        }
        help_texts = {"horaires": "Ex. Lun–Sam 8h–20h, Dim 9h–13h"}


class InscriptionForm(UserCreationForm):
    """Inscription d'une pharmacie : compte + fiche de l'officine, en attente de validation Uzima."""

    nom = forms.CharField(label="Nom de la pharmacie", max_length=150)
    numero_agrement = forms.CharField(label="Numéro d'autorisation d'ouverture", max_length=50,
                                      help_text="Délivré par l'Inspection provinciale de la santé. Uzima le vérifie.")
    telephone = forms.CharField(label="Téléphone", max_length=20)
    whatsapp = forms.CharField(label="WhatsApp", max_length=20, required=False)
    adresse = forms.CharField(label="Adresse", max_length=255)
    quartier = forms.CharField(label="Quartier", max_length=100, required=False)
    commune = forms.CharField(label="Commune", max_length=100, required=False)
    horaires = forms.CharField(label="Horaires d'ouverture", max_length=255, required=False,
                               help_text="Ex. Lun–Sam 8h–20h")
    email = forms.EmailField(label="E-mail", help_text="Pour recevoir un lien si vous oubliez votre mot de passe.")
    latitude = forms.FloatField(required=False, min_value=-90, max_value=90, widget=forms.HiddenInput)
    longitude = forms.FloatField(required=False, min_value=-180, max_value=180, widget=forms.HiddenInput)
    # Piège à robots : champ caché que les humains laissent vide.
    site_web = forms.CharField(required=False, widget=forms.HiddenInput)

    field_order = ["nom", "numero_agrement", "telephone", "whatsapp", "adresse", "quartier", "commune",
                   "horaires", "email", "username", "password1", "password2"]

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ["username"]
        labels = {"username": "Identifiant de connexion"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Django 5.1 rend les mots de passe facultatifs (option « mot de passe inutilisable ») : pas ici.
        self.fields.pop("usable_password", None)
        for nom in ("password1", "password2"):
            self.fields[nom].required = True

    def clean_numero_agrement(self):
        numero = self.cleaned_data["numero_agrement"].strip()
        if Pharmacie.objects.filter(numero_agrement__iexact=numero).exists():
            raise forms.ValidationError("Une pharmacie avec ce numéro est déjà inscrite. Contactez l'équipe Uzima.")
        return numero

    def clean(self):
        donnees = super().clean()
        if donnees.get("site_web"):
            raise forms.ValidationError("Inscription refusée.")
        return donnees

    @transaction.atomic
    def save(self, commit=True):
        utilisateur = super().save(commit=False)
        utilisateur.email = self.cleaned_data["email"].strip().lower()
        utilisateur.save()
        d = self.cleaned_data
        lat, lng = d.get("latitude"), d.get("longitude")
        position_fournie = lat is not None and lng is not None
        pharmacie = Pharmacie.objects.create(
            nom=d["nom"].strip(), numero_agrement=d["numero_agrement"], telephone=d["telephone"].strip(),
            whatsapp=d["whatsapp"].strip(), adresse=d["adresse"].strip(), quartier=d["quartier"].strip(),
            commune=d["commune"].strip(), horaires=d["horaires"].strip(), est_validee=False,
            # Sans position, centre-ville : l'équipe Uzima la corrige avant de valider.
            position=Point(lng, lat, srid=4326) if position_fournie else Point(*CENTRE_LUBUMBASHI, srid=4326),
        )
        return Pharmacien.objects.create(utilisateur=utilisateur, pharmacie=pharmacie,
                                         statut=Pharmacien.Statut.EN_ATTENTE)
